import clsx from "clsx";
import { forwardRef } from "react";

export const Input = forwardRef(function Input({ className, label, hint, error, id, ...props }, ref) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={id}
        className={clsx(
          "w-full rounded-lg border px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400",
          "focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500",
          "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500",
          error ? "border-danger-400" : "border-slate-300",
          className
        )}
        {...props}
      />
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-danger-600">{error}</p>}
    </div>
  );
});

export const Textarea = forwardRef(function Textarea(
  { className, label, hint, error, id, rows = 3, ...props },
  ref
) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={id}
        rows={rows}
        className={clsx(
          "w-full resize-y rounded-lg border px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400",
          "focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500",
          "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500",
          error ? "border-danger-400" : "border-slate-300",
          className
        )}
        {...props}
      />
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-danger-600">{error}</p>}
    </div>
  );
});
