"""
Indeed Auto-Apply Bot
Automates job search and application on Indeed.
"""
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException
)

from config import (
    INDEED_EMAIL, INDEED_PASSWORD, SEARCH_QUERIES,
    LOCATIONS, INDEED_TARGET, RESUME_PATH, PERSONAL_INFO
)
from tracker import is_already_applied, record_application, record_failure, get_today_count
from utils import logger, human_delay, safe_click, safe_send_keys, scroll_down


class IndeedBot:
    def __init__(self, driver):
        self.driver = driver
        self.applied_count = 0
        self.wait = WebDriverWait(driver, 15)

    def login(self):
        logger.info("Indeed: Logging in...")
        self.driver.get("https://secure.indeed.com/auth")
        human_delay(3, 5)

        # Check if already logged in
        if "secure.indeed.com/auth" not in self.driver.current_url and "indeed.com" in self.driver.current_url:
            logger.info("Indeed: Already logged in!")
            return True

        try:
            # Indeed login flow - email first
            try:
                email_field = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='email'], input[name='__email'], #ifl-InputFormField-3")
                ))
                safe_send_keys(email_field, INDEED_EMAIL)
                human_delay(0.5, 1)

                # Submit email
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                safe_click(self.driver, submit_btn)
                human_delay(3, 5)
            except Exception:
                pass

            # Password step (if not using magic link)
            try:
                pass_field = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='password']")
                ))
                safe_send_keys(pass_field, INDEED_PASSWORD)
                human_delay(0.5, 1)

                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                safe_click(self.driver, submit_btn)
                human_delay(3, 5)
            except TimeoutException:
                logger.warning("Indeed: May need verification. Check browser.")
                input("Press Enter after completing Indeed login...")

            # Handle CAPTCHA or verification
            if "verify" in self.driver.current_url.lower() or "challenge" in self.driver.current_url.lower():
                logger.warning("Indeed: Verification required! Please complete it manually.")
                input("Press Enter after completing verification...")

            logger.info("Indeed: Login successful!")
            return True

        except Exception as e:
            logger.error(f"Indeed: Login failed - {e}")
            logger.info("Indeed: Please login manually in the browser")
            input("Press Enter when logged in...")
            return True

    def search_jobs(self, query, location):
        logger.info(f"Indeed: Searching '{query}' in '{location}'")

        # Use Indeed's search URL
        location_param = location.replace(" ", "+")
        query_param = query.replace(" ", "+")

        search_url = (
            f"https://www.indeed.com/jobs?"
            f"q={query_param}"
            f"&l={location_param}"
            f"&fromage=1"  # Last 24 hours
            f"&sort=date"
        )

        self.driver.get(search_url)
        human_delay(3, 5)

    def get_job_listings(self):
        try:
            for _ in range(3):
                scroll_down(self.driver, 400)
                human_delay(0.5, 1)

            job_cards = self.driver.find_elements(
                By.CSS_SELECTOR, ".job_seen_beacon, .tapItem, .resultContent, div[data-jk]"
            )
            logger.info(f"Indeed: Found {len(job_cards)} job cards")
            return job_cards
        except Exception as e:
            logger.error(f"Indeed: Error getting listings - {e}")
            return []

    def apply_to_job(self, job_card):
        try:
            # Click on the job card
            try:
                title_link = job_card.find_element(By.CSS_SELECTOR, "a.jcs-JobTitle, h2.jobTitle a, a[data-jk]")
                job_title = title_link.text.strip()
                job_id = title_link.get_attribute("data-jk") or title_link.get_attribute("id") or str(hash(job_title))
            except NoSuchElementException:
                safe_click(self.driver, job_card)
                job_title = "Unknown"
                job_id = str(hash(str(time.time())))
                human_delay(1, 2)
                return False

            # Try to get company name
            try:
                company_el = job_card.find_element(By.CSS_SELECTOR, ".companyName, [data-testid='company-name'], .company")
                company = company_el.text.strip()
            except NoSuchElementException:
                company = "Unknown"

            if is_already_applied(job_id, "indeed"):
                logger.info(f"Indeed: Already applied to {job_title} at {company}, skipping")
                return False

            safe_click(self.driver, title_link)
            human_delay(2, 3)

            # Look for Apply button in the job details panel
            applied = False

            # Try "Apply now" button (Indeed Easy Apply)
            try:
                apply_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#indeedApplyButton, button.indeed-apply-button, .ia-IndeedApplyButton, button[id*='apply'], a[href*='apply']")
                ))

                # Check if it's an Indeed Apply vs external
                btn_text = apply_btn.text.lower()
                if "apply" in btn_text:
                    safe_click(self.driver, apply_btn)
                    human_delay(3, 5)

                    # Handle the apply flow
                    applied = self._handle_indeed_apply()
                else:
                    logger.info(f"Indeed: {job_title} - External application, skipping")
                    return False

            except (TimeoutException, NoSuchElementException):
                logger.info(f"Indeed: No apply button found for {job_title}")
                return False

            if applied:
                record_application({
                    "job_id": job_id,
                    "platform": "indeed",
                    "title": job_title,
                    "company": company,
                    "url": self.driver.current_url,
                })
                self.applied_count += 1
                logger.info(f"Indeed: ✓ Applied to {job_title} at {company} ({self.applied_count} today)")
                return True
            else:
                record_failure({
                    "job_id": job_id,
                    "platform": "indeed",
                    "title": job_title,
                    "company": company,
                }, "Failed to complete Indeed apply flow")
                return False

        except Exception as e:
            logger.error(f"Indeed: Error applying - {e}")
            return False

    def _handle_indeed_apply(self):
        max_steps = 10

        for step in range(max_steps):
            human_delay(1.5, 2.5)

            # Check if we're in an iframe
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    if "indeed" in (iframe.get_attribute("src") or "").lower():
                        self.driver.switch_to.frame(iframe)
                        break
            except Exception:
                pass

            # Fill form fields
            self._fill_form_fields()

            # Upload resume if needed
            self._upload_resume()

            # Check for submit/continue buttons
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, a.ia-continueButton")
                for btn in buttons:
                    btn_text = btn.text.lower().strip()

                    if "submit" in btn_text or "apply" in btn_text and "continue" not in btn_text:
                        safe_click(self.driver, btn)
                        human_delay(2, 3)

                        # Check for success
                        try:
                            self.driver.switch_to.default_content()
                        except Exception:
                            pass

                        return True

                    elif "continue" in btn_text or "next" in btn_text:
                        safe_click(self.driver, btn)
                        human_delay(1.5, 2.5)
                        break
            except Exception:
                pass

            # Also try the specific Indeed apply continue button
            try:
                continue_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "button[data-testid='continue-button'], .ia-continueButton, button.ia-continueButton"
                )
                safe_click(self.driver, continue_btn)
                human_delay(1.5, 2.5)
            except NoSuchElementException:
                pass

        # Switch back to main content
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        return False

    def _fill_form_fields(self):
        try:
            # Text inputs
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='tel'], input[type='email'], input[type='number']")
            for inp in inputs:
                if inp.get_attribute("value"):
                    continue

                label = self._get_label(inp)
                value = self._get_answer(label)
                if value:
                    safe_send_keys(inp, value)
                    human_delay(0.3, 0.6)

            # Textareas
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            for ta in textareas:
                if ta.get_attribute("value"):
                    continue
                label = self._get_label(ta)
                if "cover" in label.lower() or "letter" in label.lower():
                    safe_send_keys(ta, f"I am excited to apply for this position. With {PERSONAL_INFO['years_of_experience']} years of experience in software development, I bring strong technical skills and a passion for building quality software. I am authorized to work in the United States and available to start immediately.")

            # Select dropdowns
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            for select in selects:
                from selenium.webdriver.support.ui import Select
                sel = Select(select)
                label = self._get_label(select).lower()

                if "sponsor" in label:
                    self._select_option(sel, ["no"])
                elif "authorized" in label or "authorization" in label or "eligible" in label or "legally" in label:
                    self._select_option(sel, ["yes"])
                elif "experience" in label or "years" in label:
                    self._select_option(sel, [PERSONAL_INFO["years_of_experience"], "3", "2-4", "1-3"])
                elif "education" in label or "degree" in label:
                    self._select_option(sel, ["master", "bachelor"])
                elif "relocat" in label:
                    self._select_option(sel, ["yes"])
                elif len(sel.options) > 1:
                    sel.select_by_index(1)

            # Radio buttons
            fieldsets = self.driver.find_elements(By.CSS_SELECTOR, "fieldset, .ia-Questions-item")
            for fs in fieldsets:
                try:
                    question = fs.text.lower()
                    radios = fs.find_elements(By.CSS_SELECTOR, "input[type='radio']")

                    if "sponsor" in question:
                        self._click_radio_with_text(radios, "no")
                    elif "authorized" in question or "authorization" in question or "eligible" in question:
                        self._click_radio_with_text(radios, "yes")
                    elif "relocat" in question or "commute" in question:
                        self._click_radio_with_text(radios, "yes")
                    elif "18" in question or "age" in question:
                        self._click_radio_with_text(radios, "yes")
                    elif "background" in question and "check" in question:
                        self._click_radio_with_text(radios, "yes")
                    elif "drug" in question and "test" in question:
                        self._click_radio_with_text(radios, "yes")
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Indeed: Form fill issue - {e}")

    def _get_label(self, element):
        try:
            el_id = element.get_attribute("id")
            if el_id:
                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{el_id}']")
                return label.text
        except Exception:
            pass
        try:
            return element.get_attribute("aria-label") or element.get_attribute("placeholder") or ""
        except Exception:
            return ""

    def _get_answer(self, label):
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
            "pay": info["salary_expectation"],
            "experience": info["years_of_experience"],
            "years": info["years_of_experience"],
            "linkedin": info["linkedin_url"],
            "github": info["github_url"],
        }
        for key, value in mapping.items():
            if key in label_lower and value:
                return value
        return None

    def _select_option(self, select_el, preferred_texts):
        for pref in preferred_texts:
            for opt in select_el.options:
                if pref.lower() in opt.text.lower():
                    select_el.select_by_visible_text(opt.text)
                    return
        if len(select_el.options) > 1:
            select_el.select_by_index(1)

    def _click_radio_with_text(self, radios, target_text):
        for radio in radios:
            try:
                parent_text = radio.find_element(By.XPATH, "..").text.lower()
                if target_text.lower() in parent_text:
                    safe_click(self.driver, radio)
                    return
            except Exception:
                continue

    def _upload_resume(self):
        try:
            upload_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for upload in upload_inputs:
                if not upload.get_attribute("value"):
                    upload.send_keys(os.path.abspath(RESUME_PATH))
                    human_delay(1, 2)
                    logger.debug("Indeed: Resume uploaded")
        except Exception as e:
            logger.debug(f"Indeed: Resume upload issue - {e}")

    def _paginate(self):
        try:
            next_link = self.driver.find_element(
                By.CSS_SELECTOR, "a[data-testid='pagination-page-next'], a[aria-label='Next Page'], .np"
            )
            safe_click(self.driver, next_link)
            human_delay(2, 3)
            return True
        except NoSuchElementException:
            return False

    def run(self):
        logger.info("=" * 60)
        logger.info("Indeed Auto-Apply Bot Starting...")
        logger.info("=" * 60)

        if not self.login():
            logger.error("Indeed: Could not log in")
            return 0

        total_applied = get_today_count("indeed")

        for query in SEARCH_QUERIES:
            if total_applied >= INDEED_TARGET:
                break

            for location in LOCATIONS:
                if total_applied >= INDEED_TARGET:
                    break

                self.search_jobs(query, location)

                pages_searched = 0
                max_pages = 5

                while pages_searched < max_pages and total_applied < INDEED_TARGET:
                    job_cards = self.get_job_listings()

                    if not job_cards:
                        break

                    for card in job_cards:
                        if total_applied >= INDEED_TARGET:
                            break
                        try:
                            if self.apply_to_job(card):
                                total_applied += 1
                        except StaleElementReferenceException:
                            continue
                        except Exception as e:
                            logger.debug(f"Indeed: Skipping card - {e}")
                            continue

                    if not self._paginate():
                        break
                    pages_searched += 1

        logger.info(f"Indeed: Done! Applied to {self.applied_count} jobs this session")
        return self.applied_count
