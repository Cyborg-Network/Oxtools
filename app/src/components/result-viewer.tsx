"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Button, Card, CardContent, Spinner } from "@ansospace/ui";
import {
  AlertCircle,
  Check,
  Copy,
  Download,
  ExternalLink,
  Key,
  Lock,
  ShieldAlert,
  Sparkles,
  Timer,
} from "lucide-react";
import mermaid from "mermaid";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
});

function MermaidViewer({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    (async () => {
      try {
        const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg: generatedSvg } = await mermaid.render(id, chart);
        if (isMounted) setSvg(generatedSvg);
        setError(null);
      } catch (err: any) {
        if (isMounted) setError(err.message || "Error rendering Mermaid chart");
      }
    })();
    return () => {
      isMounted = false;
    };
  }, [chart]);

  if (error) {
    return (
      <div className="my-4 rounded-md border border-destructive/20 bg-destructive/10 p-4 text-xs font-mono text-destructive overflow-auto">
        <strong>Mermaid Syntax Error:</strong>
        <br />
        {error}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="mermaid-wrapper my-6 flex items-center justify-center overflow-auto rounded-lg border border-border bg-zinc-950 dark:bg-zinc-900 p-6"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

import type { ToolError } from "@/hooks/use-tool-execution";

interface ResultViewerProps {
  result: string;
  isLoading?: boolean;
  error?: ToolError | string | null;
  streaming?: boolean;
  onOpenSettings?: () => void;
}

const ERROR_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  model_access_denied: {
    icon: <Lock className="h-5 w-5" />,
    label: "Model Access Denied",
    color: "text-amber-600 dark:text-amber-400",
  },
  rate_limit_exceeded: {
    icon: <Timer className="h-5 w-5" />,
    label: "Rate Limit Exceeded",
    color: "text-amber-600 dark:text-amber-400",
  },
  unauthorized: {
    icon: <ShieldAlert className="h-5 w-5" />,
    label: "Unauthorized",
    color: "text-red-600 dark:text-red-400",
  },
  insufficient_quota: {
    icon: <AlertCircle className="h-5 w-5" />,
    label: "Quota Exhausted",
    color: "text-red-600 dark:text-red-400",
  },
  service_unavailable: {
    icon: <AlertCircle className="h-5 w-5" />,
    label: "Service Unavailable",
    color: "text-orange-600 dark:text-orange-400",
  },
};

function ErrorDisplay({
  error,
  onOpenSettings,
}: {
  error: ToolError;
  onOpenSettings?: () => void;
}) {
  const config = ERROR_CONFIG[error.code || ""] || {
    icon: <AlertCircle className="h-5 w-5" />,
    label: "Error",
    color: "text-destructive",
  };

  const isKeyRelated =
    error.code === "model_access_denied" ||
    error.code === "rate_limit_exceeded" ||
    error.code === "unauthorized" ||
    error.code === "insufficient_quota";

  return (
    <Card className="border-destructive/30 bg-destructive/5">
      <CardContent className="py-5">
        <div className="flex items-start gap-3">
          <div className={`mt-0.5 shrink-0 ${config.color}`}>{config.icon}</div>
          <div className="min-w-0 flex-1 space-y-3">
            {/* Error header */}
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-semibold ${config.color}`}>{config.label}</span>
                {error.code && (
                  <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                    {error.code}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-foreground/90">{error.message}</p>
            </div>

            {/* Action hint */}
            {error.action && (
              <div className="rounded-md border border-border/60 bg-muted/50 p-3 text-xs leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">💡 What to do: </span>
                {error.action}
              </div>
            )}

            {/* Action buttons */}
            {isKeyRelated && (
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (onOpenSettings) {
                      onOpenSettings();
                    } else {
                      window.dispatchEvent(new CustomEvent("open-settings"));
                    }
                  }}
                  className="h-8 gap-1.5 text-xs"
                >
                  <Key className="h-3.5 w-3.5" />
                  Add API Key
                </Button>
                <a href="https://portal.oxlo.ai/signup" target="_blank" rel="noopener noreferrer">
                  <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs">
                    Get Free Key
                    <ExternalLink className="h-3 w-3" />
                  </Button>
                </a>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CopyButton({ text }: { text: string }) {
  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(text);
    const btn = document.activeElement as HTMLButtonElement;
    if (btn) {
      btn.dataset.copied = "true";
      setTimeout(() => {
        btn.dataset.copied = "false";
      }, 2000);
    }
  }, [text]);

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="absolute top-2 right-2 rounded-md bg-muted/80 p-1.5 text-muted-foreground opacity-0 backdrop-blur-sm transition-all hover:bg-muted hover:text-foreground group-hover/code:opacity-100 data-[copied=true]:text-green-500"
      data-copied="false"
    >
      <Copy className="h-3.5 w-3.5 data-[copied=true]:hidden" />
      <Check className="hidden h-3.5 w-3.5 data-[copied=true]:block" />
    </button>
  );
}

export function ResultViewer({
  result,
  isLoading,
  error,
  streaming,
  onOpenSettings,
}: ResultViewerProps) {
  const [copiedAll, setCopiedAll] = useState(false);
  const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");

  const handleCopyAll = useCallback(async () => {
    await navigator.clipboard.writeText(result);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  }, [result]);

  const handleDownload = useCallback(() => {
    const blob = new Blob([result], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `devkernel-ai-result-${Date.now()}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [result]);

  if (error) {
    // Normalize string errors to ToolError shape
    const toolError: ToolError = typeof error === "string" ? { message: error } : error;
    return <ErrorDisplay error={toolError} onOpenSettings={onOpenSettings} />;
  }

  if (isLoading && !result) {
    return (
      <Card className="border-primary/20 bg-primary/[0.02]">
        <CardContent className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3">
            <div className="relative">
              <Spinner className="h-6 w-6 text-primary" />
              <Sparkles className="absolute -top-1 -right-1 h-3 w-3 animate-pulse text-primary" />
            </div>
            <span className="text-sm font-medium text-muted-foreground">AI is thinking...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-12 text-center">
          <div className="flex flex-col items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
              <Sparkles className="h-5 w-5 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">Results will appear here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  let parsedJson: { code?: string; [key: string]: any } | null = null;
  let displayMarkdown = result;
  
  if (result) {
    try {
      const trimmed = result.trim();
      if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
        const parsed = JSON.parse(trimmed);
        if (typeof parsed.code === "string") {
          parsedJson = parsed;
          displayMarkdown = `\`\`\`html\n${parsed.code}\n\`\`\``;
        }
      }
    } catch (e) {
      // Ignore parsing errors
    }

    // Fallback: Check if the result embeds a standalone HTML block in markdown
    if (!parsedJson) {
      const htmlBlockRegex = /```(?:html)?\s*(<!DOCTYPE html>[\s\S]*?<html[\s\S]*?)```/i;
      const match = result.trim().match(htmlBlockRegex);
      if (match && match[1]) {
        parsedJson = { code: match[1] };
      } else if (result.trim().startsWith("<!DOCTYPE html>") || result.trim().startsWith("<html")) {
        parsedJson = { code: result.trim() };
      }
    }
  }

  const hasHtmlCode = !!(parsedJson?.code && (parsedJson.code.includes("<!DOCTYPE html>") || parsedJson.code.includes("<html")));

  return (
    <Card className="overflow-hidden relative">
      <div
        className="absolute top-3 right-3 flex items-center gap-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity hover:opacity-100"
        style={{ opacity: 1 }}
      >
        <Button
          variant="outline"
          size="sm"
          onClick={handleCopyAll}
          className="h-8 text-xs bg-background/80 backdrop-blur-sm"
        >
          {copiedAll ? (
            <Check className="h-3.5 w-3.5 mr-1" />
          ) : (
            <Copy className="h-3.5 w-3.5 mr-1" />
          )}
          Copy
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownload}
          className="h-8 text-xs bg-background/80 backdrop-blur-sm"
        >
          <Download className="h-3.5 w-3.5 mr-1" />
          Download
        </Button>
      </div>

      {hasHtmlCode && (
        <div className="flex border-b border-border/50 px-4 pt-3 bg-muted/20">
          <button
            onClick={() => setActiveTab("preview")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "preview"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Preview
          </button>
          <button
            onClick={() => setActiveTab("code")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "code"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Code
          </button>
        </div>
      )}

      <CardContent className="pt-10 pb-6 relative">
        <article
          className={[
            // Base prose
            "prose prose-sm dark:prose-invert max-w-none",
            // Headings
            "prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-foreground",
            "prose-h1:text-xl prose-h1:mt-6 prose-h1:mb-4",
            "prose-h2:text-lg prose-h2:mt-6 prose-h2:mb-3 prose-h2:border-b prose-h2:border-border prose-h2:pb-2",
            "prose-h3:text-base prose-h3:mt-5 prose-h3:mb-2",
            // Paragraphs & text
            "prose-p:text-foreground/90 prose-p:leading-7 prose-p:my-3",
            "prose-strong:text-foreground prose-strong:font-semibold",
            "prose-em:text-foreground/80",
            // Links
            "prose-a:text-primary prose-a:underline prose-a:underline-offset-4 prose-a:decoration-primary/40 hover:prose-a:decoration-primary",
            // Lists
            "prose-li:text-foreground/90 prose-li:my-1 prose-li:leading-7",
            "prose-ul:my-3 prose-ul:pl-6 prose-ol:my-3 prose-ol:pl-6",
            // Inline code
            "prose-code:rounded-md prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[13px] prose-code:font-mono prose-code:font-medium",
            "prose-code:before:content-none prose-code:after:content-none",
            // Code blocks
            "prose-pre:rounded-lg prose-pre:border prose-pre:border-border prose-pre:bg-zinc-950 dark:prose-pre:bg-zinc-900",
            "prose-pre:px-4 prose-pre:py-4 prose-pre:my-4",
            // Blockquotes
            "prose-blockquote:border-l-primary/50 prose-blockquote:bg-muted/30 prose-blockquote:rounded-r-lg prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:my-4",
            "prose-blockquote:text-foreground/80 prose-blockquote:not-italic",
            // Tables
            "prose-th:text-foreground prose-th:font-semibold prose-th:text-left prose-th:px-3 prose-th:py-2",
            "prose-td:text-foreground/90 prose-td:px-3 prose-td:py-2",
            "prose-table:my-4",
            // Horizontal rules
            "prose-hr:border-border prose-hr:my-6",
            // Images
            "prose-img:rounded-lg prose-img:my-4",
            "prose-img:rounded-lg prose-img:my-4",
          ].join(" ")}
        >
          {activeTab === "preview" && hasHtmlCode ? (
            <div className="w-full h-[600px] rounded-lg border border-border bg-white overflow-hidden -mt-4 relative z-0">
              <iframe
                title="Preview"
                srcDoc={parsedJson?.code}
                className="w-full h-full border-0 absolute inset-0 bg-white"
                sandbox="allow-scripts"
              />
            </div>
          ) : (
            <>
              <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              pre({ children, ...props }) {
                let codeText = "";
                try {
                  const child = children as unknown as {
                    props?: { children?: unknown };
                  };
                  codeText = child?.props?.children
                    ? String(child.props.children)
                    : String(children || "");
                } catch {
                  codeText = String(children || "");
                }
                return (
                  <div className="group/code relative my-4">
                    <CopyButton text={codeText} />
                    <pre
                      className="overflow-x-auto rounded-lg border border-border bg-zinc-950 px-4 py-4 text-sm leading-relaxed text-zinc-100 dark:bg-zinc-900"
                      {...props}
                    >
                      {children}
                    </pre>
                  </div>
                );
              },
              code({ className, children, ...props }) {
                const isInline = !className;
                if (isInline) {
                  return (
                    <code
                      className="rounded-md bg-muted px-1.5 py-0.5 text-[13px] font-mono font-medium text-foreground"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                }

                const isMermaid = className?.includes("language-mermaid");
                if (isMermaid) {
                  return <MermaidViewer chart={String(children)} />;
                }

                return (
                  <code className={`${className || ""} text-sm leading-relaxed text-zinc-100`} {...props}>
                    {children}
                  </code>
                );
              },
              table({ children, ...props }) {
                return (
                  <div className="my-4 overflow-x-auto rounded-lg border border-border">
                    <table className="w-full text-sm" {...props}>
                      {children}
                    </table>
                  </div>
                );
              },
              thead({ children, ...props }) {
                return (
                  <thead className="border-b border-border bg-muted/50" {...props}>
                    {children}
                  </thead>
                );
              },
              th({ children, ...props }) {
                return (
                  <th
                    className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-foreground"
                    {...props}
                  >
                    {children}
                  </th>
                );
              },
              td({ children, ...props }) {
                return (
                  <td className="border-t border-border px-4 py-2.5 text-foreground/90" {...props}>
                    {children}
                  </td>
                );
              },
              blockquote({ children, ...props }) {
                return (
                  <blockquote
                    className="my-4 rounded-r-lg border-l-4 border-l-primary/50 bg-muted/30 py-2 px-4 text-foreground/80 [&>p]:my-1"
                    {...props}
                  >
                    {children}
                  </blockquote>
                );
              },
              ul({ children, ...props }) {
                return (
                  <ul className="my-3 list-disc space-y-1.5 pl-6" {...props}>
                    {children}
                  </ul>
                );
              },
              ol({ children, ...props }) {
                return (
                  <ol className="my-3 list-decimal space-y-1.5 pl-6" {...props}>
                    {children}
                  </ol>
                );
              },
              li({ children, ...props }) {
                return (
                  <li className="leading-7 text-foreground/90" {...props}>
                    {children}
                  </li>
                );
              },
              h1({ children, ...props }) {
                return (
                  <h1
                    className="mt-6 mb-4 text-xl font-semibold tracking-tight text-foreground"
                    {...props}
                  >
                    {children}
                  </h1>
                );
              },
              h2({ children, ...props }) {
                return (
                  <h2
                    className="mt-6 mb-3 border-b border-border pb-2 text-lg font-semibold tracking-tight text-foreground"
                    {...props}
                  >
                    {children}
                  </h2>
                );
              },
              h3({ children, ...props }) {
                return (
                  <h3
                    className="mt-5 mb-2 text-base font-semibold tracking-tight text-foreground"
                    {...props}
                  >
                    {children}
                  </h3>
                );
              },
              p({ children, ...props }) {
                return (
                  <p className="my-3 leading-7 text-foreground/90" {...props}>
                    {children}
                  </p>
                );
              },
              hr() {
                return <hr className="my-6 border-border" />;
              },
              a({ children, href, ...props }) {
                return (
                  <a
                    href={href}
                    className="text-primary underline underline-offset-4 decoration-primary/40 hover:decoration-primary"
                    target="_blank"
                    rel="noopener noreferrer"
                    {...props}
                  >
                    {children}
                  </a>
                );
              },
            }}
          >
              {displayMarkdown}
            </ReactMarkdown>
            {streaming && isLoading && (
              <span className="mt-1 inline-block h-5 w-1.5 animate-pulse rounded-sm bg-primary" />
            )}
            
            {parsedJson && Object.keys(parsedJson).filter(k => k !== 'code').length > 0 && activeTab === "code" && (
              <div className="mt-8 pt-4 border-t border-border">
                <h4 className="text-sm font-semibold mb-3 text-foreground" style={{ fontFamily: "var(--font-unbounded), sans-serif" }}>Additional Context</h4>
                <pre className="text-xs bg-zinc-950 dark:bg-zinc-900 border border-border text-zinc-100 p-4 rounded-lg overflow-auto font-mono">
                  {JSON.stringify(
                    Object.fromEntries(Object.entries(parsedJson).filter(([k]) => k !== 'code')),
                    null,
                    2
                  )}
                </pre>
              </div>
            )}
            </>
          )}
        </article>
      </CardContent>
    </Card>
  );
}
