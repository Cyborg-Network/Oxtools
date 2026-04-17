"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";

import {
	canExecuteTool,
	getAccessToken,
	getDevPlanOverride,
	getLoginUrl,
	getToolUsageStatus,
	getUpgradeUrl,
	getUsageStatus,
	getUserProfile,
	incrementToolUsage,
	type UsageStatus,
	type UserProfile,
} from "@/lib/auth";

interface AuthContextValue {
	/** User profile (null if not logged in) */
	user: UserProfile | null;
	/** Whether we're still loading the auth state */
	isLoading: boolean;
	/** Whether the user is authenticated */
	isAuthenticated: boolean;
	/** Detected plan ID */
	planId: string;
	/** Overall usage summary (for sidebar) */
	usage: UsageStatus;
	/** Get per-tool usage status */
	getToolUsage: (toolId: string) => UsageStatus;
	/** Check if a specific tool can be executed */
	canExecute: (toolId: string) => boolean;
	/** Track a tool execution (call after successful run) */
	trackExecution: (toolId: string) => void;
	/** Refresh usage data */
	refreshUsage: () => void;
	/** Redirect to login */
	redirectToLogin: () => void;
	/** Redirect to pricing/upgrade */
	redirectToUpgrade: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<UserProfile | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [planId, setPlanId] = useState("free");
	const [usage, setUsage] = useState<UsageStatus>({
		used: 0,
		limit: 5,
		plan: "free",
		remaining: 5,
		limitReached: false,
	});

	// Load user profile on mount
	useEffect(() => {
		async function loadAuth() {
			// Dev mode: allow plan override via ?plan=pro
			const devPlan = getDevPlanOverride();

			const token = getAccessToken();

			if (!token) {
				const effectivePlan = devPlan || "free";
				setPlanId(effectivePlan);
				setUsage(getUsageStatus(effectivePlan));
				setIsLoading(false);
				return;
			}

			const profile = await getUserProfile(token);
			if (profile) {
				const effectivePlan = devPlan || profile.plan_id || "free";
				setUser(profile);
				setPlanId(effectivePlan);
				setUsage(getUsageStatus(effectivePlan));
			} else {
				const effectivePlan = devPlan || "free";
				setPlanId(effectivePlan);
				setUsage(getUsageStatus(effectivePlan));
			}

			setIsLoading(false);
		}

		loadAuth();
	}, []);

	const refreshUsage = useCallback(() => {
		setUsage(getUsageStatus(planId));
	}, [planId]);

	const getToolUsage = useCallback(
		(toolId: string) => getToolUsageStatus(planId, toolId),
		[planId]
	);

	const trackExecution = useCallback(
		(toolId: string) => {
			incrementToolUsage(toolId);
			refreshUsage();
		},
		[refreshUsage]
	);

	const redirectToLogin = useCallback(() => {
		window.location.href = getLoginUrl();
	}, []);

	const redirectToUpgrade = useCallback(() => {
		window.location.href = getUpgradeUrl();
	}, []);

	return (
		<AuthContext.Provider
			value={{
				user,
				isLoading,
				isAuthenticated: !!user,
				planId,
				usage,
				getToolUsage,
				canExecute: (toolId: string) => canExecuteTool(planId, toolId),
				trackExecution,
				refreshUsage,
				redirectToLogin,
				redirectToUpgrade,
			}}
		>
			{children}
		</AuthContext.Provider>
	);
}

export function useAuth() {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error("useAuth must be used within AuthProvider");
	return ctx;
}
