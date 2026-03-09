const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function safeFetch(url: string, opts?: RequestInit) {
  try {
    const res = await fetch(url, { ...opts, cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchStats() {
  return (await safeFetch(`${API}/api/stats`)) ?? { total_jobs: 0, scraped: 0, applied: 0, applied_today: 0, failed: 0, eligible_to_apply: 0, daily_target: 30, remaining_today: 30 };
}

export async function fetchAgents() {
  return (await safeFetch(`${API}/api/agents`)) ?? {};
}

export async function fetchJobs(status?: string, limit = 100, offset = 0) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return (await safeFetch(`${API}/api/jobs?${params}`)) ?? { jobs: [], total: 0 };
}

export async function fetchEligibleJobs() {
  return (await safeFetch(`${API}/api/jobs/eligible`)) ?? { jobs: [], total: 0 };
}

export async function fetchAppliedJobs() {
  return (await safeFetch(`${API}/api/applied`)) ?? { jobs: [], total: 0 };
}

export async function fetchResume() {
  return (await safeFetch(`${API}/api/resume`)) ?? {};
}

export async function startApply(batchSize = 30) {
  return (await safeFetch(`${API}/api/apply?batch_size=${batchSize}`, { method: "POST" })) ?? { status: "error" };
}

export async function startScrape() {
  return (await safeFetch(`${API}/api/scrape`, { method: "POST" })) ?? { status: "error" };
}
