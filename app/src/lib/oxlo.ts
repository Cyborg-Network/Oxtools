import OpenAI from "openai";

import { DEFAULT_IMAGE_MODEL } from "./models";

/** Mask a key for safe logging — show only the first 8 chars. */
function maskKey(key: string): string {
	return key.length > 8 ? `${key.slice(0, 8)}...` : "***";
}

/**
 * Resolve the API key and log its source.
 * Priority: x-api-key header → OXLO_API_KEY env → throw.
 */
export function resolveApiKey(headerKey?: string): { key: string; source: "header" | "env" } {
	const hasHeaderKey = Boolean(headerKey && headerKey.trim());
	const hasEnvKey    = Boolean(process.env.OXLO_API_KEY);

	console.info("[api-key-source]", {
		hasHeaderKey,
		hasEnvKey,
		usingHeader: hasHeaderKey,
		usingEnv:    !hasHeaderKey && hasEnvKey,
	});

	if (hasHeaderKey) return { key: headerKey!.trim(), source: "header" };
	if (hasEnvKey)    return { key: process.env.OXLO_API_KEY!, source: "env" };

	throw new Error(
		"OXLO_API_KEY is not set. Add it to your environment variables or pass an API key via the x-api-key header."
	);
}

/**
 * Get an Oxlo API client (used for LLM streaming calls only).
 */
function getOxloClient(apiKey?: string): OpenAI {
	const key = apiKey || process.env.OXLO_API_KEY || "";
	if (!key) {
		throw new Error(
			"OXLO_API_KEY is not set. Add it to your environment variables or pass an API key via the x-api-key header."
		);
	}
	return new OpenAI({ baseURL: "https://api.oxlo.ai/v1", apiKey: key });
}

export { AVAILABLE_MODELS, type ModelId } from "./models";

function buildMessages(prompt: string, systemPrompt?: string) {
	const messages: Array<{ role: "system" | "user"; content: string }> = [];
	if (systemPrompt) messages.push({ role: "system", content: systemPrompt });
	messages.push({ role: "user", content: prompt });
	return messages;
}

export async function generateCompletion(
	prompt: string,
	systemPrompt?: string,
	model: string = "llama-3.3-70b",
	apiKey?: string
): Promise<string> {
	const client = getOxloClient(apiKey);
	const response = await client.chat.completions.create({
		model,
		messages: buildMessages(prompt, systemPrompt),
		temperature: 0.7,
		max_tokens: 4096,
	});
	return response.choices[0]?.message?.content || "";
}

export async function generateStreamingCompletion(
	prompt: string,
	systemPrompt?: string,
	model: string = "llama-3.3-70b",
	apiKey?: string
): Promise<ReadableStream<Uint8Array>> {
	const { key, source } = resolveApiKey(apiKey);

	console.info("[key-compare]", { model, keyPrefix: maskKey(key), source });

	const client = new OpenAI({ baseURL: "https://api.oxlo.ai/v1", apiKey: key });
	const stream = await client.chat.completions.create({
		model,
		messages: buildMessages(prompt, systemPrompt),
		temperature: 0.7,
		max_tokens: 4096,
		stream: true,
	});

	const encoder = new TextEncoder();
	return new ReadableStream({
		async start(controller) {
			try {
				for await (const chunk of stream) {
					const content = chunk.choices[0]?.delta?.content;
					if (content) controller.enqueue(encoder.encode(content));
				}
				controller.close();
			} catch (error) {
				controller.error(error);
			}
		},
	});
}

/**
 * Response shape returned by Oxlo's /v1/images/generations endpoint.
 */
export interface OxloImageResponse {
	created: number;
	data: Array<{ b64_json?: string; url?: string }>;
}

/**
 * Generate an image via Oxlo Flux.1 Schnell using raw fetch.
 * Bypasses the OpenAI SDK entirely — sends only the exact fields the API needs,
 * matching the working Python agents.py call:
 *   model="flux.1-schnell", prompt=prompt, size="1536x864", response_format="b64_json"
 */
export async function generateImage(
	prompt: string,
	apiKey?: string,
): Promise<OxloImageResponse> {
	const { key, source } = resolveApiKey(apiKey);

	const payload = {
		model:           DEFAULT_IMAGE_MODEL, // "flux.1-schnell"
		prompt,
		size:            "1536x864",
		response_format: "b64_json",
	};

	console.info("[key-compare]", {
		model:     DEFAULT_IMAGE_MODEL,
		keyPrefix: maskKey(key),
		source,
	});

	console.info("[flux-raw-request]", {
		url:             "https://api.oxlo.ai/v1/images/generations",
		method:          "POST",
		model:           payload.model,
		size:            payload.size,
		response_format: payload.response_format,
		promptLength:    prompt.length,
		authHeader:      `Bearer ${maskKey(key)}`,
	});

	const response = await fetch("https://api.oxlo.ai/v1/images/generations", {
		method:  "POST",
		headers: {
			"Content-Type":  "application/json",
			"Authorization": `Bearer ${key}`,
		},
		body: JSON.stringify(payload),
	});

	console.info("[flux-raw-response]", {
		status:      response.status,
		contentType: response.headers.get("content-type"),
	});

	if (!response.ok) {
		let errorBody: unknown = null;
		try { errorBody = await response.json(); } catch { /* non-JSON */ }
		console.error("[flux-raw-error]", { status: response.status, body: errorBody });

		const err = new Error(
			typeof errorBody === "object" && errorBody !== null
				? ((errorBody as Record<string, unknown>).message as string) || `Oxlo API error ${response.status}`
				: `Oxlo API error ${response.status}`
		) as Error & Record<string, unknown>;
		err.status = response.status;
		err.error  = errorBody;
		err.code   = (errorBody as Record<string, unknown>)?.error ?? undefined;
		throw err;
	}

	return response.json() as Promise<OxloImageResponse>;
}
