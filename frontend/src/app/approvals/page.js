"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Approvals() {
  const [approvals, setApprovals] = useState([]);
  const [error, setError] = useState(null);

  async function load() { setApprovals(await api("/approvals")); }
  useEffect(() => {
    load().catch((e) => setError(String(e.message)));
    const interval = setInterval(() => load().catch(() => {}), 5000);
    return () => clearInterval(interval);
  }, []);

  async function decide(id, action) {
    const rationale = window.prompt("Justificativa:") || "";
    try {
      await api(`/approvals/${id}/${action}`, {
        method: "POST", body: JSON.stringify({ rationale }),
      });
      await load();
    } catch (e) { setError(String(e.message)); }
  }

  return (
    <div>
      <h1>Aprovações humanas</h1>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {approvals.map((a) => (
        <div key={a.id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 12 }}>
          <strong>{a.approval_type}</strong> — {a.status}
          <p>{a.summary}</p>
          {a.recommendation && <p><em>Recomendação: {a.recommendation}</em></p>}
          {a.status === "REQUESTED" && (
            <div>
              <button onClick={() => decide(a.id, "approve")} style={{ marginRight: 8 }}>
                ✅ Aprovar
              </button>
              <button onClick={() => decide(a.id, "reject")}>❌ Rejeitar</button>
            </div>
          )}
          {a.decided_by && <small>Decidido por {a.decided_by}: {a.rationale}</small>}
        </div>
      ))}
    </div>
  );
}
