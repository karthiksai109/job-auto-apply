"""
AI Job Matcher — Scores jobs 0-100 based on how well they match YOUR resume.
Uses OpenAI for intelligent matching, falls back to keyword overlap scoring.
"""
import re
import json

from agents.config import OPENAI_API_KEY, OPENAI_MODEL
from agents.resume_parser import get_parsed_resume, get_all_skills_flat, _flatten_skills
from agents.logger import get_logger

logger = get_logger("JobMatcher")

# Minimum score to auto-apply (0-100)
MIN_MATCH_SCORE = 40

_ai_disabled = False  # set True after first OpenAI failure to skip retries


def score_job(job: dict) -> dict:
    """
    Score a job posting against the resume.
    Returns the job dict with added fields:
      - match_score (0-100)
      - match_reason (why it matched)
      - matched_skills (which of your skills match)
      - missing_skills (skills the job wants that you don't have)
    """
    resume = get_parsed_resume()
    if not resume.get("skills"):
        job["match_score"] = 50
        job["match_reason"] = "Resume not parsed — default score"
        job["matched_skills"] = []
        job["missing_skills"] = []
        return job

    # Try AI matching first
    ai_result = _score_with_ai(job, resume)
    if ai_result:
        job.update(ai_result)
        return job

    # Fallback to keyword matching
    keyword_result = _score_with_keywords(job, resume)
    job.update(keyword_result)
    return job


def score_jobs_batch(jobs: list) -> list:
    """Score a batch of jobs. Returns sorted by match_score descending."""
    scored = []
    for job in jobs:
        scored_job = score_job(job)
        scored.append(scored_job)

    scored.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    return scored


def is_relevant(job: dict) -> bool:
    """Check if a job is relevant enough to apply."""
    return job.get("match_score", 0) >= MIN_MATCH_SCORE


def _score_with_ai(job: dict, resume: dict) -> dict | None:
    """Use OpenAI to intelligently score job-resume match."""
    global _ai_disabled
    if not OPENAI_API_KEY or _ai_disabled:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Build concise resume summary
        skills = _flatten_skills(resume.get("skills", {}))
        resume_summary = f"""
Name: {resume.get('name', 'N/A')}
Title: {resume.get('title', 'N/A')}
Experience: {resume.get('years_experience', 0)} years
Skills: {', '.join(skills[:30])}
Target Roles: {', '.join(resume.get('target_roles', []))}
Summary: {resume.get('summary', 'N/A')}
"""

        # Build job summary
        job_desc = job.get("description", "")[:2000]
        job_summary = f"""
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Tech Stack: {', '.join(job.get('tech_stack', []))}
Description: {job_desc}
"""

        prompt = f"""Score how well this candidate matches this job posting. Return ONLY valid JSON.

CANDIDATE:
{resume_summary}

JOB POSTING:
{job_summary}

Return:
{{
    "match_score": <0-100>,
    "match_reason": "<1 sentence why>",
    "matched_skills": ["skill1", "skill2"],
    "missing_skills": ["skill1", "skill2"],
    "should_apply": true/false
}}

Scoring guide:
- 80-100: Strong match (most required skills match, role aligns with experience)
- 60-79: Good match (many skills match, some gaps)
- 40-59: Moderate match (some relevant skills, significant gaps)
- 20-39: Weak match (few matching skills)
- 0-19: Poor match (completely different domain)"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )

        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        logger.info(f"  AI Score: {result['match_score']}/100 — {job.get('title', '')} @ {job.get('company', '')}")
        return result

    except Exception as e:
        logger.debug(f"AI scoring failed, disabling for session: {e}")
        _ai_disabled = True
        return None


def _score_with_keywords(job: dict, resume: dict) -> dict:
    """Score based on keyword overlap AND experience-level fit."""
    my_skills = set(s.lower() for s in get_all_skills_flat())
    if not my_skills:
        return {"match_score": 50, "match_reason": "No skills extracted", "matched_skills": [], "missing_skills": []}

    job_text = (
        job.get("title", "") + " " +
        job.get("description", "") + " " +
        " ".join(job.get("tech_stack", []))
    ).lower()

    job_title = job.get("title", "").lower()

    # ── Experience-level penalty/boost ──
    # Hard reject: roles that require 5+ years / leadership
    SENIOR_KEYWORDS = [
        "senior", "staff", "principal", "lead ", "manager", "director",
        "head of", "vp ", "vice president", "architect",
    ]
    JUNIOR_KEYWORDS = [
        "junior", "entry", "associate", "new grad", "early career",
        "intern", " i ", " ii ", " 1 ", " 2 ",
    ]

    level_penalty = 0
    level_reason = ""
    for kw in SENIOR_KEYWORDS:
        if kw in job_title:
            level_penalty = -40
            level_reason = f"Title contains '{kw.strip()}' — likely requires 5+ years"
            break
    for kw in JUNIOR_KEYWORDS:
        if kw in job_title:
            level_penalty = 15
            level_reason = f"Entry/junior level — good fit for your experience"
            break

    # Check years-of-experience requirements in description
    yoe_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)', job_text)
    if yoe_match:
        required_yoe = int(yoe_match.group(1))
        if required_yoe >= 5:
            level_penalty = min(level_penalty, -40)
            level_reason = f"Requires {required_yoe}+ years experience"
        elif required_yoe >= 3:
            level_penalty = min(level_penalty, -20)
            level_reason = f"Requires {required_yoe}+ years (you have ~1)"
        elif required_yoe <= 1:
            level_penalty = max(level_penalty, 10)

    # ── Title relevance ──
    target_roles = [r.lower() for r in resume.get("target_roles", [])]
    title_bonus = 0
    for role in target_roles:
        role_words = set(role.split())
        title_words = set(job_title.split())
        overlap = role_words & title_words
        if len(overlap) >= 2 or role in job_title:
            title_bonus = 20
            break
        elif len(overlap) >= 1:
            title_bonus = 10

    # ── Core stack bonus (your strongest skills) ──
    CORE_STACK = {"python", "django", "flask", "fastapi", "react", "angular",
                  "docker", "kubernetes", "aws", "postgresql", "elasticsearch",
                  "node.js", "kafka", "jenkins", "github actions"}
    core_matches = [s for s in CORE_STACK if re.search(r'\b' + re.escape(s) + r'\b', job_text)]
    stack_bonus = min(len(core_matches) * 5, 20)

    # ── Skill overlap ──
    matched = []
    for skill in my_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', job_text):
            matched.append(skill.title())

    from agents.resume_parser import ALL_SKILLS
    job_required = set()
    for skill in ALL_SKILLS:
        if re.search(r'\b' + re.escape(skill) + r'\b', job_text):
            job_required.add(skill)

    missing = [s.title() for s in job_required if s.lower() not in my_skills]

    if not job_required:
        skill_score = 40
    else:
        overlap_ratio = len(matched) / max(len(job_required), 1)
        skill_score = min(int(overlap_ratio * 80), 80)

    # ── Final score ──
    total_score = max(0, min(skill_score + title_bonus + stack_bonus + level_penalty, 100))

    # Determine reason
    reasons = []
    if level_reason:
        reasons.append(level_reason)
    reasons.append(f"{len(matched)} skills match, {len(missing)} gaps")
    if core_matches:
        reasons.append(f"Core stack: {', '.join(core_matches[:5])}")
    reason = " | ".join(reasons)

    return {
        "match_score": total_score,
        "match_reason": reason,
        "matched_skills": matched[:15],
        "missing_skills": missing[:10],
        "should_apply": total_score >= MIN_MATCH_SCORE,
    }
