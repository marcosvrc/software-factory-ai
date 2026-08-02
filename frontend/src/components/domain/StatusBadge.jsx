import { Badge } from "@/components/ui/Badge";

export function StatusBadge({ status, map, className }) {
  const entry = map[status] || { label: status, tone: "neutral" };
  return (
    <Badge tone={entry.tone} dot className={className}>
      {entry.label}
    </Badge>
  );
}
