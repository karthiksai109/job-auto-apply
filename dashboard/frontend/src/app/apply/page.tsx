"use client";
import { useEffect, useState, useCallback } from "react";
import { fetchEligibleJobs, fetchAgents, fetchStats, startApply } from "../components/api";
import { Rocket, Play, Loader2, CheckCircle2, RefreshCw, Building2 } from "lucide-react";

interface Job { title: string; company: string; location: string; match_score: number; ats_type: string; match_reason: string; matched_skills: string[]; }
interface AgentStats { current_job?: string; progress?: number; total?: number; applied?: number; failed?: number; jobs_applied?: { title: string; company: string; score: number }[]; }

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

  const handleApply = async () => { setIsRunning(true); setBatchComplete(false); setStats({}); setLogs([]); await startApply(30); };
  const handleNextBatch = () => { setBatchComplete(false); loadEligible(); handleApply(); };
  const progress = stats.progress && stats.total ? (stats.progress / stats.total) * 100 : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <Rocket className="w-5 h-5" style={{ color: "#c96442" }} />
            Apply
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
            {eligible.length} eligible jobs — Junior/Entry/Intern roles
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-wider" style={{ color: "#9a9a9a" }}>Today</p>
          <p className="text-lg font-semibold" style={{ color: "#c96442" }}>
            {dailyStats.applied_today} / {dailyStats.daily_target}
          </p>
        </div>
      </div>

      {/* Main Action */}
      <div className="glass-card p-8">
        {!isRunning && !batchComplete && (
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5" style={{ background: "#f0ddd4" }}>
              <Rocket className="w-8 h-8" style={{ color: "#c96442" }} />
            </div>
            <h2 className="text-lg font-semibold mb-2" style={{ color: "#1a1a1a" }}>Ready to Apply</h2>
            <p className="text-[13px] mb-6 max-w-md mx-auto" style={{ color: "#9a9a9a" }}>
              {eligible.length} jobs matched to your profile. Playwright will open a browser and submit applications automatically.
            </p>
            <button onClick={handleApply} disabled={eligible.length === 0}
              className="inline-flex items-center gap-2 px-7 py-2.5 rounded-xl text-white text-[13px] font-semibold hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: "#c96442" }}>
              <Play className="w-4 h-4" />
              Apply to {Math.min(30, eligible.length)} Jobs
            </button>
          </div>
        )}

        {isRunning && (
          <div>
            <div className="flex items-center gap-3 mb-5">
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: "#c96442" }} />
              <div>
                <h2 className="text-[15px] font-semibold" style={{ color: "#1a1a1a" }}>Applying...</h2>
                <p className="text-[12px]" style={{ color: "#9a9a9a" }}>{stats.current_job || "Starting up..."}</p>
              </div>
            </div>
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[12px]" style={{ color: "#6b6b6b" }}>Job {stats.progress || 0} of {stats.total || "..."}</span>
                <span className="text-[12px] font-mono" style={{ color: "#c96442" }}>{Math.round(progress)}%</span>
              </div>
              <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: "#f0ece6" }}>
                <div className="h-full rounded-full transition-all duration-700" style={{ width: `${progress}%`, background: "#c96442" }} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="rounded-lg p-3 text-center" style={{ background: "#dff0e5" }}>
                <p className="text-2xl font-bold" style={{ color: "#3d8b5e" }}>{stats.applied || 0}</p>
                <p className="text-[10px] uppercase tracking-wider" style={{ color: "#5b8a72" }}>Applied</p>
              </div>
              <div className="rounded-lg p-3 text-center" style={{ background: "#f5ddd8" }}>
                <p className="text-2xl font-bold" style={{ color: "#c25a4a" }}>{stats.failed || 0}</p>
                <p className="text-[10px] uppercase tracking-wider" style={{ color: "#c25a4a" }}>Failed</p>
              </div>
            </div>
            <div className="rounded-lg p-4 max-h-52 overflow-y-auto" style={{ background: "#faf9f7", border: "1px solid #e8e5e0" }}>
              <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: "#d4d0c8" }}>Live Logs</p>
              {logs.slice(-12).map((log, i) => (
                <div key={i} className="flex items-start gap-2 py-0.5">
                  <span className="text-[10px] font-mono flex-shrink-0" style={{ color: "#d4d0c8" }}>{log.ts}</span>
                  <span className="text-[10px] font-mono"
                    style={{ color: log.level === "error" ? "#c25a4a" : log.level === "warn" ? "#c49231" : log.msg.includes("Applied") ? "#3d8b5e" : "#9a9a9a" }}>
                    {log.msg}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {batchComplete && (
          <div className="text-center">
            <CheckCircle2 className="w-14 h-14 mx-auto mb-4" style={{ color: "#3d8b5e" }} />
            <h2 className="text-lg font-semibold mb-2" style={{ color: "#1a1a1a" }}>Batch Complete</h2>
            <p className="text-[13px] mb-1" style={{ color: "#6b6b6b" }}>
              Applied to <span style={{ color: "#3d8b5e", fontWeight: 600 }}>{stats.applied || 0}</span> jobs
              {stats.failed ? (<>, <span style={{ color: "#c25a4a", fontWeight: 600 }}>{stats.failed}</span> failed</>) : null}
            </p>
            <p className="text-[11px] mb-6" style={{ color: "#9a9a9a" }}>Email notification sent</p>
            {stats.jobs_applied && stats.jobs_applied.length > 0 && (
              <div className="mb-6 text-left max-w-md mx-auto">
                <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: "#9a9a9a" }}>Submitted</p>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {stats.jobs_applied.map((j, i) => (
                    <div key={i} className="flex items-center justify-between py-1.5 px-3 rounded-lg" style={{ background: "#dff0e5" }}>
                      <div className="flex items-center gap-2 min-w-0">
                        <CheckCircle2 className="w-3 h-3 flex-shrink-0" style={{ color: "#3d8b5e" }} />
                        <span className="text-[12px] truncate" style={{ color: "#1a1a1a" }}>{j.title}</span>
                      </div>
                      <span className="text-[10px] flex-shrink-0 ml-2" style={{ color: "#6b6b6b" }}>{j.company}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {eligible.length > 0 && (
              <button onClick={handleNextBatch}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-white text-[13px] font-semibold hover:opacity-90 transition"
                style={{ background: "#c96442" }}>
                <RefreshCw className="w-4 h-4" />
                Next {Math.min(30, eligible.length)} Jobs
              </button>
            )}
          </div>
        )}
      </div>

      {/* Queue */}
      {!isRunning && (
        <div>
          <h3 className="text-[13px] font-semibold mb-3" style={{ color: "#6b6b6b" }}>
            Next {Math.min(30, eligible.length)} in queue
          </h3>
          <div className="space-y-1.5">
            {eligible.slice(0, 30).map((job, i) => (
              <div key={i} className="glass-card px-4 py-2.5 flex items-center justify-between animate-slide-up"
                style={{ animationDelay: `${Math.min(i * 15, 150)}ms` }}>
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-[10px] font-mono w-5 text-right flex-shrink-0" style={{ color: "#d4d0c8" }}>{i + 1}</span>
                  <div className="min-w-0">
                    <p className="text-[12px] font-medium truncate" style={{ color: "#1a1a1a" }}>{job.title}</p>
                    <p className="text-[10px] flex items-center gap-1" style={{ color: "#9a9a9a" }}>
                      <Building2 className="w-2.5 h-2.5" />{job.company}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {job.matched_skills.slice(0, 2).map((s) => (
                    <span key={s} className="text-[8px] px-1.5 py-0.5 rounded" style={{ background: "#f0ece6", color: "#8a7560" }}>{s}</span>
                  ))}
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded-lg"
                    style={job.match_score >= 80 ? { background: "#dff0e5", color: "#3d8b5e" } : { background: "#faf0d8", color: "#c49231" }}>
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
