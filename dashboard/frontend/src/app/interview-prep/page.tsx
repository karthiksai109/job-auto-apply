"use client";
import { useEffect, useState } from "react";
import { fetchInterviewPrep, startGeneratePrep } from "../components/api";
import { GraduationCap, Play, Loader2, ChevronDown, ChevronUp, ExternalLink, Code, Users, Layers, BookOpen, MessageSquare } from "lucide-react";

interface TechQ { question: string; topic: string; }
interface SkillReview { skill: string; priority: string; tip: string; }
interface Guide {
  job_title: string;
  company: string;
  url: string;
  match_score: number;
  generated_at: string;
  technical_questions: TechQ[];
  behavioral_questions: string[];
  system_design: string[];
  skills_to_review: SkillReview[];
  company_research: string[];
  talking_points: string[];
  expected_process: string;
}

export default function InterviewPrepPage() {
  const [guides, setGuides] = useState<Guide[]>([]);
  const [total, setTotal] = useState(0);
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [tab, setTab] = useState<Record<string, string>>({});

  const load = () => {
    fetchInterviewPrep().then((d) => {
      setGuides(d.guides || []);
      setTotal(d.total || 0);
    });
  };

  useEffect(() => { load(); const iv = setInterval(load, 5000); return () => clearInterval(iv); }, []);

  const handleGenerate = async () => {
    setRunning(true);
    await startGeneratePrep();
    setTimeout(() => { setRunning(false); load(); }, 3000);
  };

  const getTab = (url: string) => tab[url] || "technical";
  const setTabFor = (url: string, t: string) => setTab((p) => ({ ...p, [url]: t }));

  const priorityColor = (p: string) => {
    if (p === "High") return { bg: "#f5ddd8", fg: "#c25a4a" };
    if (p === "Medium") return { bg: "#faf0d8", fg: "#c49231" };
    return { bg: "#dff0e5", fg: "#3d8b5e" };
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <GraduationCap className="w-5 h-5" style={{ color: "#c96442" }} />
            Interview Prep
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
            {total} prep guides generated — ace every interview
          </p>
        </div>
        <button onClick={handleGenerate} disabled={running}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition disabled:opacity-50"
          style={{ background: "#e8e5f5", color: "#7c6bae", border: "1px solid #d5d0ea" }}>
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {running ? "Generating..." : "Generate All"}
        </button>
      </div>

      {guides.length === 0 && (
        <div className="glass-card p-12 text-center">
          <GraduationCap className="w-10 h-10 mx-auto mb-3" style={{ color: "#d4d0c8" }} />
          <p className="text-[14px] font-medium" style={{ color: "#6b6b6b" }}>No prep guides yet</p>
          <p className="text-[12px] mt-1" style={{ color: "#9a9a9a" }}>Apply to jobs, then click "Generate All"</p>
        </div>
      )}

      <div className="space-y-3">
        {guides.map((g) => {
          const isOpen = expanded === g.url;
          const activeTab = getTab(g.url);
          return (
            <div key={g.url} className="glass-card overflow-hidden">
              <button onClick={() => setExpanded(isOpen ? null : g.url)}
                className="w-full p-4 text-left flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "#e8e5f518" }}>
                  <GraduationCap className="w-5 h-5" style={{ color: "#7c6bae" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-[14px] font-semibold truncate" style={{ color: "#1a1a1a" }}>{g.job_title}</h3>
                  <p className="text-[12px] mt-0.5" style={{ color: "#6b6b6b" }}>{g.company} · Match: {g.match_score}%</p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <p className="text-[10px]" style={{ color: "#9a9a9a" }}>Questions</p>
                    <p className="text-[13px] font-semibold" style={{ color: "#7c6bae" }}>
                      {g.technical_questions.length + g.behavioral_questions.length + g.system_design.length}
                    </p>
                  </div>
                  {isOpen ? <ChevronUp className="w-4 h-4" style={{ color: "#9a9a9a" }} /> : <ChevronDown className="w-4 h-4" style={{ color: "#9a9a9a" }} />}
                </div>
              </button>

              {isOpen && (
                <div style={{ borderTop: "1px solid #e8e5e0" }}>
                  {/* Tabs */}
                  <div className="flex gap-0 px-4 pt-3" style={{ borderBottom: "1px solid #e8e5e0" }}>
                    {[
                      { key: "technical", label: "Technical", icon: Code },
                      { key: "behavioral", label: "Behavioral", icon: Users },
                      { key: "system", label: "System Design", icon: Layers },
                      { key: "skills", label: "Skills Review", icon: BookOpen },
                      { key: "tips", label: "Talking Points", icon: MessageSquare },
                    ].map(({ key, label, icon: Icon }) => (
                      <button key={key} onClick={() => setTabFor(g.url, key)}
                        className="flex items-center gap-1.5 px-3 py-2 text-[11px] font-medium transition-all"
                        style={activeTab === key
                          ? { color: "#c96442", borderBottom: "2px solid #c96442", marginBottom: "-1px" }
                          : { color: "#9a9a9a", borderBottom: "2px solid transparent", marginBottom: "-1px" }}>
                        <Icon className="w-3 h-3" /> {label}
                      </button>
                    ))}
                  </div>

                  <div className="p-5 space-y-3">
                    {activeTab === "technical" && (
                      <div className="space-y-2.5">
                        {g.technical_questions.map((q, i) => (
                          <div key={i} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "#faf9f7" }}>
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                              style={{ background: "#e8e5f5", color: "#7c6bae" }}>{q.topic}</span>
                            <p className="text-[12px]" style={{ color: "#4a4a4a" }}>{q.question}</p>
                          </div>
                        ))}
                        {g.technical_questions.length === 0 && (
                          <p className="text-[12px]" style={{ color: "#9a9a9a" }}>No technical questions generated</p>
                        )}
                      </div>
                    )}

                    {activeTab === "behavioral" && (
                      <div className="space-y-2">
                        {g.behavioral_questions.map((q, i) => (
                          <div key={i} className="p-3 rounded-lg" style={{ background: "#faf9f7" }}>
                            <p className="text-[12px]" style={{ color: "#4a4a4a" }}>{q}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {activeTab === "system" && (
                      <div className="space-y-2">
                        {g.system_design.map((q, i) => (
                          <div key={i} className="p-3 rounded-lg" style={{ background: "#faf9f7" }}>
                            <p className="text-[12px] font-medium" style={{ color: "#4a4a4a" }}>{q}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {activeTab === "skills" && (
                      <div className="space-y-2">
                        {g.skills_to_review.map((s, i) => {
                          const pc = priorityColor(s.priority);
                          return (
                            <div key={i} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "#faf9f7" }}>
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                                style={{ background: pc.bg, color: pc.fg }}>{s.priority}</span>
                              <div>
                                <p className="text-[12px] font-semibold" style={{ color: "#1a1a1a" }}>{s.skill}</p>
                                <p className="text-[11px] mt-0.5" style={{ color: "#6b6b6b" }}>{s.tip}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {activeTab === "tips" && (
                      <div className="space-y-4">
                        <div>
                          <h4 className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "#c96442" }}>Your Talking Points</h4>
                          <div className="space-y-1.5">
                            {g.talking_points.map((t, i) => (
                              <p key={i} className="text-[11px] pl-3" style={{ color: "#4a4a4a", borderLeft: "2px solid #f0ddd4" }}>{t}</p>
                            ))}
                          </div>
                        </div>
                        <div>
                          <h4 className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "#5b8a72" }}>Company Research</h4>
                          <div className="space-y-1.5">
                            {g.company_research.map((c, i) => (
                              <p key={i} className="text-[11px] pl-3" style={{ color: "#4a4a4a", borderLeft: "2px solid #dff0e5" }}>{c}</p>
                            ))}
                          </div>
                        </div>
                        <div className="p-3 rounded-lg" style={{ background: "#faf0d8" }}>
                          <p className="text-[11px] font-medium" style={{ color: "#c49231" }}>{g.expected_process}</p>
                        </div>
                      </div>
                    )}

                    <a href={g.url} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-[11px] font-medium mt-2"
                      style={{ color: "#c96442" }}>
                      <ExternalLink className="w-3 h-3" /> View Job Posting
                    </a>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
