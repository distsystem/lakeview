import { Link, useSearchParams } from "react-router";
import { usePluginView } from "@/hooks/use-plugin-view";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AgentRunStatsBar } from "@/components/plugins/agent-run/stats-bar";
import { cn } from "@/lib/utils";

interface RowData {
  row_offset: number;
  session_id?: string | null;
  correct?: boolean | null;
  error?: string | null;
  output?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
}

function statusIcon(row: RowData) {
  if (row.error) return <span className="text-yellow-500 font-bold">!</span>;
  if (row.correct === true) return <span className="text-green-500">ok</span>;
  if (row.correct === false) return <span className="text-red-500">x</span>;
  return <span className="text-muted-foreground/50">·</span>;
}

function uuid7Time(sid: string | null | undefined): string {
  if (!sid) return "";
  try {
    const ms = parseInt(sid.replace(/-/g, "").slice(0, 12), 16);
    return new Date(ms).toLocaleTimeString();
  } catch {
    return "";
  }
}

function RunCard({
  row,
  dbPath,
  selected,
}: {
  row: RowData;
  dbPath: string;
  selected: boolean;
}) {
  const label = uuid7Time(row.session_id) || `#${row.row_offset}`;
  const slug = row.metadata?.slug as string | undefined;
  const expected = row.metadata?.answer;
  const modelAns = row.output?.answer;

  return (
    <Link
      to={`/${dbPath}/r/${row.session_id ?? row.row_offset}`}
      className="no-underline"
    >
      <Card
        className={cn(
          "px-3 py-2 hover:border-foreground/30 transition-colors cursor-pointer",
          selected && "ring-2 ring-blue-500",
        )}
      >
        <div className="flex items-center gap-2 text-xs">
          <span className="w-5 text-center shrink-0">{statusIcon(row)}</span>
          <span className="font-mono font-semibold shrink-0">{label}</span>
          <span className="flex-1 truncate min-w-0 text-muted-foreground">
            {slug ?? ""}
          </span>
          {(expected != null || modelAns != null) && (
            <span className="shrink-0 font-mono text-[11px]">
              <span className="opacity-70">
                {expected != null ? String(expected) : "—"}
              </span>
              <span className="opacity-40 mx-0.5">→</span>
              <span
                className={cn(
                  row.correct === true && "text-green-500",
                  row.correct === false && "text-red-500",
                )}
              >
                {modelAns != null ? String(modelAns) : "—"}
              </span>
            </span>
          )}
        </div>
      </Card>
    </Link>
  );
}

const STATUSES = ["all", "ok", "wrong", "error", "pending"] as const;

export function AgentRunSidebar({
  dbPath,
  selectedKey,
}: {
  dbPath: string;
  selectedKey?: string | null;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const status = searchParams.get("status") ?? "all";
  const { data, isLoading } = usePluginView(dbPath, 0, 200, status);

  return (
    <div className="w-80 shrink-0 border-r flex flex-col h-full">
      {data?.stats && <AgentRunStatsBar stats={data.stats} />}
      <Tabs
        value={status}
        onValueChange={(v) => setSearchParams({ status: v })}
        className="px-3 pb-2"
      >
        <TabsList className="w-full">
          {STATUSES.map((s) => (
            <TabsTrigger key={s} value={s} className="text-xs flex-1">
              {s}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <ScrollArea className="flex-1">
        <div className="px-2 py-1 space-y-1">
          {isLoading && (
            <p className="text-xs text-muted-foreground p-2">Loading...</p>
          )}
          {data?.rows.map((row) => {
            const r = row as unknown as RowData;
            return (
              <RunCard
                key={r.session_id ?? r.row_offset}
                row={r}
                dbPath={dbPath}
                selected={
                  selectedKey === r.session_id ||
                  selectedKey === String(r.row_offset)
                }
              />
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
