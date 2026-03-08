"""
Agent 2 (v2): Safe Job Applier
Applies to jobs via Greenhouse/Lever POST APIs — no Selenium, no account bans.

How it works:
  1. Gets jobs with status "scraped" from the database
  2. For Greenhouse jobs: POST multipart form with resume to their Job Board API
  3. For Lever jobs: POST multipart form with resume to their Postings API
  4. For other jobs (RemoteOK, etc.): Opens the apply URL for manual application
  5. Updates job status to "applied" or "manual_apply_needed"

Daily target: 30 applications (configurable)
"""
import os
import time
import requests
from datetime import datetime

from agents.config import (
    RESUME_PATH, PERSONAL_INFO, JobStatus, DAILY_TARGET,
    OPENAI_API_KEY, OPENAI_MODEL,
)
from agents.logger import get_logger
from agents.job_database import (
    get_jobs_by_status, update_job_status, get_stats, add_job,
)
from agents.resume_parser import get_parsed_resume

logger = get_logger("Applier_v2")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Delay between applications to be respectful
APPLY_DELAY = 2.0  # seconds


class SafeJobApplierAgent:
    """Applies to jobs via ATS APIs. No browser automation needed."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.applied_count = 0
        self.failed_count = 0
        self.manual_count = 0
        self.resume = get_parsed_resume()

    def run(self) -> dict:
        """Run the applier. Returns stats dict."""
        logger.info("=" * 60)
        logger.info("AGENT 2 (v2): Safe Job Applier")
        logger.info("=" * 60)

        # Check resume exists
        if not os.path.exists(RESUME_PATH):
            logger.error(f"Resume not found: {RESUME_PATH}")
            logger.info("Set RESUME_PATH in your .env file")
            return {"applied": 0, "failed": 0, "manual": 0}

        # Get today's stats
        stats = get_stats()
        already_applied_today = stats.get("today_applied", 0)
        remaining = max(0, DAILY_TARGET - already_applied_today)

        logger.info(f"Already applied today: {already_applied_today}")
        logger.info(f"Daily target: {DAILY_TARGET}")
        logger.info(f"Remaining: {remaining}")

        if remaining == 0:
            logger.info("Daily target reached! Skipping.")
            return {"applied": 0, "failed": 0, "manual": 0}

        # Get scraped jobs sorted by match score
        scraped_jobs = get_jobs_by_status(JobStatus.SCRAPED)
        if not scraped_jobs:
            logger.info("No scraped jobs to apply to.")
            return {"applied": 0, "failed": 0, "manual": 0}

        # Sort by match score (highest first)
        scraped_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
        logger.info(f"Found {len(scraped_jobs)} scraped jobs to process")

        # Deduplicate by title+company (keep highest-scored location variant)
        seen_roles = set()
        unique_jobs = []
        for job in scraped_jobs:
            key = (job.get("title", "").strip().lower(), job.get("company", "").strip().lower())
            if key not in seen_roles:
                seen_roles.add(key)
                unique_jobs.append(job)
        logger.info(f"After dedup: {len(unique_jobs)} unique roles (from {len(scraped_jobs)} total)")

        # Apply to top jobs up to daily limit
        for job in unique_jobs[:remaining]:
            ats_type = job.get("ats_type", "")

            try:
                if ats_type == "greenhouse":
                    success = self._apply_greenhouse(job)
                elif ats_type == "lever":
                    success = self._apply_lever(job)
                else:
                    # RemoteOK, etc. — mark for manual apply
                    self._mark_manual(job)
                    continue

                if success:
                    self.applied_count += 1
                    update_job_status(
                        job["url"],
                        JobStatus.APPLIED,
                        applied_date=datetime.now().isoformat()
                    )
                    logger.info(f"  ✓ Applied: {job['title']} @ {job['company']} [{job.get('match_score', '?')}]")
                else:
                    self.failed_count += 1
                    update_job_status(job["url"], JobStatus.FAILED_TO_APPLY)
                    logger.warning(f"  ✗ Failed: {job['title']} @ {job['company']}")

                time.sleep(APPLY_DELAY)

            except Exception as e:
                logger.error(f"  Error applying to {job['title']} @ {job['company']}: {e}")
                self.failed_count += 1
                update_job_status(job["url"], JobStatus.FAILED_TO_APPLY)

        logger.info(f"\nApplier complete!")
        logger.info(f"  Applied:   {self.applied_count}")
        logger.info(f"  Failed:    {self.failed_count}")
        logger.info(f"  Manual:    {self.manual_count}")

        return {
            "applied": self.applied_count,
            "failed": self.failed_count,
            "manual": self.manual_count,
        }

    def _apply_greenhouse(self, job: dict) -> bool:
        """
        Apply to a Greenhouse job via their Job Board API.
        POST https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}
        """
        token = job.get("ats_token", "")
        job_id = job.get("ats_job_id", "")

        if not token or not job_id:
            logger.debug(f"Missing Greenhouse token/job_id for {job.get('title')}")
            self._mark_manual(job)
            return False

        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"

        # First, get the job to see required questions
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return False

            job_data = resp.json()
            questions = job_data.get("questions", [])
        except Exception:
            questions = []

        # Prepare form data
        form_data = {
            "first_name": PERSONAL_INFO.get("first_name", ""),
            "last_name": PERSONAL_INFO.get("last_name", ""),
            "email": PERSONAL_INFO.get("email", ""),
            "phone": PERSONAL_INFO.get("phone", ""),
            "location": f"{PERSONAL_INFO.get('city', '')}, {PERSONAL_INFO.get('state', '')}",
        }

        # Answer custom questions
        for q in questions:
            q_fields = q.get("fields", [])
            q_label = q.get("label", "").lower()
            q_required = q.get("required", False)

            for field in q_fields:
                field_name = field.get("name", "")
                field_type = field.get("type", "")
                field_values = field.get("values", [])

                answer = self._answer_question(q_label, field_type, field_values)
                if answer is not None:
                    form_data[field_name] = answer

        # Prepare resume file
        try:
            files = {
                "resume": (
                    os.path.basename(RESUME_PATH),
                    open(RESUME_PATH, "rb"),
                    "application/pdf"
                )
            }

            # Submit application
            apply_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"
            resp = self.session.post(
                apply_url,
                data=form_data,
                files=files,
                timeout=30,
            )

            files["resume"][1].close()

            if resp.status_code in (200, 201):
                return True
            else:
                logger.debug(f"Greenhouse apply returned {resp.status_code}: {resp.text[:200]}")
                return False

        except Exception as e:
            logger.debug(f"Greenhouse apply error: {e}")
            return False

    def _apply_lever(self, job: dict) -> bool:
        """
        Apply to a Lever job via their Postings API.
        POST https://api.lever.co/v0/postings/{token}/{posting_id}
        """
        token = job.get("ats_token", "")
        posting_id = job.get("ats_job_id", "")

        if not token or not posting_id:
            logger.debug(f"Missing Lever token/posting_id for {job.get('title')}")
            self._mark_manual(job)
            return False

        # Build form data
        name = f"{PERSONAL_INFO.get('first_name', '')} {PERSONAL_INFO.get('last_name', '')}".strip()

        form_data = {
            "name": name,
            "email": PERSONAL_INFO.get("email", ""),
            "phone": PERSONAL_INFO.get("phone", ""),
            "org": "",  # Current organization
            "urls[LinkedIn]": PERSONAL_INFO.get("linkedin_url", ""),
            "urls[GitHub]": PERSONAL_INFO.get("github_url", ""),
            "urls[Portfolio]": PERSONAL_INFO.get("portfolio_url", ""),
            "comments": self._generate_cover_note(job),
            "silent": "true",  # Don't send confirmation email to candidate
            "source": "Direct Application",
        }

        # Consent fields
        form_data["consent[marketing]"] = "false"
        form_data["consent[store]"] = "true"

        try:
            files = {
                "resume": (
                    os.path.basename(RESUME_PATH),
                    open(RESUME_PATH, "rb"),
                    "application/pdf"
                )
            }

            apply_url = f"https://api.lever.co/v0/postings/{token}/{posting_id}"
            resp = self.session.post(
                apply_url,
                data=form_data,
                files=files,
                timeout=30,
            )

            files["resume"][1].close()

            if resp.status_code == 200:
                result = resp.json()
                if result.get("ok"):
                    return True
                else:
                    logger.debug(f"Lever apply error: {result.get('error', 'Unknown')}")
                    return False
            elif resp.status_code == 429:
                logger.warning(f"Lever rate limited for {token}. Waiting 60s...")
                time.sleep(60)
                return False
            else:
                logger.debug(f"Lever apply returned {resp.status_code}: {resp.text[:200]}")
                return False

        except Exception as e:
            logger.debug(f"Lever apply error: {e}")
            return False

    def _mark_manual(self, job: dict):
        """Mark a job as needing manual application."""
        self.manual_count += 1
        update_job_status(job["url"], "manual_apply_needed")
        logger.info(f"  → Manual: {job['title']} @ {job['company']} — {job.get('url', '')}")

    def _answer_question(self, label: str, field_type: str, values: list) -> str | None:
        """Answer common application questions intelligently."""
        label_lower = label.lower()

        # Work authorization
        if any(kw in label_lower for kw in ["authorized", "authorization", "legally", "work in the u", "eligible to work"]):
            if field_type == "multi_value_single_select" and values:
                for v in values:
                    if v.get("label", "").lower() in ("yes", "true"):
                        return str(v.get("value", v.get("label", "Yes")))
            return "Yes"

        # Sponsorship
        if any(kw in label_lower for kw in ["sponsor", "visa"]):
            if field_type == "multi_value_single_select" and values:
                for v in values:
                    if v.get("label", "").lower() in ("no", "false"):
                        return str(v.get("value", v.get("label", "No")))
            return "No"

        # Relocation
        if "reloc" in label_lower:
            return "Yes"

        # Years of experience
        if any(kw in label_lower for kw in ["years of experience", "years experience", "how many years"]):
            return str(PERSONAL_INFO.get("years_experience", "3"))

        # LinkedIn
        if "linkedin" in label_lower:
            return PERSONAL_INFO.get("linkedin_url", "")

        # GitHub
        if "github" in label_lower:
            return PERSONAL_INFO.get("github_url", "")

        # Portfolio / Website
        if any(kw in label_lower for kw in ["portfolio", "website", "personal site"]):
            return PERSONAL_INFO.get("portfolio_url", "")

        # Location
        if any(kw in label_lower for kw in ["city", "location", "where are you"]):
            return f"{PERSONAL_INFO.get('city', '')}, {PERSONAL_INFO.get('state', '')}"

        # Salary expectation
        if any(kw in label_lower for kw in ["salary", "compensation", "expected pay"]):
            return str(PERSONAL_INFO.get("salary_expectation", ""))

        # Start date
        if any(kw in label_lower for kw in ["start date", "when can you", "availability", "available to start"]):
            return "Immediately"

        # How did you hear about us
        if any(kw in label_lower for kw in ["how did you hear", "how did you find", "referral", "source"]):
            return "Company career page"

        # Remote preference
        if any(kw in label_lower for kw in ["remote", "on-site", "hybrid", "work arrangement"]):
            return "Remote"

        return None

    def _generate_cover_note(self, job: dict) -> str:
        """Generate a brief, personalized cover note for Lever's comments field."""
        name = PERSONAL_INFO.get("first_name", "")
        title = job.get("title", "this position")
        company = job.get("company", "your company")
        matched_skills = job.get("matched_skills", [])

        if matched_skills:
            skills_text = ", ".join(matched_skills[:5])
            return (
                f"Hi, I'm {name} and I'm excited to apply for the {title} role at {company}. "
                f"My experience with {skills_text} aligns well with this position. "
                f"I'd love to contribute to your team."
            )
        else:
            return (
                f"Hi, I'm {name} and I'm interested in the {title} role at {company}. "
                f"I believe my skills and experience make me a strong candidate for this position."
            )
