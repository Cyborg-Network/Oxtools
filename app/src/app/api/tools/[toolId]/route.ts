import { type NextRequest, NextResponse } from "next/server";
import { createToolRoute } from "@/lib/create-tool-route";
import { getToolById } from "@/lib/tools/registry";
// Issue 5: maxDuration is set to 300s (5 minutes).
// We align the AbortController timeout to match this limit exactly,
// so that requests gracefully abort rather than hanging when Vercel kills the function.
export const maxDuration = 300;
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

	try {
		const body = await request.text();
		const contentType = request.headers.get("content-type") || "application/json";

		// 5 minute timeout — security scans with LLM retries can take 5 min
		const response = await fetch(targetUrl, {
			method: "POST",
			headers: { "Content-Type": contentType },
			body,
			signal: AbortSignal.timeout(300_000),
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
