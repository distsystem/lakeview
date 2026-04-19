import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useDatasets } from "@/hooks/use-datasets";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { PathBreadcrumb } from "@/components/path-breadcrumb";
import { FilePreview } from "@/components/file-preview";
import { Folder, FolderOpen, Database, File, Search } from "lucide-react";
import { cn } from "@/lib/utils";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function DatasetList({ prefix: routePrefix }: { prefix?: string }) {
  const [searchParams] = useSearchParams();
  const queryPrefix = searchParams.get("prefix");
  const initial = routePrefix || queryPrefix || "sample-data";
  const [input, setInput] = useState(initial);
  const [prefix, setPrefix] = useState(initial);
  const [filter, setFilter] = useState("");
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const navigate = useNavigate();
  const { data, isLoading } = useDatasets(prefix);

  const effectivePrefix = routePrefix || queryPrefix;
  if (effectivePrefix && effectivePrefix !== prefix) {
    setPrefix(effectivePrefix);
    setInput(effectivePrefix);
  }

  const datasets = data?.datasets ?? [];
  const filtered = filter
    ? datasets.filter((d) => d.name.toLowerCase().includes(filter.toLowerCase()))
    : datasets;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between gap-4">
        <PathBreadcrumb path={prefix} />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            navigate(`/?prefix=${encodeURIComponent(input)}`);
            setPrefix(input);
          }}
          className="flex gap-2 shrink-0"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="path or s3://bucket/prefix"
            className="font-mono text-xs w-72"
          />
          <Button type="submit" size="sm">Go</Button>
        </form>
      </div>

      <Separator />

      <div className="flex items-center justify-between gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
          <Input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter..."
            className="pl-8 text-xs h-7"
          />
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          {filtered.length} {filtered.length === 1 ? "entry" : "entries"}
        </span>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[60%] font-mono text-xs">Name</TableHead>
              <TableHead className="font-mono text-xs">Type</TableHead>
              <TableHead className="text-right font-mono text-xs">Size</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-48" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-12 ml-auto" /></TableCell>
                  <TableCell />
                </TableRow>
              ))}
            {!isLoading &&
              filtered.map((ds) => {
                const isLance = ds.kind === "lance";
                const isFile = ds.kind === "file";
                const isDir = !isLance && !isFile;

                const Icon = isLance ? Database : isFile ? File : Folder;
                const iconColor = isLance
                  ? "text-blue-500"
                  : isFile
                  ? "text-muted-foreground"
                  : "text-amber-500";

                // Primary action per row type
                const onPrimary = () => {
                  if (isLance) navigate(`/${encodeURIComponent(ds.path)}`);
                  else if (isDir) navigate(`/?prefix=${encodeURIComponent(ds.path)}`);
                  else if (isFile) setPreviewPath(ds.path);
                };

                const sizeText = isFile && ds.size != null
                  ? formatSize(ds.size)
                  : ds.row_count != null
                  ? `${ds.row_count.toLocaleString()} rows`
                  : "—";

                return (
                  <TableRow
                    key={ds.path}
                    className="cursor-pointer hover:bg-muted/50 group"
                    onClick={onPrimary}
                  >
                    <TableCell>
                      <span className="flex items-center gap-2 font-mono text-sm">
                        <Icon className={cn("size-4 shrink-0", iconColor)} />
                        {isLance || isDir ? (
                          <Link
                            to={isLance
                              ? `/${encodeURIComponent(ds.path)}`
                              : `/?prefix=${encodeURIComponent(ds.path)}`}
                            className="no-underline hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {ds.name}
                          </Link>
                        ) : (
                          ds.name
                        )}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={isLance ? "secondary" : "outline"}
                        className="font-mono text-[10px]"
                      >
                        {ds.kind}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-xs text-muted-foreground">
                      {sizeText}
                    </TableCell>
                    <TableCell className="text-right">
                      {isLance && (
                        <Tooltip>
                          <TooltipTrigger
                            render={
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="opacity-0 group-hover:opacity-100 transition-opacity"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(`/?prefix=${encodeURIComponent(ds.path)}`);
                                }}
                              >
                                <FolderOpen className="size-3.5" />
                              </Button>
                            }
                          />
                          <TooltipContent>Browse as folder</TooltipContent>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            {!isLoading && filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground py-8 text-sm">
                  {filter ? "No matches" : `No entries under: ${prefix}`}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <Sheet
        open={previewPath !== null}
        onOpenChange={(o) => { if (!o) setPreviewPath(null); }}
      >
        <SheetContent side="right" className="w-[640px] sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="font-mono text-sm break-all">
              {previewPath?.split("/").pop()}
            </SheetTitle>
            <SheetDescription className="font-mono text-xs break-all">
              {previewPath}
            </SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-4">
            {previewPath && <FilePreview path={previewPath} />}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
