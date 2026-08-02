"use client";
import clsx from "clsx";
import { Loader2 } from "lucide-react";
import { forwardRef } from "react";

const VARIANTS = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800 shadow-sm",
  secondary:
    "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 active:bg-slate-100 shadow-sm",
  ghost: "text-slate-600 hover:bg-slate-100 active:bg-slate-200",
  danger: "bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-800 shadow-sm",
  success: "bg-success-600 text-white hover:bg-success-700 active:bg-success-800 shadow-sm",
};

const SIZES = {
  sm: "text-xs px-2.5 py-1.5 gap-1.5 rounded-md",
  md: "text-sm px-3.5 py-2 gap-2 rounded-lg",
  lg: "text-sm px-5 py-2.5 gap-2 rounded-lg",
};

export const Button = forwardRef(function Button(
  { className, variant = "secondary", size = "md", loading = false, disabled, icon: Icon, children, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center font-medium transition-colors",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    >
      {loading ? (
        <Loader2 className="animate-spin" size={size === "sm" ? 14 : 16} />
      ) : (
        Icon && <Icon size={size === "sm" ? 14 : 16} />
      )}
      {children}
    </button>
  );
});
