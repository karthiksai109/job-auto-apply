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
  return (await safeFetch(`${API}/api/stats`)) ?? { total_jobs: 0, scraped: 0, applied: 0, applied_today: 0, failed: 0, eligible_to_apply: 0, daily_target: 50, remaining_today: 50 };
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

export async function startApply(batchSize = 50) {
  return (await safeFetch(`${API}/api/apply?batch_size=${batchSize}`, { method: "POST" })) ?? { status: "error" };
}

export async function startScrape() {
  return (await safeFetch(`${API}/api/scrape`, { method: "POST" })) ?? { status: "error" };
}

// ── New Agent APIs ──

export async function fetchFitReports() {
  return (await safeFetch(`${API}/api/fit-reports`)) ?? { reports: [], total: 0 };
}

export async function fetchFitReport(url: string) {
  return (await safeFetch(`${API}/api/fit-report?url=${encodeURIComponent(url)}`)) ?? null;
}

export async function startFitAnalysis() {
  return (await safeFetch(`${API}/api/analyze-fit`, { method: "POST" })) ?? { status: "error" };
}

export async function fetchInterviewPrep() {
  return (await safeFetch(`${API}/api/interview-prep`)) ?? { guides: [], total: 0 };
}

export async function fetchInterviewPrepJob(url: string) {
  return (await safeFetch(`${API}/api/interview-prep/job?url=${encodeURIComponent(url)}`)) ?? null;
}

export async function startGeneratePrep() {
  return (await safeFetch(`${API}/api/generate-prep`, { method: "POST" })) ?? { status: "error" };
}

export async function fetchProfile() {
  return (await safeFetch(`${API}/api/profile`)) ?? {};
}

export async function startProfileAnalysis() {
  return (await safeFetch(`${API}/api/analyze-profile`, { method: "POST" })) ?? { status: "error" };
}

export async function fetchSchedulerStatus() {
  return (await safeFetch(`${API}/api/scheduler/status`)) ?? { running: false, status: "idle", stats: {}, logs: [] };
}

export async function startScheduler() {
  return (await safeFetch(`${API}/api/scheduler/start`, { method: "POST" })) ?? { status: "error" };
}

export async function stopScheduler() {
  return (await safeFetch(`${API}/api/scheduler/stop`, { method: "POST" })) ?? { status: "error" };
}
