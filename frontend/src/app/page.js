"use client";
import {
  Activity,
  ArrowRight,
  CheckSquare,
  FolderKanban,
  Bot,
  AlertTriangle,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/domain/StatusBadge";
import { api } from "@/lib/api";
import { APPROVAL_STATUS, APPROVAL_TYPE_LABELS } from "@/lib/statuses";
import { useToast } from "@/components/ui/Toast";

function StatCard({ icon: Icon, label, value, href, tone = "brand" }) {
  const toneClasses = {
    brand: "bg-brand-50 text-brand-600",
    warning: "bg-warning-50 text-warning-600",
    success: "bg-success-50 text-success-600",
  };
  const content = (
    <Card className="transition-shadow hover:shadow-popover">
      <CardBody className="flex items-center gap-4">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${toneClasses[tone]}`}>
          <Icon size={20} />
        </div>
        <div>
          <div className="text-2xl font-semibold text-slate-900">{value}</div>
          <div className="text-sm text-slate-500">{label}</div>
        </div>
      </CardBody>
    </Card>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

export default function Dashboard() {
  const [projects, setProjects] = useState(null);
  const [approvals, setApprovals] = useState(null);
  const [agents, setAgents] = useState(null);
  const { notify } = useToast();

  useEffect(() => {
    async function load() {
      try {
        const [p, ap, ag] = await Promise.all([
          api("/projects"),
          api("/approvals?status=REQUESTED"),
          api("/agents"),
        ]);
        setProjects(p);
        setApprovals(ap);
        setAgents(ag);
      } catch (e) {
        notify(`Não foi possível carregar o painel: ${e.message}`, { type: "error" });
      }
    }
    load();
  }, [notify]);

  const loading = projects === null;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Painel</h1>
        <p className="mt-1 text-sm text-slate-500">
          Visão geral da fábrica de software: projetos, agentes e o que precisa da sua atenção.
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard icon={FolderKanban} label="Projetos" value={projects.length} href="/projects" />
          <StatCard
            icon={CheckSquare}
            label="Aprovações pendentes"
            value={approvals.length}
            href="/approvals"
            tone="warning"
          />
          <StatCard
            icon={Bot}
            label="Agentes habilitados"
            value={`${agents.filter((a) => a.enabled).length}/${agents.length}`}
            href="/agents"
            tone="success"
          />
        </div>
      )}

      <Card className="border-brand-100 bg-brand-50/40">
        <CardBody className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-white">
              <Activity size={18} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900">Quer ver o que está sendo processado agora?</p>
              <p className="text-sm text-slate-500">
                Acompanhe todas as execuções em tempo real, com a esteira de progresso de cada uma.
              </p>
            </div>
          </div>
          <Link
            href="/monitor"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Abrir monitor <ArrowRight size={15} />
          </Link>
        </CardBody>
      </Card>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">Aprovações aguardando decisão</h2>
          {approvals && approvals.length > 0 && (
            <Link href="/approvals" className="text-sm font-medium text-brand-600 hover:text-brand-700">
              Ver todas
            </Link>
          )}
        </div>

        {loading ? (
          <div className="flex flex-col gap-3">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : approvals.length === 0 ? (
          <EmptyState
            icon={CheckSquare}
            title="Nenhuma aprovação pendente"
            description="Tudo certo por aqui. Quando uma execução precisar da sua decisão, ela aparece nesta lista."
          />
        ) : (
          <div className="flex flex-col gap-2.5">
            {approvals.slice(0, 5).map((a) => (
              <Link key={a.id} href="/approvals">
                <Card className="transition-shadow hover:shadow-popover">
                  <CardBody className="flex items-start gap-3">
                    <AlertTriangle size={18} className="mt-0.5 shrink-0 text-warning-500" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-slate-900">
                          {APPROVAL_TYPE_LABELS[a.approval_type] || a.approval_type}
                        </p>
                        <StatusBadge status={a.status} map={APPROVAL_STATUS} />
                      </div>
                      <p className="mt-1 truncate text-sm text-slate-500">
                        {a.summary || a.workflow_run_id}
                      </p>
                    </div>
                  </CardBody>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
