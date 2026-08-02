"use client";
import clsx from "clsx";

export function Toggle({ checked, onChange, disabled, label, id }) {
  return (
    <button
      type="button"
      role="switch"
      id={id}
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
      className={clsx(
        "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2",
        checked ? "bg-brand-600" : "bg-slate-300",
        disabled && "cursor-not-allowed opacity-50"
      )}
    >
      <span
        className={clsx(
          "inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform",
          checked ? "translate-x-4.5" : "translate-x-1"
        )}
        style={{ transform: checked ? "translateX(1.125rem)" : "translateX(0.125rem)" }}
      />
    </button>
  );
}
