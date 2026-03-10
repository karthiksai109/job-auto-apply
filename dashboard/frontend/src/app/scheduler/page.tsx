"use client";
import { useEffect, useState } from "react";
import { fetchSchedulerStatus, startScheduler, stopScheduler, fetchStats, fetchAgents } from "../components/api";
import { Timer, Play, Square, Loader2, Activity, Zap, BarChart3, Clock, CheckCircle2, AlertTriangle } from "lucide-react";

interface SchedulerState {
  running: boolean;
  status: string;
  stats: { cycle?: number; last_scrape?: string; last_apply?: string };
  logs: { ts: string; level: string; msg: string }[];
}

interface Stats {
  total_jobs: number;
  scraped: number;
  applied: number;
  applied_today: number;
  eligible_to_apply: number;
  daily_target: number;
  remaining_today: number;
}

export default function SchedulerPage() {
  const [sched, setSched] = useState<SchedulerState>({ running: false, status: "idle", stats: {}, logs: [] });
  const [stats, setStats] = useState<Stats | null>(null);
  const [agents, setAgents] = useState<Record<string, { status: string }> | null>(null);
  const [starting, setStarting] = useState(false);

  const load = () => {
    fetchSchedulerStatus().then(setSched);
    fetchStats().then(setStats);
    fetchAgents().then(setAgents);
  };

  useEffect(() => { load(); const iv = setInterval(load, 3000); return () => clearInterval(iv); }, []);

  const handleStart = async () => {
    setStarting(true);
    await startScheduler();
    setTimeout(() => { setStarting(false); load(); }, 2000);
  };

  const handleStop = async () => {
    await stopScheduler();
    load();
  };

  const isRunning = sched.running || sched.status === "running";

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <Timer className="w-5 h-5" style={{ color: "#c96442" }} />
            24/7 Scheduler
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
            Autonomous scraping + applying — runs continuously
          </p>
        </div>
        {isRunning ? (
          <button onClick={handleStop}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-medium transition"
            style={{ background: "#f5ddd8", color: "#c25a4a", border: "1px solid #e8c5be" }}>
            <Square className="w-3.5 h-3.5" /> Stop Scheduler
          </button>
        ) : (
          <button onClick={handleStart} disabled={starting}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-medium transition disabled:opacity-50"
            style={{ background: "#dff0e5", color: "#3d8b5e", border: "1px solid #c5e0cc" }}>
            {starting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {starting ? "Starting..." : "Start 24/7 Mode"}
          </button>
        )}
      </div>

      {/* Status Banner */}
      <div className="glass-card p-5" style={isRunning ? { borderLeft: "4px solid #3d8b5e" } : { borderLeft: "4px solid #d4d0c8" }}>
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${isRunning ? "animate-pulse" : ""}`}
            style={{ background: isRunning ? "#dff0e518" : "#f0ece618" }}>
            {isRunning
              ? <Activity className="w-6 h-6" style={{ color: "#3d8b5e" }} />
              : <Clock className="w-6 h-6" style={{ color: "#9a9a9a" }} />}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-[15px] font-semibold" style={{ color: "#1a1a1a" }}>
                {isRunning ? "Scheduler is ACTIVE" : "Scheduler is STOPPED"}
              </h3>
              <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                style={isRunning ? { background: "#dff0e5", color: "#3d8b5e" } : { background: "#f0ece6", color: "#9a9a9a" }}>
                {sched.status}
              </span>
            </div>
            <p className="text-[12px] mt-0.5" style={{ color: "#6b6b6b" }}>
              {isRunning
                ? `Cycle ${sched.stats.cycle || 0} — scraping every 6h, applying every 4h`
                : "Click 'Start 24/7 Mode' to begin autonomous job applications"}
            </p>
          </div>
        </div>
      </div>

      {/* Live Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Applied Today", value: stats?.applied_today ?? 0, target: stats?.daily_target ?? 50, color: "#c96442", icon: Zap },
          { label: "Ready to Apply", value: stats?.eligible_to_apply ?? 0, target: null, color: "#3d8b5e", icon: CheckCircle2 },
          { label: "Total Applied", value: stats?.applied ?? 0, target: null, color: "#7c6bae", icon: BarChart3 },
          { label: "Scheduler Cycle", value: sched.stats.cycle ?? 0, target: null, color: "#c49231", icon: Timer },
        ].map(({ label, value, target, color, icon: Icon }) => (
          <div key={label} className="glass-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <Icon className="w-4 h-4" style={{ color }} />
              <span className="text-[11px]" style={{ color: "#9a9a9a" }}>{label}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color }}>
              {value}{target ? <span className="text-[13px] font-normal" style={{ color: "#9a9a9a" }}> / {target}</span> : null}
            </p>
          </div>
        ))}
      </div>

      {/* Scheduler Timing */}
      {sched.stats.last_scrape && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="glass-card p-4">
            <p className="text-[11px] font-bold uppercase tracking-wider mb-1" style={{ color: "#5b8a72" }}>Last Scrape</p>
            <p className="text-[13px] font-mono" style={{ color: "#4a4a4a" }}>{sched.stats.last_scrape}</p>
          </div>
          <div className="glass-card p-4">
            <p className="text-[11px] font-bold uppercase tracking-wider mb-1" style={{ color: "#c96442" }}>Last Apply</p>
            <p className="text-[13px] font-mono" style={{ color: "#4a4a4a" }}>{sched.stats.last_apply}</p>
          </div>
        </div>
      )}

      {/* Active Agent Statuses */}
      {agents && (
        <div className="glass-card p-5">
          <h3 className="text-[13px] font-semibold mb-3" style={{ color: "#1a1a1a" }}>Agent Status</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {["scraper", "applier", "fit_analyst", "interview_prep", "profile_marketer", "matcher", "tracker", "notifier"].map((key) => {
              const agent = agents[key];
              const isActive = agent?.status === "running";
              const labels: Record<string, string> = {
                scraper: "Scraper", applier: "Applier", fit_analyst: "Fit Analyst",
                interview_prep: "Interview Prep", profile_marketer: "Profile Marketer",
                matcher: "Matcher", tracker: "Tracker", notifier: "Notifier",
              };
              return (
                <div key={key} className="flex items-center gap-2 p-2 rounded-lg"
                  style={{ background: isActive ? "#dff0e518" : "#faf9f7" }}>
                  <div className="w-2 h-2 rounded-full" style={{ background: isActive ? "#3d8b5e" : "#d4d0c8" }} />
                  <span className="text-[11px]" style={{ color: isActive ? "#3d8b5e" : "#9a9a9a" }}>
                    {labels[key] || key}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Scheduler Logs */}
      {sched.logs.length > 0 && (
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-3" style={{ background: "#f3f1ee", borderBottom: "1px solid #e8e5e0" }}>
            <h3 className="text-[13px] font-semibold" style={{ color: "#1a1a1a" }}>Scheduler Logs</h3>
          </div>
          <div className="px-5 py-3 max-h-64 overflow-y-auto" style={{ background: "#faf9f7" }}>
            {sched.logs.map((log, i) => (
              <div key={i} className="flex items-start gap-2 py-0.5">
                <span className="text-[10px] font-mono flex-shrink-0" style={{ color: "#d4d0c8" }}>{log.ts}</span>
                <span className="text-[10px] font-mono"
                  style={{ color: log.level === "error" ? "#c25a4a" : log.level === "warn" ? "#c49231" : "#6b6b6b" }}>
                  {log.msg}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* How It Works */}
      <div className="glass-card p-6">
        <h3 className="text-[13px] font-semibold mb-4 text-center" style={{ color: "#6b6b6b" }}>How the 24/7 Scheduler Works</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {[
            { step: "1", title: "Scrape", desc: "Every 6 hours — scrapes 50+ companies for new jobs matching your profile", color: "#5b8a72" },
            { step: "2", title: "Score & Filter", desc: "90%+ match only — San Francisco, Bay Area, Remote — junior/mid level", color: "#c49231" },
            { step: "3", title: "Apply", desc: "Every 4 hours — Playwright fills forms, uploads resume, handles OTP codes", color: "#c96442" },
            { step: "4", title: "Analyze", desc: "Auto-generates fit reports and interview prep for every applied job", color: "#7c6bae" },
          ].map(({ step, title, desc, color }) => (
            <div key={step} className="text-center p-4 rounded-lg" style={{ background: color + "08" }}>
              <div className="w-8 h-8 rounded-full flex items-center justify-center mx-auto mb-2 text-[13px] font-bold"
                style={{ background: color + "18", color }}>
                {step}
              </div>
              <p className="text-[12px] font-semibold mb-1" style={{ color: "#1a1a1a" }}>{title}</p>
              <p className="text-[10px]" style={{ color: "#6b6b6b" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
