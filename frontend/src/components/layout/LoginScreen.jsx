"use client";
import { Factory, Loader2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function LoginScreen({ onLogin }) {
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await onLogin(credentials.username, credentials.password);
    } catch (err) {
      setError(err.message || "Não foi possível entrar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white shadow-card">
            <Factory size={24} />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-900">Software Factory</h1>
            <p className="text-sm text-slate-500">Entre para acompanhar as suas fábricas de software</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="rounded-xl2 border border-slate-200 bg-white p-6 shadow-card">
          <div className="flex flex-col gap-4">
            <Input
              id="username"
              label="Usuário"
              autoFocus
              autoComplete="username"
              value={credentials.username}
              onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
            />
            <Input
              id="password"
              label="Senha"
              type="password"
              autoComplete="current-password"
              value={credentials.password}
              onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
            />
            {error && (
              <p className="rounded-md bg-danger-50 px-3 py-2 text-sm text-danger-700">{error}</p>
            )}
            <Button type="submit" variant="primary" size="lg" disabled={loading} className="w-full">
              {loading ? <Loader2 className="animate-spin" size={16} /> : "Entrar"}
            </Button>
          </div>
        </form>

        <p className="mt-4 text-center text-xs text-slate-400">
          Usuários seed: admin/admin · approver/approver · developer/developer
        </p>
      </div>
    </div>
  );
}
