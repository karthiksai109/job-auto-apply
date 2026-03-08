"""
Utility functions for the auto-apply bot.
"""
import time
import random
import logging
from functools import wraps
from config import RANDOM_DELAY_MIN, RANDOM_DELAY_MAX, LOG_FILE


def setup_logger(name="AutoApplyBot"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


logger = setup_logger()


def human_delay(min_s=None, max_s=None):
    mn = min_s or RANDOM_DELAY_MIN
    mx = max_s or RANDOM_DELAY_MAX
    delay = random.uniform(mn, mx)
    time.sleep(delay)


def retry(max_attempts=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}")
                    if attempt < max_attempts:
                        time.sleep(delay * attempt)
                    else:
                        raise
        return wrapper
    return decorator


def safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        human_delay(0.3, 0.8)
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def safe_send_keys(element, text, clear_first=True):
    if clear_first:
        element.clear()
        human_delay(0.2, 0.5)
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.02, 0.08))


def scroll_down(driver, pixels=500):
    driver.execute_script(f"window.scrollBy(0, {pixels});")
    human_delay(0.5, 1.0)
