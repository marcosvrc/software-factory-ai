import { Loader2 } from "lucide-react";

export function PageSpinner({ label = "Carregando…" }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-slate-400">
      <Loader2 className="animate-spin" size={28} />
      <p className="text-sm">{label}</p>
    </div>
  );
}
