import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
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
} from "@/components/ui/command";
import { Folder, Database, Loader2 } from "lucide-react";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { root = "" } = useParams();

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

  // Palette is scoped to the current root. Typing "foo/bar/baz" browses the
  // deepest existing prefix ("foo/bar") and filters by tail ("baz").
  const trimmed = query.trim().replace(/^\/+|\/+$/g, "");
  const lastSlash = trimmed.lastIndexOf("/");
  const browsePath = lastSlash === -1 ? "" : trimmed.slice(0, lastSlash);
  const tailFilter = lastSlash === -1
    ? trimmed.toLowerCase()
    : trimmed.slice(lastSlash + 1).toLowerCase();

  const { data, isLoading } = useQuery({
    queryKey: ["palette-datasets", root, browsePath],
    queryFn: async () => {
      const { data } = await api.GET("/api/datasets", {
        params: { query: { root, path: browsePath } },
      });
      return data!;
    },
    enabled: open && !!root,
  });

  const filtered = (data?.datasets ?? []).filter((d) =>
    tailFilter ? d.name.toLowerCase().includes(tailFilter) : true,
  );

  const go = (relPath: string) => {
    setOpen(false);
    setQuery("");
    navigate(`/${root}/${relPath}`);
  };

  if (!root) return null;

  return (
    <CommandDialog open={open} onOpenChange={setOpen} shouldFilter={false}>
      <CommandInput
        placeholder={`Browse under ${root}…`}
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandGroup heading={`Contents of ${root}/${browsePath}`}>
          {isLoading && (
            <CommandItem disabled value="__loading">
              <Loader2 className="animate-spin" />
              <span className="text-muted-foreground">Loading...</span>
            </CommandItem>
          )}
          {!isLoading && filtered.length === 0 && (
            <CommandEmpty>No entries under {root}/{browsePath}</CommandEmpty>
          )}
          {filtered.map((ds) => {
            const isLance = ds.kind === "lance";
            const Icon = isLance ? Database : Folder;
            return (
              <CommandItem
                key={ds.path}
                value={ds.path}
                onSelect={() => go(ds.path)}
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
