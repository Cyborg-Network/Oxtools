import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { generateStreamingCompletion } from "@/lib/oxlo";

interface ToolRouteConfig {
  /** Fields to extract from request body (besides `model`) */
  requiredFields?: string[];
  /** Build the system prompt from the parsed body */
  buildSystemPrompt: (body: Record<string, string>) => string;
  /** Build the user prompt from the parsed body */
  buildUserPrompt: (body: Record<string, string>) => string;
  /** Default model when none is provided */
  defaultModel?: string;
  /** Error message when the request fails */
  errorMessage?: string;
}

/** Known Oxlo API error types mapped to user-friendly messages */
function parseOxloError(error: unknown): {
  status: number;
  code: string;
  message: string;
  action?: string;
} {
  // Handle OpenAI SDK errors (they have status, message, error properties)
  if (error && typeof error === "object" && "status" in error) {
    const err = error as {
      status?: number;
      message?: string;
      error?: { error?: string; message?: string; required_plan?: string; daily_limit?: number };
    };
    const status = err.status || 500;
    const innerError = err.error;
    const errorType = innerError?.error || "";
    const requiredPlan = innerError?.required_plan;

    // Model access denied — wrong plan tier
    if (errorType === "model_access_denied" || status === 403) {
      return {
        status: 403,
        code: "model_access_denied",
        message: `This model requires ${requiredPlan ? `a ${requiredPlan} plan` : "a higher plan"}. Your current plan does not include access to this model.`,
        action:
          "Try switching to a free-tier model (e.g., Neural Chat 7B or Mathstral 7B), or add your own API key with a higher plan in Settings.",
      };
    }

    // Rate limit exceeded
    if (errorType === "rate_limit_exceeded" || status === 429) {
      const dailyLimit = innerError?.daily_limit;
      return {
        status: 429,
        code: "rate_limit_exceeded",
        message: `Rate limit exceeded${dailyLimit ? ` (${dailyLimit} requests/day on free plan)` : ""}. Please try again later.`,
        action:
          "Add your own Oxlo API key in Settings to get higher limits, or wait for the daily limit to reset.",
      };
    }

    // Unauthorized — invalid API key
    if (status === 401) {
      return {
        status: 401,
        code: "unauthorized",
        message: "Invalid or expired API key. The API key being used is not authorized.",
        action:
          "Check your API key in Settings. Get a free key at portal.oxlo.ai/signup with promo code OXZ54MPIYV.",
      };
    }

    // Insufficient quota / billing
    if (status === 402 || errorType === "insufficient_quota") {
      return {
        status: 402,
        code: "insufficient_quota",
        message: "API quota exhausted. The API key has no remaining credits.",
        action: "Add a different API key in Settings, or upgrade your plan at portal.oxlo.ai.",
      };
    }

    // Service unavailable
    if (status === 503) {
      return {
        status: 503,
        code: "service_unavailable",
        message: "The AI model is temporarily unavailable. This usually resolves quickly.",
        action: "Try a different model, or wait a moment and try again.",
      };
    }

    // Generic API error with message
    if (err.message) {
      return {
        status,
        code: "api_error",
        message: err.message,
        action: undefined,
      };
    }
  }

  // Unknown/generic error
  const message = error instanceof Error ? error.message : "An unexpected error occurred";
  return {
    status: 500,
    code: "internal_error",
    message,
    action: undefined,
  };
}

/**
 * Creates a standardized POST handler for any AI tool route.
 * Handles: body parsing, field validation, API key extraction,
 * streaming completion, and structured error responses.
 */
export function createToolRoute(config: ToolRouteConfig) {
  const {
    requiredFields = [],
    buildSystemPrompt,
    buildUserPrompt,
    defaultModel = "llama-3.3-70b",
    errorMessage = "Failed to process request",
  } = config;

  return async function POST(request: NextRequest) {
    try {
      const apiKey = request.headers.get("x-api-key") || undefined;
      const body = await request.json();
      const model = body.model || defaultModel;

      // Validate required fields
      for (const field of requiredFields) {
        if (!body[field] || (typeof body[field] === "string" && !body[field].trim())) {
          return NextResponse.json(
            {
              error: `${field.replace(/([A-Z])/g, " $1").trim()} is required`,
              code: "validation_error",
            },
            { status: 400 }
          );
        }
      }

      const stream = await generateStreamingCompletion(
        buildUserPrompt(body),
        buildSystemPrompt(body),
        model,
        apiKey
      );

      return new Response(stream, {
        headers: {
          "Content-Type": "text/plain; charset=utf-8",
          "Transfer-Encoding": "chunked",
        },
      });
    } catch (error) {
      console.error(`[Tool Error] ${errorMessage}:`, error);
      const parsed = parseOxloError(error);
      return NextResponse.json(
        {
          error: parsed.message,
          code: parsed.code,
          action: parsed.action,
        },
        { status: parsed.status }
      );
    }
  };
}
