"use client";
import { useEffect, useState } from "react";
import { fetchStats, fetchAgents } from "./components/api";
import {
  Activity,
  Briefcase,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  Bot,
  Rocket,
} from "lucide-react";
import Link from "next/link";

interface Stats {
  total_jobs: number;
  scraped: number;
  applied: number;
  applied_today: number;
  failed: number;
  eligible_to_apply: number;
  daily_target: number;
  remaining_today: number;
}

interface AgentState {
  status: string;
  logs: { ts: string; level: string; msg: string }[];
  last_run: string | null;
  stats: Record<string, unknown>;
}

const STAT_CARDS = [
  { key: "total_jobs", label: "Total Jobs", icon: Briefcase, color: "from-indigo-500 to-purple-600" },
  { key: "applied", label: "Applied", icon: CheckCircle2, color: "from-emerald-500 to-teal-600" },
  { key: "applied_today", label: "Applied Today", icon: TrendingUp, color: "from-amber-500 to-orange-600" },
  { key: "eligible_to_apply", label: "Ready to Apply", icon: Rocket, color: "from-cyan-500 to-blue-600" },
  { key: "failed", label: "Failed", icon: XCircle, color: "from-red-500 to-rose-600" },
  { key: "remaining_today", label: "Remaining Today", icon: Clock, color: "from-violet-500 to-fuchsia-600" },
];

const AGENT_NAMES: Record<string, { label: string; desc: string }> = {
  scraper: { label: "Scraper Agent", desc: "Scrapes Greenhouse, Lever, RemoteOK" },
  applier: { label: "Applier Agent", desc: "Playwright browser automation" },
  matcher: { label: "Matcher Agent", desc: "Experience-aware scoring engine" },
  tracker: { label: "Tracker Agent", desc: "Excel + DB sync" },
  notifier: { label: "Notifier Agent", desc: "Email notifications" },
};

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [agents, setAgents] = useState<Record<string, AgentState> | null>(null);

  useEffect(() => {
    const load = () => {
      fetchStats().then(setStats).catch(() => {});
      fetchAgents().then(setAgents).catch(() => {});
    };
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Multi-Agent AI Job Application System — Real-time Overview
          </p>
        </div>
        <Link
          href="/apply"
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <Rocket className="w-4 h-4" />
          Apply Now
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {STAT_CARDS.map(({ key, label, icon: Icon, color }) => (
          <div
            key={key}
            className="glass-card rounded-xl p-4 animate-slide-up"
          >
            <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center mb-3`}>
              <Icon className="w-4 h-4 text-white" />
            </div>
            <p className="text-2xl font-bold text-white">
              {stats ? (stats as unknown as Record<string, number>)[key] ?? 0 : "—"}
            </p>
            <p className="text-xs text-slate-400 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Progress Bar */}
      {stats && (
        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-slate-300">
              Daily Progress
            </span>
            <span className="text-sm text-indigo-400 font-mono">
              {stats.applied_today} / {stats.daily_target}
            </span>
          </div>
          <div className="w-full h-3 bg-[#1e293b] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, (stats.applied_today / stats.daily_target) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Agents Status */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Bot className="w-5 h-5 text-indigo-400" />
          Agent Status
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(AGENT_NAMES).map(([key, { label, desc }]) => {
            const agent = agents?.[key];
            const isRunning = agent?.status === "running";
            return (
              <div
                key={key}
                className={`glass-card rounded-xl p-5 transition-all duration-300 ${
                  isRunning ? "animate-pulse-glow border-indigo-500/40" : ""
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-white">{label}</h3>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                      isRunning
                        ? "bg-indigo-500/20 text-indigo-400"
                        : "bg-emerald-500/20 text-emerald-400"
                    }`}
                  >
                    {agent?.status || "idle"}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mb-3">{desc}</p>
                {agent?.last_run && (
                  <p className="text-[10px] text-slate-500">
                    Last run: {new Date(agent.last_run).toLocaleString()}
                  </p>
                )}
                {agent?.logs && agent.logs.length > 0 && (
                  <div className="mt-3 max-h-20 overflow-y-auto">
                    {agent.logs.slice(-3).map((log, i) => (
                      <p
                        key={i}
                        className={`text-[10px] font-mono truncate ${
                          log.level === "error"
                            ? "text-red-400"
                            : log.level === "warn"
                            ? "text-amber-400"
                            : "text-slate-500"
                        }`}
                      >
                        {log.ts} {log.msg}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Architecture */}
      <div className="glass-card rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-400" />
          Agent Pipeline
        </h2>
        <div className="flex items-center justify-center gap-2 flex-wrap">
          {["Scraper", "Matcher", "Applier", "Tracker", "Notifier"].map(
            (name, i) => (
              <div key={name} className="flex items-center gap-2">
                <div className="px-4 py-2 rounded-lg bg-[#1e293b] text-xs font-medium text-slate-300 border border-[#334155]">
                  {name}
                </div>
                {i < 4 && (
                  <svg width="24" height="12" viewBox="0 0 24 12" className="text-indigo-500">
                    <path d="M0 6h18M14 1l6 5-6 5" fill="none" stroke="currentColor" strokeWidth="1.5" />
                  </svg>
                )}
              </div>
            )
          )}
        </div>
        <p className="text-center text-[11px] text-slate-500 mt-4">
          Scrape → Score & Filter (Junior/Entry only) → Apply via Playwright → Track in Excel → Email Report
        </p>
      </div>
    </div>
  );
}
