"""
Shared Job Database - Central JSON store for all agents.
Thread-safe read/write operations for the job pipeline.
"""
import json
import os
import threading
from datetime import datetime
from typing import List, Dict, Optional
from agents.config import JOB_DB_PATH, JobStatus

_lock = threading.Lock()


def _load_db() -> dict:
    if os.path.exists(JOB_DB_PATH):
        with open(JOB_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle raw list format (migration)
            if isinstance(data, list):
                return {"jobs": data, "metadata": {"created": datetime.now().isoformat(), "last_updated": ""}}
            return data
    return {"jobs": [], "metadata": {"created": datetime.now().isoformat(), "last_updated": ""}}


def _save_db(db: dict):
    db["metadata"]["last_updated"] = datetime.now().isoformat()
    with open(JOB_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, default=str, ensure_ascii=False)


def add_job(job: dict) -> bool:
    """Add a scraped job to the database. Returns False if duplicate."""
    with _lock:
        db = _load_db()
        # Check duplicates by URL or job_id + platform
        for existing in db["jobs"]:
            if job.get("url") and existing.get("url") == job.get("url"):
                return False
            if existing.get("job_id") and existing.get("job_id") == job.get("job_id") and existing.get("platform") == job.get("platform"):
                return False
        _prepare_job(job)
        db["jobs"].append(job)
        _save_db(db)
        return True


def add_jobs_bulk(jobs: list) -> int:
    """Add many jobs at once in a single write. Returns count of actually added jobs."""
    with _lock:
        db = _load_db()
        existing_urls = set(j.get("url", "") for j in db["jobs"])
        added = 0
        for job in jobs:
            url = job.get("url", "")
            if url and url in existing_urls:
                continue
            _prepare_job(job)
            db["jobs"].append(job)
            existing_urls.add(url)
            added += 1
        _save_db(db)
        return added


def _prepare_job(job: dict):
    """Set default fields on a job dict."""
    job.setdefault("status", JobStatus.SCRAPED)
    job.setdefault("scraped_at", datetime.now().isoformat())
    job.setdefault("applied_at", "")
    job.setdefault("last_checked", "")
    job.setdefault("rounds", [])
    job.setdefault("tech_stack", [])
    job.setdefault("notes", "")
    job.setdefault("interview_prep_sent", False)


def update_job(job_id: str, platform: str, updates: dict) -> bool:
    """Update fields for an existing job."""
    with _lock:
        db = _load_db()
        for job in db["jobs"]:
            if job.get("job_id") == job_id and job.get("platform") == platform:
                job.update(updates)
                job["last_checked"] = datetime.now().isoformat()
                _save_db(db)
                return True
        return False


def update_job_status(url_or_id: str, new_status: str, platform: str = None, **extra_fields) -> bool:
    """Update the status of a job by URL or by job_id+platform."""
    with _lock:
        db = _load_db()
        for job in db["jobs"]:
            # Match by URL first
            if job.get("url") == url_or_id:
                job["status"] = new_status
                job["last_checked"] = datetime.now().isoformat()
                job.update(extra_fields)
                _save_db(db)
                return True
            # Fallback: match by job_id + platform
            if platform and job.get("job_id") == url_or_id and job.get("platform") == platform:
                job["status"] = new_status
                job["last_checked"] = datetime.now().isoformat()
                job.update(extra_fields)
                _save_db(db)
                return True
        return False


def add_round(job_id: str, platform: str, round_info: dict) -> bool:
    """Add an interview round to a job."""
    with _lock:
        db = _load_db()
        for job in db["jobs"]:
            if job.get("job_id") == job_id and job.get("platform") == platform:
                if "rounds" not in job:
                    job["rounds"] = []
                round_info["added_at"] = datetime.now().isoformat()
                job["rounds"].append(round_info)
                _save_db(db)
                return True
        return False


def get_jobs_by_status(status: str) -> List[dict]:
    """Get all jobs with a given status."""
    db = _load_db()
    return [j for j in db["jobs"] if j.get("status") == status]


def get_jobs_by_platform(platform: str) -> List[dict]:
    """Get all jobs from a specific platform."""
    db = _load_db()
    return [j for j in db["jobs"] if j.get("platform") == platform]


def get_all_jobs() -> List[dict]:
    """Get every job in the database."""
    db = _load_db()
    return db["jobs"]


def get_job(job_id: str, platform: str) -> Optional[dict]:
    """Get a single job by ID and platform."""
    db = _load_db()
    for job in db["jobs"]:
        if job.get("job_id") == job_id and job.get("platform") == platform:
            return job
    return None


def get_unapplied_jobs() -> List[dict]:
    """Get jobs that are scraped but not yet applied to."""
    return get_jobs_by_status(JobStatus.SCRAPED)


def get_applied_jobs() -> List[dict]:
    """Get all applied jobs (for status tracking)."""
    db = _load_db()
    active_statuses = [
        JobStatus.APPLIED, JobStatus.SCREENING, JobStatus.PHONE_SCREEN,
        JobStatus.TECHNICAL_ROUND, JobStatus.ONSITE, JobStatus.FINAL_ROUND,
    ]
    return [j for j in db["jobs"] if j.get("status") in active_statuses]


def get_stats() -> dict:
    """Get summary statistics."""
    db = _load_db()
    jobs = db["jobs"]
    stats = {
        "total": len(jobs),
        "by_status": {},
        "by_platform": {},
        "today_applied": 0,
    }
    today = datetime.now().strftime("%Y-%m-%d")
    for job in jobs:
        s = job.get("status", "unknown")
        p = job.get("platform", "unknown")
        stats["by_status"][s] = stats["by_status"].get(s, 0) + 1
        stats["by_platform"][p] = stats["by_platform"].get(p, 0) + 1
        if job.get("applied_at", "").startswith(today):
            stats["today_applied"] += 1
    return stats
