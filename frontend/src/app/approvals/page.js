"use client";
import { CheckSquare, Check, X, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/domain/StatusBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { hasRole } from "@/lib/permissions";
import { APPROVAL_STATUS, APPROVAL_TYPE_LABELS } from "@/lib/statuses";
import { useAuth } from "@/lib/useAuth";

const REFRESH_MS = 5000;

function DecisionModal({ approval, action, onClose, onDecided }) {
  const [rationale, setRationale] = useState("");
  const [saving, setSaving] = useState(false);
  const { notify } = useToast();

  if (!approval || !action) return null;

  const isApprove = action === "approve";

  async function handleConfirm() {
    setSaving(true);
    try {
      await api(`/approvals/${approval.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ rationale }),
      });
      notify(isApprove ? "Aprovação registrada." : "Rejeição registrada.", { type: "success" });
      setRationale("");
      onDecided();
      onClose();
    } catch (err) {
      notify(`Não foi possível registrar a decisão: ${err.message}`, { type: "error" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={isApprove ? "Aprovar" : "Rejeitar"}
      description={APPROVAL_TYPE_LABELS[approval.approval_type] || approval.approval_type}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant={isApprove ? "success" : "danger"} onClick={handleConfirm} loading={saving}>
            {isApprove ? "Confirmar aprovação" : "Confirmar rejeição"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <p className="rounded-lg bg-slate-50 px-3.5 py-3 text-sm text-slate-600">{approval.summary}</p>
        <Textarea
          id="rationale"
          label="Justificativa"
          placeholder={
            approval.approval_type === "intake_clarification"
              ? "Responda aqui as lacunas apontadas (canal de acesso, escopo, volume esperado, regras de negócio, etc.)"
              : "Explique o motivo da decisão (opcional, mas recomendado para auditoria)"
          }
          rows={4}
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          autoFocus
        />
      </div>
    </Modal>
  );
}

function ApprovalCard({ approval, canDecide, onDecide }) {
  return (
    <Card>
      <CardBody className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-900">
              {APPROVAL_TYPE_LABELS[approval.approval_type] || approval.approval_type}
            </span>
            <StatusBadge status={approval.status} map={APPROVAL_STATUS} />
          </div>
          <Link
            href={`/runs/${approval.workflow_run_id}`}
            className="text-xs font-medium text-brand-600 hover:text-brand-700"
          >
            Ver execução {approval.workflow_run_id.slice(0, 8)}
          </Link>
        </div>

        {approval.summary && <p className="text-sm text-slate-600">{approval.summary}</p>}
        {approval.recommendation && (
          <p className="rounded-lg bg-brand-50/60 px-3 py-2 text-sm text-brand-800">
            <span className="font-medium">Recomendação: </span>
            {approval.recommendation}
          </p>
        )}

        {approval.risks && approval.risks.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {approval.risks.slice(0, 5).map((r, i) => (
              <Badge key={i} tone="danger">
                {r.description || r.category || "risco"}
              </Badge>
            ))}
          </div>
        )}

        {approval.status === "REQUESTED" ? (
          canDecide && (
            <div className="flex gap-2 pt-1">
              <Button variant="success" size="sm" icon={Check} onClick={() => onDecide(approval, "approve")}>
                Aprovar
              </Button>
              <Button variant="danger" size="sm" icon={X} onClick={() => onDecide(approval, "reject")}>
                Rejeitar
              </Button>
            </div>
          )
        ) : (
          approval.decided_by && (
            <p className="flex items-center gap-1.5 text-xs text-slate-400">
              <Clock size={12} />
              Decidido por {approval.decided_by}
              {approval.rationale && `: “${approval.rationale}”`}
            </p>
          )
        )}
      </CardBody>
    </Card>
  );
}

export default function Approvals() {
  const [approvals, setApprovals] = useState(null);
  const [decision, setDecision] = useState(null);
  const { notify } = useToast();
  const { user } = useAuth();

  async function load() {
    try {
      setApprovals(await api("/approvals"));
    } catch (e) {
      notify(`Falha ao carregar aprovações: ${e.message}`, { type: "error" });
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(() => load().catch(() => {}), REFRESH_MS);
    return () => clearInterval(interval);
  }, []);

  const loading = approvals === null;
  const canDecide = hasRole(user, "APPROVER");
  const pending = loading ? [] : approvals.filter((a) => a.status === "REQUESTED");
  const decided = loading ? [] : approvals.filter((a) => a.status !== "REQUESTED");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Aprovações humanas</h1>
        <p className="mt-1 text-sm text-slate-500">
          Decisões que precisam de um humano: escopo, releases, esclarecimentos e revisões após limite de ciclos.
        </p>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : (
        <>
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Aguardando decisão ({pending.length})
            </h2>
            {pending.length === 0 ? (
              <EmptyState icon={CheckSquare} title="Nenhuma aprovação pendente" />
            ) : (
              <div className="flex flex-col gap-3">
                {pending.map((a) => (
                  <ApprovalCard
                    key={a.id}
                    approval={a}
                    canDecide={canDecide}
                    onDecide={(approval, action) => setDecision({ approval, action })}
                  />
                ))}
              </div>
            )}
          </div>

          {decided.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
                Histórico recente
              </h2>
              <div className="flex flex-col gap-3">
                {decided.slice(0, 10).map((a) => (
                  <ApprovalCard key={a.id} approval={a} canDecide={false} onDecide={() => {}} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <DecisionModal
        approval={decision?.approval}
        action={decision?.action}
        onClose={() => setDecision(null)}
        onDecided={load}
      />
    </div>
  );
}
