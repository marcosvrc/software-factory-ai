import clsx from "clsx";

export function Card({ className, children, ...props }) {
  return (
    <div
      className={clsx(
        "rounded-xl2 border border-slate-200 bg-white shadow-card",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children }) {
  return (
    <div className={clsx("flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4", className)}>
      {children}
    </div>
  );
}

export function CardBody({ className, children }) {
  return <div className={clsx("px-5 py-4", className)}>{children}</div>;
}

export function CardTitle({ className, children }) {
  return <h3 className={clsx("text-sm font-semibold text-slate-900", className)}>{children}</h3>;
}
