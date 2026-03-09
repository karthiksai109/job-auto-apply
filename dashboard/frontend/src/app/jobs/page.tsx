"use client";
import { useEffect, useState } from "react";
import { fetchJobs, fetchEligibleJobs } from "../components/api";
import { Briefcase, ExternalLink, Filter, MapPin, Building2 } from "lucide-react";

interface Job {
  title: string; company: string; location: string; url: string;
  match_score: number; match_reason: string; matched_skills: string[];
  missing_skills: string[]; status: string; ats_type: string; applied_date?: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<"eligible" | "all" | "applied" | "failed">("eligible");
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (filter === "eligible") {
      fetchEligibleJobs().then((d) => { setJobs(d.jobs); setTotal(d.total); }).catch(() => {});
    } else if (filter === "all") {
      fetchJobs(undefined, 200).then((d) => { setJobs(d.jobs); setTotal(d.total); }).catch(() => {});
    } else {
      fetchJobs(filter === "applied" ? "applied" : "failed_to_apply", 200).then((d) => { setJobs(d.jobs); setTotal(d.total); }).catch(() => {});
    }
  }, [filter]);

  const filtered = search
    ? jobs.filter((j) => j.title.toLowerCase().includes(search.toLowerCase()) || j.company.toLowerCase().includes(search.toLowerCase()))
    : jobs;

  const scoreStyle = (score: number) => {
    if (score >= 80) return { background: "#dff0e5", color: "#3d8b5e" };
    if (score >= 60) return { background: "#faf0d8", color: "#c49231" };
    return { background: "#f5ddd8", color: "#c25a4a" };
  };

  const statusStyle = (status: string) => {
    switch (status) {
      case "applied": return { background: "#dff0e5", color: "#3d8b5e" };
      case "scraped": return { background: "#e8e5f5", color: "#7c6bae" };
      case "failed_to_apply": return { background: "#f5ddd8", color: "#c25a4a" };
      case "manual_apply_needed": return { background: "#faf0d8", color: "#c49231" };
      default: return { background: "#f0ece6", color: "#8a7560" };
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold flex items-center gap-2" style={{ color: "#1a1a1a" }}>
          <Briefcase className="w-5 h-5" style={{ color: "#c96442" }} />
          Jobs
        </h1>
        <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
          {total} jobs — junior/entry/intern roles matching your resume
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex rounded-lg overflow-hidden" style={{ border: "1px solid #e8e5e0" }}>
          {(["eligible", "all", "applied", "failed"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className="px-4 py-2 text-[12px] font-medium capitalize transition-colors"
              style={filter === f ? { background: "#c96442", color: "#fff" } : { background: "#fff", color: "#6b6b6b" }}>
              {f}
            </button>
          ))}
        </div>
        <input type="text" placeholder="Search title or company..."
          value={search} onChange={(e) => setSearch(e.target.value)}
          className="flex-1 max-w-xs px-3 py-2 rounded-lg text-[13px] focus:outline-none"
          style={{ background: "#fff", border: "1px solid #e8e5e0", color: "#1a1a1a" }} />
        <span className="text-[11px] flex items-center gap-1" style={{ color: "#9a9a9a" }}>
          <Filter className="w-3 h-3" /> {filtered.length} shown
        </span>
      </div>

      {/* Job List */}
      <div className="space-y-2.5">
        {filtered.map((job, i) => (
          <div key={i} className="glass-card p-4 animate-slide-up" style={{ animationDelay: `${Math.min(i * 20, 200)}ms` }}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-[13px] font-semibold truncate" style={{ color: "#1a1a1a" }}>{job.title}</h3>
                  {job.status && (
                    <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full" style={statusStyle(job.status)}>
                      {job.status.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-[11px] mb-2" style={{ color: "#9a9a9a" }}>
                  <span className="flex items-center gap-1"><Building2 className="w-3 h-3" />{job.company}</span>
                  {job.location && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{job.location}</span>}
                  <span className="text-[10px] uppercase">{job.ats_type}</span>
                </div>
                <p className="text-[11px] mb-2" style={{ color: "#9a9a9a" }}>{job.match_reason}</p>
                {job.matched_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {job.matched_skills.slice(0, 8).map((s) => (
                      <span key={s} className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: "#dff0e5", color: "#3d8b5e" }}>{s}</span>
                    ))}
                    {job.missing_skills.slice(0, 3).map((s) => (
                      <span key={s} className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: "#f5ddd8", color: "#c25a4a" }}>{s}</span>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex flex-col items-end gap-2 flex-shrink-0">
                <span className="text-[12px] font-bold px-2.5 py-1 rounded-lg" style={scoreStyle(job.match_score)}>
                  {job.match_score}
                </span>
                {job.url && (
                  <a href={job.url} target="_blank" rel="noopener noreferrer"
                    className="text-[10px] flex items-center gap-1" style={{ color: "#c96442" }}>
                    <ExternalLink className="w-3 h-3" /> View
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16">
          <Briefcase className="w-10 h-10 mx-auto mb-3" style={{ color: "#d4d0c8" }} />
          <p className="text-[13px]" style={{ color: "#9a9a9a" }}>No jobs match this filter</p>
        </div>
      )}
    </div>
  );
}
