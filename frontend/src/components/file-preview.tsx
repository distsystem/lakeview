import { useQuery } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/components/ai-elements/code-block";
import { Download, AlertTriangle } from "lucide-react";
import Markdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import type { BundledLanguage } from "shiki";

const EXT_TO_LANG: Record<string, BundledLanguage> = {
  js: "javascript",
  jsx: "jsx",
  ts: "typescript",
  tsx: "tsx",
  py: "python",
  json: "json",
  yaml: "yaml",
  yml: "yaml",
  toml: "toml",
  rs: "rust",
  go: "go",
  java: "java",
  c: "c",
  cpp: "cpp",
  h: "c",
  hpp: "cpp",
  sh: "shell",
  bash: "shell",
  zsh: "shell",
  sql: "sql",
  html: "html",
  css: "css",
  xml: "xml",
  ini: "ini",
  csv: "csv",
};

const IMAGE_EXTS = new Set(["png", "jpg", "jpeg", "gif", "webp", "svg", "avif"]);
const MARKDOWN_EXTS = new Set(["md", "markdown", "mdx"]);

function fileUrl(root: string, path: string): string {
  // Per-segment encoding keeps slashes as URL separators (FastAPI's path
  // converter) while escaping everything else.
  const segs = path.split("/").map(encodeURIComponent).join("/");
  return `/api/file/${root}/${segs}`;
}

function extOf(path: string): string {
  const i = path.lastIndexOf(".");
  return i === -1 ? "" : path.slice(i + 1).toLowerCase();
}

function ImagePreview({ root, path }: { root: string; path: string }) {
  return (
    <div className="flex items-center justify-center bg-muted/30 rounded-md p-4">
      <img
        src={fileUrl(root, path)}
        alt={path}
        className="max-w-full max-h-[70vh] rounded"
      />
    </div>
  );
}

function MarkdownPreview({ root, path }: { root: string; path: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["file-text", root, path],
    queryFn: async () => {
      const res = await fetch(fileUrl(root, path));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.text();
    },
  });
  if (isLoading) return <PreviewSkeleton />;
  if (error || data == null) return <PreviewError error={error} />;
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {data}
      </Markdown>
    </div>
  );
}

function CodePreview({
  root,
  path,
  lang,
}: {
  root: string;
  path: string;
  lang: BundledLanguage;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["file-text", root, path],
    queryFn: async () => {
      const res = await fetch(fileUrl(root, path));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.text();
    },
  });
  if (isLoading) return <PreviewSkeleton />;
  if (error || data == null) return <PreviewError error={error} />;

  let code = data;
  if (lang === "json") {
    try { code = JSON.stringify(JSON.parse(data), null, 2); } catch { /* keep raw */ }
  }
  return <CodeBlock code={code} language={lang} showLineNumbers />;
}

function DownloadFallback({ root, path }: { root: string; path: string }) {
  return (
    <Alert>
      <AlertTriangle className="size-4" />
      <AlertTitle>Cannot preview this file type</AlertTitle>
      <AlertDescription className="flex items-center gap-2">
        <span>The file format is not supported for inline preview.</span>
        <Button asChild variant="outline" size="sm">
          <a href={fileUrl(root, path)} download>
            <Download className="size-3.5" /> Download
          </a>
        </Button>
      </AlertDescription>
    </Alert>
  );
}

function PreviewSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 10 }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
}

function PreviewError({ error }: { error: unknown }) {
  return (
    <Alert variant="destructive">
      <AlertTriangle className="size-4" />
      <AlertTitle>Failed to load file</AlertTitle>
      <AlertDescription>
        {error instanceof Error ? error.message : "Unknown error"}
      </AlertDescription>
    </Alert>
  );
}

export function FilePreview({ root, path }: { root: string; path: string }) {
  const ext = extOf(path);

  if (IMAGE_EXTS.has(ext)) return <ImagePreview root={root} path={path} />;
  if (MARKDOWN_EXTS.has(ext)) return <MarkdownPreview root={root} path={path} />;
  const lang = EXT_TO_LANG[ext];
  if (lang) return <CodePreview root={root} path={path} lang={lang} />;

  if (ext === "" || ext === "txt" || ext === "log") {
    return <CodePreview root={root} path={path} lang={"text" as BundledLanguage} />;
  }
  return <DownloadFallback root={root} path={path} />;
}
