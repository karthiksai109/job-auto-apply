"use client";
import { useEffect, useState } from "react";
import { fetchJobs, fetchEligibleJobs } from "../components/api";
import {
  Briefcase,
  ExternalLink,
  Filter,
  Star,
  MapPin,
  Building2,
} from "lucide-react";

interface Job {
  title: string;
  company: string;
  location: string;
  url: string;
  match_score: number;
  match_reason: string;
  matched_skills: string[];
  missing_skills: string[];
  status: string;
  ats_type: string;
  applied_date?: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<"eligible" | "all" | "applied" | "failed">("eligible");
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (filter === "eligible") {
      fetchEligibleJobs().then((d) => {
        setJobs(d.jobs);
        setTotal(d.total);
      }).catch(() => {});
    } else if (filter === "all") {
      fetchJobs(undefined, 200).then((d) => {
        setJobs(d.jobs);
        setTotal(d.total);
      }).catch(() => {});
    } else {
      fetchJobs(filter === "applied" ? "applied" : "failed_to_apply", 200).then((d) => {
        setJobs(d.jobs);
        setTotal(d.total);
      }).catch(() => {});
    }
  }, [filter]);

  const filtered = search
    ? jobs.filter(
        (j) =>
          j.title.toLowerCase().includes(search.toLowerCase()) ||
          j.company.toLowerCase().includes(search.toLowerCase())
      )
    : jobs;

  const scoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-400 bg-emerald-500/20";
    if (score >= 60) return "text-amber-400 bg-amber-500/20";
    return "text-red-400 bg-red-500/20";
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case "applied":
        return "bg-emerald-500/20 text-emerald-400";
      case "scraped":
        return "bg-blue-500/20 text-blue-400";
      case "failed_to_apply":
        return "bg-red-500/20 text-red-400";
      case "manual_apply_needed":
        return "bg-amber-500/20 text-amber-400";
      default:
        return "bg-slate-500/20 text-slate-400";
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Briefcase className="w-6 h-6 text-indigo-400" />
          Jobs
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          {total} jobs found — filtered for junior/entry/intern roles matching your resume
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex rounded-lg overflow-hidden border border-[#1e293b]">
          {(["eligible", "all", "applied", "failed"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 text-xs font-medium capitalize transition-colors ${
                filter === f
                  ? "bg-indigo-500/20 text-indigo-400"
                  : "bg-[#0f172a] text-slate-400 hover:bg-[#1e293b]"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="flex-1 max-w-sm">
          <input
            type="text"
            placeholder="Search by title or company..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-[#0f172a] border border-[#1e293b] text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
          />
        </div>
        <span className="text-xs text-slate-500">
          <Filter className="w-3 h-3 inline mr-1" />
          {filtered.length} shown
        </span>
      </div>

      {/* Job List */}
      <div className="space-y-3">
        {filtered.map((job, i) => (
          <div
            key={i}
            className="glass-card rounded-xl p-5 hover:border-indigo-500/30 transition-colors animate-slide-up"
            style={{ animationDelay: `${Math.min(i * 30, 300)}ms` }}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold text-white truncate">
                    {job.title}
                  </h3>
                  {job.status && (
                    <span
                      className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${statusBadge(
                        job.status
                      )}`}
                    >
                      {job.status.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-400 mb-2">
                  <span className="flex items-center gap-1">
                    <Building2 className="w-3 h-3" />
                    {job.company}
                  </span>
                  {job.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {job.location}
                    </span>
                  )}
                  <span className="text-[10px] text-slate-500 uppercase">
                    {job.ats_type}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mb-2">{job.match_reason}</p>
                {job.matched_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {job.matched_skills.slice(0, 8).map((s) => (
                      <span
                        key={s}
                        className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      >
                        {s}
                      </span>
                    ))}
                    {job.missing_skills.slice(0, 3).map((s) => (
                      <span
                        key={s}
                        className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex flex-col items-end gap-2 flex-shrink-0">
                <div
                  className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-bold ${scoreColor(
                    job.match_score
                  )}`}
                >
                  <Star className="w-3 h-3" />
                  {job.match_score}
                </div>
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    <ExternalLink className="w-3 h-3" />
                    View
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-slate-500">
          <Briefcase className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No jobs match this filter</p>
        </div>
      )}
    </div>
  );
}
