import clsx from "clsx";

export function Skeleton({ className }) {
  return <div className={clsx("animate-pulse rounded-md bg-slate-200/80", className)} />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl2 border border-slate-200 bg-white p-5 shadow-card">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="mt-3 h-3 w-2/3" />
      <Skeleton className="mt-2 h-3 w-1/2" />
    </div>
  );
}

export function SkeletonRows({ rows = 4 }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
