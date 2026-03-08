"use client";
import { useEffect, useState } from "react";
import { fetchAppliedJobs } from "../components/api";
import {
  CheckCircle2,
  ExternalLink,
  Building2,
  MapPin,
  Calendar,
  Star,
  Download,
} from "lucide-react";

interface AppliedJob {
  title: string;
  company: string;
  location: string;
  url: string;
  match_score: number;
  ats_type: string;
  applied_date: string;
  match_reason: string;
}

export default function AppliedPage() {
  const [jobs, setJobs] = useState<AppliedJob[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchAppliedJobs()
      .then((d) => {
        setJobs(d.jobs);
        setTotal(d.total);
      })
      .catch(() => {});
  }, []);

  const grouped = jobs.reduce<Record<string, AppliedJob[]>>((acc, j) => {
    const dateKey = j.applied_date
      ? new Date(j.applied_date).toLocaleDateString("en-US", {
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
        })
      : "Unknown Date";
    if (!acc[dateKey]) acc[dateKey] = [];
    acc[dateKey].push(j);
    return acc;
  }, {});

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            Applied Jobs
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            {total} applications submitted — proof of every application
          </p>
        </div>
        <a
          href="http://localhost:8000/api/applied"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1e293b] text-slate-300 text-xs font-medium hover:bg-[#334155] transition border border-[#334155]"
        >
          <Download className="w-3 h-3" />
          Export JSON
        </a>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-card rounded-xl p-5 text-center">
          <p className="text-3xl font-bold text-emerald-400">{total}</p>
          <p className="text-xs text-slate-400 mt-1">Total Applied</p>
        </div>
        <div className="glass-card rounded-xl p-5 text-center">
          <p className="text-3xl font-bold text-indigo-400">
            {new Set(jobs.map((j) => j.company)).size}
          </p>
          <p className="text-xs text-slate-400 mt-1">Companies</p>
        </div>
        <div className="glass-card rounded-xl p-5 text-center">
          <p className="text-3xl font-bold text-amber-400">
            {jobs.length > 0
              ? Math.round(jobs.reduce((s, j) => s + j.match_score, 0) / jobs.length)
              : 0}
          </p>
          <p className="text-xs text-slate-400 mt-1">Avg Match Score</p>
        </div>
      </div>

      {/* Timeline */}
      {Object.entries(grouped).map(([dateStr, dateJobs]) => (
        <div key={dateStr}>
          <div className="flex items-center gap-3 mb-3">
            <Calendar className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-slate-300">{dateStr}</h2>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400">
              {dateJobs.length} apps
            </span>
          </div>
          <div className="space-y-2 ml-2 border-l-2 border-[#1e293b] pl-5">
            {dateJobs.map((job, i) => (
              <div
                key={i}
                className="glass-card rounded-xl p-4 hover:border-emerald-500/30 transition-colors animate-slide-up"
                style={{ animationDelay: `${Math.min(i * 30, 200)}ms` }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                      <h3 className="text-sm font-semibold text-white truncate">
                        {job.title}
                      </h3>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400">
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
                      {job.applied_date && (
                        <span className="text-[10px] text-slate-500">
                          {new Date(job.applied_date).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">{job.match_reason}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <span className="flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-500/20 px-2 py-0.5 rounded-lg">
                      <Star className="w-3 h-3" />
                      {job.match_score}
                    </span>
                    {job.url && (
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        View Job
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
        <div className="text-center py-20 text-slate-500">
          <CheckCircle2 className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-sm">No applications yet</p>
          <p className="text-xs mt-1">Go to the Apply page to start applying</p>
        </div>
      )}
    </div>
  );
}
