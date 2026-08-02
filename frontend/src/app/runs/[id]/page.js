"use client";
import clsx from "clsx";
import { Download, FileText, ListChecks, History, RotateCcw, Workflow, XCircle } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ProcessDiagram } from "@/components/domain/ProcessDiagram/ProcessDiagram";
import { PipelineTrack } from "@/components/domain/PipelineTrack";
import { StatusBadge } from "@/components/domain/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageSpinner } from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import { api, downloadArtifact } from "@/lib/api";
import { hasRole } from "@/lib/permissions";
import { computeProcessState, extractEscalatedGate } from "@/lib/processState";
import { RUN_STATUS, STAGE_LABELS, TASK_STATUS } from "@/lib/statuses";
import { useAuth } from "@/lib/useAuth";

const REFRESH_MS = 5000;
const TABS = [
  ["diagram", "Diagrama do processo", Workflow],
  ["tasks", "Tarefas", ListChecks],
  ["artifacts", "Artefatos", FileText],
  ["timeline", "Timeline", History],
];

function TaskRow({ task }) {
  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="whitespace-nowrap px-4 py-2.5 text-sm text-slate-700">{STAGE_LABELS[task.type] || task.type}</td>
      <td className="px-4 py-2.5 text-sm text-slate-500">{task.assigned_agent_id || "—"}</td>
      <td className="px-4 py-2.5">
        <StatusBadge status={task.status} map={TASK_STATUS} />
      </td>
      <td className="px-4 py-2.5 text-sm text-slate-500">
        {task.attempt}/{task.max_attempts}
      </td>
    </tr>
  );
}

export default function RunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [tab, setTab] = useState("diagram");
  const [actionLoading, setActionLoading] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const { notify } = useToast();
  const { user } = useAuth();

  async function load() {
    try {
      const [r, t, tl, ar, ap] = await Promise.all([
        api(`/runs/${id}`),
        api(`/runs/${id}/tasks`),
        api(`/runs/${id}/timeline`),
        api(`/runs/${id}/artifacts`).catch(() => []),
        api("/approvals").catch(() => []),
      ]);
      setRun(r);
      setTasks(t);
      setTimeline(tl);
      setArtifacts(ar);
      setApprovals(ap);
    } catch (e) {
      notify(`Falha ao carregar execução: ${e.message}`, { type: "error" });
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => clearInterval(interval);
  }, [id]);

  async function cancelRun() {
    if (!window.confirm("Cancelar esta execução? Essa ação não pode ser desfeita.")) return;
    setActionLoading(true);
    try {
      await api(`/runs/${id}/cancel`, { method: "POST" });
      notify("Execução cancelada.", { type: "success" });
      await load();
    } catch (e) {
      notify(`Não foi possível cancelar: ${e.message}`, { type: "error" });
    } finally {
      setActionLoading(false);
    }
  }

  async function retryRun() {
    setActionLoading(true);
    try {
      await api(`/runs/${id}/retry`, { method: "POST" });
      notify("Execução colocada para reprocessar.", { type: "success" });
      await load();
    } catch (e) {
      notify(`Não foi possível reprocessar: ${e.message}`, { type: "error" });
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDownload(artifact) {
    setDownloadingId(artifact.id);
    try {
      await downloadArtifact(artifact.id, artifact.name);
    } catch (e) {
      notify(`Não foi possível baixar o artefato: ${e.message}`, { type: "error" });
    } finally {
      setDownloadingId(null);
    }
  }

  if (!run) return <PageSpinner label="Carregando execução…" />;

  const runApprovals = approvals.filter((a) => a.workflow_run_id === run.id);
  const pendingHumanReview = runApprovals.find(
    (a) => a.approval_type === "human_review" && a.status === "REQUESTED"
  );
  const { nodeState, currentNodeId } = computeProcessState({ run, timeline, approvals });
  const escalatedGate = pendingHumanReview ? extractEscalatedGate(pendingHumanReview) : null;

  const canManage = hasRole(user, "DEVELOPER");
  const canCancel = canManage && !["COMPLETED", "CANCELLED"].includes(run.status);
  const canRetry = hasRole(user, "DEVELOPER") && run.status === "FAILED_RETRYABLE";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-semibold text-slate-900">
              Execução {run.id.slice(0, 8)}
            </h1>
            <StatusBadge status={run.status} map={RUN_STATUS} />
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {run.demand_title} · {run.project_name}
          </p>
        </div>
        <div className="flex gap-2">
          {canRetry && (
            <Button variant="secondary" icon={RotateCcw} loading={actionLoading} onClick={retryRun}>
              Reprocessar
            </Button>
          )}
          {canCancel && (
            <Button variant="danger" icon={XCircle} loading={actionLoading} onClick={cancelRun}>
              Cancelar
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardBody>
          <p className="mb-3 text-sm text-slate-500">
            Etapa atual: <span className="font-medium text-slate-700">{STAGE_LABELS[run.current_node] || run.current_node || "—"}</span>
          </p>
          <PipelineTrack currentNode={run.current_node} status={run.status} compact />
        </CardBody>
      </Card>

      <div className="flex gap-1.5 border-b border-slate-200 pb-px">
        {TABS.map(([key, label, Icon]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={clsx(
              "flex items-center gap-1.5 rounded-t-md px-3.5 py-2 text-sm font-medium transition-colors",
              tab === key ? "border-b-2 border-brand-600 text-brand-700" : "text-slate-500 hover:text-slate-700"
            )}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {tab === "diagram" && (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-slate-500">
            Diagrama completo do processo de entrega, com o ponto atual da execução destacado
            {escalatedGate && (
              <>
                {" "}
                (escalado a partir do gate <strong>{escalatedGate}</strong>)
              </>
            )}
            .
          </p>
          <ProcessDiagram nodeState={nodeState} currentNodeId={currentNodeId} escalatedGate={escalatedGate} />
        </div>
      )}

      {tab === "tasks" && (
        tasks.length === 0 ? (
          <EmptyState icon={ListChecks} title="Nenhuma tarefa registrada ainda" />
        ) : (
          <Card className="overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2.5">Etapa</th>
                  <th className="px-4 py-2.5">Agente</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Tentativa</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <TaskRow key={t.id} task={t} />
                ))}
              </tbody>
            </table>
          </Card>
        )
      )}

      {tab === "artifacts" && (
        artifacts.length === 0 ? (
          <EmptyState icon={FileText} title="Nenhum artefato gerado ainda" />
        ) : (
          <div className="flex flex-col gap-2">
            {artifacts.map((a) => (
              <Card key={a.id}>
                <CardBody className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-2.5">
                    <FileText size={16} className="text-slate-400" />
                    <span className="text-sm font-medium text-slate-800">{a.name}</span>
                    <span className="text-xs text-slate-400">v{a.version}</span>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={Download}
                    loading={downloadingId === a.id}
                    onClick={() => handleDownload(a)}
                  >
                    Baixar
                  </Button>
                </CardBody>
              </Card>
            ))}
          </div>
        )
      )}

      {tab === "timeline" && (
        timeline.length === 0 ? (
          <EmptyState icon={History} title="Nenhum evento registrado ainda" />
        ) : (
          <Card>
            <CardBody>
              <ol className="flex flex-col gap-3">
                {timeline.map((e, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span className="w-20 shrink-0 font-mono text-xs text-slate-400">
                      {new Date(e.timestamp).toLocaleTimeString("pt-BR")}
                    </span>
                    <span className="text-slate-700">
                      {e.event_type}
                      {e.actor_id && <span className="text-slate-400"> · {e.actor_id}</span>}
                    </span>
                  </li>
                ))}
              </ol>
            </CardBody>
          </Card>
        )
      )}
    </div>
  );
}
