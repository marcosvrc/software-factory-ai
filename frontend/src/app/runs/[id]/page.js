"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

export default function RunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [artifacts, setArtifacts] = useState([]);

  async function load() {
    setRun(await api(`/runs/${id}`));
    setTasks(await api(`/runs/${id}/tasks`));
    setTimeline(await api(`/runs/${id}/timeline`));
    setArtifacts(await api(`/runs/${id}/artifacts`));
  }
  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [id]);

  if (!run) return <p>Carregando…</p>;
  return (
    <div>
      <h1>Execução {run.id.slice(0, 8)} <small>[{run.status}]</small></h1>
      <p>Nó atual: <strong>{run.current_node || "—"}</strong></p>
      <h2>Tarefas</h2>
      <table border="1" cellPadding="6" style={{ borderCollapse: "collapse" }}>
        <thead><tr><th>Etapa</th><th>Agente</th><th>Status</th><th>Tentativa</th></tr></thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t.id}>
              <td>{t.type}</td><td>{t.assigned_agent_id}</td>
              <td>{t.status}</td><td>{t.attempt}/{t.max_attempts}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2>Artefatos</h2>
      <ul>{artifacts.map((a) => <li key={a.id}>{a.name} (v{a.version})</li>)}</ul>
      <h2>Timeline</h2>
      <ul>
        {timeline.map((e, i) => (
          <li key={i}>
            <code>{new Date(e.timestamp).toLocaleTimeString()}</code> — {e.event_type}
            {e.actor_id ? ` (${e.actor_id})` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
