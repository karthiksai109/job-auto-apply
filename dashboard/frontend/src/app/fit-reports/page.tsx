"use client";
import { useEffect, useState } from "react";
import { fetchFitReports, startFitAnalysis } from "../components/api";
import { Target, Play, Loader2, ChevronDown, ChevronUp, ExternalLink, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

interface FitReport {
  job_title: string;
  company: string;
  location: string;
  match_score: number;
  url: string;
  analyzed_at: string;
  matched_skills: string[];
  missing_skills: string[];
  skill_match_pct: number;
  why_qualified: string[];
  why_good_fit: string[];
  gaps: string[];
  confidence: string;
  summary: string;
}

export default function FitReportsPage() {
  const [reports, setReports] = useState<FitReport[]>([]);
  const [total, setTotal] = useState(0);
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = () => {
    fetchFitReports().then((d) => {
      setReports(d.reports || []);
      setTotal(d.total || 0);
    });
  };

  useEffect(() => {
    load();
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, []);

  const handleAnalyze = async () => {
    setRunning(true);
    await startFitAnalysis();
    setTimeout(() => { setRunning(false); load(); }, 3000);
  };

  const confidenceColor = (c: string) => {
    if (c.startsWith("Very High")) return "#3d8b5e";
    if (c.startsWith("High")) return "#5b8a72";
    if (c.startsWith("Moderate")) return "#c49231";
    return "#c25a4a";
  };

  const scoreColor = (s: number) => {
    if (s >= 90) return "#3d8b5e";
    if (s >= 75) return "#c49231";
    return "#c25a4a";
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <Target className="w-5 h-5" style={{ color: "#c96442" }} />
            Job Fit Reports
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
            {total} jobs analyzed — why each job matches your profile
          </p>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={running}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition disabled:opacity-50"
          style={{ background: "#f0ddd4", color: "#c96442", border: "1px solid #e5c4b4" }}
        >
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {running ? "Analyzing..." : "Analyze All"}
        </button>
      </div>

      {reports.length === 0 && (
        <div className="glass-card p-12 text-center">
          <Target className="w-10 h-10 mx-auto mb-3" style={{ color: "#d4d0c8" }} />
          <p className="text-[14px] font-medium" style={{ color: "#6b6b6b" }}>No fit reports yet</p>
          <p className="text-[12px] mt-1" style={{ color: "#9a9a9a" }}>Apply to jobs first, then click "Analyze All" to generate reports</p>
        </div>
      )}

      <div className="space-y-3">
        {reports.map((r) => {
          const isOpen = expanded === r.url;
          return (
            <div key={r.url} className="glass-card overflow-hidden">
              <button
                onClick={() => setExpanded(isOpen ? null : r.url)}
                className="w-full p-4 text-left flex items-center gap-4"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: scoreColor(r.match_score) + "18" }}>
                  <span className="text-[16px] font-bold" style={{ color: scoreColor(r.match_score) }}>
                    {r.match_score}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-[14px] font-semibold truncate" style={{ color: "#1a1a1a" }}>{r.job_title}</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold"
                      style={{ background: confidenceColor(r.confidence) + "18", color: confidenceColor(r.confidence) }}>
                      {r.confidence.split(" — ")[0]}
                    </span>
                  </div>
                  <p className="text-[12px] mt-0.5" style={{ color: "#6b6b6b" }}>{r.company} · {r.location}</p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <p className="text-[10px]" style={{ color: "#9a9a9a" }}>Skills</p>
                    <p className="text-[13px] font-semibold" style={{ color: scoreColor(r.skill_match_pct) }}>
                      {r.skill_match_pct}%
                    </p>
                  </div>
                  {isOpen ? <ChevronUp className="w-4 h-4" style={{ color: "#9a9a9a" }} /> : <ChevronDown className="w-4 h-4" style={{ color: "#9a9a9a" }} />}
                </div>
              </button>

              {isOpen && (
                <div className="px-5 pb-5 space-y-4" style={{ borderTop: "1px solid #e8e5e0" }}>
                  <div className="pt-4">
                    <p className="text-[12px] leading-relaxed" style={{ color: "#6b6b6b" }}>{r.summary}</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-[11px] font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: "#3d8b5e" }}>
                        <CheckCircle2 className="w-3.5 h-3.5" /> Why You're Qualified
                      </h4>
                      <ul className="space-y-1.5">
                        {r.why_qualified.map((q, i) => (
                          <li key={i} className="text-[11px] pl-3" style={{ color: "#4a4a4a", borderLeft: "2px solid #dff0e5" }}>{q}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="text-[11px] font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: "#5b8a72" }}>
                        <Target className="w-3.5 h-3.5" /> Why It's a Good Fit
                      </h4>
                      <ul className="space-y-1.5">
                        {r.why_good_fit.map((f, i) => (
                          <li key={i} className="text-[11px] pl-3" style={{ color: "#4a4a4a", borderLeft: "2px solid #dff0e5" }}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {r.gaps.length > 0 && (
                    <div>
                      <h4 className="text-[11px] font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: "#c49231" }}>
                        <AlertTriangle className="w-3.5 h-3.5" /> Gaps to Address
                      </h4>
                      <ul className="space-y-1">
                        {r.gaps.map((g, i) => (
                          <li key={i} className="text-[11px] pl-3" style={{ color: "#4a4a4a", borderLeft: "2px solid #faf0d8" }}>{g}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-1.5">
                    {r.matched_skills.map((s) => (
                      <span key={s} className="text-[10px] px-2 py-0.5 rounded-md" style={{ background: "#dff0e5", color: "#3d8b5e" }}>{s}</span>
                    ))}
                    {r.missing_skills.map((s) => (
                      <span key={s} className="text-[10px] px-2 py-0.5 rounded-md" style={{ background: "#f5ddd8", color: "#c25a4a" }}>{s}</span>
                    ))}
                  </div>

                  <a href={r.url} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-[11px] font-medium"
                    style={{ color: "#c96442" }}>
                    <ExternalLink className="w-3 h-3" /> View Job Posting
                  </a>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
