"""
Agent 1 (v2): Safe Job Scraper — FAST with parallel requests.
Scrapes jobs from direct company career pages via Greenhouse/Lever APIs.
No Selenium needed. No risk of bans. Pure API calls.
Uses 10 parallel threads — finishes in ~2 min instead of 20.

Sources:
  1. Greenhouse Job Board API (200+ companies)
  2. Lever Postings API (100+ companies)
  3. RemoteOK API (remote jobs)
"""
import re
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.config import SEARCH_QUERIES, JobStatus
from agents.logger import get_logger
from agents.job_database import add_job, add_jobs_bulk, get_all_jobs
from agents.resume_parser import get_parsed_resume, get_all_skills_flat
from agents.job_matcher import score_job, MIN_MATCH_SCORE
from agents.company_boards import get_greenhouse_companies, get_lever_companies

logger = get_logger("Scraper_v2")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

MAX_WORKERS = 15  # parallel API calls
MAX_JOBS_PER_COMPANY = 25  # cap per company to keep things fast


def _extract_tech_stack(text: str) -> list:
    if not text:
        return []
    text_lower = text.lower()
    tech_keywords = {
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "sql",
        "react", "angular", "vue", "next.js", "node.js", "django", "flask",
        "fastapi", "spring", "spring boot", "express", ".net",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "kafka", "rabbitmq", "graphql", "rest", "grpc",
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "pandas", "spark", "airflow", "dbt",
        "ci/cd", "jenkins", "github actions", "gitlab ci",
        "linux", "nginx", "prometheus", "grafana", "datadog",
        "git", "agile", "scrum", "microservices",
    }
    found = []
    for tech in tech_keywords:
        if re.search(r'\b' + re.escape(tech) + r'\b', text_lower):
            found.append(tech.title())
    return sorted(set(found))


def _is_relevant_title(title: str, target_roles: list, search_queries: list) -> bool:
    title_lower = title.lower()
    skip_keywords = [
        "director", "vp ", "vice president", "chief", "cto", "cfo", "ceo",
        "head of", "principal", "staff", "distinguished",
        "intern ", "internship",
        "recruiter", "talent", "hr ", "human resources",
        "sales ", "account executive", "business development",
        "marketing ", "content ", "copywriter",
        "legal", "lawyer", "counsel",
        "finance ", "accountant", "bookkeeper",
        "designer", "graphic",
    ]
    for skip in skip_keywords:
        if skip in title_lower:
            return False
    all_queries = [q.lower() for q in (target_roles + search_queries)]
    for query in all_queries:
        query_words = set(query.split())
        title_words = set(title_lower.split())
        if len(query_words & title_words) >= 1:
            return True
    if any(word in title_lower for word in ["engineer", "developer", "programmer", "swe", "sde"]):
        return True
    return False


class SafeJobScraperAgent:
    """Scrapes jobs from Greenhouse + Lever APIs + RemoteOK using parallel threads."""

    def __init__(self):
        self.existing_urls = set()
        self._lock = threading.Lock()
        self.new_jobs = 0
        self.total_scraped = 0
        self.total_matched = 0
        self.target_roles = []
        self._pending_jobs = []  # collect jobs in memory, flush periodically

    def _flush_pending(self):
        """Write pending jobs to DB and clear the buffer."""
        with self._lock:
            batch = list(self._pending_jobs)
            self._pending_jobs.clear()
        if batch:
            added = add_jobs_bulk(batch)
            logger.info(f"  [flush] Saved {added} jobs to database")

    def run(self) -> int:
        """Run the scraper. Returns number of new relevant jobs found."""
        logger.info("=" * 60)
        logger.info("AGENT 1 (v2): Safe Job Scraper (parallel)")
        logger.info("=" * 60)

        resume = get_parsed_resume()
        self.target_roles = resume.get("target_roles", SEARCH_QUERIES[:3])
        skills = get_all_skills_flat()

        logger.info(f"Target roles: {self.target_roles}")
        logger.info(f"Skills: {', '.join(skills[:15])}...")
        logger.info(f"Min match score: {MIN_MATCH_SCORE}/100")

        existing = get_all_jobs()
        self.existing_urls = set(j.get("url", "") for j in existing)
        logger.info(f"Existing jobs in DB: {len(existing)}")

        # Scrape Greenhouse + Lever in parallel
        gh_companies = get_greenhouse_companies()
        lv_companies = get_lever_companies()
        logger.info(f"\nScraping {len(gh_companies)} Greenhouse + {len(lv_companies)} Lever companies ({MAX_WORKERS} threads)...")

        tasks = []
        for token, name in gh_companies:
            tasks.append(("greenhouse", token, name))
        for token, name in lv_companies:
            tasks.append(("lever", token, name))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(self._scrape_one, ats, token, name): name for ats, token, name in tasks}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.debug(f"Thread error for {futures[future]}: {e}")

        # RemoteOK (single call)
        logger.info("\n--- Scraping RemoteOK ---")
        self._scrape_remoteok()

        # Score all collected jobs in one fast batch, then save
        logger.info(f"\nScoring {len(self._pending_jobs)} title-matched jobs...")
        scored_jobs = []
        for job in self._pending_jobs:
            job = score_job(job)
            if job.get("match_score", 0) >= MIN_MATCH_SCORE:
                scored_jobs.append(job)
                self.total_matched += 1

        self.new_jobs = len(scored_jobs)
        if scored_jobs:
            added = add_jobs_bulk(scored_jobs)
            logger.info(f"Saved {added} jobs to database")

        # Log top 10
        scored_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
        for j in scored_jobs[:10]:
            logger.info(f"  [{j['match_score']:3d}] {j.get('title','')} @ {j.get('company','')} ({j.get('location','')})")

        logger.info(f"\nScraper complete!")
        logger.info(f"  Total jobs checked: {self.total_scraped}")
        logger.info(f"  Matched your resume: {self.total_matched}")
        logger.info(f"  New jobs saved: {self.new_jobs}")

        return self.new_jobs

    def _scrape_one(self, ats_type: str, token: str, company_name: str):
        """Scrape a single company board (called from thread pool). No scoring — just fetch + title filter."""
        try:
            if ats_type == "greenhouse":
                jobs_raw = self._fetch_greenhouse(token)
            else:
                jobs_raw = self._fetch_lever(token)

            if not jobs_raw:
                return

            company_new = 0
            for job in jobs_raw:
                if company_new >= MAX_JOBS_PER_COMPANY:
                    break

                title = job.get("title", "")
                if not _is_relevant_title(title, self.target_roles, SEARCH_QUERIES):
                    continue

                job_url = job.get("url", "")
                if not job_url:
                    continue

                job["company"] = company_name
                job["platform"] = ats_type
                job["ats_type"] = ats_type
                job["ats_token"] = token

                with self._lock:
                    self.total_scraped += 1
                    if job_url not in self.existing_urls:
                        self._pending_jobs.append(job)
                        self.existing_urls.add(job_url)
                        company_new += 1

            if company_new > 0:
                logger.info(f"  {company_name}: {company_new} title-matched jobs")

        except Exception as e:
            logger.debug(f"Error scraping {company_name}: {e}")

    def _fetch_greenhouse(self, token: str) -> list:
        """Fetch jobs from a Greenhouse board. Returns normalized job list."""
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json()
            raw_jobs = data.get("jobs", [])
            result = []
            for j in raw_jobs:
                desc = j.get("content", "")
                clean = re.sub(r'<[^>]+>', ' ', desc)
                result.append({
                    "title": j.get("title", ""),
                    "location": j.get("location", {}).get("name", ""),
                    "url": j.get("absolute_url", ""),
                    "description": clean[:3000],
                    "tech_stack": _extract_tech_stack(clean),
                    "ats_job_id": str(j.get("id", "")),
                    "posted_date": j.get("updated_at", ""),
                })
            return result
        except Exception:
            return []

    def _fetch_lever(self, token: str) -> list:
        """Fetch jobs from a Lever board. Returns normalized job list."""
        try:
            url = f"https://api.lever.co/v0/postings/{token}?mode=json"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                return []
            raw = resp.json()
            if not isinstance(raw, list):
                return []
            result = []
            for j in raw:
                categories = j.get("categories", {})
                desc_parts = [j.get("descriptionPlain", "")]
                for section in j.get("lists", []):
                    desc_parts.append(section.get("content", ""))
                desc = " ".join(desc_parts)
                clean = re.sub(r'<[^>]+>', ' ', desc)
                result.append({
                    "title": j.get("text", ""),
                    "location": categories.get("location", ""),
                    "url": j.get("hostedUrl", ""),
                    "description": clean[:3000],
                    "tech_stack": _extract_tech_stack(clean),
                    "ats_job_id": j.get("id", ""),
                    "apply_url": j.get("applyUrl", ""),
                    "commitment": categories.get("commitment", ""),
                    "team": categories.get("team", ""),
                })
            return result
        except Exception:
            return []

    def _scrape_remoteok(self):
        """Scrape RemoteOK API for remote tech jobs."""
        try:
            resp = requests.get("https://remoteok.com/api",
                                headers={"User-Agent": "JobSearchBot/2.0"}, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"RemoteOK returned {resp.status_code}")
                return
            data = resp.json()
            if not isinstance(data, list):
                return
            remote_new = 0
            for item in data[1:]:
                self.total_scraped += 1
                title = item.get("position", "")
                company = item.get("company", "")
                location = item.get("location", "Remote")
                url = item.get("url", "")
                description = item.get("description", "")
                tags = item.get("tags", [])
                if url and not url.startswith("http"):
                    url = f"https://remoteok.com{url}"
                if not _is_relevant_title(title, self.target_roles, SEARCH_QUERIES):
                    continue
                if url in self.existing_urls:
                    continue
                clean_desc = re.sub(r'<[^>]+>', ' ', description)
                tech_stack = _extract_tech_stack(clean_desc)
                if tags:
                    tech_stack = list(set(tech_stack + [t.title() for t in tags]))
                job = {
                    "title": title, "company": company,
                    "location": location or "Remote", "url": url,
                    "platform": "remoteok", "description": clean_desc[:3000],
                    "tech_stack": tech_stack, "ats_type": "external",
                    "salary_min": item.get("salary_min", ""),
                    "salary_max": item.get("salary_max", ""),
                    "posted_date": item.get("date", ""),
                }
                job = score_job(job)
                if job.get("match_score", 0) >= MIN_MATCH_SCORE:
                    self.total_matched += 1
                    if url not in self.existing_urls:
                        self._pending_jobs.append(job)
                        self.existing_urls.add(url)
                        self.new_jobs += 1
                        remote_new += 1
                        logger.info(f"  + [{job['match_score']:3d}] {title} @ {company}")
            logger.info(f"RemoteOK: {remote_new} relevant remote jobs")
        except Exception as e:
            logger.error(f"RemoteOK error: {e}")
