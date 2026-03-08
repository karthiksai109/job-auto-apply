"use client";
import { useEffect, useState, useCallback } from "react";
import { fetchEligibleJobs, fetchAgents, fetchStats, startApply } from "../components/api";
import {
  Rocket,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Zap,
  Star,
  Building2,
} from "lucide-react";

interface Job {
  title: string;
  company: string;
  location: string;
  match_score: number;
  ats_type: string;
  match_reason: string;
  matched_skills: string[];
}

interface AgentStats {
  current_job?: string;
  progress?: number;
  total?: number;
  applied?: number;
  failed?: number;
  jobs_applied?: { title: string; company: string; score: number }[];
}

export default function ApplyPage() {
  const [eligible, setEligible] = useState<Job[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [stats, setStats] = useState<AgentStats>({});
  const [logs, setLogs] = useState<{ ts: string; level: string; msg: string }[]>([]);
  const [batchComplete, setBatchComplete] = useState(false);
  const [dailyStats, setDailyStats] = useState({ applied_today: 0, daily_target: 30 });

  const loadEligible = useCallback(() => {
    fetchEligibleJobs().then((d) => setEligible(d.jobs)).catch(() => {});
  }, []);

  useEffect(() => {
    loadEligible();
    fetchStats().then((s) => setDailyStats({ applied_today: s.applied_today, daily_target: s.daily_target })).catch(() => {});
  }, [loadEligible]);

  // Poll agent status while running
  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(() => {
      fetchAgents().then((agents) => {
        const applier = agents.applier;
        if (applier) {
          setStats(applier.stats || {});
          setLogs(applier.logs || []);
          if (applier.status === "idle" && isRunning) {
            setIsRunning(false);
            setBatchComplete(true);
            loadEligible();
            fetchStats().then((s) => setDailyStats({ applied_today: s.applied_today, daily_target: s.daily_target })).catch(() => {});
          }
        }
      }).catch(() => {});
    }, 1500);
    return () => clearInterval(interval);
  }, [isRunning, loadEligible]);

  const handleApply = async () => {
    setIsRunning(true);
    setBatchComplete(false);
    setStats({});
    setLogs([]);
    await startApply(30);
  };

  const handleNextBatch = () => {
    setBatchComplete(false);
    loadEligible();
    handleApply();
  };

  const progress = stats.progress && stats.total ? (stats.progress / stats.total) * 100 : 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Rocket className="w-6 h-6 text-indigo-400" />
            Apply to Jobs
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            {eligible.length} eligible jobs ready — Junior/Entry/Intern roles matching your resume
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Today</p>
          <p className="text-lg font-bold text-indigo-400">
            {dailyStats.applied_today} / {dailyStats.daily_target}
          </p>
        </div>
      </div>

      {/* Main Action Card */}
      <div className="glass-card rounded-2xl p-8">
        {!isRunning && !batchComplete && (
          <div className="text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-6">
              <Zap className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">
              Ready to Apply
            </h2>
            <p className="text-sm text-slate-400 mb-6 max-w-md mx-auto">
              {eligible.length} jobs matched to your profile. Click below to start
              applying to the top 30 via Playwright browser automation.
            </p>
            <button
              onClick={handleApply}
              disabled={eligible.length === 0}
              className="inline-flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Play className="w-4 h-4" />
              Apply to {Math.min(30, eligible.length)} Jobs
            </button>
          </div>
        )}

        {isRunning && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
              <div>
                <h2 className="text-lg font-bold text-white">Applying...</h2>
                <p className="text-xs text-slate-400">
                  {stats.current_job || "Starting up..."}
                </p>
              </div>
            </div>

            {/* Progress */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-400">
                  Job {stats.progress || 0} of {stats.total || "..."}
                </span>
                <span className="text-xs font-mono text-indigo-400">
                  {Math.round(progress)}%
                </span>
              </div>
              <div className="w-full h-2.5 bg-[#1e293b] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-700"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Live Stats */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-emerald-400">{stats.applied || 0}</p>
                <p className="text-[10px] text-emerald-400/60 uppercase tracking-wider">Applied</p>
              </div>
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-red-400">{stats.failed || 0}</p>
                <p className="text-[10px] text-red-400/60 uppercase tracking-wider">Failed</p>
              </div>
            </div>

            {/* Live Logs */}
            <div className="bg-[#060b14] rounded-lg p-4 max-h-60 overflow-y-auto">
              <p className="text-[10px] text-slate-600 uppercase tracking-wider mb-2">Live Logs</p>
              {logs.slice(-15).map((log, i) => (
                <div key={i} className="flex items-start gap-2 py-0.5">
                  <span className="text-[10px] font-mono text-slate-600 flex-shrink-0">
                    {log.ts}
                  </span>
                  <span
                    className={`text-[11px] font-mono ${
                      log.level === "error"
                        ? "text-red-400"
                        : log.level === "warn"
                        ? "text-amber-400"
                        : log.msg.includes("✓")
                        ? "text-emerald-400"
                        : "text-slate-400"
                    }`}
                  >
                    {log.msg}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {batchComplete && (
          <div className="text-center">
            <CheckCircle2 className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">
              Batch Complete!
            </h2>
            <p className="text-sm text-slate-400 mb-2">
              Applied to <span className="text-emerald-400 font-bold">{stats.applied || 0}</span> jobs
              {stats.failed ? (
                <>, <span className="text-red-400 font-bold">{stats.failed}</span> failed</>
              ) : null}
            </p>
            <p className="text-xs text-slate-500 mb-6">
              Email notification sent with application details
            </p>

            {/* Applied jobs list */}
            {stats.jobs_applied && stats.jobs_applied.length > 0 && (
              <div className="mb-6 text-left max-w-md mx-auto">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Applications Submitted</p>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {stats.jobs_applied.map((j, i) => (
                    <div key={i} className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                      <div className="flex items-center gap-2 min-w-0">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                        <span className="text-xs text-slate-300 truncate">{j.title}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 flex-shrink-0 ml-2">{j.company}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {eligible.length > 0 && (
              <button
                onClick={handleNextBatch}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold text-sm hover:opacity-90 transition-opacity"
              >
                <RefreshCw className="w-4 h-4" />
                Apply to Next {Math.min(30, eligible.length)} Jobs
              </button>
            )}
          </div>
        )}
      </div>

      {/* Eligible Jobs Preview */}
      {!isRunning && (
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-3">
            Next {Math.min(30, eligible.length)} Jobs to Apply
          </h3>
          <div className="space-y-2">
            {eligible.slice(0, 30).map((job, i) => (
              <div
                key={i}
                className="glass-card rounded-lg px-4 py-3 flex items-center justify-between animate-slide-up"
                style={{ animationDelay: `${Math.min(i * 20, 200)}ms` }}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-[10px] text-slate-600 font-mono w-5 text-right flex-shrink-0">
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-200 truncate">
                      {job.title}
                    </p>
                    <p className="text-[10px] text-slate-500 flex items-center gap-1">
                      <Building2 className="w-2.5 h-2.5" />
                      {job.company}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="flex gap-0.5">
                    {job.matched_skills.slice(0, 3).map((s) => (
                      <span key={s} className="text-[8px] px-1 py-0.5 rounded bg-indigo-500/10 text-indigo-400">
                        {s}
                      </span>
                    ))}
                  </div>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                    job.match_score >= 80 ? "text-emerald-400 bg-emerald-500/20" : "text-amber-400 bg-amber-500/20"
                  }`}>
                    <Star className="w-2.5 h-2.5 inline mr-0.5" />
                    {job.match_score}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
