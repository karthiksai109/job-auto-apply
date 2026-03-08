"""
Application Tracker - Tracks all jobs applied to, avoids duplicates.
"""
import json
import os
from datetime import datetime
from config import TRACKER_DB


def load_tracker():
    if os.path.exists(TRACKER_DB):
        with open(TRACKER_DB, "r") as f:
            return json.load(f)
    return {"applied": [], "failed": [], "stats": {}}


def save_tracker(data):
    with open(TRACKER_DB, "w") as f:
        json.dump(data, f, indent=2, default=str)


def is_already_applied(job_id: str, platform: str) -> bool:
    tracker = load_tracker()
    for job in tracker["applied"]:
        if job.get("job_id") == job_id and job.get("platform") == platform:
            return True
    return False


def record_application(job_data: dict):
    tracker = load_tracker()
    job_data["applied_at"] = datetime.now().isoformat()
    tracker["applied"].append(job_data)

    # Update stats
    date_key = datetime.now().strftime("%Y-%m-%d")
    if date_key not in tracker["stats"]:
        tracker["stats"][date_key] = {"total": 0, "linkedin": 0, "indeed": 0, "dice": 0}
    tracker["stats"][date_key]["total"] += 1
    platform = job_data.get("platform", "unknown")
    if platform in tracker["stats"][date_key]:
        tracker["stats"][date_key][platform] += 1

    save_tracker(tracker)


def record_failure(job_data: dict, error: str):
    tracker = load_tracker()
    job_data["failed_at"] = datetime.now().isoformat()
    job_data["error"] = error
    tracker["failed"].append(job_data)
    save_tracker(tracker)


def get_today_count(platform: str = None) -> int:
    tracker = load_tracker()
    date_key = datetime.now().strftime("%Y-%m-%d")
    stats = tracker["stats"].get(date_key, {"total": 0})
    if platform:
        return stats.get(platform, 0)
    return stats.get("total", 0)


def get_all_applied_ids(platform: str) -> set:
    tracker = load_tracker()
    return {j["job_id"] for j in tracker["applied"] if j.get("platform") == platform}
