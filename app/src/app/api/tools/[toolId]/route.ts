import { NextRequest, NextResponse } from "next/server";
import { createToolRoute } from "@/lib/create-tool-route";
import { getToolById } from "@/lib/tools/registry";
import http from "node:http";

// ─── No execution time cap — pipeline runs as long as it needs ───────────────
export const maxDuration = 600;
export const dynamic = "force-dynamic";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ toolId: string }> }
) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  if (!tool || tool.status !== "active") {
    return NextResponse.json(
      { error: `Tool "${toolId}" not found or not active.`, code: "not_found" },
      { status: 404 }
    );
  }

  if (tool.tier === "tier2") {
    return proxyToToolRunner(request, toolId);
  }

  const handler = createToolRoute({
    requiredFields: tool.requiredFields,
    buildSystemPrompt: tool.buildSystemPrompt,
    buildUserPrompt: tool.buildUserPrompt,
    defaultModel: tool.defaultModel,
    errorMessage: `Failed to execute ${tool.name}`,
  });
  return handler(request);
}

// ─────────────────────────────────────────────────────────────────────────────
// WHY node:http INSTEAD OF fetch()
//
// Next.js 15/16 App Router patches global fetch() with its own caching layer.
// That patched fetch does NOT support the Undici `dispatcher` option — passing
// a custom Agent throws UND_ERR_INVALID_ARG: "invalid onRequestStart method".
// The patched fetch also has an internal 5-minute (300s) headers timeout baked
// in that cannot be overridden from userland.
//
// node:http.request() bypasses all of this. It is the raw Node.js primitive,
// gives us direct socket timeout control, and needs zero extra dependencies.
// We set timeout to 36000s (10 hours) — the pipeline itself will finish long
// before that. The AbortController at 3600s is the actual safety net.
// ─────────────────────────────────────────────────────────────────────────────
function proxyViaNodeHttp(
  targetUrl: string,
  body: string,
  contentType: string,
  signal: AbortSignal
): Promise<{ status: number; contentType: string; body: string }> {
  return new Promise((resolve, reject) => {
    const url = new URL(targetUrl);

    const req = http.request(
      {
        hostname: url.hostname,
        port:     url.port || 80,
        path:     url.pathname + url.search,
        method:   "POST",
        headers: {
          "Content-Type":   contentType,
          "Content-Length": Buffer.byteLength(body),
        },
        // 1 hour socket timeout — pipeline will always finish before this.
        // This exists only to prevent zombie connections if the Docker
        // container crashes mid-run without sending a response.
        timeout: 3_600_000,
      },
      (res) => {
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => chunks.push(chunk));
        res.on("end", () => {
          resolve({
            status:      res.statusCode ?? 500,
            contentType: res.headers["content-type"] ?? "application/json",
            body:        Buffer.concat(chunks).toString("utf-8"),
          });
        });
        res.on("error", reject);
      }
    );

    // AbortController wires into socket destruction
    signal.addEventListener("abort", () => {
      req.destroy();
      reject(Object.assign(new Error("Request aborted"), { name: "AbortError" }));
    });

    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Node http socket timeout — Docker container may have crashed"));
    });

    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

async function proxyToToolRunner(request: NextRequest, toolId: string) {
  const runnerUrl = process.env.TOOL_RUNNER_URL || "http://localhost:9080";
  const targetUrl = `${runnerUrl}/api/tools/${toolId}`;
  const body        = await request.text();
  const contentType = request.headers.get("content-type") || "application/json";

  // 1-hour abort controller — lets the Python pipeline run as long as it needs.
  // The pipeline itself has its own internal step timeouts in tool.py.
  const controller = new AbortController();
  const timeoutId  = setTimeout(() => controller.abort(), 3_600_000);

  try {
    const response = await proxyViaNodeHttp(
      targetUrl,
      body,
      contentType,
      controller.signal
    );

    clearTimeout(timeoutId);

    if (response.status < 200 || response.status >= 300) {
      return NextResponse.json(
        { error: `Tool runner error: ${response.body}`, code: "runner_error" },
        { status: response.status }
      );
    }

    if (response.contentType.includes("text/plain")) {
      return new Response(response.body, {
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    const data = JSON.parse(response.body);
    return NextResponse.json(data.result ?? data);

  } catch (error: any) {
    clearTimeout(timeoutId);

    if (error.name === "AbortError") {
      console.error(`[Tool Runner Proxy] 1-hour timeout for ${toolId}`);
      return NextResponse.json(
        { error: "Pipeline timed out after 1 hour.", code: "timeout_1h" },
        { status: 504 }
      );
    }

    if (error.code === "ECONNREFUSED") {
      console.error(`[Tool Runner Proxy] Runner offline at ${targetUrl}`);
      return NextResponse.json(
        {
          error: "The Python tool runner is offline. Start it with: docker compose up",
          code:  "runner_unavailable",
        },
        { status: 503 }
      );
    }

    console.error(`[Tool Runner Proxy] Unhandled error for ${toolId}:`, error);
    return NextResponse.json(
      { error: `Connection failed: ${error.message || "Unknown error"}`, code: "proxy_error" },
      { status: 500 }
    );
  }
}