"""
Agent: Job Fit Analyst
Analyzes why a job matches your profile, why you're qualified,
and provides a detailed fit report for each applied job.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from agents.config import PERSONAL_INFO, BASE_DIR, OPENAI_API_KEY, OPENAI_MODEL
from agents.resume_parser import get_parsed_resume, get_all_skills_flat
from agents.logger import get_logger

logger = get_logger("JobFitAnalyst")

FIT_REPORTS_PATH = str(BASE_DIR / "fit_reports.json")


def _load_reports() -> list:
    try:
        with open(FIT_REPORTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_reports(reports: list):
    with open(FIT_REPORTS_PATH, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, default=str)


def analyze_job_fit(job: dict) -> dict:
    """
    Analyze how well a job matches the candidate's profile.
    Returns a detailed fit report.
    """
    resume = get_parsed_resume()
    skills = get_all_skills_flat()
    matched = job.get("matched_skills", [])
    missing = job.get("missing_skills", [])
    score = job.get("match_score", 0)
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    location = job.get("location", "Unknown")
    description = job.get("description", "")

    # Build fit analysis
    report = {
        "job_title": title,
        "company": company,
        "location": location,
        "match_score": score,
        "url": job.get("url", ""),
        "analyzed_at": datetime.now().isoformat(),
    }

    # Skill match analysis
    skill_overlap = [s for s in skills if s.lower() in [m.lower() for m in matched]]
    report["matched_skills"] = matched
    report["missing_skills"] = missing
    report["skill_match_pct"] = round(len(matched) / max(len(matched) + len(missing), 1) * 100)

    # Why you're qualified
    qualifications = []
    desc_lower = description.lower() if description else ""

    # Check experience alignment
    if any(kw in desc_lower for kw in ["python", "flask", "fastapi", "django"]):
        qualifications.append("Strong Python backend experience with Flask, FastAPI, and Django REST APIs at SVT IT Infotech and FunctionUp")
    if any(kw in desc_lower for kw in ["react", "angular", "frontend", "front-end", "ui"]):
        qualifications.append("Frontend development expertise with React and Angular, building responsive UI interfaces")
    if any(kw in desc_lower for kw in ["aws", "cloud", "ec2", "s3", "lambda"]):
        qualifications.append("Cloud-native development experience with AWS (EC2, S3, Lambda) and Azure")
    if any(kw in desc_lower for kw in ["docker", "kubernetes", "k8s", "container"]):
        qualifications.append("Containerization and orchestration with Docker and Kubernetes on AWS EC2")
    if any(kw in desc_lower for kw in ["ci/cd", "jenkins", "github actions", "pipeline"]):
        qualifications.append("CI/CD pipeline implementation with GitHub Actions and Jenkins, reducing deployment time by 50%")
    if any(kw in desc_lower for kw in ["microservice", "distributed", "event-driven"]):
        qualifications.append("Microservices architecture design with event-driven systems using Kafka and RabbitMQ")
    if any(kw in desc_lower for kw in ["sql", "postgres", "database", "nosql", "mongodb"]):
        qualifications.append("Database design expertise with PostgreSQL, MongoDB, and high-volume transaction schemas")
    if any(kw in desc_lower for kw in ["elasticsearch", "search", "analytics"]):
        qualifications.append("Search and analytics experience with optimized Elasticsearch queries for large datasets")
    if any(kw in desc_lower for kw in ["monitor", "datadog", "grafana", "observ"]):
        qualifications.append("Monitoring and observability with Datadog, Grafana, and Kibana dashboards")
    if any(kw in desc_lower for kw in ["ai", "llm", "langchain", "openai", "gpt", "ml"]):
        qualifications.append("AI/LLM experience with LangChain, OpenAI GPT-4, RAG, and vector embeddings — Hackathon winner (Akash 2026)")
    if any(kw in desc_lower for kw in ["full stack", "fullstack", "full-stack"]):
        qualifications.append("Full stack developer with end-to-end application delivery — frontend to deployment")
    if any(kw in desc_lower for kw in ["security", "auth", "jwt", "sonarqube"]):
        qualifications.append("Security-focused development with JWT auth, SonarQube, and Veracode code standards")
    if any(kw in desc_lower for kw in ["node", "express", "next.js", "nextjs"]):
        qualifications.append("Node.js and Next.js experience building production applications deployed on Netlify and Render")

    if not qualifications:
        qualifications.append(f"Technical skill overlap: {', '.join(matched[:8])}")
        qualifications.append("M.S. Computer Science from University of Dayton (2025)")
        qualifications.append("Authorized to work in US, available immediately, open to relocation")

    report["why_qualified"] = qualifications

    # Why this job is a good fit
    fit_reasons = []
    if score >= 90:
        fit_reasons.append(f"Exceptional skill match ({score}%) — your resume aligns closely with requirements")
    elif score >= 75:
        fit_reasons.append(f"Strong skill match ({score}%) — most required skills are in your toolbox")
    else:
        fit_reasons.append(f"Good skill match ({score}%) — core skills align with key requirements")

    if "remote" in location.lower():
        fit_reasons.append("Remote position — flexible work arrangement")
    if "san francisco" in location.lower() or "sf" in location.lower() or "bay area" in location.lower():
        fit_reasons.append("Located in San Francisco Bay Area — your target location")
    if "san jose" in location.lower():
        fit_reasons.append("Located in San Jose — your current area")

    title_lower = title.lower()
    if any(kw in title_lower for kw in ["junior", "entry", "associate", "i ", " i,"]):
        fit_reasons.append("Entry-level/junior position — appropriate for your experience level")
    if any(kw in title_lower for kw in ["full stack", "backend", "software engineer", "python"]):
        fit_reasons.append(f"'{title}' directly matches your target roles")

    report["why_good_fit"] = fit_reasons

    # Gaps to address
    gaps = []
    if missing:
        gaps.append(f"Skills to brush up on: {', '.join(missing[:5])}")
    if "senior" in title_lower or "lead" in title_lower:
        gaps.append("Position may require more years of experience than you currently have")
    report["gaps"] = gaps

    # Confidence level
    if score >= 90 and len(qualifications) >= 3:
        report["confidence"] = "Very High — strong candidate, expect interview callback"
    elif score >= 75 and len(qualifications) >= 2:
        report["confidence"] = "High — competitive candidate with relevant experience"
    elif score >= 60:
        report["confidence"] = "Moderate — good match but may face competition from more experienced candidates"
    else:
        report["confidence"] = "Low — apply but prepare for potential skill gap questions"

    # Summary
    report["summary"] = (
        f"You are a {'strong' if score >= 80 else 'good'} match for {title} at {company}. "
        f"Your {', '.join(matched[:3])} experience directly aligns with their requirements. "
        f"{'No significant gaps.' if not missing else f'Minor gaps in {', '.join(missing[:3])} can be addressed.'} "
        f"Confidence: {report['confidence'].split(' — ')[0]}."
    )

    # Save report
    reports = _load_reports()
    # Remove existing report for same job URL
    reports = [r for r in reports if r.get("url") != job.get("url")]
    reports.append(report)
    _save_reports(reports)

    logger.info(f"  Fit analysis: {title} @ {company} — {report['confidence'].split(' — ')[0]}")
    return report


def get_all_reports() -> list:
    """Get all fit reports."""
    return _load_reports()


def get_report_for_job(url: str) -> dict | None:
    """Get fit report for a specific job URL."""
    reports = _load_reports()
    for r in reports:
        if r.get("url") == url:
            return r
    return None
