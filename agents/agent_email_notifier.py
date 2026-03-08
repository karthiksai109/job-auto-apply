"""
Agent 5: Email Notifier
Sends comprehensive email updates including:
1. Daily job application status summary
2. Per-job status updates with tech stack info
3. Interview preparation: Top 25 Q&A based on your resume + job description
4. Previously asked questions for each interview round
5. What to prepare for each specific company/role
"""
import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional

from openai import OpenAI

from agents.config import (
    SMTP_SERVER, SMTP_PORT, EMAIL_SENDER, EMAIL_PASSWORD,
    EMAIL_RECIPIENT, OPENAI_API_KEY, OPENAI_MODEL,
    RESUME_PATH, PERSONAL_INFO, JobStatus,
)
from agents.job_database import get_all_jobs, get_applied_jobs, get_stats, update_job
from agents.logger import get_logger

logger = get_logger("EmailBot")


class EmailNotifierAgent:
    """
    Agent 5: Sends intelligent email notifications about job applications.
    - Daily summary report
    - Per-job interview prep with AI-generated Q&A
    - Tech stack study guides
    - Previously asked interview questions research
    """

    def __init__(self):
        self.client = None
        if OPENAI_API_KEY:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.resume_text = self._load_resume()
        self.emails_sent = 0

    def run(self) -> dict:
        """Run the email notification cycle."""
        logger.info("=" * 60)
        logger.info("AGENT 5: Email Notifier Starting...")
        logger.info("=" * 60)

        if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENT:
            logger.error("Email credentials not configured! Set EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT in .env")
            return {"emails_sent": 0, "error": "Missing email config"}

        results = {"emails_sent": 0, "reports": []}

        # 1. Send daily summary report
        logger.info("\n--- Generating Daily Summary Report ---")
        try:
            self._send_daily_summary()
            results["emails_sent"] += 1
            results["reports"].append("daily_summary")
        except Exception as e:
            logger.error(f"Daily summary error: {e}")

        # 2. Send interview prep for jobs in interview stages
        logger.info("\n--- Generating Interview Prep Emails ---")
        interview_jobs = self._get_interview_stage_jobs()
        for job in interview_jobs:
            try:
                if not job.get("interview_prep_sent", False):
                    self._send_interview_prep(job)
                    results["emails_sent"] += 1
                    results["reports"].append(f"prep_{job['company']}")
            except Exception as e:
                logger.error(f"Interview prep error for {job.get('company')}: {e}")

        self.emails_sent = results["emails_sent"]
        logger.info(f"\nEmail Notifier complete! Sent {self.emails_sent} emails.")
        return results

    # ----------------------------------------------------------------
    # DAILY SUMMARY REPORT
    # ----------------------------------------------------------------
    def _send_daily_summary(self):
        """Send a comprehensive daily summary email."""
        stats = get_stats()
        all_jobs = get_all_jobs()

        # Group recent jobs by status
        status_groups = {}
        for job in all_jobs:
            status = job.get("status", "unknown")
            status_groups.setdefault(status, []).append(job)

        # Build HTML email
        html = self._build_daily_summary_html(stats, status_groups, all_jobs)
        subject = f"Job Bot Daily Report - {datetime.now().strftime('%b %d, %Y')} | {stats['total']} Jobs Tracked"

        self._send_email(subject, html)
        logger.info(f"Daily summary sent to {EMAIL_RECIPIENT}")

    def _build_daily_summary_html(self, stats: dict, status_groups: dict, all_jobs: list) -> str:
        """Build the daily summary HTML email."""
        today = datetime.now().strftime("%B %d, %Y")

        # Tech stack frequency
        tech_count = {}
        for job in all_jobs:
            for tech in job.get("tech_stack", []):
                tech_count[tech] = tech_count.get(tech, 0) + 1
        top_techs = sorted(tech_count.items(), key=lambda x: -x[1])[:15]

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; background: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                h1 {{ color: #2F5496; border-bottom: 3px solid #2F5496; padding-bottom: 10px; }}
                h2 {{ color: #2F5496; margin-top: 25px; }}
                .stat-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: #f8f9fa; border-radius: 8px; padding: 15px; text-align: center; border-left: 4px solid #2F5496; }}
                .stat-card .number {{ font-size: 28px; font-weight: bold; color: #2F5496; }}
                .stat-card .label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th {{ background: #2F5496; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
                tr:hover {{ background: #f8f9fa; }}
                .status-applied {{ color: #28a745; font-weight: bold; }}
                .status-screening {{ color: #007bff; font-weight: bold; }}
                .status-rejected {{ color: #dc3545; font-weight: bold; }}
                .status-offer {{ color: #28a745; font-weight: bold; font-size: 16px; }}
                .tech-badge {{ display: inline-block; background: #e8f0fe; color: #2F5496; padding: 3px 8px; border-radius: 4px; margin: 2px; font-size: 12px; }}
                .section {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Job Application Report - {today}</h1>

                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="number">{stats['total']}</div>
                        <div class="label">Total Jobs</div>
                    </div>
                    <div class="stat-card">
                        <div class="number">{stats['today_applied']}</div>
                        <div class="label">Applied Today</div>
                    </div>
                    <div class="stat-card">
                        <div class="number">{stats['by_status'].get(JobStatus.APPLIED, 0)}</div>
                        <div class="label">Active Applications</div>
                    </div>
                </div>

                <h2>Status Breakdown</h2>
                <table>
                    <tr><th>Status</th><th>Count</th></tr>
        """

        for status in JobStatus.ALL:
            count = stats["by_status"].get(status, 0)
            if count > 0:
                display_status = status.replace("_", " ").title()
                html += f"<tr><td>{display_status}</td><td><strong>{count}</strong></td></tr>"

        html += """
                </table>

                <h2>Platform Breakdown</h2>
                <table>
                    <tr><th>Platform</th><th>Jobs</th></tr>
        """

        for platform, count in sorted(stats["by_platform"].items()):
            html += f"<tr><td>{platform.title()}</td><td><strong>{count}</strong></td></tr>"

        html += """
                </table>

                <h2>Top Tech Stacks in Demand</h2>
                <div class="section">
        """

        for tech, count in top_techs:
            html += f'<span class="tech-badge">{tech} ({count})</span> '

        html += "</div>"

        # Active applications detail
        active_statuses = [
            JobStatus.APPLIED, JobStatus.SCREENING, JobStatus.PHONE_SCREEN,
            JobStatus.TECHNICAL_ROUND, JobStatus.ONSITE, JobStatus.FINAL_ROUND, JobStatus.OFFER,
        ]
        active_jobs = [j for j in all_jobs if j.get("status") in active_statuses]

        if active_jobs:
            html += """
                <h2>Active Applications</h2>
                <table>
                    <tr><th>Company</th><th>Title</th><th>Platform</th><th>Status</th><th>Tech Stack</th></tr>
            """
            for job in active_jobs[:30]:
                status = job.get("status", "").replace("_", " ").title()
                tech = ", ".join(job.get("tech_stack", [])[:5])
                status_class = f"status-{job.get('status', '')}" if job.get("status") in [JobStatus.APPLIED, JobStatus.SCREENING, JobStatus.REJECTED, JobStatus.OFFER] else ""
                html += f"""
                    <tr>
                        <td><strong>{job.get('company', 'N/A')}</strong></td>
                        <td>{job.get('title', 'N/A')}</td>
                        <td>{job.get('platform', '').title()}</td>
                        <td class="{status_class}">{status}</td>
                        <td><small>{tech}</small></td>
                    </tr>
                """
            html += "</table>"

        # Recently rejected
        rejected = status_groups.get(JobStatus.REJECTED, [])
        if rejected:
            html += f"""
                <h2>Recently Rejected ({len(rejected)})</h2>
                <table>
                    <tr><th>Company</th><th>Title</th><th>Platform</th></tr>
            """
            for job in rejected[:10]:
                html += f"""
                    <tr>
                        <td>{job.get('company', 'N/A')}</td>
                        <td>{job.get('title', 'N/A')}</td>
                        <td>{job.get('platform', '').title()}</td>
                    </tr>
                """
            html += "</table>"

        html += f"""
                <div class="footer">
                    Automated by Job Bot Multi-Agent System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """

        return html

    # ----------------------------------------------------------------
    # INTERVIEW PREP EMAILS
    # ----------------------------------------------------------------
    def _get_interview_stage_jobs(self) -> list:
        """Get jobs in interview stages that need prep emails."""
        interview_statuses = [
            JobStatus.SCREENING, JobStatus.PHONE_SCREEN,
            JobStatus.TECHNICAL_ROUND, JobStatus.ONSITE, JobStatus.FINAL_ROUND,
        ]
        all_jobs = get_all_jobs()
        return [j for j in all_jobs if j.get("status") in interview_statuses]

    def _send_interview_prep(self, job: dict):
        """Generate and send interview prep email for a specific job."""
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        tech_stack = job.get("tech_stack", [])
        status = job.get("status", "")
        rounds = job.get("rounds", [])

        logger.info(f"Generating interview prep for {title} @ {company}")

        # Use AI to generate prep content
        prep_content = self._generate_interview_prep(job)

        # Build email
        html = self._build_interview_prep_html(job, prep_content)
        subject = f"Interview Prep: {title} @ {company} - {status.replace('_', ' ').title()}"

        self._send_email(subject, html)

        # Mark as sent
        update_job(job["job_id"], job["platform"], {"interview_prep_sent": True})
        logger.info(f"Interview prep sent for {company}")

    def _generate_interview_prep(self, job: dict) -> dict:
        """Use AI to generate comprehensive interview preparation."""
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        tech_stack = job.get("tech_stack", [])
        description = job.get("description_snippet", "")
        status = job.get("status", "")
        rounds = job.get("rounds", [])

        # Determine round type
        round_type = "general"
        if status == JobStatus.PHONE_SCREEN:
            round_type = "phone screen / recruiter call"
        elif status == JobStatus.TECHNICAL_ROUND:
            round_type = "technical interview / coding round"
        elif status == JobStatus.ONSITE:
            round_type = "onsite / virtual onsite interview"
        elif status == JobStatus.FINAL_ROUND:
            round_type = "final round / hiring manager interview"

        tech_str = ", ".join(tech_stack) if tech_stack else "Python, JavaScript, SQL, AWS"

        prompt = f"""You are an expert interview coach. Generate comprehensive interview preparation for:

CANDIDATE RESUME SUMMARY:
- Name: {PERSONAL_INFO['first_name']} {PERSONAL_INFO['last_name']}
- Experience: {PERSONAL_INFO['years_of_experience']} years
- Education: {PERSONAL_INFO['education']}
- Location: {PERSONAL_INFO['city']}, {PERSONAL_INFO['state']}

JOB DETAILS:
- Company: {company}
- Title: {title}
- Tech Stack: {tech_str}
- Job Description: {description[:800]}
- Current Round: {round_type}

{f"Resume Text: {self.resume_text[:2000]}" if self.resume_text else ""}

Generate the following in JSON format:
{{
    "company_overview": "Brief company overview and culture notes",
    "what_to_prepare": ["List of 5-7 key areas to focus on for this specific round"],
    "top_25_questions": [
        {{"q": "question text", "a": "detailed answer tailored to candidate's resume and the role"}},
        ... (exactly 25 questions and answers)
    ],
    "previously_asked": [
        "List of 10 questions commonly asked at this company based on Glassdoor/LeetCode patterns"
    ],
    "coding_topics": ["Relevant coding/system design topics if technical round"],
    "behavioral_tips": ["5 behavioral interview tips specific to this role"],
    "salary_negotiation": "Tips for salary negotiation at this company",
    "red_flags_to_watch": ["3 things to watch out for"]
}}

Make the 25 Q&A highly specific to the candidate's resume + this particular role + tech stack.
For technical roles, include coding questions. For behavioral rounds, include STAR format answers.
"""

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are an expert career coach and interview preparer. Always respond in valid JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4000,
                )
                content = response.choices[0].message.content.strip()
                # Clean JSON
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                return json.loads(content)
            except Exception as e:
                logger.error(f"AI generation error: {e}")

        # Fallback: generate without AI
        return self._generate_fallback_prep(job, round_type, tech_str)

    def _generate_fallback_prep(self, job: dict, round_type: str, tech_str: str) -> dict:
        """Generate prep content without AI as fallback."""
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")

        common_questions = [
            {"q": "Tell me about yourself.", "a": f"I'm {PERSONAL_INFO['first_name']}, a software engineer with {PERSONAL_INFO['years_of_experience']} years of experience. I have a {PERSONAL_INFO['education']} degree and specialize in {tech_str}. I'm passionate about building scalable, reliable software systems."},
            {"q": "Why are you interested in this role?", "a": f"I'm excited about the {title} position at {company} because it aligns with my experience in {tech_str} and offers opportunities to work on challenging problems at scale."},
            {"q": "What's your greatest strength?", "a": "My ability to quickly learn new technologies and apply them to solve real problems. I've consistently delivered projects ahead of schedule by leveraging both my technical skills and collaborative approach."},
            {"q": "What's your biggest weakness?", "a": "I sometimes spend too much time optimizing code for performance. I've learned to balance this by setting time limits and focusing on the MVP first, then optimizing based on actual metrics."},
            {"q": "Describe a challenging project you worked on.", "a": "I built a microservices architecture that handled high-throughput data processing. The challenge was ensuring reliability across services. I implemented circuit breakers, retry logic, and comprehensive monitoring to achieve 99.9% uptime."},
            {"q": "How do you handle disagreements with teammates?", "a": "I focus on data and facts. I listen to understand their perspective, then share mine backed by evidence. If we still disagree, I suggest a quick prototype or A/B test to let the results decide."},
            {"q": "Where do you see yourself in 5 years?", "a": f"I see myself as a senior/lead engineer, driving architectural decisions and mentoring junior developers. I want to grow with a company like {company} that values technical excellence."},
            {"q": "Why are you leaving your current position?", "a": "I'm looking for new challenges and growth opportunities. I want to work on larger-scale systems and contribute to products that make a real impact."},
            {"q": "How do you stay current with technology?", "a": "I regularly read tech blogs, contribute to open source, attend meetups, and build side projects. I also take online courses on platforms like Coursera and Udemy to deepen my expertise."},
            {"q": "Describe your experience with Agile/Scrum.", "a": "I've worked in Agile teams for my entire career. I participate in sprint planning, daily standups, and retrospectives. I'm comfortable with JIRA, story estimation, and delivering in 2-week sprints."},
            {"q": f"What experience do you have with {tech_str.split(',')[0] if tech_str else 'Python'}?", "a": f"I have {PERSONAL_INFO['years_of_experience']} years of hands-on experience. I've used it in production for building APIs, data pipelines, and automation scripts. I'm proficient with the ecosystem including testing, deployment, and monitoring."},
            {"q": "How do you approach debugging a production issue?", "a": "First, I check logs and monitoring dashboards to understand the scope. Then I reproduce the issue locally if possible. I use systematic elimination, checking recent deployments, infrastructure changes, and data anomalies."},
            {"q": "Describe your experience with databases.", "a": "I've worked with both SQL (PostgreSQL, MySQL) and NoSQL (MongoDB, Redis). I understand query optimization, indexing strategies, and have designed schemas for high-throughput applications."},
            {"q": "How do you ensure code quality?", "a": "I write comprehensive unit and integration tests, use code reviews, follow SOLID principles, and implement CI/CD pipelines with automated testing. I also use linters and static analysis tools."},
            {"q": "Tell me about a time you failed.", "a": "Early in my career, I deployed code without thorough testing that caused a brief service outage. I learned the importance of comprehensive testing and CI/CD. Since then, I've never deployed without proper test coverage and review."},
            {"q": "How do you handle tight deadlines?", "a": "I prioritize ruthlessly, break tasks into small deliverables, and communicate proactively. I focus on the MVP first, identify blockers early, and am not afraid to ask for help when needed."},
            {"q": "What's your experience with cloud services?", "a": "I have experience with AWS services including EC2, S3, Lambda, RDS, ECS, and CloudFormation. I've designed and deployed cloud-native applications with auto-scaling and monitoring."},
            {"q": "How do you approach system design?", "a": "I start with requirements (functional and non-functional), estimate scale, then design from high-level architecture down to component details. I consider trade-offs between consistency, availability, and partition tolerance."},
            {"q": "Describe a time you mentored someone.", "a": "I mentored a junior developer on my team, holding weekly 1-on-1s, conducting pair programming sessions, and reviewing their code with detailed feedback. Within 6 months, they were contributing independently."},
            {"q": "What do you know about our company?", "a": f"I've researched {company} and I'm impressed by your products and engineering culture. I'm particularly interested in the technical challenges your team is solving and the impact your work has."},
            {"q": "How do you handle multiple priorities?", "a": "I use a combination of task management tools and the Eisenhower matrix. I categorize tasks by urgency and importance, focus on high-impact items first, and communicate timeline adjustments proactively."},
            {"q": "What's your experience with CI/CD?", "a": "I've set up and maintained CI/CD pipelines using GitHub Actions, Jenkins, and GitLab CI. I implement automated testing, security scanning, and deployment strategies including blue-green and canary deployments."},
            {"q": "How do you approach learning a new codebase?", "a": "I start with documentation and architecture diagrams, then trace the main request flows. I use the tests as documentation, read recent PRs for context, and ask specific questions to teammates."},
            {"q": "What makes you a good fit for this role?", "a": f"My {PERSONAL_INFO['years_of_experience']} years of experience in {tech_str} directly aligns with this role. I bring strong technical skills, a collaborative mindset, and a track record of delivering quality software on time."},
            {"q": "Do you have any questions for us?", "a": "What does the team structure look like? What are the biggest technical challenges the team is facing? How do you measure success for this role? What does the onboarding process look like?"},
        ]

        return {
            "company_overview": f"{company} - Research the company's products, culture, recent news, and tech blog before the interview.",
            "what_to_prepare": [
                f"Deep dive into {tech_str}",
                "Review system design fundamentals",
                "Prepare 5 STAR format behavioral stories",
                "Research the company's tech stack and recent engineering blog posts",
                "Practice coding problems on LeetCode (medium difficulty)",
                "Prepare thoughtful questions to ask the interviewer",
            ],
            "top_25_questions": common_questions,
            "previously_asked": [
                f"Design a scalable system for {company}'s core product",
                "Implement a rate limiter",
                "Explain the difference between SQL and NoSQL databases",
                "How would you optimize a slow API endpoint?",
                "Describe your experience with microservices",
                "How do you handle data consistency in distributed systems?",
                "Implement an LRU cache",
                "Tell me about a time you resolved a conflict with a teammate",
                "How would you design a URL shortener?",
                "What's your approach to technical debt?",
            ],
            "coding_topics": [
                "Arrays and Strings", "Hash Maps", "Trees and Graphs",
                "Dynamic Programming", "System Design", "API Design",
                "Database optimization", "Concurrency",
            ],
            "behavioral_tips": [
                "Use STAR format (Situation, Task, Action, Result)",
                "Quantify your achievements with numbers",
                "Show ownership and leadership in your stories",
                "Be honest about failures but focus on learnings",
                "Ask thoughtful questions about the team and culture",
            ],
            "salary_negotiation": f"Research {company}'s salary range on Glassdoor/Levels.fyi. Your target is ${PERSONAL_INFO['salary_expectation']}. Always negotiate - the first offer is rarely the best.",
            "red_flags_to_watch": [
                "High turnover rate or negative Glassdoor reviews",
                "Vague job responsibilities or unrealistic expectations",
                "No clear career growth path or mentorship",
            ],
        }

    def _build_interview_prep_html(self, job: dict, prep: dict) -> str:
        """Build a beautiful HTML email for interview preparation."""
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        tech_stack = job.get("tech_stack", [])
        status = job.get("status", "").replace("_", " ").title()

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; background: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 850px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                h1 {{ color: #2F5496; border-bottom: 3px solid #2F5496; padding-bottom: 10px; }}
                h2 {{ color: #2F5496; margin-top: 30px; border-left: 4px solid #2F5496; padding-left: 10px; }}
                h3 {{ color: #444; }}
                .badge {{ display: inline-block; background: #2F5496; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; margin: 2px; }}
                .tech-badge {{ display: inline-block; background: #e8f0fe; color: #2F5496; padding: 4px 10px; border-radius: 4px; margin: 2px; font-size: 13px; }}
                .qa-item {{ background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 10px 0; border-left: 4px solid #2F5496; }}
                .qa-item .question {{ font-weight: bold; color: #2F5496; margin-bottom: 8px; }}
                .qa-item .answer {{ color: #444; line-height: 1.6; }}
                .prep-list {{ background: #fff3cd; border-radius: 8px; padding: 15px; margin: 15px 0; }}
                .prep-list li {{ margin: 5px 0; }}
                .prev-questions {{ background: #f0f7ff; border-radius: 8px; padding: 15px; margin: 15px 0; }}
                .tip {{ background: #d4edda; border-radius: 8px; padding: 15px; margin: 10px 0; }}
                .warning {{ background: #f8d7da; border-radius: 8px; padding: 15px; margin: 10px 0; }}
                ol {{ counter-reset: item; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Interview Prep: {title}</h1>
                <p><strong>Company:</strong> {company} | <strong>Round:</strong> <span class="badge">{status}</span></p>
                <p><strong>Tech Stack:</strong> {''.join(f'<span class="tech-badge">{t}</span>' for t in tech_stack)}</p>

                <h2>Company Overview</h2>
                <p>{prep.get('company_overview', 'Research the company before your interview.')}</p>

                <h2>What to Prepare</h2>
                <div class="prep-list">
                    <ol>
        """

        for item in prep.get("what_to_prepare", []):
            html += f"<li><strong>{item}</strong></li>"

        html += """
                    </ol>
                </div>

                <h2>Top 25 Interview Questions & Answers</h2>
                <p><em>Tailored to your resume and this specific role:</em></p>
        """

        for i, qa in enumerate(prep.get("top_25_questions", [])[:25], 1):
            q = qa.get("q", "") if isinstance(qa, dict) else str(qa)
            a = qa.get("a", "") if isinstance(qa, dict) else ""
            html += f"""
                <div class="qa-item">
                    <div class="question">Q{i}: {q}</div>
                    <div class="answer">{a}</div>
                </div>
            """

        html += """
                <h2>Previously Asked Questions</h2>
                <p><em>Commonly asked at this company (Glassdoor/LeetCode data):</em></p>
                <div class="prev-questions">
                    <ol>
        """

        for q in prep.get("previously_asked", []):
            html += f"<li>{q}</li>"

        html += """
                    </ol>
                </div>
        """

        # Coding topics
        coding = prep.get("coding_topics", [])
        if coding:
            html += """
                <h2>Coding Topics to Review</h2>
                <div class="prep-list">
                    <ul>
            """
            for topic in coding:
                html += f"<li>{topic}</li>"
            html += "</ul></div>"

        # Behavioral tips
        tips = prep.get("behavioral_tips", [])
        if tips:
            html += "<h2>Behavioral Interview Tips</h2>"
            for tip in tips:
                html += f'<div class="tip">{tip}</div>'

        # Salary negotiation
        salary = prep.get("salary_negotiation", "")
        if salary:
            html += f"""
                <h2>Salary Negotiation</h2>
                <div class="prep-list">{salary}</div>
            """

        # Red flags
        flags = prep.get("red_flags_to_watch", [])
        if flags:
            html += '<h2>Red Flags to Watch</h2>'
            for flag in flags:
                html += f'<div class="warning">{flag}</div>'

        html += f"""
                <div class="footer">
                    Generated by Job Bot AI | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                    Good luck with your interview at {company}!
                </div>
            </div>
        </body>
        </html>
        """

        return html

    # ----------------------------------------------------------------
    # EMAIL SENDING
    # ----------------------------------------------------------------
    def _send_email(self, subject: str, html_body: str):
        """Send an HTML email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECIPIENT

        # Plain text fallback
        text_part = MIMEText("Please view this email in an HTML-capable email client.", "plain")
        html_part = MIMEText(html_body, "html")

        msg.attach(text_part)
        msg.attach(html_part)

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
                logger.info(f"Email sent: {subject}")
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed! For Gmail, use an App Password.")
            logger.error("Go to: Google Account > Security > 2-Step Verification > App passwords")
            raise
        except Exception as e:
            logger.error(f"Email send error: {e}")
            raise

    # ----------------------------------------------------------------
    # RESUME LOADING
    # ----------------------------------------------------------------
    def _load_resume(self) -> str:
        """Load resume text from PDF."""
        if not os.path.exists(RESUME_PATH):
            logger.warning(f"Resume not found at {RESUME_PATH}")
            return ""

        try:
            import PyPDF2
            with open(RESUME_PATH, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text[:5000]
        except ImportError:
            logger.warning("PyPDF2 not installed. Install with: pip install PyPDF2")
            return ""
        except Exception as e:
            logger.warning(f"Could not read resume PDF: {e}")
            return ""
