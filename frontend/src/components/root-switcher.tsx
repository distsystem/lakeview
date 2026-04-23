import { Link, useParams } from "react-router";
import { Library } from "lucide-react";
import { useRoots } from "@/hooks/use-roots";
import { cn } from "@/lib/utils";

export function RootSwitcher() {
  const { data } = useRoots();
  const { root: current } = useParams();

  if (!data || data.roots.length === 0) return null;

  return (
    <div className="flex items-center gap-0.5 font-mono text-xs">
      {data.roots.map((r) => {
        const isNamespace = r.kind === "namespace";
        const label = isNamespace && r.driver ? `${r.uri} — ${r.driver}` : r.uri;
        return (
          <Link
            key={r.name}
            to={`/${r.name}`}
            className={cn(
              "px-2 py-1 rounded no-underline transition inline-flex items-center gap-1",
              r.name === current
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:bg-muted",
            )}
            title={label}
          >
            {isNamespace && (
              <Library className="size-3 opacity-70 text-purple-500" />
            )}
            {r.name}
          </Link>
        );
      })}
    </div>
  );
}
