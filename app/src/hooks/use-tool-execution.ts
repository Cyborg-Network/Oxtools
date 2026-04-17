"use client";

import { useCallback, useRef, useState } from "react";

import { saveToolHistory } from "@/lib/history-db";

interface UseToolExecutionOptions {
	apiEndpoint: string;
	toolId?: string;
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
}: UseToolExecutionOptions): UseToolExecutionReturn {
	const [result, setResult] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<ToolError | null>(null);
	const abortControllerRef = useRef<AbortController | null>(null);

	const toolId = explicitToolId || apiEndpoint.split("/").pop();

	const execute = useCallback(
		async (body: Record<string, unknown>) => {
			if (abortControllerRef.current) {
				abortControllerRef.current.abort();
			}

			const controller = new AbortController();
			abortControllerRef.current = controller;

			setIsLoading(true);
			setError(null);
			setResult("");

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
					finalResult = data.result || JSON.stringify(data);
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
				if (err instanceof DOMException && err.name === "AbortError") return;
				const message = err instanceof Error ? err.message : "An unexpected error occurred";
				setError({ message, code: "client_error" });
				setResult("");
			} finally {
				setIsLoading(false);
				abortControllerRef.current = null;
			}
		},
		[apiEndpoint, toolId]
	);

	const reset = useCallback(() => {
		if (abortControllerRef.current) {
			abortControllerRef.current.abort();
		}
		setResult("");
		setError(null);
		setIsLoading(false);
	}, []);

	return { result, isLoading, error, execute, reset, setResult };
}
