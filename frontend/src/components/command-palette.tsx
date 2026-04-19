import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
  CommandSeparator,
} from "@/components/ui/command";
import { Folder, Database, ArrowRight, Loader2 } from "lucide-react";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Use the typed text as the browse prefix; deepest existing prefix wins.
  // Strip trailing slashes and trailing partial segment so "sample-data/k"
  // still browses "sample-data". Preserve the `s3://` scheme when splitting.
  const trimmed = query.trim().replace(/\/+$/, "");
  const scheme = trimmed.startsWith("s3://") ? "s3://" : "";
  const body = trimmed.slice(scheme.length);
  const lastSlash = body.lastIndexOf("/");
  const browsePrefix =
    trimmed === "" ? "sample-data"
    : lastSlash === -1 ? trimmed
    : scheme + body.slice(0, lastSlash);
  const tailFilter = lastSlash === -1 ? "" : body.slice(lastSlash + 1).toLowerCase();

  const { data, isLoading } = useQuery({
    queryKey: ["palette-datasets", browsePrefix],
    queryFn: async () => {
      const { data } = await api.GET("/api/datasets", {
        params: { query: { prefix: browsePrefix } },
      });
      return data!;
    },
    enabled: open,
  });

  const filtered = (data?.datasets ?? []).filter((d) =>
    tailFilter ? d.name.toLowerCase().includes(tailFilter) : true
  );

  const go = (path: string, isLance: boolean) => {
    setOpen(false);
    setQuery("");
    if (isLance) navigate(`/${encodeURIComponent(path)}`);
    else navigate(`/?prefix=${encodeURIComponent(path)}`);
  };

  // Allow user to "force navigate" to whatever they typed, even if not in list
  const showRaw = query.trim() && query.trim() !== browsePrefix;

  return (
    <CommandDialog open={open} onOpenChange={setOpen} shouldFilter={false}>
      <CommandInput
        placeholder="Browse path... (e.g. sample-data, s3://bucket/prefix)"
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        {showRaw && (
          <>
            <CommandGroup heading="Navigate">
              <CommandItem
                value={`__raw_${query}`}
                onSelect={() => go(query.trim(), false)}
              >
                <ArrowRight />
                <span className="font-mono">Browse "{query.trim()}"</span>
              </CommandItem>
            </CommandGroup>
            <CommandSeparator />
          </>
        )}
        <CommandGroup heading={`Contents of ${browsePrefix}`}>
          {isLoading && (
            <CommandItem disabled value="__loading">
              <Loader2 className="animate-spin" />
              <span className="text-muted-foreground">Loading...</span>
            </CommandItem>
          )}
          {!isLoading && filtered.length === 0 && (
            <CommandEmpty>No entries under {browsePrefix}</CommandEmpty>
          )}
          {filtered.map((ds) => {
            const isLance = ds.kind === "lance";
            const Icon = isLance ? Database : Folder;
            return (
              <CommandItem
                key={ds.path}
                value={ds.path}
                onSelect={() => go(ds.path, isLance)}
              >
                <Icon className={isLance ? "text-blue-500" : "text-muted-foreground"} />
                <span className="font-mono">{ds.name}</span>
                {ds.row_count != null && (
                  <CommandShortcut className="tabular-nums">
                    {ds.row_count.toLocaleString()} rows
                  </CommandShortcut>
                )}
              </CommandItem>
            );
          })}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
