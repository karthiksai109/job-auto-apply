"""
Configuration for the Job Auto-Apply Bot
Fill in your credentials and preferences below.
"""
import os
from pathlib import Path

# ============================================================
# RESUME
# ============================================================
RESUME_PATH = r"C:\Users\karth\OneDrive\Desktop\updated_resume_hackathon.pdf"

# ============================================================
# JOB SEARCH SETTINGS
# ============================================================
SEARCH_QUERIES = [
    "Software Engineer",
    "Python Developer",
    "Full Stack Developer",
    "Backend Developer",
    "Software Developer",
    "Data Engineer",
    "Cloud Engineer",
    "DevOps Engineer",
]

LOCATIONS = [
    "United States",
    "Remote",
]

# Filter settings
EXPERIENCE_LEVEL = ["Entry level", "Associate", "Mid-Senior level"]
JOB_TYPE = ["Full-time", "Contract"]
REMOTE_FILTER = ["Remote", "Hybrid"]

# How many jobs to apply per platform per run
DAILY_TARGET = 50
LINKEDIN_TARGET = 20
INDEED_TARGET = 15
DICE_TARGET = 15

# ============================================================
# LINKEDIN CREDENTIALS
# ============================================================
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "YOUR_LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "YOUR_LINKEDIN_PASSWORD")

# ============================================================
# INDEED CREDENTIALS  (Indeed uses email-based login)
# ============================================================
INDEED_EMAIL = os.getenv("INDEED_EMAIL", "YOUR_INDEED_EMAIL")
INDEED_PASSWORD = os.getenv("INDEED_PASSWORD", "YOUR_INDEED_PASSWORD")

# ============================================================
# DICE CREDENTIALS
# ============================================================
DICE_EMAIL = os.getenv("DICE_EMAIL", "YOUR_DICE_EMAIL")
DICE_PASSWORD = os.getenv("DICE_PASSWORD", "YOUR_DICE_PASSWORD")

# ============================================================
# PERSONAL INFO FOR FORM FILLING
# ============================================================
PERSONAL_INFO = {
    "first_name": "Karthik",
    "last_name": "Ramadugu",
    "email": "",          # Fill in your email
    "phone": "",          # Fill in your phone
    "city": "Fairborn",
    "state": "Ohio",
    "zip": "",            # Fill in zip
    "country": "United States",
    "linkedin_url": "",   # Fill in your LinkedIn profile URL
    "github_url": "",     # Fill in your GitHub URL
    "portfolio_url": "",  # Optional
    "years_of_experience": "3",
    "work_authorization": "Yes",
    "sponsorship_needed": "No",
    "salary_expectation": "90000",
    "available_start": "Immediately",
    "education": "Master's",
    "willing_to_relocate": "Yes",
}

# ============================================================
# BROWSER SETTINGS
# ============================================================
HEADLESS = False  # Set True to run browser in background (less detectable if False)
SLOW_MO = 1.5    # Seconds between actions (human-like delay)
PAGE_LOAD_TIMEOUT = 30
IMPLICIT_WAIT = 10

# ============================================================
# APPLICATION TRACKING
# ============================================================
TRACKER_DB = os.path.join(os.path.dirname(__file__), "applied_jobs.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")

# ============================================================
# ANTI-DETECTION
# ============================================================
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
RANDOM_DELAY_MIN = 1.0
RANDOM_DELAY_MAX = 3.5
