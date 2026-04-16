import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";

interface AgentRunStats {
  total: number;
  ok: number;
  wrong: number;
  error: number;
  pending: number;
  accuracy: number | null;
}

export function AgentRunStatsBar({ stats }: { stats: Record<string, unknown> }) {
  const s = stats as unknown as AgentRunStats;
  const pct = s.accuracy != null ? Math.round(s.accuracy * 100) : null;

  return (
    <div className="px-4 py-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">
          {s.total} runs
        </span>
        {pct != null && (
          <span className="text-xs font-mono font-semibold">{pct}%</span>
        )}
      </div>
      {pct != null && <Progress value={pct} />}
      <div className="flex items-center gap-1.5 flex-wrap">
        <Badge variant="default" className="text-[11px] tabular-nums">
          {s.ok} ok
        </Badge>
        <Badge variant="destructive" className="text-[11px] tabular-nums">
          {s.wrong} wrong
        </Badge>
        <Badge variant="outline" className="text-[11px] tabular-nums">
          {s.error} error
        </Badge>
        {s.pending > 0 && (
          <Badge variant="secondary" className="text-[11px] tabular-nums">
            {s.pending} pending
          </Badge>
        )}
      </div>
      <Separator />
    </div>
  );
}
