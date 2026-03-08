<div align="center">

# 🤖 AgentApply AI

### Autonomous Multi-Agent Job Application System

**5 AI agents that scrape, score, apply, track, and notify — so you don't have to.**

Built by [Karthik Ramadugu](https://karthikramadugu.vercel.app/) · [LinkedIn](https://www.linkedin.com/in/ramadugukarthik/) · [GitHub](https://github.com/karthiksai109)

---

`Python` · `FastAPI` · `Next.js` · `Playwright` · `Tailwind CSS` · `Multi-Agent Architecture`

</div>

## What This Does

This is a **production-grade multi-agent AI system** that autonomously manages the entire job application lifecycle. It scrapes 300+ jobs from 50+ companies, filters them by experience level and skill match, applies via browser automation, tracks everything in Excel, and emails you a report — all in one click.

**Not a toy project.** This system has submitted **19 real applications** to companies like Dropbox, Twilio, Airtable, Affirm, Vercel, Duolingo, and MongoDB.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        AgentApply AI System                          │
│                                                                      │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │
│   │ Scraper │───▶│ Matcher │───▶│ Applier │───▶│ Tracker │          │
│   │  Agent  │    │  Agent  │    │  Agent  │    │  Agent  │          │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘          │
│     15 threads     Experience     Playwright     Excel + DB          │
│     Greenhouse     aware score    browser auto   sync                │
│     Lever          Junior/Entry   form fill +    ─────────┐         │
│     RemoteOK       filter         resume upload  ┌────────▼──┐      │
│                                                  │  Notifier  │      │
│   ┌──────────────────────────────────────────────│   Agent    │      │
│   │              FastAPI Backend                  └───────────┘      │
│   │        REST API + Background Tasks              Email report     │
│   └──────────────────────────────────────────────────────────────┘   │
│                              ▲                                       │
│   ┌──────────────────────────┴───────────────────────────────────┐   │
│   │              Next.js Dashboard (React + Tailwind)            │   │
│   │     Real-time stats · Agent monitor · One-click apply        │   │
│   └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## The 5 Agents

| # | Agent | What It Does | Tech |
|---|-------|-------------|------|
| 1 | **Scraper Agent** | Scrapes 50+ company career pages via Greenhouse, Lever, and RemoteOK APIs using 15 parallel threads. Finds 300+ jobs in under 2 minutes. | `ThreadPoolExecutor` `REST APIs` |
| 2 | **Matcher Agent** | Experience-aware scoring engine. Penalizes senior/lead/manager roles (-40pts), boosts junior/entry/intern (+15pts). Matches against your core stack with keyword + regex analysis. | `Regex` `Skill Matching` |
| 3 | **Applier Agent** | Uses Playwright to open real browser tabs, fill out Greenhouse/Lever application forms, upload your resume, answer custom questions, and click submit — like a human. | `Playwright` `Browser Automation` |
| 4 | **Tracker Agent** | Syncs all job data to a formatted Excel spreadsheet with color-coded statuses, match scores, company details, and timestamps. | `openpyxl` `JSON DB` |
| 5 | **Notifier Agent** | Sends styled HTML email reports when a batch completes. Includes job-by-job breakdown, stats summary, and application proof. | `SMTP` `HTML Email` |

## Key Features

- **Experience-Aware Filtering** — Only applies to jobs matching your actual experience level (junior, entry, associate, intern). Senior/lead/manager roles are automatically skipped.
- **One-Click Apply** — Dashboard button triggers 30 applications in sequence. When the batch finishes, the next 30 load automatically.
- **Real-Time Dashboard** — Next.js frontend with live agent status, progress bars, log streaming, and job analytics.
- **Proof of Application** — Applied jobs page shows every submission with timestamp, company, score, and direct link to the job posting.
- **Email Notifications** — Sends a styled HTML email after each batch with a full summary.
- **Smart Deduplication** — Same role at different locations? Only applies once, keeping the highest-scored variant.
- **Core Stack Bonus** — Jobs mentioning your specific tech stack (Python, FastAPI, React, Docker, AWS) get a score boost.

## Dashboard

The web dashboard provides a real-time control center for all 5 agents:

| Page | Description |
|------|-------------|
| **Dashboard** | Stats overview, daily progress bar, agent status cards, pipeline diagram |
| **Agents** | Detailed view of each agent with description, tech stack, live logs |
| **Jobs** | Full job list with filters (eligible, all, applied, failed), search, skill tags |
| **Apply** | One-click apply button, live progress tracking, batch completion with auto-reload |
| **Applied** | Timeline of all submitted applications with proof details |

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- A PDF resume

### 1. Clone and install

```bash
git clone https://github.com/karthiksai109/job-auto-apply.git
cd job-auto-apply

# Python dependencies
pip install -r requirements.txt
playwright install chromium

# Dashboard frontend
cd dashboard/frontend
npm install
cd ../..
```

### 2. Configure

```bash
copy .env.example .env
```

Edit `.env`:
```env
RESUME_PATH=C:\path\to\your\resume.pdf
FIRST_NAME=YourName
LAST_NAME=YourLastName
PERSONAL_EMAIL=you@email.com
PERSONAL_PHONE=+1234567890
CITY=YourCity
STATE=YourState
LINKEDIN_URL=https://linkedin.com/in/yourprofile
GITHUB_URL=https://github.com/yourusername
PORTFOLIO_URL=https://yourportfolio.com
```

### 3. Run

```bash
# Option A: Full pipeline (CLI)
python -m agents.orchestrator --full      # Scrape + Apply + Track

# Option B: Dashboard (recommended)
python -m uvicorn dashboard.server:app --port 8000    # Backend
cd dashboard/frontend && npm run dev                   # Frontend at localhost:3000

# Individual agents
python -m agents.orchestrator --scrape    # Scrape jobs only
python -m agents.orchestrator --apply     # Apply to top 30 jobs
python -m agents.orchestrator --stats     # View statistics
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Agents** | Python, ThreadPoolExecutor, Playwright |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **Frontend** | Next.js 16, React 19, TypeScript |
| **Styling** | Tailwind CSS v4, Lucide Icons |
| **Scraping** | Greenhouse API, Lever API, RemoteOK API |
| **Automation** | Playwright Chromium, Form filling, PDF upload |
| **Data** | JSON database, openpyxl Excel export |
| **Notifications** | SMTP, HTML email templates |
| **Scoring** | Regex skill matching, experience-level filtering |

## File Structure

```
job-auto-apply/
├── agents/
│   ├── orchestrator.py          # Main coordinator
│   ├── agent_scraper_v2.py      # 15-thread parallel scraper
│   ├── agent_applier_v3.py      # Playwright browser automation
│   ├── agent_excel_tracker.py   # Excel sync
│   ├── agent_email_notifier.py  # Email reports
│   ├── agent_status_checker.py  # Application monitoring
│   ├── job_matcher.py           # Experience-aware scoring
│   ├── resume_parser.py         # PDF parsing + skill extraction
│   ├── job_database.py          # Thread-safe JSON DB
│   ├── company_boards.py        # 50+ company ATS endpoints
│   ├── config.py                # Central configuration
│   └── logger.py                # Per-agent logging
├── dashboard/
│   ├── server.py                # FastAPI backend (REST API)
│   └── frontend/                # Next.js dashboard
│       └── src/app/
│           ├── page.tsx         # Dashboard overview
│           ├── agents/page.tsx  # Agent monitor
│           ├── jobs/page.tsx    # Job browser
│           ├── apply/page.tsx   # One-click apply
│           └── applied/page.tsx # Application proof
├── jobs_database.json           # Live job database
├── job_applications.xlsx        # Excel tracker
├── .env                         # Your configuration
├── requirements.txt             # Python dependencies
└── README.md
```

## How the Scoring Works

```
Score = Skill Match (0-80) + Title Relevance (0-20) + Core Stack Bonus (0-20) + Level Adjustment (-40 to +15)

Level Adjustment:
  "senior", "staff", "principal", "lead", "manager"  →  -40 (auto-reject)
  "junior", "entry", "intern", "associate"            →  +15 (preferred)
  3+ years required in description                    →  -20
  5+ years required in description                    →  -40

Core Stack Bonus:
  python, django, flask, fastapi, react, angular,
  docker, kubernetes, aws, postgresql, elasticsearch  →  +5 each (max +20)

Min Score to Apply: 60
```

## Results

| Metric | Value |
|--------|-------|
| Companies scraped | 51 |
| Jobs discovered | 362 |
| Senior roles filtered out | 208 |
| Eligible roles (junior/entry) | 76 |
| Applications submitted | 19 |
| Success rate | 63% |
| Time to scrape | ~2 min |
| Time per application | ~30 sec |

## Design Decisions

1. **Why Playwright over API POST?** Greenhouse/Lever submission APIs require company-side API keys. Browser automation is the only way to submit without company credentials.

2. **Why experience filtering?** Applying to "Senior Staff Engineer" with 1 year of experience wastes daily application slots and gets instant rejections. The -40 penalty ensures these never make the cut.

3. **Why 15 threads?** With 50 companies and fast API calls, 15 threads finishes scraping in under 2 minutes. More threads hit rate limits.

4. **Why JSON over SQL?** For a single-user local tool, a JSON file with thread-safe locking is simpler, portable, and easy to inspect. No database server needed.

5. **Why Next.js dashboard?** Real-time polling + server-side rendering + TypeScript + Tailwind = fast, type-safe, beautiful UI with minimal code.

---

<div align="center">

**Built with obsession by Karthik Ramadugu**

M.S. Computer Science · University of Dayton · 2025

[Portfolio](https://karthikramadugu.vercel.app/) · [LinkedIn](https://www.linkedin.com/in/ramadugukarthik/) · [GitHub](https://github.com/karthiksai109)

</div>
