"""
Agent: Interview Prep Coach
Generates interview preparation guides for each applied job.
Includes technical questions, behavioral questions, and company-specific prep.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from agents.config import BASE_DIR
from agents.resume_parser import get_parsed_resume, get_all_skills_flat
from agents.logger import get_logger

logger = get_logger("InterviewPrep")

PREP_GUIDES_PATH = str(BASE_DIR / "interview_prep.json")


def _load_guides() -> list:
    try:
        with open(PREP_GUIDES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_guides(guides: list):
    with open(PREP_GUIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(guides, f, indent=2, default=str)


# Common technical question banks by skill
TECH_QUESTIONS = {
    "python": [
        "Explain the difference between lists and tuples in Python.",
        "What are Python decorators and how do they work?",
        "Explain the GIL (Global Interpreter Lock) and its implications.",
        "How does memory management work in Python?",
        "What is the difference between `__init__` and `__new__`?",
        "Explain generators and when you would use them.",
        "How do you handle exceptions in Python? Best practices?",
        "What are context managers and the `with` statement?",
    ],
    "react": [
        "Explain the virtual DOM and reconciliation in React.",
        "What are React hooks? Explain useState, useEffect, useContext.",
        "How do you optimize React performance? (memo, useMemo, useCallback)",
        "Explain the component lifecycle in class vs functional components.",
        "What is state management? Compare Redux, Context API, Zustand.",
        "How do you handle side effects in React?",
        "What is server-side rendering (SSR) vs client-side rendering (CSR)?",
    ],
    "node": [
        "Explain the event loop in Node.js.",
        "What is the difference between callbacks, promises, and async/await?",
        "How does Node.js handle concurrent requests?",
        "Explain the middleware pattern in Express.js.",
        "How do you handle errors in async Node.js code?",
    ],
    "sql": [
        "Explain INNER JOIN vs LEFT JOIN vs FULL OUTER JOIN.",
        "What are indexes and how do they improve query performance?",
        "Explain ACID properties in databases.",
        "What is database normalization? Explain 1NF, 2NF, 3NF.",
        "How do you optimize a slow SQL query?",
        "Explain the difference between HAVING and WHERE.",
    ],
    "aws": [
        "Explain the difference between EC2, Lambda, and ECS.",
        "How does S3 storage work? Explain storage classes.",
        "What is a VPC and how do you configure security groups?",
        "Explain auto-scaling and load balancing on AWS.",
        "How do you implement a CI/CD pipeline on AWS?",
    ],
    "docker": [
        "What is the difference between a Docker image and a container?",
        "Explain the Dockerfile commands: FROM, RUN, CMD, ENTRYPOINT.",
        "How do you optimize Docker image size?",
        "What is Docker Compose and when would you use it?",
        "Explain Docker networking modes.",
    ],
    "kubernetes": [
        "Explain Pods, Deployments, and Services in Kubernetes.",
        "How does auto-scaling work in Kubernetes?",
        "What is a ConfigMap and Secret?",
        "Explain the difference between StatefulSet and Deployment.",
        "How do you do rolling updates and rollbacks?",
    ],
    "rest": [
        "Explain RESTful API design principles.",
        "What are HTTP methods and status codes?",
        "How do you version APIs?",
        "Explain authentication methods: JWT, OAuth2, API keys.",
        "How do you handle rate limiting and pagination?",
    ],
    "elasticsearch": [
        "How does Elasticsearch index and search data?",
        "Explain the difference between match and term queries.",
        "How do you optimize Elasticsearch for large datasets?",
        "What are analyzers and tokenizers?",
    ],
    "kafka": [
        "Explain Kafka's architecture: topics, partitions, consumers.",
        "What is the difference between Kafka and RabbitMQ?",
        "How do you ensure message ordering in Kafka?",
        "What is consumer group rebalancing?",
    ],
    "microservices": [
        "What are the benefits and challenges of microservices architecture?",
        "How do services communicate in a microservices architecture?",
        "Explain the Circuit Breaker pattern.",
        "How do you handle distributed transactions?",
        "What is service discovery?",
    ],
    "ci/cd": [
        "Explain your CI/CD pipeline from code commit to production.",
        "How do you implement blue-green or canary deployments?",
        "What testing stages do you include in your pipeline?",
        "How do you handle secrets in CI/CD?",
    ],
}

BEHAVIORAL_QUESTIONS = [
    "Tell me about yourself and your experience.",
    "Why are you interested in this role at [Company]?",
    "Describe a challenging technical problem you solved.",
    "Tell me about a time you worked effectively in a team.",
    "How do you handle disagreements with teammates?",
    "Describe a project you're most proud of.",
    "How do you prioritize tasks when you have multiple deadlines?",
    "Tell me about a time you had to learn a new technology quickly.",
    "How do you handle code reviews — both giving and receiving feedback?",
    "Where do you see yourself in 2-3 years?",
]

SYSTEM_DESIGN_QUESTIONS = [
    "Design a URL shortener (like bit.ly).",
    "Design a real-time chat application.",
    "Design a job application tracking system.",
    "Design a notification service that handles millions of events.",
    "Design a content delivery system for a social media platform.",
    "Design an API rate limiter.",
]


def generate_interview_prep(job: dict) -> dict:
    """
    Generate a comprehensive interview preparation guide for a job.
    """
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    description = job.get("description", "")
    matched_skills = job.get("matched_skills", [])
    missing_skills = job.get("missing_skills", [])
    score = job.get("match_score", 0)

    skills = get_all_skills_flat()
    desc_lower = description.lower() if description else ""

    guide = {
        "job_title": title,
        "company": company,
        "url": job.get("url", ""),
        "match_score": score,
        "generated_at": datetime.now().isoformat(),
    }

    # 1. Technical questions based on matched skills
    tech_qs = []
    skills_covered = set()
    for skill in matched_skills:
        skill_lower = skill.lower()
        for key, questions in TECH_QUESTIONS.items():
            if key in skill_lower or skill_lower in key:
                if key not in skills_covered:
                    skills_covered.add(key)
                    tech_qs.extend([(q, key) for q in questions[:3]])

    # Add questions based on job description keywords
    for key, questions in TECH_QUESTIONS.items():
        if key in desc_lower and key not in skills_covered:
            skills_covered.add(key)
            tech_qs.extend([(q, key) for q in questions[:2]])

    guide["technical_questions"] = [{"question": q, "topic": t} for q, t in tech_qs[:15]]

    # 2. Behavioral questions (customized)
    behavioral = []
    for q in BEHAVIORAL_QUESTIONS:
        behavioral.append(q.replace("[Company]", company))
    guide["behavioral_questions"] = behavioral

    # 3. System design (if mid-level or above)
    title_lower = title.lower()
    if any(kw in title_lower for kw in ["senior", "ii", "iii", "lead", "staff"]):
        guide["system_design"] = SYSTEM_DESIGN_QUESTIONS[:3]
    else:
        guide["system_design"] = SYSTEM_DESIGN_QUESTIONS[:2]

    # 4. Skills to review
    review_skills = []
    for skill in matched_skills[:8]:
        review_skills.append({
            "skill": skill,
            "priority": "High" if skill.lower() in desc_lower else "Medium",
            "tip": f"Review {skill} fundamentals, be ready to write code or explain concepts",
        })
    for skill in missing_skills[:4]:
        review_skills.append({
            "skill": skill,
            "priority": "Low",
            "tip": f"Familiarize with {skill} basics — they may ask about it",
        })
    guide["skills_to_review"] = review_skills

    # 5. Company-specific prep
    company_prep = [
        f"Research {company}'s products, mission, and recent news",
        f"Check {company}'s Glassdoor reviews for interview process insights",
        f"Look up {company}'s tech blog or engineering blog for tech stack details",
        f"Prepare 2-3 questions to ask the interviewer about {company}'s engineering culture",
    ]
    guide["company_research"] = company_prep

    # 6. Your talking points (based on resume)
    talking_points = [
        "Current role at SVT IT Infotech: Full-stack apps with React/Angular + FastAPI/Django, 40% API improvement",
        "CI/CD expertise: GitHub Actions & Jenkins pipelines, 50% deployment time reduction",
        "Cloud & containers: Docker + Kubernetes on AWS EC2, scalable architecture",
        "Event-driven systems: Kafka & RabbitMQ for async processing",
        "Hackathon winner: 1st place Akash Open Agents 2026 — HealthGuard AI agent",
        "AI/ML projects: DevAssist AI (7 agents, vector search), NestMind AI (multi-agent RAG)",
        "M.S. Computer Science from University of Dayton (2025)",
    ]
    guide["talking_points"] = talking_points

    # 7. Interview timeline estimate
    if "startup" in desc_lower or "series" in desc_lower:
        guide["expected_process"] = "Startup (1-2 weeks): Phone screen → Technical → Team fit → Offer"
    else:
        guide["expected_process"] = "Standard (2-4 weeks): Recruiter call → Technical screen → Coding round → System design → Team fit → Offer"

    # Save
    guides = _load_guides()
    guides = [g for g in guides if g.get("url") != job.get("url")]
    guides.append(guide)
    _save_guides(guides)

    logger.info(f"  Interview prep generated: {title} @ {company} ({len(tech_qs)} tech Qs)")
    return guide


def get_all_guides() -> list:
    return _load_guides()


def get_guide_for_job(url: str) -> dict | None:
    guides = _load_guides()
    for g in guides:
        if g.get("url") == url:
            return g
    return None
