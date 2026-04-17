import { usePluginDetail } from "@/hooks/use-plugin-detail";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
} from "@/components/ai-elements/reasoning";
import {
  Tool,
  ToolHeader,
  ToolContent,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
import { CodeBlock } from "@/components/ai-elements/code-block";
import {
  ChainOfThought,
  ChainOfThoughtHeader,
  ChainOfThoughtContent,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";
import {
  StackTrace,
  StackTraceHeader,
  StackTraceError,
  StackTraceErrorType,
  StackTraceErrorMessage,
  StackTraceActions,
  StackTraceCopyButton,
  StackTraceExpandButton,
  StackTraceContent,
  StackTraceFrames,
} from "@/components/ai-elements/stack-trace";
import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  User,
  Settings,
  RotateCcw,
  MessageSquare,
  CornerDownRight,
  Wrench,
  Brain,
} from "lucide-react";
import Markdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

// Normalize LaTeX delimiters: \[...\] -> $$...$$, \(...\) -> $...$
function normalizeMath(text: string): string {
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_m, inner) => `$$${inner}$$`);
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_m, inner) => `$${inner}$`);
  return text;
}

// -- Part renderers (using AI Elements) --

function PartView({ part }: { part: Record<string, unknown> }) {
  const kind = part.part_kind as string;
  const content = (part.content as string) ?? "";

  if (kind === "thinking") {
    return (
      <Reasoning defaultOpen={false}>
        <ReasoningTrigger
          getThinkingMessage={() => (
            <span>Thought · {content.length.toLocaleString()} chars</span>
          )}
        />
        <ReasoningContent>{content}</ReasoningContent>
      </Reasoning>
    );
  }

  if (kind === "tool-call") {
    const toolName = part.tool_name as string;
    const args = part.args;
    let parsedInput: Record<string, unknown> = {};
    if (typeof args === "string") {
      try { parsedInput = JSON.parse(args); } catch { parsedInput = { raw: args }; }
    } else if (typeof args === "object" && args) {
      parsedInput = args as Record<string, unknown>;
    }
    const code = parsedInput.code as string | undefined;

    return (
      <Tool>
        <ToolHeader type="dynamic-tool" state="output-available" toolName={toolName} />
        <ToolContent>
          {code ? (
            <CodeBlock code={code} language="python" />
          ) : (
            <ToolInput input={parsedInput} />
          )}
        </ToolContent>
      </Tool>
    );
  }

  if (kind === "tool-return") {
    const toolName = part.tool_name as string;
    return (
      <Tool>
        <ToolHeader type="dynamic-tool" state="output-available" toolName={`${toolName} result`} />
        <ToolContent>
          <ToolOutput output={content} errorText={undefined as never} />
        </ToolContent>
      </Tool>
    );
  }

  const labelConfig = {
    "system-prompt": { label: "SYSTEM", icon: Settings, variant: "secondary" as const },
    "user-prompt": { label: "USER", icon: User, variant: "default" as const },
    "retry-prompt": { label: "RETRY", icon: RotateCcw, variant: "destructive" as const },
  }[kind] ?? { label: "TEXT", icon: MessageSquare, variant: "secondary" as const };

  const Icon = labelConfig.icon;

  const rendered = (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {normalizeMath(content)}
      </Markdown>
    </div>
  );

  return (
    <Card>
      <div className="py-2 px-3 flex items-center gap-2">
        <Icon className="size-3.5" />
        <Badge variant={labelConfig.variant} className="text-[11px]">{labelConfig.label}</Badge>
      </div>
      <CardContent className="pt-0 px-3 pb-3">
        {content.length > 1000 ? (
          <ScrollArea className="max-h-96">{rendered}</ScrollArea>
        ) : (
          rendered
        )}
      </CardContent>
    </Card>
  );
}

// -- Message as a ChainOfThought step --

function messageIcon(msg: Record<string, unknown>) {
  const parts = (msg.parts as Record<string, unknown>[]) ?? [];
  const kind = msg.kind as string;
  const isRequest = kind === "request";

  if (!isRequest) return MessageSquare;
  if (parts.some((p) => p.part_kind === "user-prompt")) return User;
  if (parts.some((p) => p.part_kind === "tool-return")) return Wrench;
  if (parts.some((p) => p.part_kind === "retry-prompt")) return RotateCcw;
  if (parts.some((p) => p.part_kind === "system-prompt")) return Settings;
  return Settings;
}

function messageLabel(msg: Record<string, unknown>) {
  const parts = (msg.parts as Record<string, unknown>[]) ?? [];
  const kind = msg.kind as string;
  if (kind !== "request") return "Model Response";
  if (parts.some((p) => p.part_kind === "user-prompt")) return "User";
  if (parts.some((p) => p.part_kind === "tool-return")) return "Tool Result";
  if (parts.some((p) => p.part_kind === "retry-prompt")) return "Retry";
  return "Request";
}

function MessageStep({
  msg,
  index,
  total,
}: {
  msg: Record<string, unknown>;
  index: number;
  total: number;
}) {
  const parts = (msg.parts as Record<string, unknown>[]) ?? [];
  const usage = msg.usage as Record<string, number> | null;
  const icon = messageIcon(msg);
  const label = messageLabel(msg);

  const tokens = usage
    ? `in: ${usage.input_tokens ?? 0} · out: ${usage.output_tokens ?? 0}`
    : null;

  const hasTool = parts.some((p) => p.part_kind === "tool-call" || p.part_kind === "tool-return");
  const hasThinking = parts.some((p) => p.part_kind === "thinking");

  const description = (
    <span className="flex items-center gap-1.5">
      <Badge variant="secondary" className="text-[10px] font-normal">{index + 1}/{total}</Badge>
      {tokens && (
        <Tooltip>
          <TooltipTrigger>
            <Badge variant="outline" className="text-[10px] tabular-nums font-normal">{tokens}</Badge>
          </TooltipTrigger>
          <TooltipContent>Token usage</TooltipContent>
        </Tooltip>
      )}
      {hasThinking && <Brain className="size-3 text-muted-foreground" />}
      {hasTool && <Wrench className="size-3 text-muted-foreground" />}
    </span>
  );

  return (
    <ChainOfThoughtStep icon={icon} label={label} description={description} status="complete">
      <div className="space-y-2 mt-2">
        {parts.map((p, i) => (
          <PartView key={i} part={p} />
        ))}
      </div>
    </ChainOfThoughtStep>
  );
}

// -- Status badge --

function StatusBadge({ correct, hasError }: { correct: boolean | null; hasError: boolean }) {
  if (hasError)
    return <Badge variant="outline" className="gap-1"><AlertTriangle className="size-3" /> ERROR</Badge>;
  if (correct === true)
    return <Badge variant="default" className="gap-1 bg-green-600"><CheckCircle2 className="size-3" /> CORRECT</Badge>;
  if (correct === false)
    return <Badge variant="destructive" className="gap-1"><XCircle className="size-3" /> WRONG</Badge>;
  return <Badge variant="secondary" className="gap-1"><Clock className="size-3" /> PENDING</Badge>;
}

// -- Error display --

function ErrorDisplay({ error }: { error: string }) {
  const hasStackFrames = error.includes("\n") && error.includes("at ");

  if (hasStackFrames) {
    return (
      <StackTrace trace={error} defaultOpen={false}>
        <StackTraceHeader>
          <StackTraceError>
            <StackTraceErrorType />
            <StackTraceErrorMessage />
          </StackTraceError>
          <StackTraceActions>
            <StackTraceCopyButton />
            <StackTraceExpandButton />
          </StackTraceActions>
        </StackTraceHeader>
        <StackTraceContent>
          <StackTraceFrames showInternalFrames={false} />
        </StackTraceContent>
      </StackTrace>
    );
  }

  return (
    <Alert variant="destructive">
      <AlertTriangle className="size-4" />
      <AlertTitle>Error</AlertTitle>
      <AlertDescription className="font-mono text-xs">{error}</AlertDescription>
    </Alert>
  );
}

// -- Main detail component --

export function AgentRunDetail({
  dbPath,
  runKey,
}: {
  dbPath: string;
  runKey: string;
}) {
  const { data, isLoading, error } = usePluginDetail(dbPath, runKey);

  if (isLoading)
    return (
      <div className="flex-1 p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-20 w-full rounded-xl" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );

  if (error || !data)
    return (
      <div className="flex-1 p-6">
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertTitle>Error loading run</AlertTitle>
          <AlertDescription>{error?.message ?? "Run data not available"}</AlertDescription>
        </Alert>
      </div>
    );

  const { row, messages } = data.data as {
    row: Record<string, unknown>;
    messages: Record<string, unknown>[];
  };
  const metadata = row.metadata as Record<string, unknown> | null;
  const output = row.output as Record<string, unknown> | null;
  const correct = row.correct as boolean | null;
  const hasError = !!row.error;

  return (
    <ScrollArea className="flex-1 h-full">
      <div className="p-6 max-w-4xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <h1 className="font-mono text-lg font-semibold">Run {runKey}</h1>
          <Badge variant="secondary" className="text-xs font-normal">
            {messages.length} messages
          </Badge>
        </div>

        {/* Summary card */}
        <Card className="mb-6">
          <CardContent className="py-3 space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <StatusBadge correct={correct} hasError={hasError} />
              {metadata?.slug != null && (
                <span className="text-sm">
                  <span className="text-muted-foreground">slug: </span>
                  <code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{String(metadata.slug)}</code>
                </span>
              )}
            </div>
            <Separator />
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Expected</span>
              <code className="font-mono font-semibold bg-muted px-1.5 py-0.5 rounded text-xs">
                {metadata?.answer != null ? String(metadata.answer) : "—"}
              </code>
              <span className="text-muted-foreground/50">→</span>
              <span className="text-muted-foreground">Response</span>
              <code className={cn(
                "font-mono font-semibold px-1.5 py-0.5 rounded text-xs",
                correct === true && "bg-green-500/10 text-green-600",
                correct === false && "bg-red-500/10 text-red-600",
                correct == null && "bg-muted",
              )}>
                {output?.answer != null ? String(output.answer) : "—"}
              </code>
            </div>
            {hasError && row.error && (
              <>
                <Separator />
                <ErrorDisplay error={String(row.error)} />
              </>
            )}
          </CardContent>
        </Card>

        {/* Message timeline */}
        <ChainOfThought defaultOpen={true}>
          <ChainOfThoughtHeader>
            {messages.length} messages · execution trace
          </ChainOfThoughtHeader>
          <ChainOfThoughtContent>
            {messages.map((msg, i) => (
              <MessageStep key={i} msg={msg} index={i} total={messages.length} />
            ))}
          </ChainOfThoughtContent>
        </ChainOfThought>
      </div>
    </ScrollArea>
  );
}
