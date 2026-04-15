import { useRunDetail } from "@/hooks/use-run-detail";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import Markdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

// Convert \(...\) → $...$ and \[...\] → $$...$$ so remark-math can parse them.
function normalizeMath(text: string): string {
  // Display math: \[...\]
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_m, inner) => `$$${inner}$$`);
  // Inline math: \(...\)
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_m, inner) => `$${inner}$`);
  return text;
}

// -- Part renderers --

function PartView({ part }: { part: Record<string, unknown> }) {
  const kind = part.part_kind as string;
  const content = (part.content as string) ?? "";

  if (kind === "thinking") {
    const len = content.length;
    return (
      <Card className="border-dashed">
        <Collapsible>
          <CardHeader className="py-2 px-3">
            <CollapsibleTrigger className="flex items-center gap-2 text-xs cursor-pointer">
              <Badge variant="outline">THINKING</Badge>
              <span className="text-muted-foreground">{len.toLocaleString()} chars</span>
            </CollapsibleTrigger>
          </CardHeader>
          <CollapsibleContent>
            <CardContent className="pt-0 px-3 pb-3">
              <pre className="whitespace-pre-wrap text-xs opacity-70 max-h-96 overflow-y-auto">
                {content}
              </pre>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>
    );
  }

  if (kind === "tool-call") {
    const args = part.args;
    let code = "";
    if (typeof args === "string") {
      try {
        const parsed = JSON.parse(args);
        code = parsed.code ?? JSON.stringify(parsed, null, 2);
      } catch {
        code = args;
      }
    } else if (typeof args === "object" && args) {
      code = (args as Record<string, unknown>).code as string ?? JSON.stringify(args, null, 2);
    }
    return (
      <Card>
        <CardHeader className="py-2 px-3">
          <Badge variant="secondary">TOOL CALL · {part.tool_name as string}</Badge>
        </CardHeader>
        <CardContent className="pt-0 px-3 pb-3">
          <pre className="whitespace-pre-wrap text-xs bg-muted p-2 rounded overflow-x-auto">
            {code}
          </pre>
        </CardContent>
      </Card>
    );
  }

  if (kind === "tool-return") {
    return (
      <Card>
        <CardHeader className="py-2 px-3">
          <Badge variant="secondary">
            TOOL RETURN · {part.tool_name as string}
          </Badge>
        </CardHeader>
        <CardContent className="pt-0 px-3 pb-3">
          <pre className="whitespace-pre-wrap text-xs max-h-96 overflow-y-auto">
            {typeof content === "string" ? content : JSON.stringify(content, null, 2)}
          </pre>
        </CardContent>
      </Card>
    );
  }

  const label =
    kind === "system-prompt"
      ? "SYSTEM"
      : kind === "user-prompt"
        ? "USER"
        : kind === "retry-prompt"
          ? "RETRY"
          : "TEXT";
  const variant =
    kind === "user-prompt"
      ? "default"
      : kind === "retry-prompt"
        ? "destructive"
        : "secondary";

  return (
    <Card>
      <CardHeader className="py-2 px-3">
        <Badge variant={variant as "default" | "secondary" | "destructive"}>
          {label}
        </Badge>
      </CardHeader>
      <CardContent className="pt-0 px-3 pb-3 prose prose-sm dark:prose-invert max-w-none">
        <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
          {normalizeMath(content)}
        </Markdown>
      </CardContent>
    </Card>
  );
}

// -- Message view --

function MessageView({
  msg,
  defaultOpen,
}: {
  msg: Record<string, unknown>;
  defaultOpen: boolean;
}) {
  const parts = (msg.parts as Record<string, unknown>[]) ?? [];
  const kind = msg.kind as string;
  const usage = msg.usage as Record<string, number> | null;

  const isRequest = kind === "request";
  const hasUserPrompt = parts.some((p) => p.part_kind === "user-prompt");

  let label = "MODEL";
  if (isRequest) {
    if (hasUserPrompt) label = "USER";
    else if (parts.some((p) => p.part_kind === "tool-return")) label = "TOOL RESULT";
    else if (parts.some((p) => p.part_kind === "retry-prompt")) label = "RETRY";
    else label = "REQUEST";
  } else if (usage) {
    label = `MODEL · in:${usage.input_tokens ?? 0} out:${usage.output_tokens ?? 0}`;
  }

  return (
    <Collapsible defaultOpen={defaultOpen || !isRequest || hasUserPrompt}>
      <div className="border-l-2 pl-4 py-1">
        <CollapsibleTrigger className="flex items-center gap-2 py-1 cursor-pointer w-full">
          <Badge variant={isRequest && !hasUserPrompt ? "outline" : "secondary"}>
            {label}
          </Badge>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="space-y-2 mt-2">
            {parts.map((p, i) => (
              <PartView key={i} part={p} />
            ))}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

// -- Run detail page --

export function RunDetail({
  dbPath,
  runKey,
}: {
  dbPath: string;
  runKey: string;
}) {
  const { data, isLoading, error } = useRunDetail(dbPath, runKey);

  if (isLoading)
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  if (error || !data)
    return (
      <div className="flex-1 p-6">
        <p className="text-destructive">Error loading run</p>
      </div>
    );

  const { row, messages } = data;
  const metadata = row.metadata as Record<string, unknown> | null;
  const output = row.output as Record<string, unknown> | null;

  return (
    <div className="flex-1 overflow-y-auto p-6 h-full">
      <div className="max-w-4xl">
        <div className="flex items-center gap-2 border-b pb-4 mb-4">
          <h1 className="font-mono text-lg">Run {runKey}</h1>
          <span className="text-muted-foreground text-sm">
            {messages.length} messages
          </span>
        </div>
        <Card className="mb-4">
          <CardContent className="py-3 flex items-center gap-2 flex-wrap">
            <Badge
              variant={
                row.error
                  ? "outline"
                  : row.correct === true
                    ? "default"
                    : row.correct === false
                      ? "destructive"
                      : "secondary"
              }
            >
              {row.error
                ? "ERROR"
                : row.correct === true
                  ? "CORRECT"
                  : row.correct === false
                    ? "WRONG"
                    : "PENDING"}
            </Badge>
            {metadata?.slug != null && (
              <>
                <span className="opacity-30">·</span>
                <span className="text-xs">
                  <span className="opacity-60">slug: </span>
                  <span className="font-mono">{String(metadata.slug)}</span>
                </span>
              </>
            )}
            <span className="opacity-30">·</span>
            <span className="text-sm">
              <span className="opacity-60 text-xs">answer </span>
              <span className="font-mono font-semibold">
                {metadata?.answer != null ? String(metadata.answer) : "—"}
              </span>
              <span className="opacity-40 mx-1">→</span>
              <span className="opacity-60 text-xs">response </span>
              <span
                className={cn(
                  "font-mono font-semibold",
                  row.correct === true && "text-green-500",
                  row.correct === false && "text-red-500",
                )}
              >
                {output?.answer != null ? String(output.answer) : "—"}
              </span>
            </span>
          </CardContent>
        </Card>
        <div className="space-y-2">
          {messages.map((msg, i) => (
            <MessageView
              key={i}
              msg={msg as Record<string, unknown>}
              defaultOpen={i === 0}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function EmptyMain() {
  return (
    <div className="flex-1 flex items-center justify-center h-full">
      <p className="text-muted-foreground text-sm">Select a run from the sidebar</p>
    </div>
  );
}
