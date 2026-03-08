"""
Company Board Database — Top 50 companies with Greenhouse/Lever board tokens.
Curated for SWE/Full-Stack/Backend roles. Fast to scrape (~90 seconds).

Greenhouse: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
Lever: https://api.lever.co/v0/postings/{token}?mode=json
"""

COMPANY_BOARDS = [
    # --- Greenhouse: Top companies for SWE roles ---
    ("airbnb", "Airbnb", "greenhouse"),
    ("stripe", "Stripe", "greenhouse"),
    ("figma", "Figma", "greenhouse"),
    ("discord", "Discord", "greenhouse"),
    ("reddit", "Reddit", "greenhouse"),
    ("coinbase", "Coinbase", "greenhouse"),
    ("robinhood", "Robinhood", "greenhouse"),
    ("databricks", "Databricks", "greenhouse"),
    ("cloudflare", "Cloudflare", "greenhouse"),
    ("datadog", "Datadog", "greenhouse"),
    ("vercel", "Vercel", "greenhouse"),
    ("brex", "Brex", "greenhouse"),
    ("ramp", "Ramp", "greenhouse"),
    ("notion", "Notion", "greenhouse"),
    ("airtable", "Airtable", "greenhouse"),
    ("webflow", "Webflow", "greenhouse"),
    ("gitlab", "GitLab", "greenhouse"),
    ("elastic", "Elastic", "greenhouse"),
    ("twilio", "Twilio", "greenhouse"),
    ("plaid", "Plaid", "greenhouse"),
    ("dropbox", "Dropbox", "greenhouse"),
    ("asana", "Asana", "greenhouse"),
    ("duolingo", "Duolingo", "greenhouse"),
    ("affirm", "Affirm", "greenhouse"),
    ("toast", "Toast", "greenhouse"),
    ("gusto", "Gusto", "greenhouse"),
    ("grafana", "Grafana Labs", "greenhouse"),
    ("mongodb", "MongoDB", "greenhouse"),
    ("sentry", "Sentry", "greenhouse"),
    ("zapier", "Zapier", "greenhouse"),
    ("wiz", "Wiz", "greenhouse"),

    # --- Lever: Top companies for SWE roles ---
    ("netflix", "Netflix", "lever"),
    ("openai", "OpenAI", "lever"),
    ("anthropic", "Anthropic", "lever"),
    ("scale", "Scale AI", "lever"),
    ("retool", "Retool", "lever"),
    ("supabase", "Supabase", "lever"),
    ("rippling", "Rippling", "lever"),
    ("mercury", "Mercury", "lever"),
    ("vanta", "Vanta", "lever"),
    ("dbt-labs", "dbt Labs", "lever"),
    ("temporal", "Temporal", "lever"),
    ("cohere", "Cohere", "lever"),
    ("perplexity", "Perplexity", "lever"),
    ("glean", "Glean", "lever"),
    ("cursor", "Cursor", "lever"),
    ("sourcegraph", "Sourcegraph", "lever"),
    ("posthog", "PostHog", "lever"),
    ("pinecone", "Pinecone", "lever"),
    ("neon", "Neon", "lever"),
    ("linear", "Linear", "lever"),
]


def get_greenhouse_companies() -> list:
    """Return list of (token, name) tuples for Greenhouse companies."""
    return [(token, name) for token, name, ats in COMPANY_BOARDS if ats == "greenhouse"]


def get_lever_companies() -> list:
    """Return list of (token, name) tuples for Lever companies."""
    return [(token, name) for token, name, ats in COMPANY_BOARDS if ats == "lever"]


def get_all_companies() -> list:
    """Return all companies as (token, name, ats_type) tuples."""
    return COMPANY_BOARDS


def search_companies(query: str) -> list:
    """Search companies by name."""
    query = query.lower()
    return [(t, n, a) for t, n, a in COMPANY_BOARDS if query in n.lower() or query in t.lower()]


# Stats
TOTAL_COMPANIES = len(set((t, a) for t, _, a in COMPANY_BOARDS))
GREENHOUSE_COUNT = len(set(t for t, _, a in COMPANY_BOARDS if a == "greenhouse"))
LEVER_COUNT = len(set(t for t, _, a in COMPANY_BOARDS if a == "lever"))
