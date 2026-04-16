import { useState, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from "@tanstack/react-table";
import { useRows } from "@/hooks/use-rows";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { RowDetail } from "@/components/generic/row-detail";
import type { ColumnInfo } from "@/api/client";

function CellRenderer({ value }: { value: unknown }) {
  if (value == null) return <span className="text-muted-foreground/50">null</span>;
  if (typeof value === "boolean") return <span>{value ? "true" : "false"}</span>;
  if (typeof value === "object") {
    const text = JSON.stringify(value);
    return (
      <Tooltip>
        <TooltipTrigger>
          <span className="font-mono text-xs truncate block max-w-[300px]">{text}</span>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-md">
          <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(value, null, 2)}</pre>
        </TooltipContent>
      </Tooltip>
    );
  }
  const text = String(value);
  if (text.length > 120) {
    return (
      <Tooltip>
        <TooltipTrigger>
          <span className="truncate block max-w-[300px]">{text}</span>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-md">
          <p className="text-xs">{text}</p>
        </TooltipContent>
      </Tooltip>
    );
  }
  return <span>{text}</span>;
}

function TableSkeleton() {
  return (
    <div className="p-4 space-y-3">
      {Array.from({ length: 10 }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}

const PAGE_SIZE = 50;

export function GenericTableView({
  dbPath,
  schema,
}: {
  dbPath: string;
  schema: ColumnInfo[];
}) {
  const [offset, setOffset] = useState(0);
  const [selectedRow, setSelectedRow] = useState<number | null>(null);
  const { data, isLoading } = useRows(dbPath, offset, PAGE_SIZE);

  const columns = useMemo<ColumnDef<Record<string, unknown>>[]>(
    () => [
      {
        id: "_row_num",
        header: "#",
        cell: ({ row }) => (
          <span className="text-muted-foreground text-xs">{offset + row.index}</span>
        ),
        size: 50,
      },
      ...schema
        .filter((col) => col.name !== "messages")
        .map((col) => ({
          accessorKey: col.name,
          header: col.name,
          cell: ({ getValue }: { getValue: () => unknown }) => (
            <CellRenderer value={getValue()} />
          ),
        })),
    ],
    [schema, offset],
  );

  const tableData = (data?.rows ?? []) as Record<string, unknown>[];

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const total = data?.total ?? 0;
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <div className="flex h-[calc(100vh-48px)] overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-2 text-xs text-muted-foreground">
          <span>{total} rows</span>
          <span>·</span>
          <span>{schema.length} columns</span>
        </div>
        <Separator />
        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <TableSkeleton />
          ) : (
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id}>
                    {hg.headers.map((h) => (
                      <TableHead
                        key={h.id}
                        className="font-mono text-xs whitespace-nowrap"
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    className="cursor-pointer hover:bg-muted/50"
                    data-selected={selectedRow === offset + row.index}
                    onClick={() => setSelectedRow(offset + row.index)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="text-xs py-1.5">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
        <Separator />
        <div className="flex items-center justify-between px-4 py-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={!hasPrev}
          >
            Prev
          </Button>
          <span className="text-xs text-muted-foreground">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={!hasNext}
          >
            Next
          </Button>
        </div>
      </div>
      <Sheet
        open={selectedRow !== null}
        onOpenChange={(open) => { if (!open) setSelectedRow(null); }}
      >
        <SheetContent side="right" className="w-[450px] sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="font-mono">Row #{selectedRow}</SheetTitle>
            <SheetDescription>Full row data</SheetDescription>
          </SheetHeader>
          {selectedRow !== null && (
            <RowDetail dbPath={dbPath} offset={selectedRow} />
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
