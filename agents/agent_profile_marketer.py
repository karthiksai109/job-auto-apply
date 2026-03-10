"""
Agent: Profile Marketer
Analyzes your profile strength, suggests improvements to attract recruiters,
generates optimized summaries, and tracks profile marketing metrics.
"""
import json
from datetime import datetime
from pathlib import Path
from agents.config import PERSONAL_INFO, BASE_DIR
from agents.resume_parser import get_parsed_resume, get_all_skills_flat
from agents.logger import get_logger

logger = get_logger("ProfileMarketer")

PROFILE_REPORT_PATH = str(BASE_DIR / "profile_marketing.json")


def _load_report() -> dict:
    try:
        with open(PROFILE_REPORT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_report(report: dict):
    with open(PROFILE_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)


def analyze_profile() -> dict:
    """
    Comprehensive profile analysis with actionable marketing recommendations.
    """
    resume = get_parsed_resume()
    skills = get_all_skills_flat()
    name = resume.get("name", "")
    title = resume.get("title", "")

    report = {
        "name": name,
        "current_title": title,
        "analyzed_at": datetime.now().isoformat(),
    }

    # ── Profile Strength Score ──
    strength = 0
    strength_details = []

    # Check completeness
    if PERSONAL_INFO.get("linkedin_url"):
        strength += 10
        strength_details.append("✅ LinkedIn URL configured")
    else:
        strength_details.append("❌ Missing LinkedIn URL")

    if PERSONAL_INFO.get("github_url"):
        strength += 10
        strength_details.append("✅ GitHub URL configured")
    else:
        strength_details.append("❌ Missing GitHub URL")

    if PERSONAL_INFO.get("portfolio_url"):
        strength += 10
        strength_details.append("✅ Portfolio URL configured")
    else:
        strength_details.append("❌ Missing Portfolio URL")

    if len(skills) >= 20:
        strength += 15
        strength_details.append(f"✅ Strong skill set ({len(skills)} skills)")
    elif len(skills) >= 10:
        strength += 10
        strength_details.append(f"⚠️ Good skill set ({len(skills)} skills) — add more niche skills")
    else:
        strength += 5
        strength_details.append(f"❌ Weak skill set ({len(skills)} skills) — needs expansion")

    resume_text = resume.get("raw_text", "")
    if "hackathon" in resume_text.lower() or "winner" in resume_text.lower() or "award" in resume_text.lower():
        strength += 15
        strength_details.append("✅ Achievements/awards present — strong differentiator")

    if any(kw in resume_text.lower() for kw in ["40%", "50%", "reduced", "improved", "increased", "optimized"]):
        strength += 15
        strength_details.append("✅ Quantified impact metrics in experience")
    else:
        strength_details.append("❌ Missing quantified impact — add metrics (%, time saved, etc.)")

    if len(resume_text) >= 3000:
        strength += 10
        strength_details.append("✅ Detailed resume content")
    else:
        strength_details.append("⚠️ Resume could be more detailed")

    if PERSONAL_INFO.get("education") or "master" in resume_text.lower():
        strength += 10
        strength_details.append("✅ Advanced degree (M.S. Computer Science)")

    if PERSONAL_INFO.get("work_authorization") == "Yes":
        strength += 5
        strength_details.append("✅ US work authorization — no sponsorship needed")

    report["profile_strength"] = min(strength, 100)
    report["strength_breakdown"] = strength_details

    # ── Optimized Headlines ──
    report["suggested_headlines"] = [
        "Python Full Stack Developer | React, Django, FastAPI, AWS | Hackathon Winner | M.S. CS",
        "Full Stack Software Engineer | Python, React, Node.js | Cloud-Native & AI/ML | Open to Opportunities",
        "Software Engineer | Python, AWS, Docker, Kubernetes | Building Scalable Systems | 1st Place Hackathon 2026",
        "Full Stack Developer | React, Angular, FastAPI | Microservices & Event-Driven Architecture | M.S. Computer Science",
    ]

    # ── Optimized Summary ──
    report["suggested_summary"] = (
        f"Python Full Stack Software Engineer with experience building scalable web applications "
        f"using React, Angular, Next.js, Flask, Django, and FastAPI. Won 1st place at Akash Open Agents "
        f"Hackathon 2026 building a decentralized AI health agent. Skilled in cloud-native development "
        f"(AWS, Docker, Kubernetes), CI/CD automation (GitHub Actions, Jenkins), event-driven systems "
        f"(Kafka, RabbitMQ), and modern AI tools (LangChain, OpenAI GPT-4, RAG). "
        f"M.S. Computer Science from University of Dayton. "
        f"Authorized to work in the US. Open to relocation. Available immediately."
    )

    # ── LinkedIn Optimization Tips ──
    report["linkedin_tips"] = [
        {
            "area": "Headline",
            "tip": "Use keyword-rich headline: 'Python Full Stack Developer | React, Django, FastAPI, AWS | Hackathon Winner'",
            "priority": "High",
        },
        {
            "area": "About Section",
            "tip": "Lead with your strongest achievement (Hackathon win), then list key technologies",
            "priority": "High",
        },
        {
            "area": "Skills",
            "tip": "Add all skills as LinkedIn skills. Get endorsements for top 5: Python, React, AWS, Docker, FastAPI",
            "priority": "High",
        },
        {
            "area": "Featured Section",
            "tip": "Add HealthGuard project, DevAssist AI demo, and portfolio link to Featured",
            "priority": "High",
        },
        {
            "area": "Open to Work",
            "tip": "Enable 'Open to Work' badge — visible to recruiters. Target: Software Engineer, Full Stack, Backend",
            "priority": "High",
        },
        {
            "area": "Projects",
            "tip": "Add all projects with links: HealthGuard, DevAssist AI, NestMind AI, StudentNest GenZy",
            "priority": "Medium",
        },
        {
            "area": "Recommendations",
            "tip": "Request 2-3 recommendations from colleagues or professors",
            "priority": "Medium",
        },
        {
            "area": "Activity",
            "tip": "Post about your projects, share tech articles, comment on industry posts weekly",
            "priority": "Medium",
        },
    ]

    # ── GitHub Optimization Tips ──
    report["github_tips"] = [
        "Pin top 4-6 repositories: HealthGuard, DevAssist AI, NestMind AI, this job auto-apply system",
        "Add detailed README.md with screenshots, architecture diagrams, and demo links",
        "Enable GitHub Profile README with skills badges, stats, and project highlights",
        "Ensure all pinned repos have live demo links or deployment URLs",
        "Add contribution graph — maintain daily commits streak",
    ]

    # ── Portfolio Tips ──
    report["portfolio_tips"] = [
        "Ensure portfolio loads fast and is mobile-responsive",
        "Add case studies for top 3 projects with problem → solution → impact format",
        "Include a 'Hire Me' or 'Contact' CTA above the fold",
        "Add testimonials or hackathon win proof",
        "Include a downloadable resume PDF link",
    ]

    # ── Keywords for ATS ──
    report["ats_keywords"] = [
        "Python", "JavaScript", "TypeScript", "React", "Angular", "Next.js", "Node.js",
        "Django", "Flask", "FastAPI", "REST API", "GraphQL",
        "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
        "AWS", "EC2", "S3", "Lambda", "Azure", "GCP",
        "Docker", "Kubernetes", "CI/CD", "GitHub Actions", "Jenkins",
        "Microservices", "Event-Driven", "Kafka", "RabbitMQ",
        "LangChain", "OpenAI", "GPT-4", "RAG", "Vector Embeddings",
        "Agile", "Scrum", "Git", "TDD", "Code Review",
    ]

    # ── Recruiter Attraction Score ──
    recruiter_score = 0
    if report["profile_strength"] >= 80:
        recruiter_score += 30
    elif report["profile_strength"] >= 60:
        recruiter_score += 20
    if PERSONAL_INFO.get("linkedin_url"):
        recruiter_score += 20
    if PERSONAL_INFO.get("github_url"):
        recruiter_score += 15
    if PERSONAL_INFO.get("portfolio_url"):
        recruiter_score += 15
    if "hackathon" in resume_text.lower():
        recruiter_score += 20

    report["recruiter_attraction_score"] = min(recruiter_score, 100)

    # ── Action Items ──
    actions = []
    if report["profile_strength"] < 80:
        actions.append("🔴 Improve profile strength to 80%+ by filling missing fields")
    if not PERSONAL_INFO.get("linkedin_url"):
        actions.append("🔴 Add LinkedIn URL to .env")
    actions.append("🟡 Update LinkedIn headline with suggested keyword-rich version")
    actions.append("🟡 Enable 'Open to Work' on LinkedIn if not already")
    actions.append("🟡 Pin top GitHub repos with detailed READMEs")
    actions.append("🟢 Post on LinkedIn about your Hackathon win and projects")
    actions.append("🟢 Apply to 50+ jobs daily through this automation system")
    report["action_items"] = actions

    _save_report(report)
    logger.info(f"Profile analysis complete: strength={report['profile_strength']}%, recruiter={report['recruiter_attraction_score']}%")
    return report


def get_profile_report() -> dict:
    report = _load_report()
    if not report:
        return analyze_profile()
    return report
