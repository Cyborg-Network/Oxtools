import { NextRequest, NextResponse } from "next/server";
import { createToolRoute } from "@/lib/create-tool-route";
import { getToolById } from "@/lib/tools/registry";
// Issue 5: maxDuration is set to 600s (10 minutes).
// We align the AbortController timeout to match this limit exactly,
// so that requests gracefully abort rather than hanging when Vercel kills the function.
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

async function proxyToToolRunner(request: NextRequest, toolId: string) {
  const runnerUrl = process.env.TOOL_RUNNER_URL || "http://localhost:9080";
  const targetUrl = `${runnerUrl}/api/tools/${toolId}`;
  const body        = await request.text();
  const contentType = request.headers.get("content-type") || "application/json";

  // Issue 5: Match the Vercel function timeout (maxDuration = 600s)
  const controller = new AbortController();
  const timeoutId  = setTimeout(() => controller.abort(), 600_000);

  try {
    // Issue 6: Replace http.request with fetch for protocol awareness (HTTPS support)
    const response = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": contentType,
      },
      body,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const resContentType = response.headers.get("content-type") || "application/json";

    if (!response.ok) {
      const errBody = await response.text();
      return NextResponse.json(
        { error: `Tool runner error: ${errBody}`, code: "runner_error" },
        { status: response.status }
      );
    }

    // Issue 7: Restore streaming for text/plain
    if (resContentType.includes("text/plain")) {
      return new Response(response.body, {
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    const responseText = await response.text();
    let data;
    try {
      // Issue 8: Wrap JSON.parse in try-catch
      data = JSON.parse(responseText);
    } catch {
      return NextResponse.json(
        { error: `Tool runner returned non-JSON: ${responseText.substring(0, 200)}`, code: "proxy_error" },
        { status: 502 }
      );
    }
    
    return NextResponse.json(data.result !== undefined ? data.result : data);

  } catch (error: any) {
    clearTimeout(timeoutId);

    if (error.name === "AbortError") {
      console.error(`[Tool Runner Proxy] 10-minute timeout for ${toolId}`);
      return NextResponse.json(
        { error: "Pipeline timed out after 10 minutes.", code: "timeout_10m" },
        { status: 504 }
      );
    }

    if (error.cause?.code === "ECONNREFUSED" || error.code === "ECONNREFUSED") {
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