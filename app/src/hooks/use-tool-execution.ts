"use client";

import { useCallback, useRef, useState } from "react";

import { saveToolHistory } from "@/lib/history-db";

interface UseToolExecutionOptions {
	apiEndpoint: string;
	toolId?: string;
	timeoutMs?: number;
}

export interface ToolError {
	message: string;
	code?: string;
	action?: string;
}

interface UseToolExecutionReturn {
	result: string;
	isLoading: boolean;
	error: ToolError | null;
	execute: (body: Record<string, unknown>) => Promise<void>;
	reset: () => void;
	setResult: (value: string) => void;
}

export function useToolExecution({
	apiEndpoint,
	toolId: explicitToolId,
	timeoutMs = 30_000,
}: UseToolExecutionOptions): UseToolExecutionReturn {
	const [result, setResult] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<ToolError | null>(null);
	const timeoutErrorRef = useRef(false);
	const abortControllerRef = useRef<AbortController | null>(null);
	const timeoutIdRef = useRef<NodeJS.Timeout | null>(null);

	const toolId = explicitToolId || apiEndpoint.split("/").pop();

	const execute = useCallback(
		async (body: Record<string, unknown>) => {
			if (abortControllerRef.current) {
				abortControllerRef.current.abort();
			}
			if (timeoutIdRef.current) {
				clearTimeout(timeoutIdRef.current);
			}
			timeoutErrorRef.current = false;

			const controller = new AbortController();
			abortControllerRef.current = controller;

			const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

			setIsLoading(true);
			setError(null);
			setResult("");

			// Set a timeout of 120 seconds for image processing tools, 30 seconds for others
			const timeoutMs = toolId === "color-palette" ? 120000 : 30000;

			const timeoutId = setTimeout(() => {
				timeoutErrorRef.current = true;
				controller.abort();
				setError({
					message:
						"Request timeout. The process is taking too long. Please try with a smaller image or check your connection.",
					code: "timeout",
					action: "retry",
				});
				setIsLoading(false);
			}, timeoutMs);

			timeoutIdRef.current = timeoutId;

			try {
				const customApiKey = localStorage.getItem("oxloApiKey");
				const headers: Record<string, string> = { "Content-Type": "application/json" };
				if (customApiKey) {
					headers["x-api-key"] = customApiKey;
				}

				const response = await fetch(apiEndpoint, {
					method: "POST",
					headers,
					body: JSON.stringify(body),
					signal: controller.signal,
				});

				if (!response.ok) {
					const data = await response.json().catch(() => ({
						error: "Request failed",
						code: "unknown",
					}));
					setError({
						message: data.error || `Request failed with status ${response.status}`,
						code: data.code,
						action: data.action,
					});
					return;
				}

				const contentType = response.headers.get("content-type") || "";
				let finalResult = "";

				if (contentType.includes("application/json")) {
					const data = await response.json();
					if (toolId === "color-palette" && typeof body.image === "string") {
						finalResult = JSON.stringify({
							...data,
							image: data.image || body.image,
						});
					} else {
						finalResult = data.result || JSON.stringify(data);
					}
					setResult(finalResult);
				} else if (response.body) {
					const reader = response.body.getReader();
					const decoder = new TextDecoder();

					while (true) {
						const { done, value } = await reader.read();
						if (done) break;
						finalResult += decoder.decode(value, { stream: true });
						setResult(finalResult);
					}
				}

				if (toolId && finalResult.trim()) {
					saveToolHistory({
						id: Date.now().toString(),
						toolId,
						model: (body.model as string) || undefined,
						body,
						result: finalResult,
						timestamp: Date.now(),
					});
				}
			} catch (err) {
				if (err instanceof DOMException && err.name === "AbortError") {
					// Request was aborted (either by timeout or user action)
					if (!timeoutErrorRef.current) {
						setError({
							message: "Request was cancelled. Please try again.",
							code: "aborted",
						});
					}
					setResult("");
					return;
				}
				const message = err instanceof Error ? err.message : "An unexpected error occurred";
				setError({ message, code: "client_error" });
				setResult("");
			} finally {
				clearTimeout(timeoutId);
				setIsLoading(false);
				abortControllerRef.current = null;
				if (timeoutIdRef.current) {
					clearTimeout(timeoutIdRef.current);
					timeoutIdRef.current = null;
				}
			}
		},
		[apiEndpoint, toolId]
	);

	const reset = useCallback(() => {
		if (abortControllerRef.current) {
			abortControllerRef.current.abort();
		}
		if (timeoutIdRef.current) {
			clearTimeout(timeoutIdRef.current);
			timeoutIdRef.current = null;
		}
		timeoutErrorRef.current = false;
		setResult("");
		setError(null);
		setIsLoading(false);
	}, []);

	return { result, isLoading, error, execute, reset, setResult };
}
