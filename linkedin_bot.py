"""
LinkedIn Easy Apply Bot
Automates job search and Easy Apply on LinkedIn.
"""
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException
)

from config import (
    LINKEDIN_EMAIL, LINKEDIN_PASSWORD, SEARCH_QUERIES,
    LOCATIONS, LINKEDIN_TARGET, RESUME_PATH, PERSONAL_INFO
)
from tracker import is_already_applied, record_application, record_failure, get_today_count
from utils import logger, human_delay, safe_click, safe_send_keys, scroll_down


class LinkedInBot:
    def __init__(self, driver):
        self.driver = driver
        self.applied_count = 0
        self.wait = WebDriverWait(driver, 15)

    def login(self):
        logger.info("LinkedIn: Logging in...")
        self.driver.get("https://www.linkedin.com/login")
        human_delay(2, 4)

        # Check if already logged in
        if "feed" in self.driver.current_url:
            logger.info("LinkedIn: Already logged in!")
            return True

        try:
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            safe_send_keys(email_field, LINKEDIN_EMAIL)
            human_delay(0.5, 1)

            pass_field = self.driver.find_element(By.ID, "password")
            safe_send_keys(pass_field, LINKEDIN_PASSWORD)
            human_delay(0.5, 1)

            submit = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            safe_click(self.driver, submit)
            human_delay(3, 5)

            # Handle security checkpoint if any
            if "checkpoint" in self.driver.current_url:
                logger.warning("LinkedIn: Security checkpoint detected! Please solve manually.")
                input("Press Enter after solving the checkpoint...")

            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                logger.info("LinkedIn: Login successful!")
                return True
            else:
                logger.warning(f"LinkedIn: May need manual intervention. Current URL: {self.driver.current_url}")
                input("Press Enter when you're logged in...")
                return True

        except Exception as e:
            logger.error(f"LinkedIn: Login failed - {e}")
            return False

    def search_jobs(self, query, location):
        logger.info(f"LinkedIn: Searching '{query}' in '{location}'")

        # Build search URL with Easy Apply filter
        search_url = (
            f"https://www.linkedin.com/jobs/search/?"
            f"keywords={query.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20')}"
            f"&f_AL=true"  # Easy Apply filter
            f"&f_TPR=r86400"  # Past 24 hours
            f"&sortBy=DD"  # Most recent
        )

        self.driver.get(search_url)
        human_delay(3, 5)

    def get_job_listings(self):
        jobs = []
        try:
            # Scroll to load all jobs
            for _ in range(3):
                scroll_down(self.driver, 500)
                human_delay(1, 2)

            job_cards = self.driver.find_elements(
                By.CSS_SELECTOR, ".job-card-container, .jobs-search-results__list-item"
            )
            logger.info(f"LinkedIn: Found {len(job_cards)} job cards")
            return job_cards
        except Exception as e:
            logger.error(f"LinkedIn: Error getting job listings - {e}")
            return jobs

    def apply_to_job(self, job_card):
        try:
            # Click job card to open details
            safe_click(self.driver, job_card)
            human_delay(2, 3)

            # Get job info
            try:
                title_el = self.driver.find_element(
                    By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title"
                )
                title = title_el.text.strip()
            except NoSuchElementException:
                title = "Unknown"

            try:
                company_el = self.driver.find_element(
                    By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name"
                )
                company = company_el.text.strip()
            except NoSuchElementException:
                company = "Unknown"

            # Get job ID from URL
            current_url = self.driver.current_url
            job_id = current_url.split("currentJobId=")[-1].split("&")[0] if "currentJobId=" in current_url else current_url.split("/view/")[-1].split("/")[0] if "/view/" in current_url else str(hash(title + company))

            if is_already_applied(job_id, "linkedin"):
                logger.info(f"LinkedIn: Already applied to {title} at {company}, skipping")
                return False

            # Find Easy Apply button
            try:
                apply_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".jobs-apply-button, button.jobs-apply-button--top-card")
                ))

                if "Easy Apply" not in apply_btn.text and "easy apply" not in apply_btn.text.lower():
                    logger.info(f"LinkedIn: {title} at {company} - Not Easy Apply, skipping")
                    return False

                safe_click(self.driver, apply_btn)
                human_delay(2, 3)

            except (TimeoutException, NoSuchElementException):
                logger.info(f"LinkedIn: No Easy Apply button for {title} at {company}")
                return False

            # Handle the Easy Apply modal
            applied = self._handle_easy_apply_modal()

            if applied:
                record_application({
                    "job_id": job_id,
                    "platform": "linkedin",
                    "title": title,
                    "company": company,
                    "url": current_url,
                })
                self.applied_count += 1
                logger.info(f"LinkedIn: ✓ Applied to {title} at {company} ({self.applied_count} today)")
                return True
            else:
                record_failure({
                    "job_id": job_id,
                    "platform": "linkedin",
                    "title": title,
                    "company": company,
                }, "Failed to complete Easy Apply flow")
                return False

        except Exception as e:
            logger.error(f"LinkedIn: Error applying to job - {e}")
            return False

    def _handle_easy_apply_modal(self):
        max_pages = 8
        for page in range(max_pages):
            human_delay(1, 2)

            # Fill form fields on current page
            self._fill_form_fields()

            # Upload resume if prompted
            self._upload_resume_if_needed()

            # Check for Submit button
            try:
                submit_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label='Submit application'], button[aria-label='Review your application']"
                )
                if "Submit" in submit_btn.text:
                    safe_click(self.driver, submit_btn)
                    human_delay(2, 3)
                    # Dismiss success modal
                    try:
                        dismiss = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                        safe_click(self.driver, dismiss)
                    except NoSuchElementException:
                        pass
                    return True
                elif "Review" in submit_btn.text:
                    safe_click(self.driver, submit_btn)
                    human_delay(1, 2)
                    continue
            except NoSuchElementException:
                pass

            # Click Next button
            try:
                next_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label='Continue to next step'], button[data-easy-apply-next-button]"
                )
                safe_click(self.driver, next_btn)
                human_delay(1, 2)
            except NoSuchElementException:
                # Try generic next button
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, ".artdeco-button--primary")
                    for btn in buttons:
                        if any(kw in btn.text.lower() for kw in ["next", "continue", "review", "submit"]):
                            safe_click(self.driver, btn)
                            human_delay(1, 2)
                            if "submit" in btn.text.lower():
                                try:
                                    dismiss = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                                    safe_click(self.driver, dismiss)
                                except NoSuchElementException:
                                    pass
                                return True
                            break
                except Exception:
                    pass

        # If we didn't submit, close the modal
        self._close_modal()
        return False

    def _fill_form_fields(self):
        try:
            # Text inputs
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='tel'], input[type='email'], input[type='number']")
            for inp in inputs:
                if inp.get_attribute("value"):
                    continue
                label = ""
                try:
                    label_id = inp.get_attribute("id")
                    label_el = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{label_id}']")
                    label = label_el.text.lower()
                except Exception:
                    pass

                value = self._get_answer_for_field(label)
                if value:
                    safe_send_keys(inp, value)
                    human_delay(0.3, 0.6)

            # Select dropdowns
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            for select in selects:
                from selenium.webdriver.support.ui import Select
                sel = Select(select)
                label = ""
                try:
                    label_id = select.get_attribute("id")
                    label_el = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{label_id}']")
                    label = label_el.text.lower()
                except Exception:
                    pass

                # Try to select the best option
                if "yes" in label or "authorization" in label or "authorized" in label or "eligible" in label:
                    for opt in sel.options:
                        if "yes" in opt.text.lower():
                            sel.select_by_visible_text(opt.text)
                            break
                elif "sponsor" in label:
                    for opt in sel.options:
                        if "no" in opt.text.lower():
                            sel.select_by_visible_text(opt.text)
                            break
                elif "experience" in label or "years" in label:
                    for opt in sel.options:
                        if PERSONAL_INFO["years_of_experience"] in opt.text:
                            sel.select_by_visible_text(opt.text)
                            break
                elif len(sel.options) > 1:
                    sel.select_by_index(1)  # Select first non-empty option

            # Radio buttons - try to answer Yes for work authorization, No for sponsorship
            radios = self.driver.find_elements(By.CSS_SELECTOR, "fieldset")
            for fieldset in radios:
                try:
                    legend = fieldset.find_element(By.TAG_NAME, "legend").text.lower()
                    radio_buttons = fieldset.find_elements(By.CSS_SELECTOR, "input[type='radio']")

                    if "sponsor" in legend:
                        for rb in radio_buttons:
                            label_text = rb.find_element(By.XPATH, "..").text.lower()
                            if "no" in label_text:
                                safe_click(self.driver, rb)
                                break
                    elif "authorized" in legend or "authorization" in legend or "eligible" in legend or "legally" in legend:
                        for rb in radio_buttons:
                            label_text = rb.find_element(By.XPATH, "..").text.lower()
                            if "yes" in label_text:
                                safe_click(self.driver, rb)
                                break
                    elif "relocat" in legend:
                        for rb in radio_buttons:
                            label_text = rb.find_element(By.XPATH, "..").text.lower()
                            if "yes" in label_text:
                                safe_click(self.driver, rb)
                                break
                    elif "commut" in legend:
                        for rb in radio_buttons:
                            label_text = rb.find_element(By.XPATH, "..").text.lower()
                            if "yes" in label_text:
                                safe_click(self.driver, rb)
                                break
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"LinkedIn: Form fill issue - {e}")

    def _get_answer_for_field(self, label):
        label = label.lower()
        info = PERSONAL_INFO

        mapping = {
            "first name": info["first_name"],
            "last name": info["last_name"],
            "email": info["email"],
            "phone": info["phone"],
            "mobile": info["phone"],
            "city": info["city"],
            "state": info["state"],
            "zip": info["zip"],
            "linkedin": info["linkedin_url"],
            "github": info["github_url"],
            "portfolio": info["portfolio_url"],
            "website": info["portfolio_url"],
            "salary": info["salary_expectation"],
            "compensation": info["salary_expectation"],
            "experience": info["years_of_experience"],
            "years": info["years_of_experience"],
            "gpa": "3.5",
        }

        for key, value in mapping.items():
            if key in label and value:
                return value
        return None

    def _upload_resume_if_needed(self):
        try:
            upload_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for upload in upload_inputs:
                if not upload.get_attribute("value"):
                    upload.send_keys(os.path.abspath(RESUME_PATH))
                    human_delay(1, 2)
                    logger.debug("LinkedIn: Resume uploaded")
        except Exception as e:
            logger.debug(f"LinkedIn: Resume upload issue - {e}")

    def _close_modal(self):
        try:
            close_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
            safe_click(self.driver, close_btn)
            human_delay(0.5, 1)
            # Confirm discard
            try:
                discard_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "button[data-control-name='discard_application_confirm_btn']"
                )
                safe_click(self.driver, discard_btn)
            except NoSuchElementException:
                # Try by text
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "discard" in btn.text.lower():
                        safe_click(self.driver, btn)
                        break
        except Exception:
            pass

    def _paginate(self):
        try:
            next_page = self.driver.find_element(
                By.CSS_SELECTOR, "button[aria-label='View next page'], li.artdeco-pagination__indicator--number.active + li button"
            )
            safe_click(self.driver, next_page)
            human_delay(2, 3)
            return True
        except NoSuchElementException:
            return False

    def run(self):
        logger.info("=" * 60)
        logger.info("LinkedIn Easy Apply Bot Starting...")
        logger.info("=" * 60)

        if not self.login():
            logger.error("LinkedIn: Could not log in")
            return 0

        total_applied = get_today_count("linkedin")

        for query in SEARCH_QUERIES:
            if total_applied >= LINKEDIN_TARGET:
                break

            for location in LOCATIONS:
                if total_applied >= LINKEDIN_TARGET:
                    break

                self.search_jobs(query, location)

                pages_searched = 0
                max_pages = 5

                while pages_searched < max_pages and total_applied < LINKEDIN_TARGET:
                    job_cards = self.get_job_listings()

                    if not job_cards:
                        break

                    for card in job_cards:
                        if total_applied >= LINKEDIN_TARGET:
                            break
                        try:
                            if self.apply_to_job(card):
                                total_applied += 1
                        except StaleElementReferenceException:
                            continue
                        except Exception as e:
                            logger.debug(f"LinkedIn: Skipping job card - {e}")
                            continue

                    if not self._paginate():
                        break
                    pages_searched += 1

        logger.info(f"LinkedIn: Done! Applied to {self.applied_count} jobs this session")
        return self.applied_count
