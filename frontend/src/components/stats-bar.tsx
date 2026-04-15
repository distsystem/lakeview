import type { Stats } from "@/api/client";
import { Badge } from "@/components/ui/badge";

export function StatsBar({ stats }: { stats: Stats }) {
  return (
    <div className="flex items-center gap-1.5 px-4 py-2 text-xs">
      <span className="text-muted-foreground">{stats.total} runs</span>
      <Dot />
      <Badge variant={stats.ok ? "default" : "secondary"} className="text-xs">
        {stats.ok} ok
      </Badge>
      <Dot />
      <Badge variant={stats.wrong ? "destructive" : "secondary"} className="text-xs">
        {stats.wrong} wrong
      </Badge>
      <Dot />
      <Badge variant={stats.error ? "outline" : "secondary"} className="text-xs">
        {stats.error} error
      </Badge>
      {stats.pending > 0 && (
        <>
          <Dot />
          <span className="text-muted-foreground">{stats.pending} pending</span>
        </>
      )}
      {stats.accuracy != null && (
        <>
          <Dot />
          <span className="text-muted-foreground">
            {(stats.accuracy * 100).toFixed(0)}%
          </span>
        </>
      )}
    </div>
  );
}

function Dot() {
  return <span className="text-muted-foreground/50">·</span>;
}
