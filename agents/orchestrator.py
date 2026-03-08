"""
Multi-Agent Orchestrator (v2 — Safe Mode)
Applies via Greenhouse/Lever APIs only. No Selenium. No account bans.

Pipeline:
  Agent 1 (Scraper v2) -> Agent 2 (Applier v2) -> Agent 3 (Status Checker)
  Agent 4 (Excel Tracker) syncs continuously
  Agent 5 (Email Notifier) sends reports on schedule

Usage:
    python -m agents.orchestrator                # Run full cycle once
    python -m agents.orchestrator --daemon       # Run continuously 24/7
    python -m agents.orchestrator --scrape       # Scrape only
    python -m agents.orchestrator --apply        # Apply only
    python -m agents.orchestrator --status       # Check statuses only
    python -m agents.orchestrator --excel        # Sync Excel only
    python -m agents.orchestrator --email        # Send email report only
    python -m agents.orchestrator --prep <company>  # Send interview prep for specific company
    python -m agents.orchestrator --resume       # Parse and display resume analysis
"""
import sys
import os
import argparse
import time
import schedule
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.config import (
    SCRAPE_INTERVAL_HOURS, APPLY_INTERVAL_HOURS,
    STATUS_CHECK_INTERVAL_HOURS, EMAIL_REPORT_INTERVAL_HOURS,
    EXCEL_SYNC_INTERVAL_MINUTES, JobStatus,
)
from agents.logger import get_logger
from agents.job_database import get_stats, get_all_jobs

logger = get_logger("Orchestr")


def run_scraper():
    """Run Agent 1 (v2): Safe Job Scraper — Greenhouse/Lever APIs + RemoteOK."""
    from agents.agent_scraper_v2 import SafeJobScraperAgent
    agent = SafeJobScraperAgent()
    return agent.run()


def run_applier():
    """Run Agent 2 (v3): Playwright Job Applier — browser automation for Greenhouse/Lever forms."""
    from agents.agent_applier_v3 import PlaywrightJobApplierAgent
    agent = PlaywrightJobApplierAgent()
    return agent.run()


def run_status_checker():
    """Run Agent 3: Status Checker (email monitoring only, no Selenium)."""
    from agents.agent_status_checker import StatusCheckerAgent
    agent = StatusCheckerAgent(driver=None)
    return agent.run()


def run_excel_tracker():
    """Run Agent 4: Excel Tracker."""
    from agents.agent_excel_tracker import ExcelTrackerAgent
    agent = ExcelTrackerAgent()
    return agent.run()


def run_email_notifier():
    """Run Agent 5: Email Notifier."""
    from agents.agent_email_notifier import EmailNotifierAgent
    agent = EmailNotifierAgent()
    return agent.run()


def run_resume_analysis():
    """Parse and display resume analysis."""
    from agents.resume_parser import get_parsed_resume, get_all_skills_flat

    print("\n" + "=" * 60)
    print("  RESUME ANALYSIS")
    print("=" * 60)

    resume = get_parsed_resume()

    print(f"\n  Name:       {resume.get('name', 'N/A')}")
    print(f"  Title:      {resume.get('title', 'N/A')}")
    print(f"  Experience: {resume.get('years_experience', 'N/A')} years")
    print(f"  Email:      {resume.get('email', 'N/A')}")
    print(f"  Phone:      {resume.get('phone', 'N/A')}")

    skills = resume.get("skills", {})
    print(f"\n  Skills:")
    for category, skill_list in skills.items():
        if skill_list:
            print(f"    {category:25s} {', '.join(skill_list[:10])}")

    target = resume.get("target_roles", [])
    print(f"\n  Target Roles: {', '.join(target)}")

    if resume.get("summary"):
        print(f"\n  Summary: {resume['summary']}")

    all_skills = get_all_skills_flat()
    print(f"\n  Total skills found: {len(all_skills)}")
    print("=" * 60)


def run_interview_prep(company_name: str):
    """Run interview prep for a specific company."""
    from agents.agent_email_notifier import EmailNotifierAgent

    agent = EmailNotifierAgent()
    all_jobs = get_all_jobs()

    matched = [j for j in all_jobs if company_name.lower() in j.get("company", "").lower()]
    if not matched:
        logger.error(f"No jobs found for company: {company_name}")
        companies = sorted(set(j.get("company", "") for j in all_jobs if j.get("company")))
        if companies:
            logger.info("Available companies:\n  " + "\n  ".join(companies[:30]))
        return

    for job in matched:
        logger.info(f"Generating prep for: {job['title']} @ {job['company']}")
        agent._send_interview_prep(job)


def run_full_cycle():
    """Run all agents in sequence (one full cycle). No browser needed."""
    logger.info("\n" + "=" * 70)
    logger.info("  MULTI-AGENT JOB BOT - FULL CYCLE (Safe Mode)")
    logger.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("  Mode: Greenhouse/Lever APIs — No Selenium, No Bans")
    logger.info("=" * 70)

    results = {}

    try:
        # Phase 1: Scrape new jobs via APIs
        logger.info("\n" + "-" * 50)
        logger.info("PHASE 1: Scraping jobs from company career pages...")
        logger.info("-" * 50)
        new_jobs = run_scraper()
        results["scraper"] = {"new_jobs": new_jobs}

        # Phase 2: Apply to matched jobs via APIs
        logger.info("\n" + "-" * 50)
        logger.info("PHASE 2: Applying via Greenhouse/Lever APIs...")
        logger.info("-" * 50)
        apply_results = run_applier()
        results["applier"] = apply_results

        # Phase 3: Check statuses (email only)
        logger.info("\n" + "-" * 50)
        logger.info("PHASE 3: Checking application statuses...")
        logger.info("-" * 50)
        try:
            status_results = run_status_checker()
            results["status_checker"] = status_results
        except Exception as e:
            logger.warning(f"Status check skipped: {e}")
            results["status_checker"] = {}

        # Phase 4: Sync Excel
        logger.info("\n" + "-" * 50)
        logger.info("PHASE 4: Syncing Excel tracker...")
        logger.info("-" * 50)
        excel_results = run_excel_tracker()
        results["excel_tracker"] = excel_results

        # Phase 5: Send email reports
        logger.info("\n" + "-" * 50)
        logger.info("PHASE 5: Sending email notifications...")
        logger.info("-" * 50)
        try:
            email_results = run_email_notifier()
            results["email_notifier"] = email_results
        except Exception as e:
            logger.warning(f"Email skipped: {e}")
            results["email_notifier"] = {}

    except Exception as e:
        logger.error(f"Full cycle error: {e}")

    # Print summary
    stats = get_stats()
    logger.info("\n" + "=" * 70)
    logger.info("  CYCLE COMPLETE - SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  New jobs scraped:  {results.get('scraper', {}).get('new_jobs', 0)}")
    logger.info(f"  Jobs applied:      {results.get('applier', {}).get('applied', 0)}")
    logger.info(f"  Jobs failed:       {results.get('applier', {}).get('failed', 0)}")
    logger.info(f"  Manual apply:      {results.get('applier', {}).get('manual', 0)}")
    sc = results.get("status_checker", {})
    if isinstance(sc, dict) and sc:
        logger.info(f"  Status updates:    {sum(sc.values())}")
    logger.info(f"  Total in database: {stats['total']}")
    logger.info(f"  Applied today:     {stats['today_applied']}")
    logger.info("=" * 70)

    return results


def run_daemon():
    """Run continuously as a daemon with scheduled tasks. No browser needed."""
    logger.info("\n" + "=" * 70)
    logger.info("  MULTI-AGENT JOB BOT - DAEMON MODE (24/7 Safe)")
    logger.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Mode: Greenhouse/Lever APIs only")
    logger.info(f"  Scrape every:  {SCRAPE_INTERVAL_HOURS}h")
    logger.info(f"  Apply every:   {APPLY_INTERVAL_HOURS}h")
    logger.info(f"  Status every:  {STATUS_CHECK_INTERVAL_HOURS}h")
    logger.info(f"  Email every:   {EMAIL_REPORT_INTERVAL_HOURS}h")
    logger.info(f"  Excel every:   {EXCEL_SYNC_INTERVAL_MINUTES}min")
    logger.info("=" * 70)

    # Schedule tasks — all are safe API calls, no browser
    schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(_safe_run, run_scraper)
    schedule.every(APPLY_INTERVAL_HOURS).hours.do(_safe_run, run_applier)
    schedule.every(EXCEL_SYNC_INTERVAL_MINUTES).minutes.do(_safe_run, run_excel_tracker)
    schedule.every(STATUS_CHECK_INTERVAL_HOURS).hours.do(_safe_run, run_status_checker)
    schedule.every(EMAIL_REPORT_INTERVAL_HOURS).hours.do(_safe_run, run_email_notifier)

    # Run initial cycle
    logger.info("Running initial cycle...")
    _safe_run(run_scraper)
    _safe_run(run_applier)
    _safe_run(run_excel_tracker)

    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("\nDaemon stopped by user (Ctrl+C)")


def _safe_run(func, *args, **kwargs):
    """Run a function with error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in {func.__name__}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Job Application Bot (Safe Mode — API Only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agents.orchestrator                  # Full cycle (all 5 agents)
  python -m agents.orchestrator --daemon         # Run 24/7
  python -m agents.orchestrator --scrape         # Scrape from company career pages
  python -m agents.orchestrator --apply          # Apply via Greenhouse/Lever APIs
  python -m agents.orchestrator --status         # Check application statuses
  python -m agents.orchestrator --excel          # Sync Excel tracker
  python -m agents.orchestrator --email          # Send email report
  python -m agents.orchestrator --prep Google    # Interview prep for Google
  python -m agents.orchestrator --resume         # Show resume analysis
  python -m agents.orchestrator --stats          # Show statistics
        """
    )

    parser.add_argument("--daemon", action="store_true", help="Run 24/7 in daemon mode")
    parser.add_argument("--scrape", action="store_true", help="Scrape from company career pages")
    parser.add_argument("--apply", action="store_true", help="Apply via Greenhouse/Lever APIs")
    parser.add_argument("--status", action="store_true", help="Check application statuses")
    parser.add_argument("--excel", action="store_true", help="Sync Excel tracker")
    parser.add_argument("--email", action="store_true", help="Send email report")
    parser.add_argument("--prep", type=str, help="Generate interview prep for a company")
    parser.add_argument("--resume", action="store_true", help="Show resume analysis")
    parser.add_argument("--stats", action="store_true", help="Show current statistics")

    args = parser.parse_args()

    if args.stats:
        stats = get_stats()
        print("\n" + "=" * 50)
        print("  JOB BOT STATISTICS")
        print("=" * 50)
        print(f"  Total jobs:     {stats['total']}")
        print(f"  Applied today:  {stats['today_applied']}")
        print(f"\n  By Status:")
        for status, count in sorted(stats["by_status"].items()):
            print(f"    {status:25s} {count}")
        print(f"\n  By Platform:")
        for platform, count in sorted(stats["by_platform"].items()):
            print(f"    {platform:25s} {count}")
        print("=" * 50)
        return

    if args.resume:
        run_resume_analysis()
    elif args.daemon:
        run_daemon()
    elif args.scrape:
        run_scraper()
        run_excel_tracker()
    elif args.apply:
        run_applier()
        run_excel_tracker()
    elif args.status:
        run_status_checker()
        run_excel_tracker()
    elif args.excel:
        run_excel_tracker()
    elif args.email:
        run_email_notifier()
    elif args.prep:
        run_interview_prep(args.prep)
    else:
        run_full_cycle()


if __name__ == "__main__":
    main()
