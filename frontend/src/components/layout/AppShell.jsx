"use client";
import { useEffect, useState } from "react";
import { LoginScreen } from "@/components/layout/LoginScreen";
import { Sidebar } from "@/components/layout/Sidebar";
import { PageSpinner } from "@/components/ui/Spinner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

const APPROVALS_POLL_MS = 15000;

export function AppShell({ children }) {
  const { user, checked, login, logout } = useAuth();
  const [pendingApprovals, setPendingApprovals] = useState(0);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    async function poll() {
      try {
        const data = await api("/approvals?status=REQUESTED");
        if (!cancelled) setPendingApprovals(data.length);
      } catch {
        // silencioso: contagem de aprovações é informativa, não crítica
      }
    }
    poll();
    const interval = setInterval(poll, APPROVALS_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [user]);

  if (!checked) {
    return <PageSpinner label="Preparando sessão…" />;
  }

  if (!user) {
    return <LoginScreen onLogin={login} />;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar user={user} pendingApprovals={pendingApprovals} onLogout={logout} />
      <main className="ml-60 min-h-screen">
        <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
