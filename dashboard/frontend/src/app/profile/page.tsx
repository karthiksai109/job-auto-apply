"use client";
import { useEffect, useState } from "react";
import { fetchProfile, startProfileAnalysis } from "../components/api";
import { UserCheck, Play, Loader2, Linkedin, Github, Globe, Sparkles, TrendingUp, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

interface Tip { area: string; tip: string; priority: string; }
interface ProfileData {
  name: string;
  current_title: string;
  analyzed_at: string;
  profile_strength: number;
  strength_breakdown: string[];
  suggested_headlines: string[];
  suggested_summary: string;
  linkedin_tips: Tip[];
  github_tips: string[];
  portfolio_tips: string[];
  ats_keywords: string[];
  recruiter_attraction_score: number;
  action_items: string[];
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [running, setRunning] = useState(false);

  const load = () => {
    fetchProfile().then((d) => { if (d && d.name) setProfile(d as ProfileData); });
  };

  useEffect(() => { load(); }, []);

  const handleAnalyze = async () => {
    setRunning(true);
    await startProfileAnalysis();
    setTimeout(() => { setRunning(false); load(); }, 3000);
  };

  const strengthColor = (s: number) => {
    if (s >= 80) return "#3d8b5e";
    if (s >= 60) return "#c49231";
    return "#c25a4a";
  };

  if (!profile) return (
    <div className="max-w-5xl mx-auto">
      <div className="glass-card p-12 text-center">
        <UserCheck className="w-10 h-10 mx-auto mb-3" style={{ color: "#d4d0c8" }} />
        <p className="text-[14px] font-medium" style={{ color: "#6b6b6b" }}>Loading profile analysis...</p>
        <button onClick={handleAnalyze} className="mt-4 px-4 py-2 rounded-lg text-[13px] font-medium"
          style={{ background: "#f0ddd4", color: "#c96442" }}>
          Analyze Profile
        </button>
      </div>
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <UserCheck className="w-5 h-5" style={{ color: "#c96442" }} />
            Profile Marketing
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "#9a9a9a" }}>
            Optimize your profile to attract recruiters
          </p>
        </div>
        <button onClick={handleAnalyze} disabled={running}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition disabled:opacity-50"
          style={{ background: "#dff0e5", color: "#3d8b5e", border: "1px solid #c5e0cc" }}>
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {running ? "Analyzing..." : "Re-analyze"}
        </button>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" style={{ color: "#c96442" }} />
              <span className="text-[13px] font-semibold" style={{ color: "#1a1a1a" }}>Profile Strength</span>
            </div>
            <span className="text-3xl font-bold" style={{ color: strengthColor(profile.profile_strength) }}>
              {profile.profile_strength}%
            </span>
          </div>
          <div className="w-full h-3 rounded-full overflow-hidden mb-4" style={{ background: "#f0ece6" }}>
            <div className="h-full rounded-full transition-all duration-700"
              style={{ width: `${profile.profile_strength}%`, background: strengthColor(profile.profile_strength) }} />
          </div>
          <div className="space-y-1.5">
            {profile.strength_breakdown.map((s, i) => (
              <p key={i} className="text-[11px]" style={{ color: s.includes("Missing") || s.includes("Weak") ? "#c25a4a" : "#4a4a4a" }}>{s}</p>
            ))}
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" style={{ color: "#7c6bae" }} />
              <span className="text-[13px] font-semibold" style={{ color: "#1a1a1a" }}>Recruiter Attraction</span>
            </div>
            <span className="text-3xl font-bold" style={{ color: strengthColor(profile.recruiter_attraction_score) }}>
              {profile.recruiter_attraction_score}%
            </span>
          </div>
          <div className="w-full h-3 rounded-full overflow-hidden mb-4" style={{ background: "#f0ece6" }}>
            <div className="h-full rounded-full transition-all duration-700"
              style={{ width: `${profile.recruiter_attraction_score}%`, background: "#7c6bae" }} />
          </div>
          <div>
            <h4 className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "#c96442" }}>Action Items</h4>
            <div className="space-y-1.5">
              {profile.action_items.map((a, i) => (
                <p key={i} className="text-[11px]" style={{ color: "#4a4a4a" }}>{a}</p>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Suggested Summary */}
      <div className="glass-card p-6">
        <h3 className="text-[13px] font-semibold mb-3 flex items-center gap-2" style={{ color: "#1a1a1a" }}>
          <Sparkles className="w-4 h-4" style={{ color: "#c96442" }} />
          Optimized Summary
        </h3>
        <div className="p-4 rounded-lg text-[12px] leading-relaxed" style={{ background: "#faf9f7", color: "#4a4a4a", border: "1px solid #e8e5e0" }}>
          {profile.suggested_summary}
        </div>
      </div>

      {/* Suggested Headlines */}
      <div className="glass-card p-6">
        <h3 className="text-[13px] font-semibold mb-3" style={{ color: "#1a1a1a" }}>Suggested Headlines</h3>
        <div className="space-y-2">
          {profile.suggested_headlines.map((h, i) => (
            <div key={i} className="p-3 rounded-lg text-[12px] font-medium" style={{ background: "#f0ece6", color: "#4a4a4a" }}>
              {h}
            </div>
          ))}
        </div>
      </div>

      {/* LinkedIn Tips */}
      <div className="glass-card p-6">
        <h3 className="text-[13px] font-semibold mb-3 flex items-center gap-2" style={{ color: "#1a1a1a" }}>
          <Linkedin className="w-4 h-4" style={{ color: "#0a66c2" }} /> LinkedIn Optimization
        </h3>
        <div className="space-y-2.5">
          {profile.linkedin_tips.map((t, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "#faf9f7" }}>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                style={t.priority === "High" ? { background: "#f5ddd8", color: "#c25a4a" } : { background: "#faf0d8", color: "#c49231" }}>
                {t.priority}
              </span>
              <div>
                <p className="text-[11px] font-semibold" style={{ color: "#1a1a1a" }}>{t.area}</p>
                <p className="text-[11px] mt-0.5" style={{ color: "#6b6b6b" }}>{t.tip}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* GitHub + Portfolio Tips */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-6">
          <h3 className="text-[13px] font-semibold mb-3 flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <Github className="w-4 h-4" /> GitHub Optimization
          </h3>
          <div className="space-y-1.5">
            {profile.github_tips.map((t, i) => (
              <p key={i} className="text-[11px] pl-3" style={{ color: "#4a4a4a", borderLeft: "2px solid #e8e5e0" }}>{t}</p>
            ))}
          </div>
        </div>
        <div className="glass-card p-6">
          <h3 className="text-[13px] font-semibold mb-3 flex items-center gap-2" style={{ color: "#1a1a1a" }}>
            <Globe className="w-4 h-4" style={{ color: "#c96442" }} /> Portfolio Optimization
          </h3>
          <div className="space-y-1.5">
            {profile.portfolio_tips.map((t, i) => (
              <p key={i} className="text-[11px] pl-3" style={{ color: "#4a4a4a", borderLeft: "2px solid #f0ddd4" }}>{t}</p>
            ))}
          </div>
        </div>
      </div>

      {/* ATS Keywords */}
      <div className="glass-card p-6">
        <h3 className="text-[13px] font-semibold mb-3" style={{ color: "#1a1a1a" }}>ATS-Friendly Keywords</h3>
        <div className="flex flex-wrap gap-1.5">
          {profile.ats_keywords.map((k) => (
            <span key={k} className="text-[10px] px-2 py-1 rounded-md" style={{ background: "#f0ece6", color: "#8a7560" }}>{k}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
