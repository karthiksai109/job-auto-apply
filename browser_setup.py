"""
Browser setup with anti-detection measures using undetected-chromedriver.
"""
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from config import HEADLESS, USER_AGENT, PAGE_LOAD_TIMEOUT, IMPLICIT_WAIT


def create_driver():
    options = uc.ChromeOptions()

    if HEADLESS:
        options.add_argument("--headless=new")

    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    # Persistent profile to retain login sessions
    options.add_argument("--user-data-dir=./chrome_profile")

    driver = uc.Chrome(options=options, version_main=None)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)

    return driver
