"use client";
import { useEffect, useState } from "react";
import { fetchStats, fetchAgents } from "./components/api";
import {
  Briefcase,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  Bot,
  Rocket,
  ArrowRight,
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
  { key: "total_jobs", label: "Total Jobs", icon: Briefcase, bg: "#f0ece6", fg: "#8a7560" },
  { key: "applied", label: "Applied", icon: CheckCircle2, bg: "#dff0e5", fg: "#3d8b5e" },
  { key: "applied_today", label: "Today", icon: TrendingUp, bg: "#f0ddd4", fg: "#c96442" },
  { key: "eligible_to_apply", label: "Ready", icon: Rocket, bg: "#faf0d8", fg: "#c49231" },
  { key: "failed", label: "Failed", icon: XCircle, bg: "#f5ddd8", fg: "#c25a4a" },
  { key: "remaining_today", label: "Remaining", icon: Clock, bg: "#e8e5f5", fg: "#7c6bae" },
];

const AGENT_NAMES: Record<string, { label: string; desc: string; color: string }> = {
  scraper: { label: "Scraper", desc: "Greenhouse, Lever, RemoteOK", color: "#5b8a72" },
  applier: { label: "Applier", desc: "Playwright browser automation", color: "#c96442" },
  matcher: { label: "Matcher", desc: "Experience-aware scoring", color: "#c49231" },
  tracker: { label: "Tracker", desc: "Excel + DB sync", color: "#7c6bae" },
  notifier: { label: "Notifier", desc: "Email reports", color: "#8a7560" },
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
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold" style={{ color: "#1a1a1a" }}>Dashboard</h1>
          <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
            Real-time overview of your autonomous job application system
          </p>
        </div>
        <Link
          href="/apply"
          className="flex items-center gap-2 px-5 py-2 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition-opacity"
          style={{ background: "#c96442" }}
        >
          <Rocket className="w-3.5 h-3.5" />
          Apply Now
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {STAT_CARDS.map(({ key, label, icon: Icon, bg, fg }) => (
          <div key={key} className="glass-card p-4 animate-slide-up">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3" style={{ background: bg }}>
              <Icon className="w-4 h-4" style={{ color: fg }} />
            </div>
            <p className="text-2xl font-semibold" style={{ color: "#1a1a1a" }}>
              {stats ? (stats as unknown as Record<string, number>)[key] ?? 0 : "—"}
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: "#9a9a9a" }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Progress Bar */}
      {stats && (
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[13px] font-medium" style={{ color: "#1a1a1a" }}>
              Daily Progress
            </span>
            <span className="text-[13px] font-mono" style={{ color: "#c96442" }}>
              {stats.applied_today} / {stats.daily_target}
            </span>
          </div>
          <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: "#f0ece6" }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, (stats.applied_today / stats.daily_target) * 100)}%`,
                background: "#c96442",
              }}
            />
          </div>
        </div>
      )}

      {/* Agents Status */}
      <div>
        <h2 className="text-[15px] font-semibold mb-4 flex items-center gap-2" style={{ color: "#1a1a1a" }}>
          <Bot className="w-4 h-4" style={{ color: "#c96442" }} />
          Agents
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(AGENT_NAMES).map(([key, { label, desc, color }]) => {
            const agent = agents?.[key];
            const isRunning = agent?.status === "running";
            return (
              <div
                key={key}
                className={`glass-card p-4 ${isRunning ? "animate-pulse-glow" : ""}`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: isRunning ? color : "#d4d0c8" }} />
                    <h3 className="text-[13px] font-semibold" style={{ color: "#1a1a1a" }}>{label}</h3>
                  </div>
                  <span
                    className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                    style={isRunning ? {
                      background: "#f0ddd4", color: "#c96442"
                    } : {
                      background: "#dff0e5", color: "#3d8b5e"
                    }}
                  >
                    {agent?.status || "idle"}
                  </span>
                </div>
                <p className="text-[11px] mb-2" style={{ color: "#9a9a9a" }}>{desc}</p>
                {agent?.logs && agent.logs.length > 0 && (
                  <div className="mt-2 max-h-16 overflow-y-auto">
                    {agent.logs.slice(-2).map((log, i) => (
                      <p
                        key={i}
                        className="text-[10px] font-mono truncate"
                        style={{ color: log.level === "error" ? "#c25a4a" : log.level === "warn" ? "#c49231" : "#9a9a9a" }}
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

      {/* Pipeline */}
      <div className="glass-card p-6">
        <h2 className="text-[13px] font-semibold mb-5 text-center" style={{ color: "#6b6b6b" }}>
          Agent Pipeline
        </h2>
        <div className="flex items-center justify-center gap-1.5 flex-wrap">
          {[
            { name: "Scrape", sub: "50+ companies" },
            { name: "Score", sub: "Junior/Entry filter" },
            { name: "Apply", sub: "Playwright" },
            { name: "Track", sub: "Excel + DB" },
            { name: "Notify", sub: "Email report" },
          ].map((step, i) => (
            <div key={step.name} className="flex items-center gap-1.5">
              <div className="px-4 py-2.5 rounded-lg text-center" style={{ background: "#f0ece6" }}>
                <p className="text-[12px] font-semibold" style={{ color: "#1a1a1a" }}>{step.name}</p>
                <p className="text-[9px]" style={{ color: "#9a9a9a" }}>{step.sub}</p>
              </div>
              {i < 4 && <ArrowRight className="w-3.5 h-3.5" style={{ color: "#d4d0c8" }} />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
