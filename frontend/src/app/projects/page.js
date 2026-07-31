"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [demands, setDemands] = useState({});
  const [form, setForm] = useState({ name: "", description: "" });
  const [demandForm, setDemandForm] = useState({});
  const [error, setError] = useState(null);

  async function load() {
    const p = await api("/projects");
    setProjects(p);
    const d = {};
    for (const project of p) d[project.id] = await api(`/projects/${project.id}/demands`);
    setDemands(d);
  }
  useEffect(() => { load().catch((e) => setError(String(e.message))); }, []);

  async function createProject(e) {
    e.preventDefault();
    await api("/projects", { method: "POST", body: JSON.stringify(form) });
    setForm({ name: "", description: "" });
    await load();
  }

  async function createDemand(projectId) {
    const title = demandForm[projectId];
    if (!title) return;
    await api(`/projects/${projectId}/demands`, {
      method: "POST", body: JSON.stringify({ title }),
    });
    setDemandForm({ ...demandForm, [projectId]: "" });
    await load();
  }

  async function startRun(demandId) {
    const run = await api(`/demands/${demandId}/runs`, { method: "POST" });
    window.location.href = `/runs/${run.id}`;
  }

  return (
    <div>
      <h1>Projetos</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <form onSubmit={createProject} style={{ marginBottom: "2rem" }}>
        <input
          placeholder="nome do projeto" value={form.name} style={{ padding: 8, marginRight: 8 }}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <input
          placeholder="descrição" value={form.description} style={{ padding: 8, marginRight: 8 }}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <button type="submit">Criar projeto</button>
      </form>
      {projects.map((p) => (
        <div key={p.id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 16 }}>
          <h3>{p.name} <small style={{ color: "#777" }}>[{p.status}]</small></h3>
          <p>{p.description}</p>
          <h4>Demandas</h4>
          <ul>
            {(demands[p.id] || []).map((d) => (
              <li key={d.id}>
                {d.title} [{d.status}]{" "}
                <button onClick={() => startRun(d.id)}>▶ iniciar workflow</button>
              </li>
            ))}
          </ul>
          <input
            placeholder="nova demanda" value={demandForm[p.id] || ""}
            style={{ padding: 6, marginRight: 8 }}
            onChange={(e) => setDemandForm({ ...demandForm, [p.id]: e.target.value })}
          />
          <button onClick={() => createDemand(p.id)}>Registrar demanda</button>
        </div>
      ))}
    </div>
  );
}
