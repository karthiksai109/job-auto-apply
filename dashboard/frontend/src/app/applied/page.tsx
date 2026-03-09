"use client";
import { useEffect, useState } from "react";
import { fetchAppliedJobs } from "../components/api";
import { CheckCircle2, ExternalLink, Building2, MapPin, Calendar, Download } from "lucide-react";

interface AppliedJob {
  title: string; company: string; location: string; url: string;
  match_score: number; ats_type: string; applied_date: string; match_reason: string;
}

export default function AppliedPage() {
  const [jobs, setJobs] = useState<AppliedJob[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchAppliedJobs().then((d) => { setJobs(d.jobs); setTotal(d.total); }).catch(() => {});
  }, []);

  const grouped = jobs.reduce<Record<string, AppliedJob[]>>((acc, j) => {
    const dateKey = j.applied_date
      ? new Date(j.applied_date).toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })
      : "Unknown Date";
    if (!acc[dateKey]) acc[dateKey] = [];
    acc[dateKey].push(j);
    return acc;
  }, {});

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <CheckCircle2 className="w-5 h-5" style={{ color: "#3d8b5e" }} />
            Applied
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
            {total} applications submitted — proof of every application
          </p>
        </div>
        <a href="http://localhost:8000/api/applied" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium transition"
          style={{ background: "#f0ece6", color: "#8a7560", border: "1px solid #e8e5e0" }}>
          <Download className="w-3 h-3" /> Export
        </a>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="glass-card p-5 text-center">
          <p className="text-2xl font-semibold" style={{ color: "#3d8b5e" }}>{total}</p>
          <p className="text-[11px] mt-1" style={{ color: "#9a9a9a" }}>Total Applied</p>
        </div>
        <div className="glass-card p-5 text-center">
          <p className="text-2xl font-semibold" style={{ color: "#c96442" }}>
            {new Set(jobs.map((j) => j.company)).size}
          </p>
          <p className="text-[11px] mt-1" style={{ color: "#9a9a9a" }}>Companies</p>
        </div>
        <div className="glass-card p-5 text-center">
          <p className="text-2xl font-semibold" style={{ color: "#c49231" }}>
            {jobs.length > 0 ? Math.round(jobs.reduce((s, j) => s + j.match_score, 0) / jobs.length) : 0}
          </p>
          <p className="text-[11px] mt-1" style={{ color: "#9a9a9a" }}>Avg Score</p>
        </div>
      </div>

      {/* Timeline */}
      {Object.entries(grouped).map(([dateStr, dateJobs]) => (
        <div key={dateStr}>
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-3.5 h-3.5" style={{ color: "#c96442" }} />
            <h2 className="text-[13px] font-semibold" style={{ color: "#1a1a1a" }}>{dateStr}</h2>
            <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
              style={{ background: "#f0ddd4", color: "#c96442" }}>
              {dateJobs.length} apps
            </span>
          </div>
          <div className="space-y-2 ml-1.5 pl-5" style={{ borderLeft: "2px solid #e8e5e0" }}>
            {dateJobs.map((job, i) => (
              <div key={i} className="glass-card p-4 animate-slide-up" style={{ animationDelay: `${Math.min(i * 25, 200)}ms` }}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" style={{ color: "#3d8b5e" }} />
                      <h3 className="text-[13px] font-semibold truncate" style={{ color: "#1a1a1a" }}>{job.title}</h3>
                    </div>
                    <div className="flex items-center gap-3 text-[11px]" style={{ color: "#9a9a9a" }}>
                      <span className="flex items-center gap-1"><Building2 className="w-3 h-3" />{job.company}</span>
                      {job.location && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{job.location}</span>}
                      <span className="text-[10px] uppercase">{job.ats_type}</span>
                      {job.applied_date && <span className="text-[10px]">{new Date(job.applied_date).toLocaleTimeString()}</span>}
                    </div>
                    <p className="text-[10px] mt-1" style={{ color: "#9a9a9a" }}>{job.match_reason}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <span className="text-[12px] font-bold px-2 py-0.5 rounded-lg" style={{ background: "#dff0e5", color: "#3d8b5e" }}>
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
        </div>
      ))}

      {jobs.length === 0 && (
        <div className="text-center py-16">
          <CheckCircle2 className="w-10 h-10 mx-auto mb-3" style={{ color: "#e8e5e0" }} />
          <p className="text-[13px]" style={{ color: "#9a9a9a" }}>No applications yet</p>
          <p className="text-[11px] mt-1" style={{ color: "#d4d0c8" }}>Go to Apply to start</p>
        </div>
      )}
    </div>
  );
}
