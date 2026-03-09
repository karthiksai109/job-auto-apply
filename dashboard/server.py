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
    EMAIL_PASSWORD, EMAIL_RECIPIENT,
)
from agents.job_database import get_jobs_by_status, get_stats, update_job_status
from agents.resume_parser import get_parsed_resume, get_all_skills_flat
from agents.job_matcher import score_job

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
agent_states = {
    "scraper": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "applier": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "matcher": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "tracker": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
    "notifier": {"status": "idle", "logs": [], "last_run": None, "stats": {}},
}

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
        if j.get("match_score", 0) < 60:
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

        from agents.agent_applier_v3 import PlaywrightJobApplierAgent
        from agents.config import HEADLESS, SLOW_MO
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            slow_mo=int(SLOW_MO * 1000) if SLOW_MO < 5 else int(SLOW_MO),
        )

        applied_count = 0
        failed_count = 0
        jobs_applied = []
        applier = PlaywrightJobApplierAgent()
        applier.pw = pw
        applier.browser = browser

        for i, job in enumerate(eligible[:batch_size]):
            title = job.get("title", "?")
            company = job.get("company", "?")
            score = job.get("match_score", "?")
            ats = job.get("ats_type", "")

            _log("applier", f"[{i+1}/{min(batch_size, len(eligible))}] Applying: {title} @ {company} [{score}]")
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
                    _log("applier", f"  → Manual: {title} @ {company}", "warn")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
