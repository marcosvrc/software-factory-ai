// Estilos por status de nó do diagrama de processo (estilo Camunda Cockpit).
export const NODE_STATUS_STYLE = {
  pending: {
    border: "border-slate-300",
    bg: "bg-white",
    text: "text-slate-500",
    ring: "",
    dot: "bg-slate-300",
  },
  active: {
    border: "border-info-500",
    bg: "bg-info-50",
    text: "text-info-800",
    ring: "ring-2 ring-info-300 animate-pulse",
    dot: "bg-info-500",
  },
  waiting: {
    border: "border-warning-500",
    bg: "bg-warning-50",
    text: "text-warning-800",
    ring: "ring-2 ring-warning-300 animate-pulse",
    dot: "bg-warning-500",
  },
  looping: {
    border: "border-warning-400",
    bg: "bg-warning-50",
    text: "text-warning-700",
    ring: "",
    dot: "bg-warning-400",
  },
  done: {
    border: "border-success-500",
    bg: "bg-success-50",
    text: "text-success-800",
    ring: "",
    dot: "bg-success-500",
  },
  escalated: {
    border: "border-danger-500",
    bg: "bg-danger-50",
    text: "text-danger-800",
    ring: "ring-2 ring-danger-300 animate-pulse",
    dot: "bg-danger-500",
  },
};

export const EDGE_KIND_STYLE = {
  happy: { stroke: "#94a3b8", strokeWidth: 1.5, dashed: false },
  cycle: { stroke: "#f59e0b", strokeWidth: 1.5, dashed: true },
  escalate: { stroke: "#ef4444", strokeWidth: 1.5, dashed: true },
  resume: { stroke: "#cbd5e1", strokeWidth: 1, dashed: true },
};
