"use client";
import { useEffect, useState } from "react";
import { fetchAgents, startScrape } from "../components/api";
import {
  Bot,
  Search,
  Crosshair,
  Rocket,
  FileSpreadsheet,
  Mail,
  Play,
  Loader2,
} from "lucide-react";

interface LogEntry {
  ts: string;
  level: string;
  msg: string;
}

interface AgentState {
  status: string;
  logs: LogEntry[];
  last_run: string | null;
  stats: Record<string, unknown>;
}

const AGENTS = [
  {
    key: "scraper",
    label: "Scraper Agent",
    icon: Search,
    color: "from-cyan-500 to-blue-600",
    desc: "Scrapes job postings from Greenhouse, Lever, and RemoteOK APIs using 15 parallel threads. Collects titles, descriptions, locations, and tech stacks.",
    tech: ["ThreadPoolExecutor", "REST APIs", "Greenhouse", "Lever", "RemoteOK"],
  },
  {
    key: "matcher",
    label: "Matcher Agent",
    icon: Crosshair,
    color: "from-violet-500 to-purple-600",
    desc: "Experience-aware scoring engine. Penalizes senior/lead/manager roles, boosts junior/entry/intern. Matches your core stack (Python, React, FastAPI, Docker, AWS).",
    tech: ["Keyword Matching", "Experience Filter", "Core Stack Bonus"],
  },
  {
    key: "applier",
    label: "Applier Agent",
    icon: Rocket,
    color: "from-indigo-500 to-blue-600",
    desc: "Uses Playwright browser automation to fill out and submit Greenhouse/Lever application forms. Uploads resume, answers questions, handles custom fields.",
    tech: ["Playwright", "Browser Automation", "Form Filling", "PDF Upload"],
  },
  {
    key: "tracker",
    label: "Tracker Agent",
    icon: FileSpreadsheet,
    color: "from-emerald-500 to-teal-600",
    desc: "Syncs all job data to Excel spreadsheet and JSON database. Tracks status changes, applied dates, match scores, and company details.",
    tech: ["openpyxl", "JSON DB", "Excel Export"],
  },
  {
    key: "notifier",
    label: "Notifier Agent",
    icon: Mail,
    color: "from-amber-500 to-orange-600",
    desc: "Sends email notifications when application batches complete. Includes summary stats and job-by-job breakdown in a styled HTML email.",
    tech: ["SMTP", "HTML Email", "Gmail"],
  },
];

export default function AgentsPage() {
  const [agents, setAgents] = useState<Record<string, AgentState> | null>(null);
  const [scraping, setScraping] = useState(false);

  useEffect(() => {
    const load = () => fetchAgents().then(setAgents).catch(() => {});
    load();
    const interval = setInterval(load, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleScrape = async () => {
    setScraping(true);
    await startScrape();
  };

  useEffect(() => {
    if (agents?.scraper?.status === "idle" && scraping) {
      setScraping(false);
    }
  }, [agents, scraping]);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Bot className="w-6 h-6 text-indigo-400" />
            AI Agents
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            5 specialized agents working autonomously to find and apply to jobs
          </p>
        </div>
        <button
          onClick={handleScrape}
          disabled={scraping}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-sm font-medium hover:bg-cyan-500/30 transition disabled:opacity-50"
        >
          {scraping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {scraping ? "Scraping..." : "Run Scraper"}
        </button>
      </div>

      <div className="space-y-6">
        {AGENTS.map(({ key, label, icon: Icon, color, desc, tech }) => {
          const agent = agents?.[key];
          const isRunning = agent?.status === "running";
          return (
            <div
              key={key}
              className={`glass-card rounded-xl overflow-hidden transition-all duration-300 ${
                isRunning ? "animate-pulse-glow" : ""
              }`}
            >
              <div className="p-6">
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center flex-shrink-0`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-base font-semibold text-white">{label}</h3>
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
                    <p className="text-sm text-slate-400 mb-3">{desc}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {tech.map((t) => (
                        <span
                          key={t}
                          className="text-[10px] px-2 py-0.5 rounded-md bg-[#1e293b] text-slate-400 border border-[#334155]"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Logs */}
              {agent?.logs && agent.logs.length > 0 && (
                <div className="border-t border-[#1e293b] bg-[#060b14] px-6 py-3 max-h-40 overflow-y-auto">
                  {agent.logs.slice(-10).map((log, i) => (
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
                            : "text-slate-400"
                        }`}
                      >
                        {log.msg}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
