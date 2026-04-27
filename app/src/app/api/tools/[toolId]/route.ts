import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { createToolRoute } from "@/lib/create-tool-route";
import { getToolById } from "@/lib/tools/registry";

// Allow long-running tool executions (up to 5 min locally, 300s on Vercel)
export const maxDuration = 300;

/**
 * Dynamic API route for ALL tools.
 *
 * TIER 1: Dispatches to createToolRoute (calls Oxlo LLM API directly).
 * TIER 2: Proxies to the unified Python tool runner on port 9080.
 *
 * The unified runner handles ALL Python tools on ONE port.
 * Route: POST http://localhost:9080/api/tools/{toolId}
 */
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

	// --- Tier 2: Proxy to unified Python tool runner ---
	if (tool.tier === "tier2") {
		return proxyToToolRunner(request, toolId);
	}

	// --- Tier 1: Handle via LLM prompt (default) ---
	const handler = createToolRoute({
		requiredFields: tool.requiredFields,
		buildSystemPrompt: tool.buildSystemPrompt,
		buildUserPrompt: tool.buildUserPrompt,
		defaultModel: tool.defaultModel,
		errorMessage: `Failed to execute ${tool.name}`,
	});

	return handler(request);
}

/**
 * Proxy a request to the unified Python tool runner.
 *
 * ALL Tier 2 tools run on ONE service (port 9080) via:
 *   POST http://runner:9080/api/tools/{toolId}
 *
 * No more port-per-tool. One port, one container, unlimited tools.
 */
async function proxyToToolRunner(request: NextRequest, toolId: string) {
	const runnerUrl = process.env.TOOL_RUNNER_URL || "http://localhost:9080";
	const targetUrl = `${runnerUrl}/api/tools/${toolId}`;

	try {
		const body = await request.text();
		const contentType = request.headers.get("content-type") || "application/json";

		// 10 minute timeout — security scans with LLM retries can take 5-10 min
		const response = await fetch(targetUrl, {
			method: "POST",
			headers: { "Content-Type": contentType },
			body,
			signal: AbortSignal.timeout(600_000),
		});

		if (!response.ok) {
			const errorText = await response.text();
			return NextResponse.json(
				{ error: `Tool runner error: ${errorText}`, code: "runner_error" },
				{ status: response.status }
			);
		}

		// Stream text/plain responses (for agents with progress updates)
		const respContentType = response.headers.get("content-type") || "";
		if (respContentType.includes("text/plain") && response.body) {
			// CRITICAL: Actively pipe chunks through a new ReadableStream.
			// Passing response.body directly causes Next.js to silently close
			// long-lived streams after ~30s due to internal buffering.
			const upstream = response.body;
			const stream = new ReadableStream({
				async start(controller) {
					const reader = upstream.getReader();
					try {
						while (true) {
							const { done, value } = await reader.read();
							if (done) break;
							controller.enqueue(value);
						}
						controller.close();
					} catch (err) {
						console.error("[Stream Proxy] Error piping:", err);
						controller.close();
					}
				},
			});

			return new Response(stream, {
				headers: {
					"Content-Type": "text/plain; charset=utf-8",
					"Transfer-Encoding": "chunked",
					"X-Accel-Buffering": "no",
					"Cache-Control": "no-cache",
				},
			});
		}

		// JSON responses
		const data = await response.json();
		if (data.result) {
			return NextResponse.json(data.result);
		}
		return NextResponse.json(data);
	} catch (error) {
		console.error(`[Tool Runner] Failed to reach ${targetUrl}:`, error);
		return NextResponse.json(
			{
				error:
					"The Python tool runner is not running. Start it with: docker compose -f docker-compose.dev.yml up --build",
				code: "runner_unavailable",
			},
			{ status: 503 }
		);
	}
}
