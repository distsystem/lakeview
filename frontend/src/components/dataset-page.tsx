import { useParams } from "react-router";
import { useDatasetInfo } from "@/hooks/use-dataset-info";
import { DatasetList } from "@/components/dataset-list";
import { GenericTableView } from "@/components/generic/table-view";
import { Skeleton } from "@/components/ui/skeleton";
import { getPlugin } from "@/components/plugins";

function EmptyMain() {
  return (
    <div className="flex-1 flex items-center justify-center h-full">
      <p className="text-muted-foreground text-sm">Select a run from the sidebar</p>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-32" />
      <div className="space-y-2 mt-6">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  );
}

export function DatasetPage() {
  const { root = "", "*": splat = "" } = useParams();
  const [dbPath, runKey] = (() => {
    const parts = splat.split("/r/");
    return [parts[0].replace(/\/$/, ""), parts[1] ?? null] as const;
  })();

  const { data: info, isLoading, isError } = useDatasetInfo(root, dbPath);

  // Empty path = browse root top-level. No info fetch possible.
  if (!dbPath) {
    return <DatasetList root={root} path="" />;
  }

  if (isLoading) return <LoadingSkeleton />;

  if (isError || !info) {
    return <DatasetList root={root} path={dbPath} />;
  }

  if (info.plugin) {
    const plugin = getPlugin(info.plugin);
    if (plugin) {
      return (
        <div className="flex h-[calc(100vh-48px)] overflow-hidden">
          <plugin.Sidebar root={root} path={dbPath} selectedKey={runKey} />
          {runKey ? (
            <plugin.Detail root={root} path={dbPath} runKey={runKey} />
          ) : (
            <EmptyMain />
          )}
        </div>
      );
    }
  }

  return <GenericTableView root={root} path={dbPath} schema={info.columns} />;
}
