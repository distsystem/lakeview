import { useParams } from "react-router";
import { useDatasetInfo } from "@/hooks/use-dataset-info";
import { DatasetList } from "@/components/dataset-list";
import { GenericTableView } from "@/components/generic/table-view";
import { getPlugin } from "@/components/plugins";

function EmptyMain() {
  return (
    <div className="flex-1 flex items-center justify-center h-full">
      <p className="text-muted-foreground text-sm">Select a run from the sidebar</p>
    </div>
  );
}

export function DatasetView() {
  const { "*": splat } = useParams();
  const parts = (splat ?? "").split("/r/");
  const dbPath = parts[0].replace(/\/$/, "");
  const runKey = parts[1] ?? null;

  const { data: info, isLoading, isError } = useDatasetInfo(dbPath);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-48px)]">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  // Not a dataset — fall back to directory browser
  if (isError || !info) {
    return <DatasetList prefix={dbPath} />;
  }

  // Plugin detected? Use rich view.
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

  // Fallback: generic table view
  return <GenericTableView dbPath={dbPath} schema={info.columns} />;
}
