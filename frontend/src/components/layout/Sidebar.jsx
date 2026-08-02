"use client";
import clsx from "clsx";
import {
  Activity,
  Bot,
  CheckSquare,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Factory,
  Plug,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ROLE_LABELS } from "@/lib/permissions";

const NAV_ITEMS = [
  { href: "/", label: "Painel", icon: LayoutDashboard },
  { href: "/monitor", label: "Monitor", icon: Activity },
  { href: "/projects", label: "Projetos", icon: FolderKanban },
  { href: "/approvals", label: "Aprovações", icon: CheckSquare },
  { href: "/agents", label: "Agentes", icon: Bot },
  { href: "/mcp", label: "MCP", icon: Plug },
];

export function Sidebar({ user, pendingApprovals = 0, onLogout }) {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
          <Factory size={18} />
        </div>
        <span className="text-sm font-semibold text-slate-900">Software Factory</span>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
              )}
            >
              <span className="flex items-center gap-2.5">
                <Icon size={17} />
                {label}
              </span>
              {href === "/approvals" && pendingApprovals > 0 && (
                <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-warning-500 px-1 text-[11px] font-semibold text-white">
                  {pendingApprovals}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {user && (
        <div className="border-t border-slate-100 px-3 py-3">
          <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-600">
              {user.username?.slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-800">{user.username}</p>
              <p className="truncate text-xs text-slate-500">{ROLE_LABELS[user.role] || user.role}</p>
            </div>
            <button
              onClick={onLogout}
              title="Sair"
              aria-label="Sair"
              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
