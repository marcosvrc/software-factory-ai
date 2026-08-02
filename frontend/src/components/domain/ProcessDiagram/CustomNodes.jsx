"use client";
import { Handle, Position } from "@xyflow/react";
import clsx from "clsx";
import { CheckCircle2, Clock, RotateCcw, AlertTriangle, Flag } from "lucide-react";
import { NODE_STATUS_STYLE } from "./nodeStyles";

const STATUS_ICON = {
  active: Clock,
  waiting: AlertTriangle,
  looping: RotateCcw,
  done: CheckCircle2,
  escalated: AlertTriangle,
};

function CycleBadge({ cycles, max = 3 }) {
  if (!cycles) return null;
  const isMax = cycles >= max;
  return (
    <span
      className={clsx(
        "absolute -right-2 -top-2 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[10px] font-semibold",
        isMax ? "bg-danger-500 text-white" : "bg-warning-400 text-white"
      )}
      title={`${cycles} de ${max} ciclos automáticos usados`}
    >
      {cycles}/{max}
    </span>
  );
}

export function StageNode({ data }) {
  const style = NODE_STATUS_STYLE[data.status] || NODE_STATUS_STYLE.pending;
  const Icon = STATUS_ICON[data.status];
  return (
    <div
      className={clsx(
        "relative flex w-[200px] flex-col gap-1 rounded-lg border-2 px-3 py-2.5 shadow-sm",
        style.border,
        style.bg,
        style.ring
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400" />
      <div className="flex items-center gap-1.5">
        <span className={clsx("h-1.5 w-1.5 shrink-0 rounded-full", style.dot)} />
        {Icon && <Icon size={13} className={style.text} />}
        <span className={clsx("whitespace-pre-line text-xs font-medium leading-tight", style.text)}>
          {data.label}
        </span>
      </div>
      {data.agentCount ? (
        <span className="text-[10px] text-slate-400">{data.agentCount} agente(s)</span>
      ) : null}
      <CycleBadge cycles={data.cycles} />
    </div>
  );
}

export function GateNode({ data }) {
  const style = NODE_STATUS_STYLE[data.status] || NODE_STATUS_STYLE.pending;
  const Icon = STATUS_ICON[data.status];
  return (
    <div
      className={clsx(
        "relative flex w-[200px] flex-col gap-1 rounded-lg border-2 px-3 py-2.5 shadow-sm",
        style.border,
        style.bg,
        style.ring
      )}
      style={{ borderStyle: "solid" }}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400" />
      <Handle type="source" position={Position.Right} id="side" className="!bg-slate-400" />
      <div className="flex items-center gap-1.5">
        <span className={clsx("flex h-3.5 w-3.5 shrink-0 rotate-45 items-center justify-center", style.dot, "rounded-[2px]")} />
        {Icon && <Icon size={13} className={style.text} />}
        <span className={clsx("whitespace-pre-line text-xs font-medium leading-tight", style.text)}>
          {data.label}
        </span>
      </div>
      <span className="text-[10px] uppercase tracking-wide text-slate-400">gate</span>
      <CycleBadge cycles={data.cycles} />
    </div>
  );
}

export function EndNode({ data }) {
  // Nós terminais (delivered/cancelled) nunca ficam "em andamento" — o
  // status só é diferente de "pending" quando a execução de fato chegou
  // nesse desfecho. Por isso o destaque de cor depende só de status !==
  // pending, não de um valor específico como "active"/"escalated".
  const reached = data.status !== "pending";
  const isDelivered = data.kind === "delivered";
  return (
    <div
      className={clsx(
        "flex w-[140px] items-center justify-center gap-1.5 rounded-full border-2 px-3 py-2 text-xs font-semibold shadow-sm",
        !reached && "border-slate-300 bg-white text-slate-400",
        reached &&
          isDelivered &&
          "border-success-500 bg-success-500 text-white",
        reached &&
          !isDelivered &&
          "border-danger-500 bg-danger-500 text-white"
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      <Flag size={13} />
      {data.label}
    </div>
  );
}
