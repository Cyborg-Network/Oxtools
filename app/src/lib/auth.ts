/**
 * Oxtools Auth & Usage Integration
 *
 * Connects to the Oxlo backend to:
 * 1. Validate user sessions (JWT from portal.oxlo.ai)
 * 2. Get user plan (free/pro/premium)
 * 3. Track and enforce usage limits
 *
 * Usage limits per day:
 *   Free:    5 tool executions
 *   Pro:     20 tool executions
 *   Premium: 100 tool executions
 */

// The Oxlo backend URL - same one oxlo-ui uses
const OXLO_BACKEND_URL = process.env.NEXT_PUBLIC_OXLO_BACKEND_URL || "http://localhost:8000";

export interface UserProfile {
	email: string;
	name: string;
	plan_id: string;
	is_superuser: boolean;
	profile_completed: boolean;
}

export interface UsageStatus {
	used: number;
	limit: number;
	plan: string;
	remaining: number;
	limitReached: boolean;
}

// Plan limits mapping
const PLAN_LIMITS: Record<string, number> = {
	free: 500, 
	pro: 20,
	premium: 100,
};

/**
 * Get the usage limit for a given plan
 */
export function getPlanLimit(planId: string): number {
	const normalizedPlan = planId?.toLowerCase() || "free";
	// Enterprise/custom plans get premium limits
	if (normalizedPlan in PLAN_LIMITS) {
		return PLAN_LIMITS[normalizedPlan];
	}
	return PLAN_LIMITS.premium; // Custom enterprise plans get premium limits
}

/**
 * Get the plan display name
 */
export function getPlanDisplayName(planId: string): string {
	const map: Record<string, string> = {
		free: "Free",
		pro: "Pro",
		premium: "Premium",
	};
	return map[planId?.toLowerCase()] || planId || "Free";
}

/**
 * Fetch user profile from Oxlo backend using the JWT token
 */
export async function getUserProfile(accessToken: string): Promise<UserProfile | null> {
	try {
		const res = await fetch(`${OXLO_BACKEND_URL}/auth/me/profile-status`, {
			headers: {
				Authorization: `Bearer ${accessToken}`,
			},
			cache: "no-store",
		});

		if (!res.ok) return null;
		return await res.json();
	} catch {
		return null;
	}
}

/**
 * Get the access token from various sources
 * Priority: cookie > localStorage
 */
export function getAccessToken(): string | null {
	if (typeof window === "undefined") return null;

	// Try cookie first (shared across subdomains via domain=.oxlo.ai)
	const cookies = document.cookie.split(";");
	for (const cookie of cookies) {
		const [key, value] = cookie.trim().split("=");
		if (key === "access_token" && value) {
			return value;
		}
	}

	// Fallback to localStorage
	return localStorage.getItem("access_token");
}

// ─── Per-Tool Usage Tracking ─────────────────────────────────────────
// Each tool has its OWN usage counter per day.
// Free: 5 per tool/day, Pro: 20 per tool/day, Premium: 100 per tool/day
//
// Storage format: { date: "2026-04-16", tools: { "code-error-debugger": 3, "deep-research": 1 } }
// (Will be replaced with backend PostgreSQL tracking in production)

interface UsageStore {
	date: string;
	tools: Record<string, number>;
}

function getUsageStore(): UsageStore {
	if (typeof window === "undefined") return { date: "", tools: {} };

	const today = new Date().toISOString().split("T")[0];
	const stored = localStorage.getItem("oxtools_usage");

	if (stored) {
		try {
			const data = JSON.parse(stored) as UsageStore;
			if (data.date === today && data.tools) {
				return data;
			}
		} catch {
			// Invalid data, reset
		}
	}

	// New day or first visit - reset all counters
	const fresh: UsageStore = { date: today, tools: {} };
	localStorage.setItem("oxtools_usage", JSON.stringify(fresh));
	return fresh;
}

/**
 * Get usage count for a specific tool today
 */
export function getToolUsageToday(toolId: string): number {
	const store = getUsageStore();
	return store.tools[toolId] || 0;
}

/**
 * Get total usage across all tools today (for sidebar summary)
 */
export function getTotalUsageToday(): number {
	const store = getUsageStore();
	return Object.values(store.tools).reduce((sum, count) => sum + count, 0);
}

/**
 * Increment usage count for a specific tool
 */
export function incrementToolUsage(toolId: string): number {
	if (typeof window === "undefined") return 0;

	const store = getUsageStore();
	const newCount = (store.tools[toolId] || 0) + 1;
	store.tools[toolId] = newCount;
	localStorage.setItem("oxtools_usage", JSON.stringify(store));
	return newCount;
}

/**
 * Get usage status for a specific tool
 */
export function getToolUsageStatus(planId: string, toolId: string): UsageStatus {
	const used = getToolUsageToday(toolId);
	const limit = getPlanLimit(planId);
	const remaining = Math.max(0, limit - used);

	return {
		used,
		limit,
		plan: planId || "free",
		remaining,
		limitReached: used >= limit,
	};
}

/**
 * Get overall usage summary (for sidebar display)
 */
export function getUsageStatus(planId: string): UsageStatus {
	const totalUsed = getTotalUsageToday();
	const limit = getPlanLimit(planId);

	return {
		used: totalUsed,
		limit,
		plan: planId || "free",
		remaining: Math.max(0, limit - totalUsed),
		limitReached: false, // Global summary doesn't block - per-tool does
	};
}

/**
 * Check if a specific tool execution is allowed
 */
export function canExecuteTool(planId: string, toolId?: string): boolean {
	if (!toolId) return true; // No tool context = allow
	const status = getToolUsageStatus(planId, toolId);
	return !status.limitReached;
}

/**
 * Dev mode: Override plan via URL param ?plan=pro or ?plan=premium
 * Only works in development. Returns null if no override.
 */
export function getDevPlanOverride(): string | null {
	if (typeof window === "undefined") return null;
	if (process.env.NODE_ENV !== "development") return null;
	const params = new URLSearchParams(window.location.search);
	return params.get("plan");
}

/**
 * Get the upgrade URL for the pricing page
 */
export function getUpgradeUrl(): string {
	return "https://portal.oxlo.ai/pricing";
}

/**
 * Get the login URL with return redirect
 */
export function getLoginUrl(): string {
	if (typeof window === "undefined") return "https://portal.oxlo.ai/login";
	const returnUrl = encodeURIComponent(window.location.href);
	return `https://portal.oxlo.ai/login?returnUrl=${returnUrl}`;
}
