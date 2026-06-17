import { type NextRequest, NextResponse } from "next/server";
import { createToolRoute } from "@/lib/create-tool-route";
import { generateImage, type OxloImageResponse } from "@/lib/oxlo";
import { getToolById } from "@/lib/tools/registry";

export const maxDuration = 300;
export const dynamic = "force-dynamic";

/** Prompt builder — matches agents.py _build_architecture_image_prompt() */
function buildFluxPrompt(description: string): string {
	return (
		"Professional modern cloud architecture diagram based on: " +
		`${description}. ` +
		"Clean arrows, engineering infographic style, readable labels, " +
		"white background, polished Canva/Figma design, 16:9."
	);
}

/** Deep-serialize an OpenAI SDK APIError or any error for structured logging. */
function serializeError(err: unknown): Record<string, unknown> {
	if (!err || typeof err !== "object") return { message: String(err) };
	const e = err as Record<string, unknown>;
	const innerBody = e.error as Record<string, unknown> | undefined;

	let headersRecord: Record<string, string> | undefined;
	try {
		if (e.headers && typeof (e.headers as Record<string, unknown>).entries === "function") {
			headersRecord = {};
			for (const [k, v] of (e.headers as Headers).entries()) headersRecord[k] = v;
		}
	} catch { /* not iterable */ }

	return {
		message:         typeof e.message === "string" ? e.message : String(err),
		status:          e.status    ?? undefined,
		code:            e.code      ?? innerBody?.error ?? undefined,
		type:            e.type      ?? innerBody?.type  ?? undefined,
		requestID:       e.requestID ?? undefined,
		providerMessage: innerBody?.message      ?? undefined,
		requiredPlan:    innerBody?.required_plan ?? undefined,
		dailyLimit:      innerBody?.daily_limit   ?? undefined,
		providerBody:    innerBody  ?? undefined,
		headers:         headersRecord,
	};
}

/** Translate a Flux/Oxlo error into a structured, user-actionable response. */
function parseFluxError(err: unknown, model: string): {
	httpStatus: number; code: string; message: string; action: string;
	detail: Record<string, unknown>;
} {
	const detail    = serializeError(err);
	const status    = (detail.status      as number | undefined) ?? 500;
	const inner     = (detail.providerBody as Record<string, unknown> | undefined) ?? {};
	const errorType = (inner.error         as string | undefined) ?? (detail.code as string | undefined) ?? "";
	const reqPlan   = (inner.required_plan  as string | undefined);

	console.error("[oxlo-raw-error]", {
		model, status, errorType,
		requiredPlan:    reqPlan,
		providerMessage: detail.providerMessage,
		requestID:       detail.requestID,
		headers:         detail.headers,
		providerBody:    inner,
		sdkMessage:      detail.message,
	});

	if (errorType === "model_access_denied" || status === 403) return {
		httpStatus: 403, code: "model_access_denied",
		message: `flux.1-schnell requires ${reqPlan ? `a ${reqPlan} plan` : "a higher plan"}. Your current plan does not include image generation access.`,
		action:  "Add an Oxlo API key with image generation access in Settings, or upgrade at portal.oxlo.ai.",
		detail,
	};
	if (status === 401) return {
		httpStatus: 401, code: "unauthorized",
		message: "Invalid or missing API key for Oxlo image generation.",
		action:  "Add a valid Oxlo API key in Settings. Get one free at portal.oxlo.ai/signup.",
		detail,
	};
	if (errorType === "rate_limit_exceeded" || status === 429) return {
		httpStatus: 429, code: "rate_limit_exceeded",
		message: `Rate limit exceeded for ${model}.`,
		action:  "Wait a moment and retry, or add your own API key with higher limits in Settings.",
		detail,
	};
	if (status === 402 || errorType === "insufficient_quota") return {
		httpStatus: 402, code: "insufficient_quota",
		message: "API quota exhausted — no remaining image generation credits.",
		action:  "Add a different API key in Settings, or upgrade at portal.oxlo.ai.",
		detail,
	};
	return {
		httpStatus: status >= 400 ? status : 500,
		code:    errorType || "flux_error",
		message: (detail.message as string) || "Flux image generation failed.",
		action:  "Check server logs for [oxlo-raw-error] for the full provider response.",
		detail,
	};
}

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

	// ── Architecture Diagram: Flux ai_image intercept ────────────────────────
	if (toolId === "architecture-diagram") {
		let body: Record<string, string> = {};
		try { body = (await request.clone().json()) as Record<string, string>; } catch { /* empty */ }

		const requestedMode  = (body.generationMode || body.generation_mode || "").toLowerCase();
		const requestedModel = (body.model || "").toLowerCase();
		const resolvedMode   =
			requestedMode === "ai_image" || requestedModel.includes("flux")
				? "ai_image"
				: "svg_renderer";

		// ── Stage 0: resolve & log API key ────────────────────────────────────
		const headerKey = request.headers.get("x-api-key") ?? undefined;
		const envKey    = process.env.OXLO_API_KEY ?? undefined;

		console.info("[mode-resolved]", {
			requestedModel: body.model || tool.defaultModel,
			requestedMode,
			resolvedMode,
		});

		console.info("[api-key-source]", {
			hasHeaderKey: Boolean(headerKey),
			hasEnvKey:    Boolean(envKey),
			usingHeader:  Boolean(headerKey),
			usingEnv:     !headerKey && Boolean(envKey),
		});

		const resolvedApiKey = headerKey || envKey;

		if (resolvedMode === "ai_image") {
			if (!resolvedApiKey) {
				return NextResponse.json(
					{
						error:  "No API key available. Set OXLO_API_KEY in your .env file or add a key in Settings.",
						code:   "missing_api_key",
						action: "Add your Oxlo API key in Settings, or set OXLO_API_KEY in your .env file.",
					},
					{ status: 401 }
				);
			}

			console.info("[key-compare]", {
				model:     "flux.1-schnell",
				keyPrefix: resolvedApiKey.length > 8 ? `${resolvedApiKey.slice(0, 8)}...` : "***",
				source:    headerKey ? "header" : "env",
			});

			// ── Stage 1: build prompt ─────────────────────────────────────────
			let fluxPrompt = "";
			try {
				fluxPrompt = buildFluxPrompt(body.description || "");
			} catch (promptErr) {
				console.error("[flux-error]", { stage: "prompt_build", error: serializeError(promptErr) });
				return NextResponse.json(
					{ error: "Failed to build Flux prompt.", stage: "prompt_build", detail: serializeError(promptErr) },
					{ status: 500 }
				);
			}

			console.info("[flux-request]", {
				model:           "flux.1-schnell",
				size:            "1536x864",
				response_format: "b64_json",
				promptLength:    fluxPrompt.length,
				generation_mode: "ai_image",
			});

			// ── Stage 2: call Flux API ────────────────────────────────────────
			let imageResponse: OxloImageResponse;
			try {
				imageResponse = await generateImage(fluxPrompt, resolvedApiKey);
			} catch (fluxErr) {
				const parsed = parseFluxError(fluxErr, "flux.1-schnell");
				return NextResponse.json(
					{ error: parsed.message, code: parsed.code, action: parsed.action, stage: "flux_generate", model: "flux.1-schnell", detail: parsed.detail },
					{ status: parsed.httpStatus }
				);
			}

			// ── Stage 3: extract image ────────────────────────────────────────
			const firstImage = imageResponse.data?.[0];
			const b64    = firstImage?.b64_json ?? null;
			const imgUrl = firstImage?.url      ?? null;

			console.info("[flux-response]", {
				hasBase64:  Boolean(b64),
				hasUrl:     Boolean(imgUrl),
				dataLength: imageResponse.data?.length ?? 0,
			});

			const rawImage = b64 ?? imgUrl;
			if (!rawImage) {
				console.error("[flux-error]", { stage: "response_parse", error: "No b64_json or url in response" });
				return NextResponse.json(
					{ error: "Flux returned no image data.", stage: "response_parse" },
					{ status: 500 }
				);
			}

			const imageDataUri =
				rawImage.startsWith("data:") || rawImage.startsWith("http")
					? rawImage
					: `data:image/png;base64,${rawImage}`;

			return NextResponse.json({
				generation_mode: "ai_image",
				image_model:     "Flux.1 Schnell",
				output_type:     "image",
				image:           imageDataUri,
				image_prompt:    fluxPrompt,
				title: body.description
					? body.description.slice(0, 60) + (body.description.length > 60 ? "…" : "")
					: "Architecture Diagram",
			});
		}
	}

	if (tool.tier === "tier2") {
		return proxyToToolRunner(request, toolId);
	}

	const handler = createToolRoute({
		requiredFields:    tool.requiredFields,
		buildSystemPrompt: tool.buildSystemPrompt,
		buildUserPrompt:   tool.buildUserPrompt,
		defaultModel:      tool.defaultModel,
		errorMessage:      `Failed to execute ${tool.name}`,
	});
	return handler(request);
}

async function proxyToToolRunner(request: NextRequest, toolId: string) {
	const runnerUrl = process.env.TOOL_RUNNER_URL || "http://localhost:9080";
	const targetUrl = `${runnerUrl}/api/tools/${toolId}`;

	try {
		const body        = await request.text();
		const contentType = request.headers.get("content-type") || "application/json";

		const response = await fetch(targetUrl, {
			method:  "POST",
			headers: { "Content-Type": contentType },
			body,
			signal:  AbortSignal.timeout(300_000),
		});

		if (!response.ok) {
			const errorText = await response.text();
			return NextResponse.json(
				{ error: `Tool runner error: ${errorText}`, code: "runner_error" },
				{ status: response.status }
			);
		}

		const respContentType = response.headers.get("content-type") || "";
		if (respContentType.includes("text/plain") && response.body) {
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
					"Content-Type":      "text/plain; charset=utf-8",
					"Transfer-Encoding": "chunked",
					"X-Accel-Buffering": "no",
					"Cache-Control":     "no-cache",
				},
			});
		}

		const data = await response.json();
		if (data.result) return NextResponse.json(data.result);
		return NextResponse.json(data);
	} catch (error) {
		console.error(`[Tool Runner] Failed to reach ${targetUrl}:`, error);
		return NextResponse.json(
			{
				error: "The Python tool runner is not running. Start it with: docker compose -f docker-compose.dev.yml up --build",
				code:  "runner_unavailable",
			},
			{ status: 503 }
		);
	}
}
