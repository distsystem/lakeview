import { Badge } from "@/components/ui/badge";

interface AgentRunStats {
  total: number;
  ok: number;
  wrong: number;
  error: number;
  pending: number;
  accuracy: number | null;
}

function Dot() {
  return <span className="text-muted-foreground/50">·</span>;
}

export function AgentRunStatsBar({ stats }: { stats: Record<string, unknown> }) {
  const s = stats as unknown as AgentRunStats;
  return (
    <div className="flex items-center gap-1.5 px-4 py-2 text-xs">
      <span className="text-muted-foreground">{s.total} runs</span>
      <Dot />
      <Badge variant={s.ok ? "default" : "secondary"} className="text-xs">
        {s.ok} ok
      </Badge>
      <Dot />
      <Badge variant={s.wrong ? "destructive" : "secondary"} className="text-xs">
        {s.wrong} wrong
      </Badge>
      <Dot />
      <Badge variant={s.error ? "outline" : "secondary"} className="text-xs">
        {s.error} error
      </Badge>
      {s.pending > 0 && (
        <>
          <Dot />
          <span className="text-muted-foreground">{s.pending} pending</span>
        </>
      )}
      {s.accuracy != null && (
        <>
          <Dot />
          <span className="text-muted-foreground">
            {(s.accuracy * 100).toFixed(0)}%
          </span>
        </>
      )}
    </div>
  );
}
