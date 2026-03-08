"""
Dice Auto-Apply Bot
Automates job search and Easy Apply on Dice.com.
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
    DICE_EMAIL, DICE_PASSWORD, SEARCH_QUERIES,
    LOCATIONS, DICE_TARGET, RESUME_PATH, PERSONAL_INFO
)
from tracker import is_already_applied, record_application, record_failure, get_today_count
from utils import logger, human_delay, safe_click, safe_send_keys, scroll_down


class DiceBot:
    def __init__(self, driver):
        self.driver = driver
        self.applied_count = 0
        self.wait = WebDriverWait(driver, 15)

    def login(self):
        logger.info("Dice: Logging in...")
        self.driver.get("https://www.dice.com/dashboard/login")
        human_delay(3, 5)

        # Check if already logged in
        if "dashboard" in self.driver.current_url and "login" not in self.driver.current_url:
            logger.info("Dice: Already logged in!")
            return True

        try:
            # Email field
            email_field = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='email'], input[type='email']")
            ))
            safe_send_keys(email_field, DICE_EMAIL)
            human_delay(0.5, 1)

            # Sign in button (email step)
            try:
                submit_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "button[type='submit'], button.btn-next"
                )
                safe_click(self.driver, submit_btn)
                human_delay(2, 3)
            except NoSuchElementException:
                pass

            # Password field
            try:
                pass_field = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='password'], input[name='password']")
                ))
                safe_send_keys(pass_field, DICE_PASSWORD)
                human_delay(0.5, 1)

                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                safe_click(self.driver, submit_btn)
                human_delay(3, 5)
            except TimeoutException:
                logger.warning("Dice: No password field found, might need manual login")
                input("Press Enter after completing Dice login...")

            if "login" not in self.driver.current_url.lower():
                logger.info("Dice: Login successful!")
                return True
            else:
                logger.warning("Dice: Login may have failed. Please check browser.")
                input("Press Enter when logged in...")
                return True

        except Exception as e:
            logger.error(f"Dice: Login failed - {e}")
            input("Press Enter after logging into Dice manually...")
            return True

    def search_jobs(self, query, location):
        logger.info(f"Dice: Searching '{query}' in '{location}'")

        query_param = query.replace(" ", "%20")
        location_param = location.replace(" ", "%20")

        # Dice search URL with Easy Apply filter and posted today
        search_url = (
            f"https://www.dice.com/jobs?"
            f"q={query_param}"
            f"&location={location_param}"
            f"&filters.easyApply=true"
            f"&filters.postedDate=ONE"  # Past 24 hours
            f"&page=1"
            f"&pageSize=20"
        )

        self.driver.get(search_url)
        human_delay(3, 5)

    def get_job_listings(self):
        try:
            for _ in range(3):
                scroll_down(self.driver, 400)
                human_delay(0.5, 1)

            # Dice uses shadow DOM in some cases, try multiple selectors
            job_cards = self.driver.find_elements(
                By.CSS_SELECTOR, "dhi-search-card, .card-search-result, a.card-title-link"
            )

            # If shadow DOM cards, try another approach
            if not job_cards:
                job_cards = self.driver.find_elements(
                    By.CSS_SELECTOR, "[data-cy='search-card'], .search-card"
                )

            # Fallback: find all job links
            if not job_cards:
                job_cards = self.driver.find_elements(
                    By.CSS_SELECTOR, "a[href*='/job-detail/']"
                )

            logger.info(f"Dice: Found {len(job_cards)} job cards")
            return job_cards
        except Exception as e:
            logger.error(f"Dice: Error getting listings - {e}")
            return []

    def apply_to_job(self, job_card):
        try:
            # Get job link
            try:
                if job_card.tag_name == "a":
                    job_link = job_card
                else:
                    job_link = job_card.find_element(By.CSS_SELECTOR, "a[href*='/job-detail/'], a.card-title-link")

                job_url = job_link.get_attribute("href")
                job_title = job_link.text.strip() or "Unknown"
                job_id = job_url.split("/job-detail/")[-1].split("?")[0] if "/job-detail/" in job_url else str(hash(job_url))
            except Exception:
                job_title = "Unknown"
                job_id = str(hash(str(time.time())))
                job_url = ""

            # Get company name
            try:
                company_el = job_card.find_element(By.CSS_SELECTOR, ".card-company a, [data-cy='search-result-company-name']")
                company = company_el.text.strip()
            except NoSuchElementException:
                company = "Unknown"

            if is_already_applied(job_id, "dice"):
                logger.info(f"Dice: Already applied to {job_title} at {company}, skipping")
                return False

            # Navigate to job detail page
            if job_url:
                self.driver.get(job_url)
            else:
                safe_click(self.driver, job_card)
            human_delay(2, 4)

            # Find the Easy Apply / Apply button
            applied = False
            try:
                apply_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "apply-button-wc, button.btn-apply, a.apply-button, [data-cy='apply-button'], button.seds-button-primary")
                ))
                safe_click(self.driver, apply_btn)
                human_delay(2, 4)

                applied = self._handle_dice_apply()
            except (TimeoutException, NoSuchElementException):
                # Try shadow DOM approach for Dice
                try:
                    apply_btn = self.driver.execute_script("""
                        const applyWc = document.querySelector('apply-button-wc');
                        if (applyWc && applyWc.shadowRoot) {
                            return applyWc.shadowRoot.querySelector('button');
                        }
                        return null;
                    """)
                    if apply_btn:
                        self.driver.execute_script("arguments[0].click();", apply_btn)
                        human_delay(2, 4)
                        applied = self._handle_dice_apply()
                    else:
                        logger.info(f"Dice: No apply button for {job_title}")
                        return False
                except Exception:
                    logger.info(f"Dice: Could not find apply button for {job_title}")
                    return False

            if applied:
                record_application({
                    "job_id": job_id,
                    "platform": "dice",
                    "title": job_title,
                    "company": company,
                    "url": job_url or self.driver.current_url,
                })
                self.applied_count += 1
                logger.info(f"Dice: ✓ Applied to {job_title} at {company} ({self.applied_count} today)")
                return True
            else:
                record_failure({
                    "job_id": job_id,
                    "platform": "dice",
                    "title": job_title,
                    "company": company,
                }, "Failed to complete Dice apply flow")
                return False

        except Exception as e:
            logger.error(f"Dice: Error applying - {e}")
            return False

    def _handle_dice_apply(self):
        max_steps = 8

        for step in range(max_steps):
            human_delay(1.5, 2.5)

            # Check for new tab/window
            if len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[-1])

            # Fill form fields
            self._fill_form_fields()

            # Upload resume if needed
            self._upload_resume()

            # Look for Submit / Apply / Next buttons
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, input[type='submit']")
                for btn in buttons:
                    btn_text = btn.text.lower().strip()
                    btn_value = (btn.get_attribute("value") or "").lower()

                    if any(kw in btn_text or kw in btn_value for kw in ["submit", "apply now", "apply"]):
                        safe_click(self.driver, btn)
                        human_delay(2, 3)

                        # Close extra tab if opened
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])

                        return True

                    elif any(kw in btn_text or kw in btn_value for kw in ["next", "continue"]):
                        safe_click(self.driver, btn)
                        human_delay(1.5, 2.5)
                        break
            except Exception:
                pass

            # Dice-specific: Check for "Already Applied" message
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if "already applied" in page_text or "application submitted" in page_text:
                    logger.info("Dice: Already applied / Application submitted")
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                    return True
            except Exception:
                pass

        # Cleanup
        if len(self.driver.window_handles) > 1:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

        return False

    def _fill_form_fields(self):
        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='tel'], input[type='email'], input[type='number']")
            for inp in inputs:
                if inp.get_attribute("value"):
                    continue

                label = self._get_label(inp)
                value = self._get_answer(label)
                if value:
                    safe_send_keys(inp, value)
                    human_delay(0.3, 0.6)

            # Textareas (cover letter etc.)
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            for ta in textareas:
                if ta.get_attribute("value"):
                    continue
                label = self._get_label(ta)
                if any(kw in label.lower() for kw in ["cover", "letter", "message", "note"]):
                    safe_send_keys(ta, f"I am excited to apply for this position. With {PERSONAL_INFO['years_of_experience']} years of software development experience, I bring strong technical skills in Python, cloud technologies, and full-stack development. I am authorized to work in the US and available to start immediately.")

            # Selects
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            for select in selects:
                from selenium.webdriver.support.ui import Select
                sel = Select(select)
                label = self._get_label(select).lower()

                if "sponsor" in label:
                    self._select_option(sel, ["no"])
                elif "authorized" in label or "authorization" in label:
                    self._select_option(sel, ["yes"])
                elif "experience" in label:
                    self._select_option(sel, [PERSONAL_INFO["years_of_experience"]])
                elif len(sel.options) > 1:
                    sel.select_by_index(1)

        except Exception as e:
            logger.debug(f"Dice: Form fill issue - {e}")

    def _get_label(self, element):
        try:
            el_id = element.get_attribute("id")
            if el_id:
                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{el_id}']")
                return label.text
        except Exception:
            pass
        try:
            return element.get_attribute("aria-label") or element.get_attribute("placeholder") or element.get_attribute("name") or ""
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

    def _upload_resume(self):
        try:
            upload_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for upload in upload_inputs:
                if not upload.get_attribute("value"):
                    upload.send_keys(os.path.abspath(RESUME_PATH))
                    human_delay(1, 2)
                    logger.debug("Dice: Resume uploaded")
        except Exception as e:
            logger.debug(f"Dice: Resume upload issue - {e}")

    def _paginate(self):
        try:
            next_btn = self.driver.find_element(
                By.CSS_SELECTOR, "a[aria-label='Next'], li.pagination-next a, button[aria-label='Next']"
            )
            safe_click(self.driver, next_btn)
            human_delay(2, 3)
            return True
        except NoSuchElementException:
            return False

    def run(self):
        logger.info("=" * 60)
        logger.info("Dice Auto-Apply Bot Starting...")
        logger.info("=" * 60)

        if not self.login():
            logger.error("Dice: Could not log in")
            return 0

        total_applied = get_today_count("dice")

        for query in SEARCH_QUERIES:
            if total_applied >= DICE_TARGET:
                break

            for location in LOCATIONS:
                if total_applied >= DICE_TARGET:
                    break

                self.search_jobs(query, location)

                pages_searched = 0
                max_pages = 5

                while pages_searched < max_pages and total_applied < DICE_TARGET:
                    job_cards = self.get_job_listings()

                    if not job_cards:
                        break

                    for card in job_cards:
                        if total_applied >= DICE_TARGET:
                            break
                        try:
                            if self.apply_to_job(card):
                                total_applied += 1
                        except StaleElementReferenceException:
                            continue
                        except Exception as e:
                            logger.debug(f"Dice: Skipping card - {e}")
                            continue

                    if not self._paginate():
                        break
                    pages_searched += 1

        logger.info(f"Dice: Done! Applied to {self.applied_count} jobs this session")
        return self.applied_count
