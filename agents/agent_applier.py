"""
Agent 2: Job Applier
Takes scraped jobs from the database and applies to them automatically.
Uses Selenium to navigate job sites, fill forms, and submit applications.
Integrates with existing LinkedIn, Indeed, and Dice bots.
"""
import os
import time
import random
from datetime import datetime
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException
)

from agents.config import (
    LINKEDIN_EMAIL, LINKEDIN_PASSWORD, INDEED_EMAIL, INDEED_PASSWORD,
    DICE_EMAIL, DICE_PASSWORD, RESUME_PATH, PERSONAL_INFO,
    LINKEDIN_TARGET, INDEED_TARGET, DICE_TARGET, DAILY_TARGET, JobStatus,
)
from agents.job_database import (
    get_unapplied_jobs, update_job_status, update_job, get_stats,
)
from agents.logger import get_logger

logger = get_logger("Applier")


def _human_delay(min_s=1.0, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))


def _safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        _human_delay(0.3, 0.8)
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def _safe_send_keys(element, text, clear_first=True):
    if clear_first:
        element.clear()
        _human_delay(0.2, 0.5)
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.02, 0.08))


class JobApplierAgent:
    """
    Agent 2: Automatically applies to scraped jobs.
    Picks up jobs with status='scraped' and attempts to apply.
    """

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        self.applied_count = 0
        self.failed_count = 0

    def run(self) -> dict:
        """Run the apply cycle for all unapplied jobs."""
        logger.info("=" * 60)
        logger.info("AGENT 2: Job Applier Starting...")
        logger.info("=" * 60)

        stats = get_stats()
        logger.info(f"Today's applications so far: {stats['today_applied']}")

        unapplied = get_unapplied_jobs()
        logger.info(f"Found {len(unapplied)} unapplied jobs in queue")

        if not unapplied:
            logger.info("No jobs to apply to. Run the Scraper first.")
            return {"applied": 0, "failed": 0}

        # Group by platform
        by_platform = {}
        for job in unapplied:
            p = job.get("platform", "unknown")
            by_platform.setdefault(p, []).append(job)

        # Apply per platform
        if "linkedin" in by_platform:
            self._apply_linkedin_batch(by_platform["linkedin"])

        if "indeed" in by_platform:
            self._apply_indeed_batch(by_platform["indeed"])

        if "dice" in by_platform:
            self._apply_dice_batch(by_platform["dice"])

        # For other platforms (Monster, RemoteOK), open URL for manual apply
        for platform in ["monster", "remoteok"]:
            if platform in by_platform:
                self._mark_for_manual_apply(by_platform[platform], platform)

        result = {"applied": self.applied_count, "failed": self.failed_count}
        logger.info(f"\nApplier complete! Applied: {self.applied_count}, Failed: {self.failed_count}")
        return result

    # ----------------------------------------------------------------
    # LINKEDIN APPLY
    # ----------------------------------------------------------------
    def _apply_linkedin_batch(self, jobs: list):
        logger.info(f"\n--- Applying to {len(jobs)} LinkedIn jobs ---")

        # Login first
        if not self._login_linkedin():
            logger.error("Could not login to LinkedIn, skipping batch")
            return

        for job in jobs[:LINKEDIN_TARGET]:
            try:
                update_job_status(job["job_id"], "linkedin", JobStatus.APPLYING)
                success = self._apply_single_linkedin(job)

                if success:
                    update_job(job["job_id"], "linkedin", {
                        "status": JobStatus.APPLIED,
                        "applied_at": datetime.now().isoformat(),
                    })
                    self.applied_count += 1
                    logger.info(f"  Applied: {job['title']} @ {job['company']}")
                else:
                    update_job_status(job["job_id"], "linkedin", JobStatus.FAILED_TO_APPLY)
                    self.failed_count += 1

                _human_delay(2, 5)

            except Exception as e:
                logger.error(f"  Error applying to {job.get('title')}: {e}")
                update_job_status(job["job_id"], "linkedin", JobStatus.FAILED_TO_APPLY)
                self.failed_count += 1

    def _login_linkedin(self) -> bool:
        try:
            self.driver.get("https://www.linkedin.com/login")
            _human_delay(2, 4)

            if "feed" in self.driver.current_url:
                return True

            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            _safe_send_keys(email_field, LINKEDIN_EMAIL)
            _human_delay(0.5, 1)

            pass_field = self.driver.find_element(By.ID, "password")
            _safe_send_keys(pass_field, LINKEDIN_PASSWORD)
            _human_delay(0.5, 1)

            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            _human_delay(3, 5)

            if "checkpoint" in self.driver.current_url:
                logger.warning("LinkedIn security checkpoint! Please solve manually.")
                input("Press Enter after solving the checkpoint...")

            return "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url

        except Exception as e:
            logger.error(f"LinkedIn login failed: {e}")
            return False

    def _apply_single_linkedin(self, job: dict) -> bool:
        try:
            url = job.get("url", "")
            if not url:
                return False

            self.driver.get(url)
            _human_delay(2, 4)

            # Find Easy Apply button
            try:
                apply_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".jobs-apply-button, button.jobs-apply-button--top-card")
                ))
                if "easy apply" not in apply_btn.text.lower():
                    logger.info(f"  Not Easy Apply: {job['title']}")
                    return False

                _safe_click(self.driver, apply_btn)
                _human_delay(2, 3)
            except (TimeoutException, NoSuchElementException):
                return False

            # Handle multi-step Easy Apply modal
            return self._handle_linkedin_modal()

        except Exception as e:
            logger.debug(f"  LinkedIn apply error: {e}")
            return False

    def _handle_linkedin_modal(self) -> bool:
        for page in range(8):
            _human_delay(1, 2)
            self._fill_form_fields()
            self._upload_resume_if_needed()

            # Check for Submit
            try:
                submit_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Submit application'], button[aria-label='Review your application']"
                )
                if "Submit" in submit_btn.text:
                    _safe_click(self.driver, submit_btn)
                    _human_delay(2, 3)
                    try:
                        dismiss = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                        _safe_click(self.driver, dismiss)
                    except NoSuchElementException:
                        pass
                    return True
                elif "Review" in submit_btn.text:
                    _safe_click(self.driver, submit_btn)
                    _human_delay(1, 2)
                    continue
            except NoSuchElementException:
                pass

            # Click Next
            try:
                next_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Continue to next step'], button[data-easy-apply-next-button]"
                )
                _safe_click(self.driver, next_btn)
                _human_delay(1, 2)
            except NoSuchElementException:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, ".artdeco-button--primary")
                    for btn in buttons:
                        if any(kw in btn.text.lower() for kw in ["next", "continue", "review", "submit"]):
                            _safe_click(self.driver, btn)
                            _human_delay(1, 2)
                            if "submit" in btn.text.lower():
                                try:
                                    dismiss = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                                    _safe_click(self.driver, dismiss)
                                except NoSuchElementException:
                                    pass
                                return True
                            break
                except Exception:
                    pass

        self._close_modal()
        return False

    # ----------------------------------------------------------------
    # INDEED APPLY
    # ----------------------------------------------------------------
    def _apply_indeed_batch(self, jobs: list):
        logger.info(f"\n--- Applying to {len(jobs)} Indeed jobs ---")

        if not self._login_indeed():
            logger.error("Could not login to Indeed, skipping batch")
            return

        for job in jobs[:INDEED_TARGET]:
            try:
                update_job_status(job["job_id"], "indeed", JobStatus.APPLYING)
                success = self._apply_single_indeed(job)

                if success:
                    update_job(job["job_id"], "indeed", {
                        "status": JobStatus.APPLIED,
                        "applied_at": datetime.now().isoformat(),
                    })
                    self.applied_count += 1
                    logger.info(f"  Applied: {job['title']} @ {job['company']}")
                else:
                    update_job_status(job["job_id"], "indeed", JobStatus.FAILED_TO_APPLY)
                    self.failed_count += 1

                _human_delay(2, 5)

            except Exception as e:
                logger.error(f"  Error applying to {job.get('title')}: {e}")
                update_job_status(job["job_id"], "indeed", JobStatus.FAILED_TO_APPLY)
                self.failed_count += 1

    def _login_indeed(self) -> bool:
        try:
            self.driver.get("https://secure.indeed.com/auth")
            _human_delay(3, 5)

            if "secure.indeed.com/auth" not in self.driver.current_url:
                return True

            try:
                email_field = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='email'], input[name='__email']")
                ))
                _safe_send_keys(email_field, INDEED_EMAIL)
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                _human_delay(3, 5)
            except Exception:
                pass

            try:
                pass_field = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='password']")
                ))
                _safe_send_keys(pass_field, INDEED_PASSWORD)
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                _human_delay(3, 5)
            except TimeoutException:
                logger.warning("Indeed may need manual login")
                input("Press Enter after Indeed login...")

            return True

        except Exception as e:
            logger.error(f"Indeed login failed: {e}")
            return False

    def _apply_single_indeed(self, job: dict) -> bool:
        try:
            url = job.get("url", "")
            if not url:
                return False

            self.driver.get(url)
            _human_delay(2, 4)

            try:
                apply_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#indeedApplyButton, button.indeed-apply-button, .ia-IndeedApplyButton")
                ))
                _safe_click(self.driver, apply_btn)
                _human_delay(3, 5)
            except (TimeoutException, NoSuchElementException):
                return False

            # Handle multi-step
            for step in range(10):
                _human_delay(1.5, 2.5)

                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        if "indeed" in (iframe.get_attribute("src") or "").lower():
                            self.driver.switch_to.frame(iframe)
                            break
                except Exception:
                    pass

                self._fill_form_fields()
                self._upload_resume_if_needed()

                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, a.ia-continueButton")
                    for btn in buttons:
                        btn_text = btn.text.lower().strip()
                        if "submit" in btn_text or ("apply" in btn_text and "continue" not in btn_text):
                            _safe_click(self.driver, btn)
                            _human_delay(2, 3)
                            try:
                                self.driver.switch_to.default_content()
                            except Exception:
                                pass
                            return True
                        elif "continue" in btn_text or "next" in btn_text:
                            _safe_click(self.driver, btn)
                            _human_delay(1.5, 2.5)
                            break
                except Exception:
                    pass

            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return False

        except Exception as e:
            logger.debug(f"  Indeed apply error: {e}")
            return False

    # ----------------------------------------------------------------
    # DICE APPLY
    # ----------------------------------------------------------------
    def _apply_dice_batch(self, jobs: list):
        logger.info(f"\n--- Applying to {len(jobs)} Dice jobs ---")

        if not self._login_dice():
            logger.error("Could not login to Dice, skipping batch")
            return

        for job in jobs[:DICE_TARGET]:
            try:
                update_job_status(job["job_id"], "dice", JobStatus.APPLYING)
                success = self._apply_single_dice(job)

                if success:
                    update_job(job["job_id"], "dice", {
                        "status": JobStatus.APPLIED,
                        "applied_at": datetime.now().isoformat(),
                    })
                    self.applied_count += 1
                    logger.info(f"  Applied: {job['title']} @ {job['company']}")
                else:
                    update_job_status(job["job_id"], "dice", JobStatus.FAILED_TO_APPLY)
                    self.failed_count += 1

                _human_delay(2, 5)

            except Exception as e:
                logger.error(f"  Error applying to {job.get('title')}: {e}")
                update_job_status(job["job_id"], "dice", JobStatus.FAILED_TO_APPLY)
                self.failed_count += 1

    def _login_dice(self) -> bool:
        try:
            self.driver.get("https://www.dice.com/dashboard/login")
            _human_delay(3, 5)

            if "dashboard" in self.driver.current_url and "login" not in self.driver.current_url:
                return True

            email_field = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='email'], input[type='email']")
            ))
            _safe_send_keys(email_field, DICE_EMAIL)
            _human_delay(0.5, 1)

            try:
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                _human_delay(2, 3)
            except NoSuchElementException:
                pass

            try:
                pass_field = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='password']")
                ))
                _safe_send_keys(pass_field, DICE_PASSWORD)
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                _human_delay(3, 5)
            except TimeoutException:
                input("Press Enter after Dice login...")

            return True

        except Exception as e:
            logger.error(f"Dice login failed: {e}")
            return False

    def _apply_single_dice(self, job: dict) -> bool:
        try:
            url = job.get("url", "")
            if not url:
                return False

            self.driver.get(url)
            _human_delay(2, 4)

            try:
                apply_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "apply-button-wc, button.btn-apply, [data-cy='apply-button']")
                ))
                _safe_click(self.driver, apply_btn)
                _human_delay(2, 4)
            except (TimeoutException, NoSuchElementException):
                # Shadow DOM fallback
                try:
                    apply_btn = self.driver.execute_script("""
                        const wc = document.querySelector('apply-button-wc');
                        return wc && wc.shadowRoot ? wc.shadowRoot.querySelector('button') : null;
                    """)
                    if apply_btn:
                        self.driver.execute_script("arguments[0].click();", apply_btn)
                        _human_delay(2, 4)
                    else:
                        return False
                except Exception:
                    return False

            # Handle apply flow
            for step in range(8):
                _human_delay(1.5, 2.5)

                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])

                self._fill_form_fields()
                self._upload_resume_if_needed()

                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, input[type='submit']")
                    for btn in buttons:
                        btn_text = (btn.text or btn.get_attribute("value") or "").lower().strip()
                        if any(kw in btn_text for kw in ["submit", "apply now", "apply"]):
                            _safe_click(self.driver, btn)
                            _human_delay(2, 3)
                            if len(self.driver.window_handles) > 1:
                                self.driver.close()
                                self.driver.switch_to.window(self.driver.window_handles[0])
                            return True
                        elif any(kw in btn_text for kw in ["next", "continue"]):
                            _safe_click(self.driver, btn)
                            _human_delay(1.5, 2.5)
                            break
                except Exception:
                    pass

                # Check already applied
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    if "already applied" in page_text or "application submitted" in page_text:
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                        return True
                except Exception:
                    pass

            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            return False

        except Exception as e:
            logger.debug(f"  Dice apply error: {e}")
            return False

    # ----------------------------------------------------------------
    # MANUAL APPLY (for platforms without Easy Apply)
    # ----------------------------------------------------------------
    def _mark_for_manual_apply(self, jobs: list, platform: str):
        """Mark jobs that need manual application."""
        logger.info(f"\n--- {platform.title()}: {len(jobs)} jobs need manual application ---")
        for job in jobs:
            update_job(job["job_id"], platform, {
                "status": JobStatus.SCRAPED,
                "notes": f"Manual application needed. URL: {job.get('url', '')}",
            })
            logger.info(f"  Manual: {job['title']} @ {job['company']} - {job.get('url', '')}")

    # ----------------------------------------------------------------
    # SHARED FORM HANDLING
    # ----------------------------------------------------------------
    def _fill_form_fields(self):
        try:
            inputs = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='text'], input[type='tel'], input[type='email'], input[type='number']"
            )
            for inp in inputs:
                if inp.get_attribute("value"):
                    continue
                label = self._get_field_label(inp)
                value = self._get_answer_for_field(label)
                if value:
                    _safe_send_keys(inp, value)
                    _human_delay(0.3, 0.6)

            # Select dropdowns
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            for select in selects:
                from selenium.webdriver.support.ui import Select
                sel = Select(select)
                label = self._get_field_label(select).lower()

                if "sponsor" in label:
                    self._select_best(sel, ["no"])
                elif any(kw in label for kw in ["authorized", "authorization", "eligible", "legally"]):
                    self._select_best(sel, ["yes"])
                elif "experience" in label or "years" in label:
                    self._select_best(sel, [PERSONAL_INFO["years_of_experience"], "3"])
                elif "education" in label or "degree" in label:
                    self._select_best(sel, ["master", "bachelor"])
                elif "relocat" in label:
                    self._select_best(sel, ["yes"])
                elif len(sel.options) > 1:
                    sel.select_by_index(1)

            # Radio buttons
            fieldsets = self.driver.find_elements(By.CSS_SELECTOR, "fieldset")
            for fs in fieldsets:
                try:
                    legend = fs.text.lower()
                    radios = fs.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    if "sponsor" in legend:
                        self._click_radio(radios, "no")
                    elif any(kw in legend for kw in ["authorized", "authorization", "eligible", "legally"]):
                        self._click_radio(radios, "yes")
                    elif "relocat" in legend or "commut" in legend:
                        self._click_radio(radios, "yes")
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Form fill issue: {e}")

    def _get_field_label(self, element) -> str:
        try:
            el_id = element.get_attribute("id")
            if el_id:
                label_el = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{el_id}']")
                return label_el.text
        except Exception:
            pass
        try:
            return element.get_attribute("aria-label") or element.get_attribute("placeholder") or ""
        except Exception:
            return ""

    def _get_answer_for_field(self, label: str) -> Optional[str]:
        label_lower = label.lower()
        info = PERSONAL_INFO
        mapping = {
            "first name": info["first_name"],
            "last name": info["last_name"],
            "full name": f"{info['first_name']} {info['last_name']}",
            "email": info["email"],
            "phone": info["phone"],
            "mobile": info["phone"],
            "city": info["city"],
            "state": info["state"],
            "zip": info["zip"],
            "salary": info["salary_expectation"],
            "compensation": info["salary_expectation"],
            "experience": info["years_of_experience"],
            "years": info["years_of_experience"],
            "linkedin": info["linkedin_url"],
            "github": info["github_url"],
            "portfolio": info["portfolio_url"],
            "website": info["portfolio_url"],
            "gpa": "3.5",
        }
        for key, value in mapping.items():
            if key in label_lower and value:
                return value
        return None

    def _select_best(self, select_el, preferred: list):
        for pref in preferred:
            for opt in select_el.options:
                if pref.lower() in opt.text.lower():
                    select_el.select_by_visible_text(opt.text)
                    return
        if len(select_el.options) > 1:
            select_el.select_by_index(1)

    def _click_radio(self, radios, target_text: str):
        for radio in radios:
            try:
                parent_text = radio.find_element(By.XPATH, "..").text.lower()
                if target_text.lower() in parent_text:
                    _safe_click(self.driver, radio)
                    return
            except Exception:
                continue

    def _upload_resume_if_needed(self):
        try:
            uploads = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for upload in uploads:
                if not upload.get_attribute("value"):
                    upload.send_keys(os.path.abspath(RESUME_PATH))
                    _human_delay(1, 2)
        except Exception:
            pass

    def _close_modal(self):
        try:
            close_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
            _safe_click(self.driver, close_btn)
            _human_delay(0.5, 1)
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "discard" in btn.text.lower():
                        _safe_click(self.driver, btn)
                        break
            except Exception:
                pass
        except Exception:
            pass
