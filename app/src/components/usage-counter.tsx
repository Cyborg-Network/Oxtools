"use client";

import { Button } from "@ansospace/ui";
import { ArrowUpRight, Zap } from "lucide-react";
import { getPlanDisplayName } from "@/lib/auth";
import { useAuth } from "@/providers/auth-provider";

/**
 * Displays the user's usage counter and plan info in the sidebar.
 * Shows upgrade prompt when approaching or at limit.
 */
export function UsageCounter() {
	const { user, usage, isLoading, isAuthenticated, redirectToLogin, redirectToUpgrade } = useAuth();

	if (isLoading) {
		return (
			<div className="rounded-lg border border-border/50 bg-muted/30 p-3 animate-pulse">
				<div className="h-4 w-20 bg-muted rounded" />
				<div className="h-2 w-full bg-muted rounded mt-2" />
			</div>
		);
	}

	const percentage = usage.limit > 0 ? (usage.used / usage.limit) * 100 : 0;
	const isWarning = percentage >= 80;
	const isExhausted = usage.limitReached;
	const planName = getPlanDisplayName(user?.plan_id ?? usage.plan);

	return (
		<div className="rounded-lg border border-border/50 bg-muted/20 p-3 space-y-2.5">
			{/* Plan + Usage */}
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-1.5">
					<Zap className="h-3.5 w-3.5 text-primary" />
					<span className="text-xs font-medium text-foreground">{planName} Plan</span>
				</div>
				<span
					className={`text-xs font-mono ${isExhausted ? "text-destructive" : isWarning ? "text-yellow-500" : "text-muted-foreground"}`}
				>
					{usage.used}/{usage.limit}
				</span>
			</div>

			{/* Progress Bar */}
			<div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
				<div
					className={`h-full rounded-full transition-all duration-300 ${
						isExhausted ? "bg-destructive" : isWarning ? "bg-yellow-500" : "bg-primary"
					}`}
					style={{ width: `${Math.min(percentage, 100)}%` }}
				/>
			</div>

			{/* Status text */}
			<p className="text-[10px] text-muted-foreground">
				{isExhausted ? "Daily limit reached" : `${usage.remaining} uses remaining today`}
			</p>

			{/* Upgrade / Login CTA */}
			{isExhausted && (
				<Button
					variant="default"
					size="sm"
					className="w-full gap-1.5 text-xs h-7"
					onClick={redirectToUpgrade}
				>
					<ArrowUpRight className="h-3 w-3" />
					Upgrade for more
				</Button>
			)}

			{!isAuthenticated && !isExhausted && (
				<button
					type="button"
					onClick={redirectToLogin}
					className="w-full text-[10px] text-primary hover:underline underline-offset-2 text-center"
				>
					Sign in for higher limits
				</button>
			)}
		</div>
	);
}
