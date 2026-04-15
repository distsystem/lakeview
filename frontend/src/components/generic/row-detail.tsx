import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";

function JsonValue({ value }: { value: unknown }) {
  if (value == null) return <span className="text-muted-foreground/50">null</span>;
  if (typeof value === "boolean") return <span className="text-blue-500">{String(value)}</span>;
  if (typeof value === "number") return <span className="text-green-600">{value}</span>;
  if (typeof value === "string") {
    if (value.length > 500) {
      return <pre className="whitespace-pre-wrap text-xs max-h-96 overflow-y-auto">{value}</pre>;
    }
    return <span>{value}</span>;
  }
  return (
    <pre className="whitespace-pre-wrap text-xs bg-muted p-2 rounded max-h-96 overflow-y-auto">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function RowDetail({
  dbPath,
  offset,
  onClose,
}: {
  dbPath: string;
  offset: number;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["row", dbPath, offset],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{db_path}/row/{offset}", {
        params: { path: { db_path: dbPath, offset } },
      });
      return data!;
    },
  });

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-mono text-sm font-semibold">Row #{offset}</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          ×
        </Button>
      </div>
      {isLoading && <p className="text-muted-foreground text-xs">Loading...</p>}
      {data && (
        <div className="space-y-3">
          {Object.entries(data as Record<string, unknown>).map(([key, value]) => (
            <div key={key}>
              <div className="font-mono text-xs text-muted-foreground mb-1">{key}</div>
              <div className="text-sm">
                <JsonValue value={value} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
