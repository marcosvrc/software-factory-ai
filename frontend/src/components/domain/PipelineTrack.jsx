import clsx from "clsx";
import { Check } from "lucide-react";
import { PIPELINE_STAGES } from "@/lib/statuses";

const ACTIVE_TONE = {
  RUNNING: "bg-info-500 text-white",
  WAITING_TOOL: "bg-info-500 text-white",
  WAITING_AGENT: "bg-info-500 text-white",
  WAITING_HUMAN: "bg-warning-500 text-white",
  RETRYING: "bg-warning-500 text-white",
  PARTIALLY_COMPLETED: "bg-info-500 text-white",
  FAILED_RETRYABLE: "bg-danger-500 text-white",
  FAILED_FINAL: "bg-danger-500 text-white",
};

/** Esteira visual de progresso do pipeline de entrega (14 etapas). */
export function PipelineTrack({ currentNode, status, compact = false }) {
  const currentIndex = PIPELINE_STAGES.findIndex((s) => s.key === currentNode);
  const completed = status === "COMPLETED";

  return (
    <div className={clsx("flex flex-wrap gap-1", compact && "gap-1")}>
      {PIPELINE_STAGES.map((stage, i) => {
        const isPast = completed || i < currentIndex;
        const isCurrent = !completed && i === currentIndex;
        const activeClass = ACTIVE_TONE[status] || "bg-info-500 text-white";

        return (
          <span
            key={stage.key}
            title={stage.label}
            className={clsx(
              "inline-flex items-center gap-1 whitespace-nowrap rounded-md px-1.5 text-[11px] font-medium leading-5",
              isPast && "bg-success-500 text-white",
              isCurrent && activeClass,
              !isPast && !isCurrent && "bg-slate-100 text-slate-400"
            )}
          >
            {isPast && <Check size={10} strokeWidth={3} />}
            {!compact && stage.label}
          </span>
        );
      })}
    </div>
  );
}
