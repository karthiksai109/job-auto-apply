"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Briefcase,
  Rocket,
  CheckCircle2,
  Zap,
} from "lucide-react";
import clsx from "clsx";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/apply", label: "Apply", icon: Rocket },
  { href: "/applied", label: "Applied", icon: CheckCircle2 },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex flex-col w-64 bg-[#0a0f1a] border-r border-[#1e293b] p-4">
      {/* Logo */}
      <div className="flex items-center gap-3 px-3 py-4 mb-6">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-white tracking-tight">AgentApply AI</h1>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest">Multi-Agent System</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                active
                  ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="mt-auto px-3 py-4 border-t border-[#1e293b]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center text-xs font-bold text-white">
            KR
          </div>
          <div>
            <p className="text-xs font-medium text-slate-300">Karthik Ramadugu</p>
            <p className="text-[10px] text-slate-500">Full Stack Developer</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
