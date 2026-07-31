"use client";
import { useEffect, useState } from "react";
import { api, getToken, login } from "@/lib/api";

export default function Dashboard() {
  const [authed, setAuthed] = useState(false);
  const [projects, setProjects] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [agents, setAgents] = useState([]);
  const [credentials, setCredentials] = useState({ username: "admin", password: "admin" });
  const [error, setError] = useState(null);

  async function load() {
    try {
      const [p, ap, ag] = await Promise.all([
        api("/projects"),
        api("/approvals?status=REQUESTED"),
        api("/agents"),
      ]);
      setProjects(p); setApprovals(ap); setAgents(ag); setAuthed(true);
    } catch (e) {
      setAuthed(false);
    }
  }

  useEffect(() => { if (getToken()) load(); }, []);

  async function handleLogin(e) {
    e.preventDefault();
    setError(null);
    try {
      await login(credentials.username, credentials.password);
      await load();
    } catch (err) { setError(String(err.message)); }
  }

  if (!authed) {
    return (
      <form onSubmit={handleLogin} style={{ maxWidth: 320 }}>
        <h1>Entrar</h1>
        <p>Usuários seed: admin/admin, approver/approver, developer/developer.</p>
        <input
          style={{ display: "block", width: "100%", marginBottom: 8, padding: 8 }}
          value={credentials.username} placeholder="usuário"
          onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
        />
        <input
          style={{ display: "block", width: "100%", marginBottom: 8, padding: 8 }}
          type="password" value={credentials.password} placeholder="senha"
          onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
        />
        <button type="submit" style={{ padding: "8px 16px" }}>Entrar</button>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
      </form>
    );
  }

  return (
    <div>
      <h1>Dashboard</h1>
      <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
        <Card title="Projetos" value={projects.length} href="/projects" />
        <Card title="Aprovações pendentes" value={approvals.length} href="/approvals" />
        <Card title="Agentes lógicos" value={agents.length} />
      </div>
      <h2>Aprovações aguardando decisão</h2>
      {approvals.length === 0 ? <p>Nenhuma.</p> : (
        <ul>{approvals.map((a) => (
          <li key={a.id}>
            <a href="/approvals">{a.approval_type}</a> — {a.summary || a.workflow_run_id}
          </li>
        ))}</ul>
      )}
    </div>
  );
}

function Card({ title, value, href }) {
  const box = {
    border: "1px solid #ddd", borderRadius: 8, padding: "1rem 2rem", minWidth: 180,
  };
  const inner = (
    <div style={box}><div style={{ fontSize: 32, fontWeight: 700 }}>{value}</div>{title}</div>
  );
  return href ? <a href={href} style={{ textDecoration: "none", color: "inherit" }}>{inner}</a> : inner;
}
