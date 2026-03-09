"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Briefcase,
  Rocket,
  CheckCircle2,
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
    <aside className="hidden lg:flex flex-col w-60" style={{ background: "#f3f1ee", borderRight: "1px solid #e8e5e0" }}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-6 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base" style={{ background: "#c96442", color: "#fff" }}>
          A
        </div>
        <div>
          <h1 className="text-[13px] font-semibold" style={{ color: "#1a1a1a", letterSpacing: "-0.02em" }}>AgentApply</h1>
          <p className="text-[10px]" style={{ color: "#9a9a9a" }}>by Karthik</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150",
              )}
              style={active ? {
                background: "#ffffff",
                color: "#c96442",
                boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                border: "1px solid #e8e5e0",
              } : {
                color: "#6b6b6b",
                border: "1px solid transparent",
              }}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-5" style={{ borderTop: "1px solid #e8e5e0" }}>
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold" style={{ background: "#c96442", color: "#fff" }}>
            KR
          </div>
          <div>
            <p className="text-[11px] font-medium" style={{ color: "#1a1a1a" }}>Karthik Ramadugu</p>
            <p className="text-[10px]" style={{ color: "#9a9a9a" }}>M.S. CS · Dayton</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
