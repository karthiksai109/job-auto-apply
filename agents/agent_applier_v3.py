"""
Agent 2 (v3): Playwright-based Job Applier
Uses browser automation to fill out and submit Greenhouse/Lever application forms.

How it works:
  1. Gets jobs with status "scraped" from the database (sorted by match score)
  2. Deduplicates by title+company
  3. For Greenhouse jobs: navigates to the apply page, fills form, uploads resume, submits
  4. For Lever jobs: navigates to the apply page, fills form, uploads resume, submits
  5. For other jobs (RemoteOK, etc.): marks as manual_apply_needed
  6. Updates job status to "applied" or "failed_to_apply"

Daily target: configurable (default 30)
"""
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

from agents.config import (
    RESUME_PATH, PERSONAL_INFO, JobStatus, DAILY_TARGET, HEADLESS, SLOW_MO,
)
from agents.logger import get_logger
from agents.job_database import (
    get_jobs_by_status, update_job_status, get_stats,
)
from agents.resume_parser import get_parsed_resume

logger = get_logger("Applier_v3")

# Delay between applications to appear human-like
APPLY_DELAY = 3.0
FORM_TIMEOUT = 8000  # ms to wait for form elements


class PlaywrightJobApplierAgent:
    """Applies to jobs via Playwright browser automation."""

    def __init__(self):
        self.applied_count = 0
        self.failed_count = 0
        self.manual_count = 0
        self.resume = get_parsed_resume()
        self.pw = None
        self.browser = None

    def run(self) -> dict:
        """Run the applier. Returns stats dict."""
        logger.info("=" * 60)
        logger.info("AGENT 2 (v3): Playwright Job Applier")
        logger.info("=" * 60)

        if not os.path.exists(RESUME_PATH):
            logger.error(f"Resume not found: {RESUME_PATH}")
            return {"applied": 0, "failed": 0, "manual": 0}

        stats = get_stats()
        already_applied_today = stats.get("today_applied", 0)
        remaining = max(0, DAILY_TARGET - already_applied_today)

        logger.info(f"Already applied today: {already_applied_today}")
        logger.info(f"Daily target: {DAILY_TARGET}")
        logger.info(f"Remaining: {remaining}")

        if remaining == 0:
            logger.info("Daily target reached! Skipping.")
            return {"applied": 0, "failed": 0, "manual": 0}

        scraped_jobs = get_jobs_by_status(JobStatus.SCRAPED)
        if not scraped_jobs:
            logger.info("No scraped jobs to apply to.")
            return {"applied": 0, "failed": 0, "manual": 0}

        scraped_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
        logger.info(f"Found {len(scraped_jobs)} scraped jobs")

        # Hard-filter: skip senior/lead/manager titles (auto-reject for ~1yr experience)
        REJECT_TITLE_KEYWORDS = [
            "senior", "staff", "principal", "lead ", "manager", "director",
            "head of", "vp ", "vice president", "architect",
        ]
        filtered_jobs = []
        skipped_senior = 0
        for job in scraped_jobs:
            title_lower = job.get("title", "").lower()
            if any(kw in title_lower for kw in REJECT_TITLE_KEYWORDS):
                skipped_senior += 1
                continue
            if job.get("match_score", 0) < 60:
                continue
            filtered_jobs.append(job)
        logger.info(f"Skipped {skipped_senior} senior/lead/manager roles (would be auto-rejected)")

        # Deduplicate by title+company
        seen_roles = set()
        unique_jobs = []
        for job in filtered_jobs:
            key = (job.get("title", "").strip().lower(), job.get("company", "").strip().lower())
            if key not in seen_roles:
                seen_roles.add(key)
                unique_jobs.append(job)
        logger.info(f"After filter + dedup: {len(unique_jobs)} realistic interview-worthy roles")

        # Launch browser
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(
            headless=HEADLESS,
            slow_mo=int(SLOW_MO * 1000) if SLOW_MO < 5 else int(SLOW_MO),
        )

        try:
            for job in unique_jobs[:remaining]:
                ats_type = job.get("ats_type", "")
                title = job.get("title", "?")
                company = job.get("company", "?")
                score = job.get("match_score", "?")

                try:
                    if ats_type == "greenhouse":
                        success = self._apply_greenhouse(job)
                    elif ats_type == "lever":
                        success = self._apply_lever(job)
                    else:
                        self._mark_manual(job)
                        continue

                    if success:
                        self.applied_count += 1
                        update_job_status(
                            job["url"], JobStatus.APPLIED,
                            applied_date=datetime.now().isoformat()
                        )
                        logger.info(f"  ✓ Applied: {title} @ {company} [{score}]")
                    else:
                        self.failed_count += 1
                        update_job_status(job["url"], JobStatus.FAILED_TO_APPLY)
                        logger.warning(f"  ✗ Failed: {title} @ {company}")

                    time.sleep(APPLY_DELAY)

                except Exception as e:
                    logger.error(f"  Error: {title} @ {company}: {e}")
                    self.failed_count += 1
                    update_job_status(job["url"], JobStatus.FAILED_TO_APPLY)

        finally:
            self.browser.close()
            self.pw.stop()

        logger.info(f"\nApplier complete!")
        logger.info(f"  Applied:   {self.applied_count}")
        logger.info(f"  Failed:    {self.failed_count}")
        logger.info(f"  Manual:    {self.manual_count}")

        return {
            "applied": self.applied_count,
            "failed": self.failed_count,
            "manual": self.manual_count,
        }

    # ------------------------------------------------------------------
    # Greenhouse
    # ------------------------------------------------------------------
    def _apply_greenhouse(self, job: dict) -> bool:
        """Fill out a Greenhouse application form via Playwright."""
        url = job.get("url", "")
        if not url:
            return False

        # Greenhouse apply pages typically append #app to the job URL
        apply_url = url if "#app" in url else url + "#app"

        page = self.browser.new_page()
        try:
            page.goto(apply_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)  # let JS render

            # Look for the application form
            form = page.locator("form#application-form, form[data-ui='application-form'], form.application--form, form#application_form, form").first
            if not form.is_visible(timeout=FORM_TIMEOUT):
                # Some pages need you to click "Apply" button first
                apply_btn = page.locator("a:has-text('Apply'), button:has-text('Apply')")
                if apply_btn.count() > 0:
                    apply_btn.first.click()
                    page.wait_for_timeout(2000)

            # Fill standard fields
            self._fill_field(page, "#first_name", PERSONAL_INFO["first_name"])
            self._fill_field(page, "#last_name", PERSONAL_INFO["last_name"])
            self._fill_field(page, "#email", PERSONAL_INFO["email"])
            self._fill_field(page, "#phone", PERSONAL_INFO["phone"])
            self._fill_field(page, "#location", f"{PERSONAL_INFO['city']}, {PERSONAL_INFO['state']}")

            # Try alternate selectors for Greenhouse forms
            self._fill_field(page, "input[name='job_application[first_name]']", PERSONAL_INFO["first_name"])
            self._fill_field(page, "input[name='job_application[last_name]']", PERSONAL_INFO["last_name"])
            self._fill_field(page, "input[name='job_application[email]']", PERSONAL_INFO["email"])
            self._fill_field(page, "input[name='job_application[phone]']", PERSONAL_INFO["phone"])
            self._fill_field(page, "input[name='job_application[location]']", f"{PERSONAL_INFO['city']}, {PERSONAL_INFO['state']}")

            # Upload resume
            resume_uploaded = self._upload_resume(page)
            if not resume_uploaded:
                logger.debug(f"Could not upload resume for {job.get('title')}")

            # Answer custom questions
            self._answer_greenhouse_questions(page)

            # Submit
            submitted = self._click_submit(page)
            if submitted:
                page.wait_for_timeout(3000)
                # Check for success indicators
                if self._check_success(page):
                    return True
                else:
                    logger.debug(f"No success confirmation detected for {job.get('title')}")
                    # Still count as applied if we got past submit
                    return True
            return False

        except PlaywrightTimeout:
            logger.debug(f"Timeout on {url}")
            return False
        except Exception as e:
            logger.debug(f"Greenhouse error: {e}")
            return False
        finally:
            page.close()

    # ------------------------------------------------------------------
    # Lever
    # ------------------------------------------------------------------
    def _apply_lever(self, job: dict) -> bool:
        """Fill out a Lever application form via Playwright."""
        url = job.get("url", "")
        if not url:
            return False

        # Lever apply pages: append /apply to the job URL
        apply_url = url + "/apply" if "/apply" not in url else url

        page = self.browser.new_page()
        try:
            page.goto(apply_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)

            # Lever forms use specific input names
            self._fill_field(page, "input[name='name']",
                             f"{PERSONAL_INFO['first_name']} {PERSONAL_INFO['last_name']}")
            self._fill_field(page, "input[name='email']", PERSONAL_INFO["email"])
            self._fill_field(page, "input[name='phone']", PERSONAL_INFO["phone"])
            self._fill_field(page, "input[name='org']", "")
            self._fill_field(page, "input[name='urls[LinkedIn]']", PERSONAL_INFO.get("linkedin_url", ""))
            self._fill_field(page, "input[name='urls[GitHub]']", PERSONAL_INFO.get("github_url", ""))
            self._fill_field(page, "input[name='urls[Portfolio]']", PERSONAL_INFO.get("portfolio_url", ""))

            # Generate and fill cover note
            comments = self._generate_cover_note(job)
            self._fill_field(page, "textarea[name='comments']", comments)

            # Upload resume
            self._upload_resume(page)

            # Answer custom questions
            self._answer_lever_questions(page)

            # Submit
            submitted = self._click_submit(page)
            if submitted:
                page.wait_for_timeout(3000)
                return True
            return False

        except PlaywrightTimeout:
            logger.debug(f"Timeout on {url}")
            return False
        except Exception as e:
            logger.debug(f"Lever error: {e}")
            return False
        finally:
            page.close()

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _fill_field(self, page: Page, selector: str, value: str) -> bool:
        """Safely fill a form field if it exists."""
        if not value:
            return False
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=1000):
                el.click()
                el.fill(value)
                return True
        except Exception:
            pass
        return False

    def _upload_resume(self, page: Page) -> bool:
        """Upload resume via file input."""
        try:
            # Look for file input elements
            file_inputs = page.locator("input[type='file']")
            count = file_inputs.count()
            if count > 0:
                # Use the first file input (usually resume)
                file_inputs.first.set_input_files(RESUME_PATH)
                page.wait_for_timeout(1000)
                return True

            # Try drag-drop areas with hidden file inputs
            hidden_file = page.locator("input[type='file'][style*='display: none'], input[type='file'][hidden], input[type='file'].hidden")
            if hidden_file.count() > 0:
                hidden_file.first.set_input_files(RESUME_PATH)
                page.wait_for_timeout(1000)
                return True

        except Exception as e:
            logger.debug(f"Resume upload failed: {e}")
        return False

    def _click_submit(self, page: Page) -> bool:
        """Find and click the submit button."""
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Apply')",
            "button:has-text('Submit Application')",
            "button:has-text('Submit application')",
            "a:has-text('Submit Application')",
            "#submit_app",
            ".application-submit",
        ]
        for selector in submit_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    return True
            except Exception:
                continue
        logger.debug("No submit button found")
        return False

    def _check_success(self, page: Page) -> bool:
        """Check if the application was submitted successfully."""
        success_indicators = [
            "text=Thank you",
            "text=thanks for applying",
            "text=application has been submitted",
            "text=successfully submitted",
            "text=Application submitted",
            "text=We've received your application",
            "text=received your application",
            ".flash-success",
            ".application-confirmation",
        ]
        for indicator in success_indicators:
            try:
                if page.locator(indicator).first.is_visible(timeout=1000):
                    return True
            except Exception:
                continue
        return False

    def _answer_greenhouse_questions(self, page: Page):
        """Answer common Greenhouse custom questions."""
        # Work authorization
        self._answer_select_or_radio(page, "authorized", "Yes")
        self._answer_select_or_radio(page, "authorization", "Yes")
        self._answer_select_or_radio(page, "legally", "Yes")
        self._answer_select_or_radio(page, "eligible to work", "Yes")

        # Sponsorship
        self._answer_select_or_radio(page, "sponsor", "No")
        self._answer_select_or_radio(page, "visa", "No")

        # Years of experience
        self._answer_text_question(page, "years of experience", PERSONAL_INFO.get("years_experience", "3"))
        self._answer_text_question(page, "years experience", PERSONAL_INFO.get("years_experience", "3"))

        # LinkedIn
        self._answer_text_question(page, "linkedin", PERSONAL_INFO.get("linkedin_url", ""))

        # GitHub
        self._answer_text_question(page, "github", PERSONAL_INFO.get("github_url", ""))

        # How did you hear
        self._answer_text_question(page, "how did you hear", "Company career page")
        self._answer_text_question(page, "how did you find", "Company career page")

        # Salary
        self._answer_text_question(page, "salary", PERSONAL_INFO.get("salary_expectation", ""))
        self._answer_text_question(page, "compensation", PERSONAL_INFO.get("salary_expectation", ""))

        # Location / relocation
        self._answer_text_question(page, "location", f"{PERSONAL_INFO.get('city', '')}, {PERSONAL_INFO.get('state', '')}")
        self._answer_select_or_radio(page, "reloc", "Yes")
        self._answer_select_or_radio(page, "remote", "Yes")

        # Start date
        self._answer_text_question(page, "start date", "Immediately")
        self._answer_text_question(page, "when can you start", "Immediately")
        self._answer_text_question(page, "availability", "Immediately")

    def _answer_lever_questions(self, page: Page):
        """Answer common Lever custom questions."""
        # Similar to greenhouse
        self._answer_greenhouse_questions(page)

    def _answer_select_or_radio(self, page: Page, keyword: str, preferred_value: str):
        """Find a question containing keyword and select the preferred answer."""
        try:
            # Find labels containing the keyword
            labels = page.locator(f"label:has-text('{keyword}')")
            for i in range(min(labels.count(), 3)):
                label = labels.nth(i)
                parent = label.locator("..").first

                # Try select dropdown
                select = parent.locator("select").first
                if select.count() > 0 and select.is_visible(timeout=500):
                    options = select.locator("option")
                    for j in range(options.count()):
                        opt_text = options.nth(j).text_content().strip().lower()
                        if opt_text == preferred_value.lower() or preferred_value.lower() in opt_text:
                            select.select_option(index=j)
                            return

                # Try radio buttons
                radios = parent.locator("input[type='radio']")
                for j in range(radios.count()):
                    radio = radios.nth(j)
                    radio_label = radio.locator("..").text_content().strip().lower()
                    if preferred_value.lower() in radio_label:
                        radio.click()
                        return
        except Exception:
            pass

    def _answer_text_question(self, page: Page, keyword: str, value: str):
        """Find a text input question containing keyword and fill it."""
        if not value:
            return
        try:
            labels = page.locator(f"label:has-text('{keyword}')")
            for i in range(min(labels.count(), 2)):
                label = labels.nth(i)
                # Try to find associated input
                for_attr = label.get_attribute("for")
                if for_attr:
                    inp = page.locator(f"#{for_attr}")
                    if inp.count() > 0 and inp.is_visible(timeout=500):
                        inp.fill(value)
                        return
                # Try sibling input
                parent = label.locator("..").first
                inp = parent.locator("input[type='text'], input[type='url'], input[type='number'], textarea").first
                if inp.count() > 0 and inp.is_visible(timeout=500):
                    inp.fill(value)
                    return
        except Exception:
            pass

    def _mark_manual(self, job: dict):
        """Mark a job as needing manual application."""
        self.manual_count += 1
        update_job_status(job["url"], "manual_apply_needed")
        logger.info(f"  → Manual: {job['title']} @ {job['company']} — {job.get('url', '')}")

    def _generate_cover_note(self, job: dict) -> str:
        """Generate a brief cover note for Lever's comments field."""
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
        return (
            f"Hi, I'm {name} and I'm interested in the {title} role at {company}. "
            f"I believe my skills and experience make me a strong candidate for this position."
        )
