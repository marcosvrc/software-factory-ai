import clsx from "clsx";

const TONES = {
  neutral: "bg-slate-100 text-slate-700",
  brand: "bg-brand-100 text-brand-700",
  success: "bg-success-100 text-success-700",
  warning: "bg-warning-100 text-warning-700",
  danger: "bg-danger-100 text-danger-700",
  info: "bg-info-100 text-info-700",
};

const DOT_TONES = {
  neutral: "bg-slate-400",
  brand: "bg-brand-500",
  success: "bg-success-500",
  warning: "bg-warning-500",
  danger: "bg-danger-500",
  info: "bg-info-500",
};

export function Badge({ tone = "neutral", dot = false, className, children }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        TONES[tone],
        className
      )}
    >
      {dot && <span className={clsx("h-1.5 w-1.5 rounded-full", DOT_TONES[tone])} />}
      {children}
    </span>
  );
}
