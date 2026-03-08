"""
Agent 3: Status Checker
Monitors application statuses 24/7 by:
1. Checking email inbox for interview invites, rejections, etc.
2. Scraping platform dashboards for status updates
3. Using AI to classify email content into status categories
4. Updating the central job database with new statuses
"""
import time
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from agents.config import (
    EMAIL_SENDER, EMAIL_PASSWORD, SMTP_SERVER,
    OPENAI_API_KEY, OPENAI_MODEL, JobStatus,
)
from agents.job_database import (
    get_applied_jobs, update_job_status, update_job, add_round, get_all_jobs,
)
from agents.logger import get_logger

logger = get_logger("StatusChk")


class StatusCheckerAgent:
    """
    Agent 3: Continuously monitors the status of all applied jobs.
    - Scans email for interview invites, rejections, follow-ups
    - Checks job portal dashboards for status changes
    - Uses AI to parse and classify email content
    - Updates job database with new statuses and interview rounds
    """

    def __init__(self, driver=None):
        self.driver = driver
        self.updates_found = 0

    def run(self) -> dict:
        """Run the full status check cycle."""
        logger.info("=" * 60)
        logger.info("AGENT 3: Status Checker Starting...")
        logger.info("=" * 60)

        applied_jobs = get_applied_jobs()
        logger.info(f"Monitoring {len(applied_jobs)} active applications")

        results = {
            "email_updates": 0,
            "dashboard_updates": 0,
            "no_response_flagged": 0,
        }

        # 1. Check emails for updates
        logger.info("\n--- Checking Email for Updates ---")
        email_updates = self._check_emails()
        results["email_updates"] = email_updates

        # 2. Check platform dashboards (if driver available)
        if self.driver:
            logger.info("\n--- Checking Platform Dashboards ---")
            dash_updates = self._check_dashboards()
            results["dashboard_updates"] = dash_updates

        # 3. Flag old applications with no response
        logger.info("\n--- Flagging No-Response Applications ---")
        no_response = self._flag_no_response(applied_jobs)
        results["no_response_flagged"] = no_response

        self.updates_found = sum(results.values())
        logger.info(f"\nStatus Checker complete! {self.updates_found} updates processed.")
        return results

    # ----------------------------------------------------------------
    # EMAIL MONITORING
    # ----------------------------------------------------------------
    def _check_emails(self) -> int:
        """Scan inbox for job-related emails and update statuses."""
        if not EMAIL_SENDER or not EMAIL_PASSWORD:
            logger.warning("Email credentials not configured. Skipping email check.")
            return 0

        updates = 0
        try:
            # Connect to IMAP
            imap_server = SMTP_SERVER.replace("smtp.", "imap.")
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(EMAIL_SENDER, EMAIL_PASSWORD)
            mail.select("inbox")

            # Search for recent emails (last 3 days)
            since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
            _, message_numbers = mail.search(None, f'SINCE {since_date}')

            if not message_numbers[0]:
                logger.info("No recent emails found")
                mail.logout()
                return 0

            msg_ids = message_numbers[0].split()
            logger.info(f"Found {len(msg_ids)} recent emails to scan")

            # Get all applied jobs for matching
            all_jobs = get_all_jobs()
            company_names = {j["company"].lower(): j for j in all_jobs if j.get("company")}

            for msg_id in msg_ids[-50:]:  # Last 50 emails max
                try:
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])

                    subject = self._decode_header(msg["Subject"])
                    sender = self._decode_header(msg["From"])
                    body = self._get_email_body(msg)

                    if not body:
                        continue

                    # Check if this email is job-related
                    classification = self._classify_email(subject, sender, body, company_names)

                    if classification:
                        job = classification["job"]
                        new_status = classification["status"]
                        round_info = classification.get("round_info")

                        old_status = job.get("status", "")
                        if old_status != new_status:
                            update_job_status(job["job_id"], job["platform"], new_status)
                            logger.info(
                                f"  Updated: {job['title']} @ {job['company']} "
                                f"({old_status} -> {new_status})"
                            )
                            updates += 1

                        if round_info:
                            add_round(job["job_id"], job["platform"], round_info)
                            logger.info(f"    Round added: {round_info.get('type', 'unknown')}")

                except Exception as e:
                    logger.debug(f"  Email parse error: {e}")
                    continue

            mail.logout()

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP error: {e}")
        except Exception as e:
            logger.error(f"Email check error: {e}")

        logger.info(f"Email: {updates} status updates found")
        return updates

    def _decode_header(self, header_value) -> str:
        if not header_value:
            return ""
        decoded_parts = decode_header(header_value)
        result = ""
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(charset or "utf-8", errors="replace")
            else:
                result += part
        return result

    def _get_email_body(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
                    except Exception:
                        continue
                elif content_type == "text/html" and not body:
                    try:
                        from bs4 import BeautifulSoup
                        html = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        body = BeautifulSoup(html, "html.parser").get_text()
                    except Exception:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except Exception:
                pass
        return body[:3000]  # Limit size

    def _classify_email(self, subject: str, sender: str, body: str, company_jobs: dict) -> Optional[dict]:
        """Classify an email as job-related and determine status update."""
        combined = f"{subject} {body}".lower()

        # Quick filter: is this job-related?
        job_keywords = [
            "application", "interview", "position", "role", "candidate",
            "hiring", "recruiter", "opportunity", "offer", "reject",
            "unfortunately", "moved forward", "next steps", "schedule",
            "assessment", "coding challenge", "phone screen", "technical",
            "onsite", "final round", "congratulations",
        ]
        if not any(kw in combined for kw in job_keywords):
            return None

        # Try to match to a company in our database
        matched_job = None
        for company_lower, job in company_jobs.items():
            if company_lower in combined or company_lower in sender.lower():
                matched_job = job
                break

        if not matched_job:
            return None

        # Classify the status
        new_status = None
        round_info = None

        # Rejection indicators
        rejection_phrases = [
            "unfortunately", "not moving forward", "other candidates",
            "not selected", "decided not to", "position has been filled",
            "won't be moving", "will not be moving", "regret to inform",
            "not a match", "pursue other candidates",
        ]
        if any(phrase in combined for phrase in rejection_phrases):
            new_status = JobStatus.REJECTED

        # Offer indicators
        elif any(phrase in combined for phrase in [
            "pleased to offer", "offer letter", "congratulations",
            "we'd like to offer", "compensation package", "start date",
        ]):
            new_status = JobStatus.OFFER
            round_info = {"type": "offer", "details": subject}

        # Interview scheduling indicators
        elif any(phrase in combined for phrase in [
            "schedule an interview", "interview invitation", "phone screen",
            "screening call", "would like to schedule", "calendar invite",
            "next steps in the process", "move you forward",
        ]):
            # Determine round type
            if any(kw in combined for kw in ["technical", "coding", "assessment", "hackerrank", "leetcode"]):
                new_status = JobStatus.TECHNICAL_ROUND
                round_info = {"type": "technical", "details": subject}
            elif any(kw in combined for kw in ["onsite", "on-site", "final"]):
                new_status = JobStatus.FINAL_ROUND
                round_info = {"type": "onsite/final", "details": subject}
            elif any(kw in combined for kw in ["phone", "screen", "initial", "introductory"]):
                new_status = JobStatus.PHONE_SCREEN
                round_info = {"type": "phone_screen", "details": subject}
            else:
                new_status = JobStatus.SCREENING
                round_info = {"type": "screening", "details": subject}

        if new_status:
            return {
                "job": matched_job,
                "status": new_status,
                "round_info": round_info,
            }

        return None

    # ----------------------------------------------------------------
    # DASHBOARD MONITORING (Selenium)
    # ----------------------------------------------------------------
    def _check_dashboards(self) -> int:
        """Check job platform dashboards for status updates."""
        if not self.driver:
            return 0

        updates = 0

        # Check LinkedIn application status
        try:
            updates += self._check_linkedin_dashboard()
        except Exception as e:
            logger.error(f"LinkedIn dashboard error: {e}")

        # Check Indeed application status
        try:
            updates += self._check_indeed_dashboard()
        except Exception as e:
            logger.error(f"Indeed dashboard error: {e}")

        return updates

    def _check_linkedin_dashboard(self) -> int:
        """Check LinkedIn for application status updates."""
        updates = 0
        try:
            self.driver.get("https://www.linkedin.com/jobs/tracker/applied/")
            time.sleep(5)

            # Scroll to load
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(1)

            from selenium.webdriver.common.by import By

            cards = self.driver.find_elements(
                By.CSS_SELECTOR, ".job-card-container, .application-card"
            )
            logger.info(f"LinkedIn dashboard: Found {len(cards)} tracked applications")

            for card in cards:
                try:
                    status_el = card.find_element(
                        By.CSS_SELECTOR, ".job-card-container__footer-item, .application-card__status"
                    )
                    status_text = status_el.text.lower().strip()

                    title_el = card.find_element(By.CSS_SELECTOR, "a, .job-card-container__link")
                    title = title_el.text.strip()

                    if "viewed" in status_text:
                        logger.info(f"  LinkedIn: '{title}' was viewed by employer")
                    elif "not selected" in status_text or "closed" in status_text:
                        logger.info(f"  LinkedIn: '{title}' - application closed/rejected")
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"LinkedIn dashboard check error: {e}")

        return updates

    def _check_indeed_dashboard(self) -> int:
        """Check Indeed for application status updates."""
        updates = 0
        try:
            self.driver.get("https://www.indeed.com/myjobs")
            time.sleep(5)

            from selenium.webdriver.common.by import By

            cards = self.driver.find_elements(
                By.CSS_SELECTOR, ".applied-job-card, .gnav-AppliedJobs-card"
            )
            logger.info(f"Indeed dashboard: Found {len(cards)} tracked applications")

        except Exception as e:
            logger.debug(f"Indeed dashboard check error: {e}")

        return updates

    # ----------------------------------------------------------------
    # NO-RESPONSE FLAGGING
    # ----------------------------------------------------------------
    def _flag_no_response(self, applied_jobs: list) -> int:
        """Flag jobs that have had no response for 14+ days."""
        count = 0
        cutoff = datetime.now() - timedelta(days=14)

        for job in applied_jobs:
            if job.get("status") != JobStatus.APPLIED:
                continue

            applied_at_str = job.get("applied_at", "")
            if not applied_at_str:
                continue

            try:
                applied_at = datetime.fromisoformat(applied_at_str)
                if applied_at < cutoff:
                    update_job_status(job["job_id"], job["platform"], JobStatus.NO_RESPONSE)
                    logger.info(
                        f"  No response (14+ days): {job['title']} @ {job['company']}"
                    )
                    count += 1
            except (ValueError, TypeError):
                continue

        logger.info(f"Flagged {count} jobs with no response")
        return count


class StatusCheckerDaemon:
    """
    Runs the status checker continuously in the background.
    Checks every N hours as configured.
    """

    def __init__(self, driver=None, interval_hours: int = 12):
        self.driver = driver
        self.interval = interval_hours * 3600
        self.running = False

    def start(self):
        """Start the daemon loop."""
        self.running = True
        logger.info(f"Status Checker Daemon started (interval: {self.interval // 3600}h)")

        while self.running:
            try:
                checker = StatusCheckerAgent(self.driver)
                checker.run()
            except Exception as e:
                logger.error(f"Daemon cycle error: {e}")

            logger.info(f"Next check in {self.interval // 3600} hours...")
            time.sleep(self.interval)

    def stop(self):
        self.running = False
        logger.info("Status Checker Daemon stopped")
