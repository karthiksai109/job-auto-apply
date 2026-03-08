"""
Resume Parser — Extracts skills, tech stack, experience, and profile from your PDF resume.
Uses PyPDF2 for text extraction and AI (OpenAI) for intelligent parsing.
Falls back to regex-based extraction if no API key.
"""
import os
import re
import json
from pathlib import Path

from agents.config import RESUME_PATH, OPENAI_API_KEY, OPENAI_MODEL
from agents.logger import get_logger

logger = get_logger("ResumeParser")

# ============================================================
# KNOWN TECH / SKILL KEYWORDS (for regex fallback)
# ============================================================
PROGRAMMING_LANGUAGES = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "bash", "shell", "powershell", "sql", "html", "css", "sass", "less",
}

FRAMEWORKS_LIBRARIES = {
    "react", "reactjs", "react.js", "angular", "angularjs", "vue", "vuejs", "vue.js",
    "next.js", "nextjs", "nuxt", "svelte", "django", "flask", "fastapi", "spring",
    "spring boot", "springboot", "express", "expressjs", "node.js", "nodejs",
    "rails", "ruby on rails", ".net", "asp.net", "laravel", "symfony",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "matplotlib", "opencv", "huggingface", "langchain", "streamlit",
    "bootstrap", "tailwind", "tailwindcss", "material-ui", "chakra",
    "jquery", "redux", "graphql", "rest", "restful",
}

DATABASES = {
    "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "dynamodb", "cassandra", "sqlite", "oracle", "sql server", "mssql",
    "firebase", "firestore", "supabase", "neo4j", "mariadb", "couchdb",
}

CLOUD_DEVOPS = {
    "aws", "amazon web services", "azure", "gcp", "google cloud",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "ci/cd", "github actions", "gitlab ci", "circleci", "travis ci",
    "heroku", "netlify", "vercel", "cloudflare", "nginx", "apache",
    "linux", "ubuntu", "centos", "lambda", "ec2", "s3", "rds", "ecs",
    "eks", "fargate", "cloudformation", "helm", "prometheus", "grafana",
    "datadog", "splunk", "kafka", "rabbitmq", "celery", "airflow",
}

TOOLS_CONCEPTS = {
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "agile", "scrum", "kanban", "microservices", "api", "rest api",
    "graphql", "grpc", "websocket", "oauth", "jwt", "saml",
    "machine learning", "deep learning", "nlp", "computer vision",
    "data science", "data engineering", "etl", "data pipeline",
    "big data", "hadoop", "spark", "pyspark", "hive",
    "devops", "sre", "monitoring", "logging", "testing",
    "unit testing", "integration testing", "tdd", "bdd",
    "pytest", "jest", "mocha", "selenium", "cypress",
    "figma", "sketch", "adobe", "photoshop",
}

ALL_SKILLS = PROGRAMMING_LANGUAGES | FRAMEWORKS_LIBRARIES | DATABASES | CLOUD_DEVOPS | TOOLS_CONCEPTS

# Cache parsed resume
_resume_cache = {}


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF resume."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to read PDF: {e}")
        return ""


def parse_resume_with_ai(text: str) -> dict:
    """Use OpenAI to intelligently parse resume text."""
    if not OPENAI_API_KEY:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""Analyze this resume and extract structured information. Return ONLY valid JSON.

Resume text:
---
{text[:6000]}
---

Return this exact JSON structure:
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "phone number",
    "location": "City, State",
    "title": "most recent job title or target role",
    "years_experience": 3,
    "education": [
        {{"degree": "BS Computer Science", "school": "University Name", "year": 2023}}
    ],
    "work_experience": [
        {{"company": "Company", "title": "Role", "duration": "1 year", "highlights": ["key achievement 1"]}}
    ],
    "skills": {{
        "programming_languages": ["Python", "Java"],
        "frameworks": ["React", "Django"],
        "databases": ["PostgreSQL", "MongoDB"],
        "cloud_devops": ["AWS", "Docker"],
        "tools": ["Git", "Jira"],
        "other": ["Machine Learning", "REST API"]
    }},
    "summary": "2-3 sentence professional summary based on the resume",
    "target_roles": ["Software Engineer", "Backend Developer", "Full Stack Developer"],
    "strengths": ["key strength 1", "key strength 2"]
}}"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except Exception as e:
        logger.warning(f"AI parsing failed, falling back to regex: {e}")
        return None


def parse_resume_with_regex(text: str) -> dict:
    """Fallback: extract skills and info using regex/keyword matching."""
    text_lower = text.lower()

    # Extract email
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    email = email_match.group(0) if email_match else ""

    # Extract phone
    phone_match = re.search(r'[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    phone = phone_match.group(0) if phone_match else ""

    # Extract name (usually first line or first large text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    name = lines[0] if lines else ""
    # Clean name — usually first line that's short and doesn't contain @
    for line in lines[:5]:
        if '@' not in line and len(line) < 50 and not any(c.isdigit() for c in line):
            name = line
            break

    # Extract skills by keyword matching
    found_skills = {
        "programming_languages": [],
        "frameworks": [],
        "databases": [],
        "cloud_devops": [],
        "tools": [],
        "other": [],
    }

    for skill in PROGRAMMING_LANGUAGES:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found_skills["programming_languages"].append(skill.title())

    for skill in FRAMEWORKS_LIBRARIES:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found_skills["frameworks"].append(skill.title())

    for skill in DATABASES:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found_skills["databases"].append(skill.title())

    for skill in CLOUD_DEVOPS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found_skills["cloud_devops"].append(skill.title())

    for skill in TOOLS_CONCEPTS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found_skills["tools"].append(skill.title())

    # Guess years of experience
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)', text_lower)
    years_exp = int(exp_match.group(1)) if exp_match else 0

    # Extract education
    education = []
    edu_patterns = [
        r"(?:bachelor|master|phd|b\.?s\.?|m\.?s\.?|b\.?e\.?|m\.?e\.?|b\.?tech|m\.?tech)\s*(?:of|in)?\s*[\w\s]+",
    ]
    for pat in edu_patterns:
        matches = re.findall(pat, text_lower)
        for m in matches:
            education.append({"degree": m.strip().title(), "school": "", "year": ""})

    # Determine target roles from skills
    all_found = []
    for cat_skills in found_skills.values():
        all_found.extend(cat_skills)

    target_roles = _infer_target_roles(all_found)

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "location": "",
        "title": target_roles[0] if target_roles else "Software Engineer",
        "years_experience": years_exp,
        "education": education,
        "work_experience": [],
        "skills": found_skills,
        "summary": "",
        "target_roles": target_roles,
        "strengths": all_found[:10],
    }


def _infer_target_roles(skills: list) -> list:
    """Infer target job roles from extracted skills."""
    skills_lower = [s.lower() for s in skills]
    roles = []

    # Backend
    if any(s in skills_lower for s in ["python", "django", "flask", "fastapi", "java", "spring", "spring boot", "node.js", "express"]):
        roles.append("Backend Developer")
        roles.append("Software Engineer")

    # Frontend
    if any(s in skills_lower for s in ["react", "angular", "vue", "next.js", "javascript", "typescript", "html", "css"]):
        roles.append("Frontend Developer")

    # Full Stack
    if "Backend Developer" in roles and "Frontend Developer" in roles:
        roles.insert(0, "Full Stack Developer")

    # Data
    if any(s in skills_lower for s in ["pandas", "numpy", "machine learning", "tensorflow", "pytorch", "data science", "spark"]):
        roles.append("Data Engineer")
        roles.append("Data Scientist")

    # Cloud/DevOps
    if any(s in skills_lower for s in ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd"]):
        roles.append("Cloud Engineer")
        roles.append("DevOps Engineer")

    # Fallback
    if not roles:
        roles = ["Software Engineer", "Software Developer", "Python Developer"]

    return list(dict.fromkeys(roles))[:6]  # Deduplicate, max 6


def get_parsed_resume() -> dict:
    """
    Parse the resume and return structured data. Uses cache.
    Returns dict with: name, skills, target_roles, years_experience, etc.
    """
    global _resume_cache

    if _resume_cache:
        return _resume_cache

    resume_path = RESUME_PATH
    if not os.path.exists(resume_path):
        logger.error(f"Resume not found at: {resume_path}")
        logger.info("Set RESUME_PATH in your .env file")
        return {"skills": {}, "target_roles": ["Software Engineer"], "name": "", "years_experience": 0}

    logger.info(f"Parsing resume: {resume_path}")
    text = extract_text_from_pdf(resume_path)

    if not text:
        logger.error("Could not extract text from resume PDF")
        return {"skills": {}, "target_roles": ["Software Engineer"], "name": "", "years_experience": 0}

    logger.info(f"Extracted {len(text)} chars from resume")

    # Try AI parsing first
    result = parse_resume_with_ai(text)
    if result:
        logger.info(f"AI parsed: {result.get('name', 'Unknown')} — {len(_flatten_skills(result.get('skills', {})))} skills found")
    else:
        result = parse_resume_with_regex(text)
        logger.info(f"Regex parsed: {result.get('name', 'Unknown')} — {len(_flatten_skills(result.get('skills', {})))} skills found")

    # Store raw text for AI matching later
    result["raw_text"] = text

    _resume_cache = result
    return result


def get_all_skills_flat() -> list:
    """Get a flat list of all skills from the resume."""
    resume = get_parsed_resume()
    return _flatten_skills(resume.get("skills", {}))


def _flatten_skills(skills_dict: dict) -> list:
    """Flatten skills dict into a single list."""
    flat = []
    for category_skills in skills_dict.values():
        if isinstance(category_skills, list):
            flat.extend(category_skills)
    return flat


def get_resume_text() -> str:
    """Get raw resume text."""
    resume = get_parsed_resume()
    return resume.get("raw_text", "")
