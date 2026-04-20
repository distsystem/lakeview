import { useState } from "react";
import { Download } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";

export type BlobValue = { size?: number; position?: number } | null | undefined;

function blobUrl(
  root: string,
  path: string,
  offset: number,
  column: string,
): string {
  const segs = path.split("/").map(encodeURIComponent).join("/");
  return `/api/d/${root}/${segs}/blob/${offset}/${encodeURIComponent(column)}`;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function NonImageFallback({
  url,
  size,
  variant,
}: {
  url: string;
  size?: number;
  variant: "thumb" | "full";
}) {
  const label = size != null ? `blob · ${formatBytes(size)}` : "blob";
  if (variant === "thumb") {
    return (
      <a
        href={url}
        download
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        onClick={(e) => e.stopPropagation()}
      >
        <Download className="size-3" />
        {label}
      </a>
    );
  }
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span>{label}</span>
      <a
        href={url}
        download
        className={buttonVariants({ variant: "outline", size: "sm" })}
      >
        <Download className="size-3.5" /> Download
      </a>
    </div>
  );
}

export function BlobCell({
  root,
  path,
  offset,
  column,
  value,
  variant,
}: {
  root: string;
  path: string;
  offset: number;
  column: string;
  value: BlobValue;
  variant: "thumb" | "full";
}) {
  const [failed, setFailed] = useState(false);
  if (value == null) {
    return <span className="text-muted-foreground/50">null</span>;
  }
  const url = blobUrl(root, path, offset, column);
  const size = value.size;

  if (failed) {
    return <NonImageFallback url={url} size={size} variant={variant} />;
  }

  if (variant === "thumb") {
    return (
      <img
        src={url}
        alt={column}
        loading="lazy"
        onError={() => setFailed(true)}
        className="h-12 max-w-[96px] object-contain rounded"
      />
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-center bg-muted/30 rounded-md p-4">
        <img
          src={url}
          alt={column}
          loading="lazy"
          onError={() => setFailed(true)}
          className="max-w-full max-h-[70vh] rounded"
        />
      </div>
      {size != null && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{formatBytes(size)}</span>
          <a
            href={url}
            download
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            <Download className="size-3.5" /> Download
          </a>
        </div>
      )}
    </div>
  );
}
