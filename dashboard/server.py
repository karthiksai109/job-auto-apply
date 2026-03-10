"""
FastAPI Backend Server for the Agentic AI Job Application Dashboard.
Bridges the Next.js frontend with the multi-agent system.
"""
import os
import sys
import json
import asyncio
import smtplib
import threading
import time
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent dir so we can import agents
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.config import (
    RESUME_PATH, PERSONAL_INFO, JobStatus, DAILY_TARGET,
    JOB_DB_PATH, SMTP_SERVER, SMTP_PORT, EMAIL_SENDER,
    EMAIL_PASSWORD, EMAIL_RECIPIENT, MIN_MATCH_SCORE,
    SCRAPE_INTERVAL_HOURS, APPLY_INTERVAL_HOURS,
)
from agents.job_database import get_jobs_by_status, get_stats, update_job_status
from agents.resume_parser import get_parsed_resume, get_all_skills_flat
from agents.job_matcher import score_job
from agents.agent_job_fit import analyze_job_fit, get_all_reports as get_fit_reports, get_report_for_job
from agents.agent_interview_prep import generate_interview_prep, get_all_guides, get_guide_for_job
from agents.agent_profile_marketer import analyze_profile, get_profile_report

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
agent_states = {
    "scraper": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "applier": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "matcher": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "tracker": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "notifier": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "fit_analyst": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "interview_prep": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "profile_marketer": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "scheduler": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
}

_scheduler_running = False
_scheduler_thread = None

ws_clients: list[WebSocket] = []
_apply_lock = threading.Lock()

REJECT_TITLE_KEYWORDS = [
    "senior", "staff", "principal", "lead ", "manager", "director",
    "head of", "vp ", "vice president", "architect",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(agent: str, msg: str, level: str = "info"):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = {"ts": ts, "level": level, "msg": msg}
    agent_states[agent]["logs"].append(entry)
    # keep last 200 logs
    agent_states[agent]["logs"] = agent_states[agent]["logs"][-200:]


def _load_db():
    try:
        with open(JOB_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"jobs": [], "metadata": {}}


def _get_filtered_jobs(status="scraped"):
    """Get jobs filtered for junior/entry/intern level only."""
    db = _load_db()
    jobs = [j for j in db.get("jobs", []) if j.get("status") == status]
    filtered = []
    for j in jobs:
        title_lower = j.get("title", "").lower()
        if any(kw in title_lower for kw in REJECT_TITLE_KEYWORDS):
            continue
        if j.get("match_score", 0) < MIN_MATCH_SCORE:
            continue
        filtered.append(j)
    # dedup
    seen = set()
    unique = []
    for j in filtered:
        key = (j.get("title", "").strip().lower(), j.get("company", "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(j)
    unique.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    return unique


def _send_completion_email(applied_count: int, failed_count: int, jobs_applied: list):
    """Send email notification when a batch is complete."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENT:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚀 Job Auto-Apply: {applied_count} Applications Submitted"
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECIPIENT

        job_rows = ""
        for j in jobs_applied[:30]:
            job_rows += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #eee;">{j.get('title','?')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;">{j.get('company','?')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;">{j.get('match_score','?')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;">✓ Applied</td>
            </tr>"""

        html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width:700px; margin:0 auto; padding:20px;">
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color:white; padding:30px; border-radius:12px; margin-bottom:20px;">
                <h1 style="margin:0;">🤖 Job Auto-Apply Report</h1>
                <p style="opacity:0.8; margin-top:8px;">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            <div style="background:#f8fafc; padding:20px; border-radius:8px; margin-bottom:20px;">
                <h2 style="margin-top:0;">📊 Batch Summary</h2>
                <p><strong>✅ Applied:</strong> {applied_count}</p>
                <p><strong>❌ Failed:</strong> {failed_count}</p>
                <p><strong>📋 Total in Database:</strong> {len(_load_db().get('jobs',[]))}</p>
            </div>
            <h2>📝 Applications Submitted</h2>
            <table style="width:100%; border-collapse:collapse;">
                <thead>
                    <tr style="background:#0f172a; color:white;">
                        <th style="padding:8px; text-align:left;">Title</th>
                        <th style="padding:8px; text-align:left;">Company</th>
                        <th style="padding:8px; text-align:left;">Score</th>
                        <th style="padding:8px; text-align:left;">Status</th>
                    </tr>
                </thead>
                <tbody>{job_rows}</tbody>
            </table>
            <p style="color:#64748b; margin-top:20px; font-size:13px;">
                Sent by Karthik's Agentic AI Job Application System
            </p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        return True
    except Exception as e:
        _log("notifier", f"Email failed: {e}", "error")
        return False


# ---------------------------------------------------------------------------
# Apply engine (runs in background thread)
# ---------------------------------------------------------------------------

def _run_apply_batch(batch_size: int = 30):
    """Run a batch of applications using Playwright."""
    if not _apply_lock.acquire(blocking=False):
        _log("applier", "Already running a batch", "warn")
        return

    try:
        agent_states["applier"]["status"] = "running"
        _log("applier", f"Starting batch of {batch_size} applications...")

        eligible = _get_filtered_jobs("scraped")
        if not eligible:
            _log("applier", "No eligible jobs to apply to", "warn")
            agent_states["applier"]["status"] = "idle"
            return

        _log("applier", f"Found {len(eligible)} eligible jobs (junior/entry/intern, score≥60)")

        import logging
        from agents.agent_applier_v3 import PlaywrightJobApplierAgent
        from agents.config import HEADLESS, SLOW_MO
        from playwright.sync_api import sync_playwright

        # Hook applier logger to dashboard logs
        class DashboardLogHandler(logging.Handler):
            def emit(self, record):
                level = "error" if record.levelno >= logging.ERROR else "warn" if record.levelno >= logging.WARNING else "info"
                _log("applier", record.getMessage(), level)

        applier_logger = logging.getLogger("Applier_v3")
        dash_handler = DashboardLogHandler()
        applier_logger.addHandler(dash_handler)

        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=int(SLOW_MO * 1000) if SLOW_MO < 5 else int(SLOW_MO),
        )

        applied_count = 0
        failed_count = 0
        jobs_applied = []
        applier = PlaywrightJobApplierAgent()
        applier.pw = pw
        applier.browser = browser

        _log("applier", f"Resume path: {os.path.exists(RESUME_PATH)} ({RESUME_PATH})")

        for i, job in enumerate(eligible[:batch_size]):
            title = job.get("title", "?")
            company = job.get("company", "?")
            score = job.get("match_score", "?")
            ats = job.get("ats_type", "")

            _log("applier", f"[{i+1}/{min(batch_size, len(eligible))}] Applying: {title} @ {company} [{score}] ({ats})")
            agent_states["applier"]["stats"] = {
                "current_job": f"{title} @ {company}",
                "progress": i + 1,
                "total": min(batch_size, len(eligible)),
                "applied": applied_count,
                "failed": failed_count,
            }

            try:
                if ats == "greenhouse":
                    success = applier._apply_greenhouse(job)
                elif ats == "lever":
                    success = applier._apply_lever(job)
                else:
                    update_job_status(job["url"], "manual_apply_needed")
                    _log("applier", f"  → Manual: {title} @ {company} (ats={ats})", "warn")
                    continue

                if success:
                    applied_count += 1
                    update_job_status(job["url"], JobStatus.APPLIED, applied_date=datetime.now().isoformat())
                    _log("applier", f"  ✓ Applied: {title} @ {company} [{score}]")
                    jobs_applied.append(job)
                else:
                    failed_count += 1
                    update_job_status(job["url"], JobStatus.FAILED_TO_APPLY)
                    _log("applier", f"  ✗ Failed: {title} @ {company}", "error")

                time.sleep(3)
            except Exception as e:
                failed_count += 1
                update_job_status(job["url"], JobStatus.FAILED_TO_APPLY)
                _log("applier", f"  Error: {title} @ {company}: {e}", "error")

        # Remove dashboard handler
        applier_logger.removeHandler(dash_handler)

        browser.close()
        pw.stop()

        agent_states["applier"]["status"] = "idle"
        agent_states["applier"]["last_run"] = datetime.now().isoformat()
        agent_states["applier"]["stats"] = {
            "applied": applied_count,
            "failed": failed_count,
            "total": applied_count + failed_count,
            "jobs_applied": [{"title": j.get("title"), "company": j.get("company"), "score": j.get("match_score")} for j in jobs_applied],
        }

        _log("applier", f"Batch complete: {applied_count} applied, {failed_count} failed")

        # Sync to Excel immediately
        _run_excel_sync()

        # Send email notification
        _log("notifier", "Sending completion email...")
        agent_states["notifier"]["status"] = "running"
        sent = _send_completion_email(applied_count, failed_count, jobs_applied)
        agent_states["notifier"]["status"] = "idle"
        if sent:
            _log("notifier", f"Email sent: {applied_count} applications reported")
        else:
            _log("notifier", "Email not configured or failed", "warn")

    finally:
        _apply_lock.release()


def _run_excel_sync():
    """Sync job database to Excel spreadsheet."""
    try:
        agent_states["tracker"]["status"] = "running"
        _log("tracker", "Syncing to Excel...")
        from agents.agent_excel_tracker import ExcelTrackerAgent
        tracker = ExcelTrackerAgent()
        result = tracker.run()
        agent_states["tracker"]["stats"] = result
        agent_states["tracker"]["last_run"] = datetime.now().isoformat()
        _log("tracker", f"Excel synced: {result.get('total_jobs', 0)} jobs written to {result.get('file', '')}")
    except Exception as e:
        _log("tracker", f"Excel sync error: {e}", "error")
    finally:
        agent_states["tracker"]["status"] = "idle"


def _run_scraper():
    """Run the scraper agent."""
    agent_states["scraper"]["status"] = "running"
    _log("scraper", "Starting scraper...")
    try:
        from agents.agent_scraper_v2 import SafeJobScraperAgent
        agent = SafeJobScraperAgent()
        result = agent.run()
        agent_states["scraper"]["stats"] = result
        _log("scraper", f"Scraper done: {result.get('new_jobs', 0)} new jobs")
        # Auto-sync to Excel after scraping
        _run_excel_sync()
    except Exception as e:
        _log("scraper", f"Scraper error: {e}", "error")
    finally:
        agent_states["scraper"]["status"] = "idle"
        agent_states["scraper"]["last_run"] = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Agentic AI Job Application System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- API Routes --

@app.get("/api/stats")
def api_stats():
    db = _load_db()
    all_jobs = db.get("jobs", [])
    today_str = date.today().isoformat()

    scraped = len([j for j in all_jobs if j.get("status") == "scraped"])
    applied = len([j for j in all_jobs if j.get("status") == "applied"])
    applied_today = len([j for j in all_jobs if j.get("status") == "applied" and j.get("applied_date", "").startswith(today_str)])
    failed = len([j for j in all_jobs if j.get("status") == "failed_to_apply"])
    manual = len([j for j in all_jobs if j.get("status") == "manual_apply_needed"])
    eligible = len(_get_filtered_jobs("scraped"))

    return {
        "total_jobs": len(all_jobs),
        "scraped": scraped,
        "applied": applied,
        "applied_today": applied_today,
        "failed": failed,
        "manual": manual,
        "eligible_to_apply": eligible,
        "daily_target": DAILY_TARGET,
        "remaining_today": max(0, DAILY_TARGET - applied_today),
    }


@app.get("/api/jobs")
def api_jobs(status: Optional[str] = None, limit: int = 100, offset: int = 0):
    db = _load_db()
    jobs = db.get("jobs", [])
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    total = len(jobs)
    jobs = jobs[offset:offset + limit]
    # slim down for API
    slim = []
    for j in jobs:
        slim.append({
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "url": j.get("url", ""),
            "match_score": j.get("match_score", 0),
            "match_reason": j.get("match_reason", ""),
            "matched_skills": j.get("matched_skills", []),
            "missing_skills": j.get("missing_skills", []),
            "status": j.get("status", ""),
            "ats_type": j.get("ats_type", ""),
            "applied_date": j.get("applied_date", ""),
        })
    return {"jobs": slim, "total": total}


@app.get("/api/jobs/eligible")
def api_eligible_jobs():
    eligible = _get_filtered_jobs("scraped")
    slim = []
    for j in eligible:
        slim.append({
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "url": j.get("url", ""),
            "match_score": j.get("match_score", 0),
            "match_reason": j.get("match_reason", ""),
            "matched_skills": j.get("matched_skills", []),
            "missing_skills": j.get("missing_skills", []),
            "ats_type": j.get("ats_type", ""),
        })
    return {"jobs": slim, "total": len(slim)}


@app.get("/api/agents")
def api_agents():
    return agent_states


@app.get("/api/resume")
def api_resume():
    resume = get_parsed_resume()
    skills_flat = get_all_skills_flat()
    return {
        "name": resume.get("name", ""),
        "title": resume.get("title", ""),
        "years_experience": resume.get("years_experience", 0),
        "target_roles": resume.get("target_roles", []),
        "skills": resume.get("skills", {}),
        "skills_flat": skills_flat,
        "education": resume.get("education", []),
        "summary": resume.get("summary", ""),
    }


@app.post("/api/apply")
def api_apply(background_tasks: BackgroundTasks, batch_size: int = 30):
    if agent_states["applier"]["status"] == "running":
        return {"error": "Applier is already running", "status": "running"}
    background_tasks.add_task(_run_apply_batch, batch_size)
    return {"status": "started", "batch_size": batch_size}


@app.post("/api/scrape")
def api_scrape(background_tasks: BackgroundTasks):
    if agent_states["scraper"]["status"] == "running":
        return {"error": "Scraper is already running", "status": "running"}
    background_tasks.add_task(_run_scraper)
    return {"status": "started"}


@app.post("/api/excel-sync")
def api_excel_sync(background_tasks: BackgroundTasks):
    if agent_states["tracker"]["status"] == "running":
        return {"error": "Tracker is already running", "status": "running"}
    background_tasks.add_task(_run_excel_sync)
    return {"status": "started"}


@app.get("/api/applied")
def api_applied_jobs():
    db = _load_db()
    jobs = [j for j in db.get("jobs", []) if j.get("status") == "applied"]
    jobs.sort(key=lambda j: j.get("applied_date", ""), reverse=True)
    slim = []
    for j in jobs:
        slim.append({
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "url": j.get("url", ""),
            "match_score": j.get("match_score", 0),
            "ats_type": j.get("ats_type", ""),
            "applied_date": j.get("applied_date", ""),
            "match_reason": j.get("match_reason", ""),
        })
    return {"jobs": slim, "total": len(slim)}


# ---------------------------------------------------------------------------
# New Agent API Routes
# ---------------------------------------------------------------------------

@app.get("/api/fit-reports")
def api_fit_reports():
    """Get all job fit analysis reports."""
    reports = get_fit_reports()
    reports.sort(key=lambda r: r.get("analyzed_at", ""), reverse=True)
    return {"reports": reports, "total": len(reports)}


@app.get("/api/fit-report")
def api_fit_report(url: str):
    """Get fit report for a specific job."""
    report = get_report_for_job(url)
    if report:
        return report
    return {"error": "No report found for this job"}


@app.post("/api/analyze-fit")
def api_analyze_fit(background_tasks: BackgroundTasks):
    """Run fit analysis on all applied jobs that don't have reports yet."""
    def _run_fit_analysis():
        agent_states["fit_analyst"]["status"] = "running"
        _log("fit_analyst", "Running fit analysis on applied jobs...")
        try:
            db = _load_db()
            applied = [j for j in db.get("jobs", []) if j.get("status") == "applied"]
            existing = {r.get("url") for r in get_fit_reports()}
            new_count = 0
            for job in applied:
                if job.get("url") not in existing:
                    analyze_job_fit(job)
                    new_count += 1
            _log("fit_analyst", f"Analyzed {new_count} new jobs")
            agent_states["fit_analyst"]["stats"] = {"analyzed": new_count}
        except Exception as e:
            _log("fit_analyst", f"Error: {e}", "error")
        finally:
            agent_states["fit_analyst"]["status"] = "idle"
            agent_states["fit_analyst"]["last_run"] = datetime.now().isoformat()

    background_tasks.add_task(_run_fit_analysis)
    return {"status": "started"}


@app.get("/api/interview-prep")
def api_interview_guides():
    """Get all interview prep guides."""
    guides = get_all_guides()
    guides.sort(key=lambda g: g.get("generated_at", ""), reverse=True)
    return {"guides": guides, "total": len(guides)}


@app.get("/api/interview-prep/job")
def api_interview_guide(url: str):
    """Get interview prep for a specific job."""
    guide = get_guide_for_job(url)
    if guide:
        return guide
    return {"error": "No guide found for this job"}


@app.post("/api/generate-prep")
def api_generate_prep(background_tasks: BackgroundTasks):
    """Generate interview prep for all applied jobs without guides."""
    def _run_prep():
        agent_states["interview_prep"]["status"] = "running"
        _log("interview_prep", "Generating interview prep guides...")
        try:
            db = _load_db()
            applied = [j for j in db.get("jobs", []) if j.get("status") == "applied"]
            existing = {g.get("url") for g in get_all_guides()}
            new_count = 0
            for job in applied:
                if job.get("url") not in existing:
                    generate_interview_prep(job)
                    new_count += 1
            _log("interview_prep", f"Generated {new_count} new prep guides")
            agent_states["interview_prep"]["stats"] = {"generated": new_count}
        except Exception as e:
            _log("interview_prep", f"Error: {e}", "error")
        finally:
            agent_states["interview_prep"]["status"] = "idle"
            agent_states["interview_prep"]["last_run"] = datetime.now().isoformat()

    background_tasks.add_task(_run_prep)
    return {"status": "started"}


@app.get("/api/profile")
def api_profile():
    """Get profile marketing analysis."""
    return get_profile_report()


@app.post("/api/analyze-profile")
def api_analyze_profile_route(background_tasks: BackgroundTasks):
    """Run profile marketing analysis."""
    def _run():
        agent_states["profile_marketer"]["status"] = "running"
        _log("profile_marketer", "Analyzing profile...")
        try:
            result = analyze_profile()
            agent_states["profile_marketer"]["stats"] = {
                "strength": result.get("profile_strength", 0),
                "recruiter_score": result.get("recruiter_attraction_score", 0),
            }
            _log("profile_marketer", f"Profile strength: {result.get('profile_strength')}%")
        except Exception as e:
            _log("profile_marketer", f"Error: {e}", "error")
        finally:
            agent_states["profile_marketer"]["status"] = "idle"
            agent_states["profile_marketer"]["last_run"] = datetime.now().isoformat()

    background_tasks.add_task(_run)
    return {"status": "started"}


# ---------------------------------------------------------------------------
# 24/7 Scheduler
# ---------------------------------------------------------------------------

def _scheduler_loop():
    """Continuous scheduler: scrape + apply on intervals, 24/7."""
    global _scheduler_running
    _log("scheduler", f"🚀 24/7 Scheduler started — scrape every {SCRAPE_INTERVAL_HOURS}h, apply every {APPLY_INTERVAL_HOURS}h")
    agent_states["scheduler"]["status"] = "running"

    last_scrape = 0
    last_apply = 0
    cycle = 0

    while _scheduler_running:
        now = time.time()
        cycle += 1

        # Scrape new jobs
        if now - last_scrape >= SCRAPE_INTERVAL_HOURS * 3600:
            _log("scheduler", f"[Cycle {cycle}] Scraping new jobs...")
            try:
                _run_scraper()
                last_scrape = time.time()
            except Exception as e:
                _log("scheduler", f"Scraper error: {e}", "error")

        # Apply to eligible jobs
        if now - last_apply >= APPLY_INTERVAL_HOURS * 3600:
            eligible = _get_filtered_jobs("scraped")
            if eligible:
                _log("scheduler", f"[Cycle {cycle}] Applying to {len(eligible)} eligible jobs...")
                try:
                    _run_apply_batch(min(50, len(eligible)))
                    last_apply = time.time()

                    # Auto-generate fit reports and interview prep for newly applied jobs
                    db = _load_db()
                    applied = [j for j in db.get("jobs", []) if j.get("status") == "applied"]
                    existing_fit = {r.get("url") for r in get_fit_reports()}
                    existing_prep = {g.get("url") for g in get_all_guides()}
                    for job in applied:
                        url = job.get("url")
                        if url and url not in existing_fit:
                            try:
                                analyze_job_fit(job)
                            except:
                                pass
                        if url and url not in existing_prep:
                            try:
                                generate_interview_prep(job)
                            except:
                                pass
                except Exception as e:
                    _log("scheduler", f"Apply error: {e}", "error")
            else:
                _log("scheduler", f"[Cycle {cycle}] No eligible jobs to apply to")

        agent_states["scheduler"]["stats"] = {
            "cycle": cycle,
            "last_scrape": datetime.fromtimestamp(last_scrape).isoformat() if last_scrape else "never",
            "last_apply": datetime.fromtimestamp(last_apply).isoformat() if last_apply else "never",
        }

        # Sleep 5 minutes between checks
        for _ in range(60):
            if not _scheduler_running:
                break
            time.sleep(5)

    agent_states["scheduler"]["status"] = "idle"
    _log("scheduler", "Scheduler stopped")


@app.post("/api/scheduler/start")
def api_start_scheduler(background_tasks: BackgroundTasks):
    """Start the 24/7 scheduler."""
    global _scheduler_running, _scheduler_thread
    if _scheduler_running:
        return {"status": "already_running"}
    _scheduler_running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()
    return {"status": "started"}


@app.post("/api/scheduler/stop")
def api_stop_scheduler():
    """Stop the 24/7 scheduler."""
    global _scheduler_running
    _scheduler_running = False
    _log("scheduler", "Stop requested...")
    return {"status": "stopping"}


@app.get("/api/scheduler/status")
def api_scheduler_status():
    """Get scheduler status."""
    return {
        "running": _scheduler_running,
        "status": agent_states["scheduler"]["status"],
        "stats": agent_states["scheduler"]["stats"],
        "logs": agent_states["scheduler"]["logs"][-20:],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
