"use client";
import clsx from "clsx";
import { Activity, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PipelineTrack } from "@/components/domain/PipelineTrack";
import { StatusBadge } from "@/components/domain/StatusBadge";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { ACTIVE_RUN_STATUSES, RUN_STATUS, STAGE_LABELS } from "@/lib/statuses";

const REFRESH_MS = 5000;

const FILTERS = [
  ["active", "Em andamento"],
  ["attention", "Precisa de atenção"],
  ["done", "Finalizadas"],
  ["all", "Todas"],
];

function SummaryPill({ label, value, toneClass }) {
  return (
    <div className="min-w-[140px] rounded-xl2 border border-slate-200 bg-white px-4 py-3 shadow-card">
      <div className={clsx("text-2xl font-semibold", toneClass || "text-slate-900")}>{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function RunCard({ run }) {
  return (
    <Link href={`/runs/${run.id}`}>
      <Card className="transition-shadow hover:shadow-popover">
        <CardBody>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <span className="font-medium text-slate-900">{run.demand_title || run.demand_id}</span>
              <span className="ml-2 text-sm text-slate-500">{run.project_name}</span>
            </div>
            <StatusBadge status={run.status} map={RUN_STATUS} />
          </div>
          <div className="mt-1 text-xs text-slate-400">
            execução {run.id.slice(0, 8)} · criada em {new Date(run.created_at).toLocaleString("pt-BR")}
            {run.current_node && (
              <>
                {" "}
                · etapa atual:{" "}
                <span className="font-medium text-slate-600">
                  {STAGE_LABELS[run.current_node] || run.current_node}
                </span>
              </>
            )}
          </div>
          <div className="mt-3">
            <PipelineTrack currentNode={run.current_node} status={run.status} />
          </div>
        </CardBody>
      </Card>
    </Link>
  );
}

export default function Monitor() {
  const [runs, setRuns] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [filter, setFilter] = useState("active");
  const { notify } = useToast();

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api("/runs?limit=100");
        if (cancelled) return;
        setRuns(data);
        setLastUpdated(new Date());
      } catch (e) {
        if (!cancelled) notify(`Falha ao atualizar execuções: ${e.message}`, { type: "error" });
      }
    }
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [notify]);

  const loading = runs === null;
  const visibleRuns = loading
    ? []
    : runs.filter((r) => {
        if (filter === "active") return ACTIVE_RUN_STATUSES.includes(r.status);
        if (filter === "attention") return r.status === "WAITING_HUMAN" || r.status.startsWith("FAILED");
        if (filter === "done") return r.status === "COMPLETED" || r.status === "CANCELLED";
        return true;
      });

  const counts = loading
    ? {}
    : runs.reduce((acc, r) => {
        acc[r.status] = (acc[r.status] || 0) + 1;
        return acc;
      }, {});

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Monitor de execuções</h1>
          <p className="mt-1 text-sm text-slate-500">Acompanhe o progresso de cada demanda em tempo real.</p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <RefreshCw size={13} />
          {lastUpdated ? `atualizado às ${lastUpdated.toLocaleTimeString("pt-BR")}` : "carregando…"}
          {" · a cada 5s"}
        </div>
      </div>

      {!loading && (
        <div className="flex flex-wrap gap-3">
          <SummaryPill
            label="Em andamento"
            value={ACTIVE_RUN_STATUSES.reduce((s, k) => s + (counts[k] || 0), 0)}
          />
          <SummaryPill label="Aguardando você" value={counts.WAITING_HUMAN || 0} toneClass="text-warning-600" />
          <SummaryPill
            label="Falharam"
            value={(counts.FAILED_RETRYABLE || 0) + (counts.FAILED_FINAL || 0)}
            toneClass="text-danger-600"
          />
          <SummaryPill label="Concluídas" value={counts.COMPLETED || 0} toneClass="text-success-600" />
        </div>
      )}

      <div className="flex gap-1.5 border-b border-slate-200 pb-px">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={clsx(
              "rounded-t-md px-3.5 py-2 text-sm font-medium transition-colors",
              filter === key
                ? "border-b-2 border-brand-600 text-brand-700"
                : "text-slate-500 hover:text-slate-700"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : visibleRuns.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="Nenhuma execução nesta categoria"
          description="Troque o filtro acima ou inicie uma nova execução a partir de um projeto."
        />
      ) : (
        <div className="flex flex-col gap-3">
          {visibleRuns.map((run) => (
            <RunCard key={run.id} run={run} />
          ))}
        </div>
      )}
    </div>
  );
}
