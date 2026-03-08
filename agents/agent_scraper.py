"""
Agent 1: Job Scraper
Scrapes jobs from LinkedIn, Indeed, Monster, Dice, and career sites.
Uses Selenium for dynamic pages and requests/BeautifulSoup for static ones.
Stores all found jobs in the central job database.
"""
import time
import hashlib
import re
from datetime import datetime
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from agents.config import (
    SEARCH_QUERIES, LOCATIONS, LINKEDIN_EMAIL, LINKEDIN_PASSWORD,
    INDEED_EMAIL, MONSTER_EMAIL, PERSONAL_INFO, OPENAI_API_KEY, OPENAI_MODEL,
)
from agents.job_database import add_job, get_all_jobs
from agents.logger import get_logger

logger = get_logger("Scraper")


class JobScraperAgent:
    """
    Agent 1: Discovers new job postings across multiple platforms.
    Extracts job title, company, location, tech stack, URL, and platform.
    """

    def __init__(self, driver=None):
        self.driver = driver
        self.new_jobs_found = 0

    def run(self) -> int:
        """Run the full scraping cycle across all platforms."""
        logger.info("=" * 60)
        logger.info("AGENT 1: Job Scraper Starting...")
        logger.info(f"Search queries: {SEARCH_QUERIES}")
        logger.info(f"Locations: {LOCATIONS}")
        logger.info("=" * 60)

        total_new = 0

        # Scrape Indeed (API-like scraping with requests)
        logger.info("\n--- Scraping Indeed ---")
        total_new += self._scrape_indeed()

        # Scrape LinkedIn (requires Selenium)
        if self.driver:
            logger.info("\n--- Scraping LinkedIn ---")
            total_new += self._scrape_linkedin()

        # Scrape Dice (requests-based)
        logger.info("\n--- Scraping Dice ---")
        total_new += self._scrape_dice()

        # Scrape Monster (requests-based)
        logger.info("\n--- Scraping Monster ---")
        total_new += self._scrape_monster()

        # Scrape RemoteOK (API)
        logger.info("\n--- Scraping RemoteOK ---")
        total_new += self._scrape_remoteok()

        self.new_jobs_found = total_new
        logger.info(f"\nScraper complete! {total_new} new jobs found and added to database.")
        return total_new

    # ----------------------------------------------------------------
    # INDEED
    # ----------------------------------------------------------------
    def _scrape_indeed(self) -> int:
        count = 0
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        for query in SEARCH_QUERIES:
            for location in LOCATIONS:
                try:
                    url = (
                        f"https://www.indeed.com/jobs?"
                        f"q={query.replace(' ', '+')}"
                        f"&l={location.replace(' ', '+')}"
                        f"&fromage=3&sort=date"
                    )

                    resp = requests.get(url, headers=headers, timeout=15)
                    if resp.status_code != 200:
                        logger.warning(f"Indeed returned {resp.status_code} for {query}")
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    job_cards = soup.select(".job_seen_beacon, .resultContent, div[data-jk]")

                    for card in job_cards:
                        try:
                            title_el = card.select_one("h2.jobTitle a, a.jcs-JobTitle, .jobTitle span")
                            company_el = card.select_one(".companyName, [data-testid='company-name']")
                            location_el = card.select_one(".companyLocation, [data-testid='text-location']")
                            snippet_el = card.select_one(".job-snippet, .underShelfFooter")

                            title = title_el.get_text(strip=True) if title_el else "Unknown"
                            company = company_el.get_text(strip=True) if company_el else "Unknown"
                            job_location = location_el.get_text(strip=True) if location_el else location
                            description_snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                            # Extract job ID
                            jk = card.get("data-jk") or ""
                            if not jk and title_el and title_el.get("href"):
                                jk = title_el["href"].split("jk=")[-1].split("&")[0] if "jk=" in title_el.get("href", "") else ""
                            if not jk:
                                jk = hashlib.md5(f"{title}{company}indeed".encode()).hexdigest()[:12]

                            job_url = f"https://www.indeed.com/viewjob?jk={jk}" if jk and len(jk) < 30 else ""

                            tech_stack = self._extract_tech_stack(f"{title} {description_snippet}")

                            job = {
                                "job_id": jk,
                                "platform": "indeed",
                                "title": title,
                                "company": company,
                                "location": job_location,
                                "url": job_url,
                                "tech_stack": tech_stack,
                                "description_snippet": description_snippet[:500],
                                "search_query": query,
                            }

                            if add_job(job):
                                count += 1
                                logger.info(f"  + Indeed: {title} @ {company}")

                        except Exception as e:
                            logger.debug(f"  Indeed card parse error: {e}")
                            continue

                except Exception as e:
                    logger.error(f"Indeed scrape error for '{query}': {e}")

                time.sleep(2)  # Rate limiting

        logger.info(f"Indeed: {count} new jobs found")
        return count

    # ----------------------------------------------------------------
    # LINKEDIN (Selenium-based)
    # ----------------------------------------------------------------
    def _scrape_linkedin(self) -> int:
        count = 0
        if not self.driver:
            logger.warning("LinkedIn scraping requires a browser driver")
            return 0

        try:
            # Login
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(3)

            if "feed" not in self.driver.current_url:
                try:
                    email_el = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "username"))
                    )
                    email_el.clear()
                    email_el.send_keys(LINKEDIN_EMAIL)
                    pass_el = self.driver.find_element(By.ID, "password")
                    pass_el.clear()
                    pass_el.send_keys(LINKEDIN_PASSWORD)
                    self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                    time.sleep(5)
                except Exception as e:
                    logger.warning(f"LinkedIn login issue: {e}")

            for query in SEARCH_QUERIES[:4]:  # Limit to avoid rate limiting
                for location in LOCATIONS[:1]:
                    try:
                        search_url = (
                            f"https://www.linkedin.com/jobs/search/?"
                            f"keywords={query.replace(' ', '%20')}"
                            f"&location={location.replace(' ', '%20')}"
                            f"&f_AL=true&f_TPR=r86400&sortBy=DD"
                        )
                        self.driver.get(search_url)
                        time.sleep(4)

                        # Scroll to load
                        for _ in range(3):
                            self.driver.execute_script("window.scrollBy(0, 500);")
                            time.sleep(1)

                        cards = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            ".job-card-container, .jobs-search-results__list-item"
                        )

                        for card in cards[:15]:
                            try:
                                card.click()
                                time.sleep(2)

                                title = "Unknown"
                                company = "Unknown"
                                try:
                                    title_el = self.driver.find_element(
                                        By.CSS_SELECTOR,
                                        ".job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title"
                                    )
                                    title = title_el.text.strip()
                                except NoSuchElementException:
                                    pass

                                try:
                                    comp_el = self.driver.find_element(
                                        By.CSS_SELECTOR,
                                        ".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name"
                                    )
                                    company = comp_el.text.strip()
                                except NoSuchElementException:
                                    pass

                                # Get description for tech stack extraction
                                desc = ""
                                try:
                                    desc_el = self.driver.find_element(
                                        By.CSS_SELECTOR, ".jobs-description__content, .jobs-box__html-content"
                                    )
                                    desc = desc_el.text[:1000]
                                except NoSuchElementException:
                                    pass

                                url = self.driver.current_url
                                job_id_match = re.search(r"currentJobId=(\d+)", url)
                                job_id = job_id_match.group(1) if job_id_match else hashlib.md5(f"{title}{company}".encode()).hexdigest()[:12]

                                tech_stack = self._extract_tech_stack(f"{title} {desc}")

                                job = {
                                    "job_id": job_id,
                                    "platform": "linkedin",
                                    "title": title,
                                    "company": company,
                                    "location": location,
                                    "url": url.split("&")[0] if "&" in url else url,
                                    "tech_stack": tech_stack,
                                    "description_snippet": desc[:500],
                                    "search_query": query,
                                }

                                if add_job(job):
                                    count += 1
                                    logger.info(f"  + LinkedIn: {title} @ {company}")

                            except Exception as e:
                                logger.debug(f"  LinkedIn card error: {e}")
                                continue

                    except Exception as e:
                        logger.error(f"LinkedIn search error: {e}")

                    time.sleep(3)

        except Exception as e:
            logger.error(f"LinkedIn scraper error: {e}")

        logger.info(f"LinkedIn: {count} new jobs found")
        return count

    # ----------------------------------------------------------------
    # DICE (requests-based)
    # ----------------------------------------------------------------
    def _scrape_dice(self) -> int:
        count = 0
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        for query in SEARCH_QUERIES:
            try:
                # Dice has a jobs API
                api_url = (
                    f"https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search?"
                    f"q={query.replace(' ', '%20')}"
                    f"&countryCode2=US&radius=50&radiusUnit=mi"
                    f"&page=1&pageSize=20&facets=employmentType%7CpostedDate%7Cworkplace"
                    f"&filters.postedDate=ONE&filters.employmentType=CONTRACTS%7CFULLTIME"
                    f"&language=en"
                )

                resp = requests.get(api_url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", []):
                        try:
                            title = item.get("title", "Unknown")
                            company = item.get("companyName", "Unknown")
                            job_id = item.get("id", hashlib.md5(f"{title}{company}dice".encode()).hexdigest()[:12])
                            job_location = item.get("jobLocation", {}).get("displayName", "Remote")
                            desc = item.get("summary", "")

                            tech_stack = self._extract_tech_stack(f"{title} {desc}")

                            job = {
                                "job_id": job_id,
                                "platform": "dice",
                                "title": title,
                                "company": company,
                                "location": job_location,
                                "url": f"https://www.dice.com/job-detail/{job_id}",
                                "tech_stack": tech_stack,
                                "description_snippet": desc[:500],
                                "search_query": query,
                            }

                            if add_job(job):
                                count += 1
                                logger.info(f"  + Dice: {title} @ {company}")

                        except Exception as e:
                            logger.debug(f"  Dice item parse error: {e}")
                else:
                    # Fallback: scrape HTML
                    count += self._scrape_dice_html(query, headers)

            except Exception as e:
                logger.error(f"Dice API error for '{query}': {e}")

            time.sleep(2)

        logger.info(f"Dice: {count} new jobs found")
        return count

    def _scrape_dice_html(self, query: str, headers: dict) -> int:
        count = 0
        try:
            url = f"https://www.dice.com/jobs?q={query.replace(' ', '%20')}&filters.postedDate=ONE&filters.easyApply=true"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return 0

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("a[href*='/job-detail/']")
            for card in cards:
                try:
                    href = card.get("href", "")
                    title = card.get_text(strip=True) or "Unknown"
                    job_id = href.split("/job-detail/")[-1].split("?")[0] if "/job-detail/" in href else hashlib.md5(title.encode()).hexdigest()[:12]

                    job = {
                        "job_id": job_id,
                        "platform": "dice",
                        "title": title,
                        "company": "Unknown",
                        "location": "USA",
                        "url": f"https://www.dice.com{href}" if href.startswith("/") else href,
                        "tech_stack": self._extract_tech_stack(title),
                        "description_snippet": "",
                        "search_query": query,
                    }

                    if add_job(job):
                        count += 1
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Dice HTML fallback error: {e}")

        return count

    # ----------------------------------------------------------------
    # MONSTER (requests-based)
    # ----------------------------------------------------------------
    def _scrape_monster(self) -> int:
        count = 0
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        for query in SEARCH_QUERIES:
            try:
                url = (
                    f"https://www.monster.com/jobs/search?"
                    f"q={query.replace(' ', '+')}"
                    f"&where=United+States"
                    f"&page=1&so=m.h.s"
                )

                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Monster returned {resp.status_code}")
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("[data-testid='svx-job-card'], .job-cardstyle__JobCardComponent, article")

                for card in cards:
                    try:
                        title_el = card.select_one("h3, .job-cardstyle__JobCardTitle, [data-testid='jobTitle']")
                        company_el = card.select_one(".company, [data-testid='company'], .job-cardstyle__CompanyName")
                        location_el = card.select_one(".location, [data-testid='jobLocation']")
                        link_el = card.select_one("a[href*='job-openings']") or card.select_one("a")

                        title = title_el.get_text(strip=True) if title_el else "Unknown"
                        company = company_el.get_text(strip=True) if company_el else "Unknown"
                        job_location = location_el.get_text(strip=True) if location_el else "USA"
                        job_url = link_el.get("href", "") if link_el else ""
                        if job_url and not job_url.startswith("http"):
                            job_url = f"https://www.monster.com{job_url}"

                        job_id = hashlib.md5(f"{title}{company}monster".encode()).hexdigest()[:12]

                        tech_stack = self._extract_tech_stack(title)

                        job = {
                            "job_id": job_id,
                            "platform": "monster",
                            "title": title,
                            "company": company,
                            "location": job_location,
                            "url": job_url,
                            "tech_stack": tech_stack,
                            "description_snippet": "",
                            "search_query": query,
                        }

                        if add_job(job):
                            count += 1
                            logger.info(f"  + Monster: {title} @ {company}")

                    except Exception as e:
                        logger.debug(f"  Monster card error: {e}")

            except Exception as e:
                logger.error(f"Monster scrape error: {e}")

            time.sleep(2)

        logger.info(f"Monster: {count} new jobs found")
        return count

    # ----------------------------------------------------------------
    # REMOTE OK (JSON API - no auth needed)
    # ----------------------------------------------------------------
    def _scrape_remoteok(self) -> int:
        count = 0
        try:
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            resp = requests.get("https://remoteok.com/api", headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"RemoteOK returned {resp.status_code}")
                return 0

            data = resp.json()
            for item in data:
                if not isinstance(item, dict) or "id" not in item:
                    continue

                title = item.get("position", "Unknown")
                company = item.get("company", "Unknown")

                # Filter relevant jobs
                title_lower = title.lower()
                if not any(kw.lower() in title_lower for kw in ["engineer", "developer", "python", "backend", "fullstack", "full stack", "devops", "cloud", "data"]):
                    continue

                tags = item.get("tags", [])
                tech_stack = [t for t in tags if t] if tags else self._extract_tech_stack(title)

                job = {
                    "job_id": str(item.get("id", "")),
                    "platform": "remoteok",
                    "title": title,
                    "company": company,
                    "location": "Remote",
                    "url": item.get("url", f"https://remoteok.com/remote-jobs/{item.get('slug', '')}"),
                    "tech_stack": tech_stack,
                    "description_snippet": (item.get("description", "") or "")[:500],
                    "search_query": "remote",
                    "salary_min": item.get("salary_min", ""),
                    "salary_max": item.get("salary_max", ""),
                }

                if add_job(job):
                    count += 1
                    logger.info(f"  + RemoteOK: {title} @ {company}")

        except Exception as e:
            logger.error(f"RemoteOK error: {e}")

        logger.info(f"RemoteOK: {count} new jobs found")
        return count

    # ----------------------------------------------------------------
    # TECH STACK EXTRACTION
    # ----------------------------------------------------------------
    def _extract_tech_stack(self, text: str) -> List[str]:
        """Extract technology keywords from job text."""
        if not text:
            return []

        tech_keywords = [
            "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "Ruby",
            "React", "Angular", "Vue", "Node.js", "Django", "Flask", "FastAPI", "Spring",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Jenkins",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "DynamoDB",
            "REST", "GraphQL", "gRPC", "Microservices", "CI/CD",
            "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "NLP",
            "Kafka", "RabbitMQ", "Spark", "Hadoop", "Airflow",
            "Linux", "Git", "Agile", "Scrum", "JIRA",
            "HTML", "CSS", "SQL", "NoSQL", "API",
            ".NET", "PHP", "Scala", "Kotlin", "Swift",
            "Pandas", "NumPy", "Scikit-learn", "Tableau", "Power BI",
            "Snowflake", "Databricks", "dbt", "ETL",
            "Next.js", "Express", "NestJS", "Svelte",
            "Nginx", "Apache", "Serverless", "Lambda",
        ]

        found = []
        text_lower = text.lower()
        for tech in tech_keywords:
            if tech.lower() in text_lower:
                found.append(tech)

        return list(set(found))
