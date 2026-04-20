import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import type { AgentRunStats } from "@/api/client";

export function AgentRunStatsBar({ stats }: { stats: AgentRunStats }) {
  const pct = stats.accuracy != null ? Math.round(stats.accuracy * 100) : null;

  return (
    <div className="px-4 py-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">
          {stats.total} runs
        </span>
        {pct != null && (
          <span className="text-xs font-mono font-semibold">{pct}%</span>
        )}
      </div>
      {pct != null && <Progress value={pct} />}
      <div className="flex items-center gap-1.5 flex-wrap">
        <Badge variant="default" className="text-[11px] tabular-nums">
          {stats.ok} ok
        </Badge>
        <Badge variant="destructive" className="text-[11px] tabular-nums">
          {stats.wrong} wrong
        </Badge>
        <Badge variant="outline" className="text-[11px] tabular-nums">
          {stats.error} error
        </Badge>
        {stats.pending > 0 && (
          <Badge variant="secondary" className="text-[11px] tabular-nums">
            {stats.pending} pending
          </Badge>
        )}
      </div>
      <Separator />
    </div>
  );
}
