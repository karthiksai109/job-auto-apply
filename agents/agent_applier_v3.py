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
FORM_TIMEOUT = 12000  # ms to wait for form elements
FIELD_TIMEOUT = 3000  # ms to wait for individual fields


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
    # Companies whose boards.greenhouse.io URLs redirect to job-boards.greenhouse.io (form works)
    GREENHOUSE_DIRECT_WORKS = {"twilio", "figma", "reddit", "cloudflare", "grafana", "sentry", "zapier", "wiz", "gusto", "elastic", "affirm", "duolingo"}

    def _apply_greenhouse(self, job: dict) -> bool:
        """Fill out a Greenhouse application form via Playwright."""
        url = job.get("url", "")
        if not url:
            logger.warning(f"  No URL for {job.get('title')}")
            return False

        ats_token = job.get("ats_token", "")
        ats_job_id = job.get("ats_job_id", "")

        # Strategy: try boards.greenhouse.io first (works for some companies),
        # then fall back to the Greenhouse embed iframe URL
        urls_to_try = []

        if ats_token and ats_job_id:
            urls_to_try.append(f"https://boards.greenhouse.io/{ats_token}/jobs/{ats_job_id}")
        if "job-boards.greenhouse.io" in url or "boards.greenhouse.io" in url:
            urls_to_try.append(url)
        if url and url not in urls_to_try:
            # Original URL as fallback (company career page)
            urls_to_try.append(url if "#app" in url else url + "#app")

        if not urls_to_try:
            logger.warning(f"  No valid URL for {job.get('title')}")
            return False

        page = self.browser.new_page()
        try:
            form_found = False
            for try_url in urls_to_try:
                logger.info(f"  Trying: {try_url}")
                try:
                    page.goto(try_url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3000)
                except PlaywrightTimeout:
                    logger.warning(f"  Timeout loading {try_url}")
                    continue

                final_url = page.url

                # Check if we landed on a Cloudflare challenge or error page
                title = page.title().lower()
                if "attention required" in title or "just a moment" in title:
                    logger.warning(f"  Cloudflare blocked: {try_url}")
                    continue

                # Check for error page (invalid job ID)
                if "error=true" in final_url or page.locator("input").count() < 2:
                    # Check if there's an iframe with the Greenhouse embed
                    iframes = page.locator("iframe[src*='greenhouse']")
                    if iframes.count() > 0:
                        iframe_src = iframes.first.get_attribute("src")
                        if iframe_src:
                            logger.info(f"  Found Greenhouse iframe: {iframe_src}")
                            page.goto(iframe_src, wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(3000)

                # STEP 1: Look for form
                form_found = self._find_greenhouse_form(page)

                if not form_found:
                    # Try clicking "Apply" button
                    apply_btns = [
                        "a:has-text('Apply for this job')", "a:has-text('Apply Now')",
                        "a:has-text('Apply now')", "a:has-text('Apply')",
                        "button:has-text('Apply for this job')", "button:has-text('Apply Now')",
                        "button:has-text('Apply')", "#apply_button",
                        "a[href*='#app']",
                    ]
                    for btn_sel in apply_btns:
                        try:
                            btn = page.locator(btn_sel).first
                            if btn.is_visible(timeout=1500):
                                btn.click()
                                page.wait_for_timeout(4000)
                                form_found = self._find_greenhouse_form(page)
                                if form_found:
                                    logger.info(f"  Form found after clicking Apply button")
                                    break
                        except Exception:
                            continue

                if not form_found and "#app" not in page.url:
                    try:
                        page.goto(page.url + "#app", wait_until="domcontentloaded", timeout=10000)
                        page.wait_for_timeout(2000)
                        form_found = self._find_greenhouse_form(page)
                    except Exception:
                        pass

                if form_found:
                    break

            if not form_found:
                logger.warning(f"  No form found for {job.get('title')} @ {job.get('company')} (tried {len(urls_to_try)} URLs)")
                return False

            logger.info(f"  Form found! Filling fields for {job.get('title')}")

            # STEP 2: Fill standard Greenhouse fields
            filled_any = False
            gh_fields = [
                (["#first_name", "input[name='job_application[first_name]']", "input[autocomplete='given-name']", "input[name*='first_name']"], PERSONAL_INFO["first_name"]),
                (["#last_name", "input[name='job_application[last_name]']", "input[autocomplete='family-name']", "input[name*='last_name']"], PERSONAL_INFO["last_name"]),
                (["#email", "input[name='job_application[email]']", "input[autocomplete='email']", "input[type='email']", "input[name*='email']"], PERSONAL_INFO["email"]),
                (["#phone", "input[name='job_application[phone]']", "input[autocomplete='tel']", "input[type='tel']", "input[name*='phone']"], PERSONAL_INFO["phone"]),
                (["#location", "input[name='job_application[location]']", "input[autocomplete='address-level2']"], f"{PERSONAL_INFO['city']}, {PERSONAL_INFO['state']}"),
            ]
            for selectors, value in gh_fields:
                for sel in selectors:
                    if self._fill_field(page, sel, value):
                        filled_any = True
                        break

            # Fill LinkedIn/GitHub/portfolio if fields exist
            for sel in ["input[name*='linkedin']", "input[placeholder*='LinkedIn']", "input[id*='linkedin']"]:
                if self._fill_field(page, sel, PERSONAL_INFO["linkedin_url"]): break
            for sel in ["input[name*='github']", "input[placeholder*='GitHub']", "input[id*='github']"]:
                if self._fill_field(page, sel, PERSONAL_INFO["github_url"]): break
            for sel in ["input[name*='website']", "input[name*='portfolio']", "input[placeholder*='Website']", "input[placeholder*='Portfolio']"]:
                if self._fill_field(page, sel, PERSONAL_INFO["portfolio_url"]): break

            if not filled_any:
                logger.warning(f"  Could not fill any fields for {job.get('title')} @ {job.get('company')}")
                return False

            logger.info(f"  Fields filled for {job.get('title')}")

            # STEP 3: Upload resume
            resume_uploaded = self._upload_resume(page)
            if not resume_uploaded:
                logger.warning(f"  Resume upload failed for {job.get('title')}")

            # STEP 4: Answer custom questions
            self._answer_greenhouse_questions(page)

            # STEP 5: Submit
            submitted = self._click_submit(page)
            if submitted:
                page.wait_for_timeout(4000)
                # Check for success indicators
                body_text = page.locator("body").text_content()[:1000].lower()
                if self._check_success(page):
                    logger.info(f"  SUCCESS confirmed for {job.get('title')}")
                    return True
                # Check for validation errors
                if "error" in body_text or "required" in body_text or "please" in body_text:
                    logger.warning(f"  Form validation errors for {job.get('title')}")
                    return False
                # No clear error — likely submitted
                logger.info(f"  Submit clicked, no errors detected for {job.get('title')}")
                return True

            logger.warning(f"  No submit button found for {job.get('title')} @ {job.get('company')}")
            return False

        except PlaywrightTimeout:
            logger.warning(f"  Timeout for {job.get('title')}")
            return False
        except Exception as e:
            logger.warning(f"  Greenhouse error for {job.get('title')}: {e}")
            return False
        finally:
            page.close()

    def _find_greenhouse_form(self, page: Page) -> bool:
        """Check if a Greenhouse application form is visible on the page."""
        form_selectors = [
            "#application-form", "form[data-ui='application-form']",
            "form.application--form", "#application_form",
            "#application", "form[action*='applications']",
            "#main_fields", "div[data-controller='application']",
            "#first_name", "#email",  # If we can see form fields, form is here
        ]
        for sel in form_selectors:
            try:
                if page.locator(sel).first.is_visible(timeout=1500):
                    return True
            except Exception:
                continue
        return False

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
            page.goto(apply_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            # Lever forms use specific input names
            filled = False
            for sel in ["input[name='name']", "input[placeholder*='name']"]:
                if self._fill_field(page, sel, f"{PERSONAL_INFO['first_name']} {PERSONAL_INFO['last_name']}"):
                    filled = True; break
            for sel in ["input[name='email']", "input[type='email']"]:
                if self._fill_field(page, sel, PERSONAL_INFO["email"]):
                    filled = True; break
            for sel in ["input[name='phone']", "input[type='tel']"]:
                self._fill_field(page, sel, PERSONAL_INFO["phone"]); break

            self._fill_field(page, "input[name='org']", "")
            self._fill_field(page, "input[name='urls[LinkedIn]']", PERSONAL_INFO.get("linkedin_url", ""))
            self._fill_field(page, "input[name='urls[GitHub]']", PERSONAL_INFO.get("github_url", ""))
            self._fill_field(page, "input[name='urls[Portfolio]']", PERSONAL_INFO.get("portfolio_url", ""))

            if not filled:
                logger.warning(f"  Could not fill Lever form for {job.get('title')} @ {job.get('company')}")

            # Generate and fill cover note
            comments = self._generate_cover_note(job)
            self._fill_field(page, "textarea[name='comments']", comments)
            self._fill_field(page, "textarea[name='additional']", comments)

            # Upload resume
            resume_uploaded = self._upload_resume(page)
            if not resume_uploaded:
                logger.warning(f"  Resume upload failed for Lever: {job.get('title')}")

            # Answer custom questions
            self._answer_lever_questions(page)

            # Submit
            submitted = self._click_submit(page)
            if submitted:
                page.wait_for_timeout(3000)
                return True

            logger.warning(f"  No submit button for Lever: {job.get('title')} @ {job.get('company')}")
            return False

        except PlaywrightTimeout:
            logger.warning(f"  Timeout on Lever {apply_url}")
            return False
        except Exception as e:
            logger.warning(f"  Lever error for {job.get('title')}: {e}")
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
            if el.is_visible(timeout=FIELD_TIMEOUT):
                el.scroll_into_view_if_needed(timeout=2000)
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
        # Work authorization — try multiple keyword variations
        for kw in ["authorized", "authorization", "legally", "eligible to work", "work in the u", "right to work"]:
            self._answer_select_or_radio(page, kw, "Yes")

        # Sponsorship — answer No (on OPT, no sponsorship needed now)
        for kw in ["sponsor", "visa", "immigration"]:
            self._answer_select_or_radio(page, kw, "No")

        # Gender / demographics (optional but sometimes required dropdowns)
        for kw in ["gender", "Gender"]:
            self._answer_select_or_radio(page, kw, "Male")
        for kw in ["race", "ethnicity", "veteran", "disability"]:
            self._answer_select_or_radio(page, kw, "Decline")

        # Years of experience
        for kw in ["years of experience", "years experience", "experience level"]:
            self._answer_text_question(page, kw, PERSONAL_INFO.get("years_experience", "3"))

        # LinkedIn / GitHub / Portfolio
        self._answer_text_question(page, "linkedin", PERSONAL_INFO.get("linkedin_url", ""))
        self._answer_text_question(page, "github", PERSONAL_INFO.get("github_url", ""))
        self._answer_text_question(page, "portfolio", PERSONAL_INFO.get("portfolio_url", ""))
        self._answer_text_question(page, "website", PERSONAL_INFO.get("portfolio_url", ""))

        # How did you hear
        for kw in ["how did you hear", "how did you find", "how did you learn", "source", "referral"]:
            self._answer_text_question(page, kw, "Company career page")
            self._answer_select_or_radio(page, kw, "Other")

        # Salary
        for kw in ["salary", "compensation", "pay expectation"]:
            self._answer_text_question(page, kw, PERSONAL_INFO.get("salary_expectation", "90000"))

        # Location / relocation
        self._answer_text_question(page, "location", f"{PERSONAL_INFO.get('city', '')}, {PERSONAL_INFO.get('state', '')}")
        self._answer_text_question(page, "address", PERSONAL_INFO.get("address", ""))
        for kw in ["reloc", "willing to relocate", "open to relocation"]:
            self._answer_select_or_radio(page, kw, "Yes")
        self._answer_select_or_radio(page, "remote", "Yes")

        # Start date
        for kw in ["start date", "when can you start", "availability", "earliest start", "available to start"]:
            self._answer_text_question(page, kw, "Immediately")

        # Education
        self._answer_text_question(page, "degree", "Master of Science in Computer Science")
        self._answer_text_question(page, "university", "Wright State University")
        self._answer_text_question(page, "school", "Wright State University")
        self._answer_text_question(page, "graduation", "2025")

        # Fill any remaining required selects with first non-empty option
        self._fill_required_selects(page)

        # Fill any remaining empty required text inputs with reasonable defaults
        self._fill_required_text_inputs(page)

    def _fill_required_selects(self, page: Page):
        """Fill any required select dropdowns that still have no value selected."""
        try:
            selects = page.locator("select")
            for i in range(selects.count()):
                sel = selects.nth(i)
                try:
                    if not sel.is_visible(timeout=300):
                        continue
                    # Check if it's still on the default/empty option
                    current = sel.input_value()
                    if current and current.strip():
                        continue
                    # Select the first non-empty option
                    options = sel.locator("option")
                    for j in range(options.count()):
                        val = options.nth(j).get_attribute("value") or ""
                        text = options.nth(j).text_content().strip().lower()
                        if val and val.strip() and text and text not in ["select", "choose", "--", "select...", "please select"]:
                            sel.select_option(index=j)
                            break
                except Exception:
                    continue
        except Exception:
            pass

    def _fill_required_text_inputs(self, page: Page):
        """Fill any visible empty required text inputs with N/A or reasonable defaults."""
        try:
            inputs = page.locator("input[required]:visible, input[aria-required='true']:visible")
            for i in range(inputs.count()):
                inp = inputs.nth(i)
                try:
                    if not inp.is_visible(timeout=300):
                        continue
                    current = inp.input_value()
                    if current and current.strip():
                        continue
                    inp_type = inp.get_attribute("type") or "text"
                    if inp_type in ["text", "url", "tel", "number"]:
                        inp.fill("N/A")
                except Exception:
                    continue
        except Exception:
            pass

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
