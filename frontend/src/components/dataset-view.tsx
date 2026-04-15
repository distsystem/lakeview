import { useParams } from "react-router";
import { RunSidebar } from "@/components/run-sidebar";
import { RunDetail, EmptyMain } from "@/components/run-detail";
import { DatasetList } from "@/components/dataset-list";
import { useRows } from "@/hooks/use-rows";

export function DatasetView() {
  const { "*": splat } = useParams();
  const parts = (splat ?? "").split("/r/");
  const dbPath = parts[0].replace(/\/$/, "");
  const runKey = parts[1] ?? null;

  // Probe: try loading rows to detect if this path is a Lance dataset
  const { data, isLoading, isError } = useRows(dbPath, 0, 1, "all");

  // Still loading the probe
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-48px)]">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  // Not a Lance dataset — fall back to directory browser
  if (isError || !data) {
    return <DatasetList prefix={dbPath} />;
  }

  // Lance dataset — render viewer
  return (
    <div className="flex h-[calc(100vh-48px)] overflow-hidden">
      <RunSidebar dbPath={dbPath} selectedKey={runKey} />
      {runKey ? (
        <RunDetail dbPath={dbPath} runKey={runKey} />
      ) : (
        <EmptyMain />
      )}
    </div>
  );
}
