import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { usePluginView } from "@/hooks/use-plugin-view";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { AgentRunStatsBar } from "@/components/plugins/agent-run/stats-bar";
import { cn } from "@/lib/utils";
import type { AgentRunSidebar as Row } from "@/api/client";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Search,
} from "lucide-react";

function statusConfig(row: Row) {
  if (row.error)
    return {
      icon: <AlertTriangle className="size-3.5" />,
      color: "text-yellow-500",
      label: "error",
    };
  if (row.correct === true)
    return {
      icon: <CheckCircle2 className="size-3.5" />,
      color: "text-green-500",
      label: "correct",
    };
  if (row.correct === false)
    return {
      icon: <XCircle className="size-3.5" />,
      color: "text-red-500",
      label: "wrong",
    };
  return {
    icon: <Clock className="size-3.5" />,
    color: "text-muted-foreground",
    label: "pending",
  };
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
  root,
  path,
  selected,
}: {
  row: Row;
  root: string;
  path: string;
  selected: boolean;
}) {
  const label = uuid7Time(row.session_id) || `#${row.row_offset}`;
  const metadata = row.metadata as Record<string, unknown> | null | undefined;
  const output = row.output as Record<string, unknown> | null | undefined;
  const slug = metadata?.slug as string | undefined;
  const expected = metadata?.answer;
  const modelAns = output?.answer;
  const status = statusConfig(row);

  return (
    <Link
      to={`/${root}/${path}/r/${row.session_id ?? row.row_offset}`}
      className="no-underline block"
    >
      <Card
        className={cn(
          "px-3 py-2.5 transition-all cursor-pointer hover:bg-accent/50",
          selected && "ring-2 ring-primary bg-accent/30",
        )}
      >
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger>
              <span className={cn("shrink-0", status.color)}>
                {status.icon}
              </span>
            </TooltipTrigger>
            <TooltipContent side="right">{status.label}</TooltipContent>
          </Tooltip>
          <span className="font-mono text-xs font-semibold shrink-0">
            {label}
          </span>
          {slug && (
            <span className="flex-1 truncate min-w-0 text-xs text-muted-foreground">
              {slug}
            </span>
          )}
        </div>
        {(expected != null || modelAns != null) && (
          <div className="mt-1.5 ml-5.5 flex items-center gap-1 text-[11px] font-mono">
            <span className="text-muted-foreground">
              {expected != null ? String(expected) : "—"}
            </span>
            <span className="text-muted-foreground/50">→</span>
            <span
              className={cn(
                "font-semibold",
                row.correct === true && "text-green-500",
                row.correct === false && "text-red-500",
                row.correct == null && "text-muted-foreground",
              )}
            >
              {modelAns != null ? String(modelAns) : "—"}
            </span>
          </div>
        )}
      </Card>
    </Link>
  );
}

const STATUSES = ["all", "ok", "wrong", "error", "pending"] as const;

export function AgentRunSidebar({
  root,
  path,
  selectedKey,
}: {
  root: string;
  path: string;
  selectedKey?: string | null;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const status = searchParams.get("status") ?? "all";
  const { data, isLoading } = usePluginView(root, path, 0, 200, status);

  const filteredRows = data?.rows.filter((row) => {
    if (!search) return true;
    const metadata = row.metadata as Record<string, unknown> | null | undefined;
    const slug = (metadata?.slug as string) ?? "";
    const sid = row.session_id ?? "";
    const q = search.toLowerCase();
    return slug.toLowerCase().includes(q) || sid.includes(q);
  });

  return (
    <div className="w-80 shrink-0 border-r flex flex-col h-full bg-muted/30">
      {data?.stats && <AgentRunStatsBar stats={data.stats} />}
      <Tabs
        value={status}
        onValueChange={(v) => setSearchParams({ status: v })}
        className="px-3"
      >
        <TabsList className="w-full">
          {STATUSES.map((s) => (
            <TabsTrigger key={s} value={s} className="text-xs flex-1 capitalize">
              {s}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="px-3 py-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter runs..."
            className="pl-8 text-xs h-7"
          />
        </div>
      </div>
      <Separator />
      <ScrollArea className="flex-1">
        <div className="px-2 py-1 space-y-1">
          {isLoading &&
            Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-xl" />
            ))}
          {filteredRows?.map((row) => (
            <RunCard
              key={row.session_id ?? row.row_offset}
              row={row}
              root={root}
              path={path}
              selected={
                selectedKey === row.session_id ||
                selectedKey === String(row.row_offset)
              }
            />
          ))}
          {filteredRows && filteredRows.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-8">
              No runs found
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
