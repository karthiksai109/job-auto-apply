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

interface LogEntry { ts: string; level: string; msg: string; }
interface AgentState { status: string; logs: LogEntry[]; last_run: string | null; stats: Record<string, unknown>; }

const AGENTS = [
  { key: "scraper", label: "Scraper Agent", icon: Search, color: "#5b8a72",
    desc: "Scrapes job postings from Greenhouse, Lever, and RemoteOK APIs using 15 parallel threads. Collects titles, descriptions, locations, and tech stacks.",
    tech: ["ThreadPoolExecutor", "REST APIs", "Greenhouse", "Lever", "RemoteOK"] },
  { key: "matcher", label: "Matcher Agent", icon: Crosshair, color: "#c49231",
    desc: "Experience-aware scoring engine. Penalizes senior/lead/manager roles, boosts junior/entry/intern. Matches your core stack (Python, React, FastAPI, Docker, AWS).",
    tech: ["Keyword Matching", "Experience Filter", "Core Stack Bonus"] },
  { key: "applier", label: "Applier Agent", icon: Rocket, color: "#c96442",
    desc: "Uses Playwright browser automation to fill out and submit Greenhouse/Lever application forms. Uploads resume, answers questions, handles custom fields.",
    tech: ["Playwright", "Browser Automation", "Form Filling", "PDF Upload"] },
  { key: "tracker", label: "Tracker Agent", icon: FileSpreadsheet, color: "#7c6bae",
    desc: "Syncs all job data to Excel spreadsheet and JSON database. Tracks status changes, applied dates, match scores, and company details.",
    tech: ["openpyxl", "JSON DB", "Excel Export"] },
  { key: "notifier", label: "Notifier Agent", icon: Mail, color: "#8a7560",
    desc: "Sends email notifications when application batches complete. Includes summary stats and job-by-job breakdown in a styled HTML email.",
    tech: ["SMTP", "HTML Email", "Gmail"] },
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

  const handleScrape = async () => { setScraping(true); await startScrape(); };

  useEffect(() => {
    if (agents?.scraper?.status === "idle" && scraping) setScraping(false);
  }, [agents, scraping]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <Bot className="w-5 h-5" style={{ color: "#c96442" }} />
            Agents
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
            5 specialized agents working autonomously
          </p>
        </div>
        <button
          onClick={handleScrape}
          disabled={scraping}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition disabled:opacity-50"
          style={{ background: "#dff0e5", color: "#3d8b5e", border: "1px solid #c5e0cc" }}
        >
          {scraping ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {scraping ? "Scraping..." : "Run Scraper"}
        </button>
      </div>

      <div className="space-y-4">
        {AGENTS.map(({ key, label, icon: Icon, color, desc, tech }) => {
          const agent = agents?.[key];
          const isRunning = agent?.status === "running";
          return (
            <div key={key} className={`glass-card overflow-hidden ${isRunning ? "animate-pulse-glow" : ""}`}>
              <div className="p-5">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: color + "18" }}>
                    <Icon className="w-5 h-5" style={{ color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 mb-1">
                      <h3 className="text-[14px] font-semibold" style={{ color: "#1a1a1a" }}>{label}</h3>
                      <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                        style={isRunning ? { background: "#f0ddd4", color: "#c96442" } : { background: "#dff0e5", color: "#3d8b5e" }}>
                        {agent?.status || "idle"}
                      </span>
                    </div>
                    <p className="text-[12px] mb-3" style={{ color: "#6b6b6b" }}>{desc}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {tech.map((t) => (
                        <span key={t} className="text-[10px] px-2 py-0.5 rounded-md" style={{ background: "#f0ece6", color: "#8a7560" }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
              {agent?.logs && agent.logs.length > 0 && (
                <div className="px-5 py-3 max-h-32 overflow-y-auto" style={{ borderTop: "1px solid #e8e5e0", background: "#faf9f7" }}>
                  {agent.logs.slice(-8).map((log, i) => (
                    <div key={i} className="flex items-start gap-2 py-0.5">
                      <span className="text-[10px] font-mono flex-shrink-0" style={{ color: "#d4d0c8" }}>{log.ts}</span>
                      <span className="text-[10px] font-mono"
                        style={{ color: log.level === "error" ? "#c25a4a" : log.level === "warn" ? "#c49231" : "#9a9a9a" }}>
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
