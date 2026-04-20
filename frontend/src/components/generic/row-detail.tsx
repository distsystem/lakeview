import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

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
  root,
  path,
  offset,
}: {
  root: string;
  path: string;
  offset: number;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["row", root, path, offset],
    queryFn: async () => {
      const { data } = await api.GET("/api/d/{root}/{path}/row/{offset}", {
        params: { path: { root, path, offset } },
      });
      return data!;
    },
  });

  if (isLoading) {
    return (
      <div className="px-4 py-2 space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-5 w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (!data) return null;

  const entries = Object.entries(data as Record<string, unknown>);

  return (
    <div className="px-4 py-2 space-y-3">
      {entries.map(([key, value], i) => (
        <div key={key}>
          <div className="font-mono text-xs text-muted-foreground mb-1">{key}</div>
          <div className="text-sm">
            <JsonValue value={value} />
          </div>
          {i < entries.length - 1 && <Separator className="mt-3" />}
        </div>
      ))}
    </div>
  );
}
