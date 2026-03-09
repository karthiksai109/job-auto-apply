"""
Central configuration for the Multi-Agent Job Application System.
All agents read from this config + .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ============================================================
# PATHS
# ============================================================
BASE_DIR = Path(__file__).parent.parent
RESUME_PATH = os.getenv("RESUME_PATH", str(BASE_DIR / "resume.pdf"))
EXCEL_TRACKER_PATH = str(BASE_DIR / "job_applications.xlsx")
JOB_DB_PATH = str(BASE_DIR / "jobs_database.json")
LOG_DIR = str(BASE_DIR / "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ============================================================
# OPENAI / LLM SETTINGS (for AI agents)
# ============================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ============================================================
# EMAIL SETTINGS (for Agent 5 - Email Notifier)
# ============================================================
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")  # Gmail App Password
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")  # Your email to receive updates

# ============================================================
# PLATFORM CREDENTIALS
# ============================================================
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
INDEED_EMAIL = os.getenv("INDEED_EMAIL", "")
INDEED_PASSWORD = os.getenv("INDEED_PASSWORD", "")
DICE_EMAIL = os.getenv("DICE_EMAIL", "")
DICE_PASSWORD = os.getenv("DICE_PASSWORD", "")
MONSTER_EMAIL = os.getenv("MONSTER_EMAIL", "")
MONSTER_PASSWORD = os.getenv("MONSTER_PASSWORD", "")

# ============================================================
# JOB SEARCH PREFERENCES
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

EXPERIENCE_LEVEL = ["Entry level", "Associate", "Mid-Senior level"]
JOB_TYPE = ["Full-time", "Contract"]
REMOTE_FILTER = ["Remote", "Hybrid"]

# Daily targets
DAILY_TARGET = 30

# Minimum match score (0-100) to auto-apply
MIN_MATCH_SCORE = 60

# ============================================================
# PERSONAL INFO (for form auto-fill)
# ============================================================
PERSONAL_INFO = {
    "first_name": os.getenv("FIRST_NAME", "Karthik"),
    "last_name": os.getenv("LAST_NAME", "Ramadugu"),
    "email": os.getenv("PERSONAL_EMAIL", "karthiksaidham2001@gmail.com"),
    "phone": os.getenv("PERSONAL_PHONE", "+19375160692"),
    "city": os.getenv("CITY", "San Jose"),
    "state": os.getenv("STATE", "California"),
    "zip": os.getenv("ZIP_CODE", "95134"),
    "address": os.getenv("ADDRESS", "80 Descanso Dr, San Jose, CA 95134"),
    "country": "United States",
    "linkedin_url": os.getenv("LINKEDIN_URL", "https://www.linkedin.com/in/ramadugukarthik/"),
    "github_url": os.getenv("GITHUB_URL", "https://github.com/karthiksai109"),
    "portfolio_url": os.getenv("PORTFOLIO_URL", "https://karthikramadugu.vercel.app/"),
    "years_of_experience": os.getenv("YEARS_EXPERIENCE", "3"),
    "years_experience": os.getenv("YEARS_EXPERIENCE", "3"),
    "work_authorization": "Yes",
    "sponsorship_needed": "No",
    "salary_expectation": os.getenv("SALARY_EXPECTATION", "90000"),
    "available_start": "Immediately",
    "education": "Master's",
    "university": "Wright State University",
    "degree": "Master of Science in Computer Science",
    "graduation_year": "2025",
    "btech_year": "2022",
    "willing_to_relocate": "Yes",
    "dob": "2001-08-14",
    "us_entry_date": "2023-12-30",
    "opt_start": "2026-01-21",
}

# ============================================================
# BROWSER SETTINGS
# ============================================================
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
SLOW_MO = float(os.getenv("SLOW_MO", "1.5"))
PAGE_LOAD_TIMEOUT = 30
IMPLICIT_WAIT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
RANDOM_DELAY_MIN = 1.0
RANDOM_DELAY_MAX = 3.5

# ============================================================
# SCHEDULER SETTINGS
# ============================================================
SCRAPE_INTERVAL_HOURS = 6       # How often to scrape new jobs
APPLY_INTERVAL_HOURS = 4        # How often to run the apply cycle
STATUS_CHECK_INTERVAL_HOURS = 12 # How often to check application statuses
EMAIL_REPORT_INTERVAL_HOURS = 24 # How often to send email reports
EXCEL_SYNC_INTERVAL_MINUTES = 30 # How often to sync the Excel tracker

# ============================================================
# JOB STATUS ENUM
# ============================================================
class JobStatus:
    SCRAPED = "scraped"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED_TO_APPLY = "failed_to_apply"
    MANUAL_APPLY_NEEDED = "manual_apply_needed"
    SCREENING = "screening"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL_ROUND = "technical_round"
    ONSITE = "onsite"
    FINAL_ROUND = "final_round"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    NO_RESPONSE = "no_response"

    ALL = [
        SCRAPED, APPLYING, APPLIED, FAILED_TO_APPLY,
        MANUAL_APPLY_NEEDED,
        SCREENING, PHONE_SCREEN, TECHNICAL_ROUND,
        ONSITE, FINAL_ROUND, OFFER, REJECTED,
        WITHDRAWN, NO_RESPONSE,
    ]
