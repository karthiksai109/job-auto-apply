const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchStats() {
  const res = await fetch(`${API}/api/stats`, { cache: "no-store" });
  return res.json();
}

export async function fetchAgents() {
  const res = await fetch(`${API}/api/agents`, { cache: "no-store" });
  return res.json();
}

export async function fetchJobs(status?: string, limit = 100, offset = 0) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const res = await fetch(`${API}/api/jobs?${params}`, { cache: "no-store" });
  return res.json();
}

export async function fetchEligibleJobs() {
  const res = await fetch(`${API}/api/jobs/eligible`, { cache: "no-store" });
  return res.json();
}

export async function fetchAppliedJobs() {
  const res = await fetch(`${API}/api/applied`, { cache: "no-store" });
  return res.json();
}

export async function fetchResume() {
  const res = await fetch(`${API}/api/resume`, { cache: "no-store" });
  return res.json();
}

export async function startApply(batchSize = 30) {
  const res = await fetch(`${API}/api/apply?batch_size=${batchSize}`, {
    method: "POST",
  });
  return res.json();
}

export async function startScrape() {
  const res = await fetch(`${API}/api/scrape`, { method: "POST" });
  return res.json();
}
