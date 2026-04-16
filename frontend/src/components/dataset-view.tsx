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

export function DatasetView() {
  const { "*": splat } = useParams();
  const parts = (splat ?? "").split("/r/");
  const dbPath = parts[0].replace(/\/$/, "");
  const runKey = parts[1] ?? null;

  const { data: info, isLoading, isError } = useDatasetInfo(dbPath);

  if (isLoading) return <LoadingSkeleton />;

  if (isError || !info) {
    return <DatasetList prefix={dbPath} />;
  }

  if (info.plugin) {
    const plugin = getPlugin(info.plugin);
    if (plugin) {
      return (
        <div className="flex h-[calc(100vh-48px)] overflow-hidden">
          <plugin.Sidebar dbPath={dbPath} selectedKey={runKey} />
          {runKey ? (
            <plugin.Detail dbPath={dbPath} runKey={runKey} />
          ) : (
            <EmptyMain />
          )}
        </div>
      );
    }
  }

  return <GenericTableView dbPath={dbPath} schema={info.columns} />;
}
