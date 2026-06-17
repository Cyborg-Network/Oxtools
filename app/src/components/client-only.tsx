"use client";

import * as React from "react";

/**
 * Renders children only after the client has mounted.
 * Avoids hydration mismatches when browser extensions (e.g. Dark Reader)
 * mutate server-rendered attributes before React hydrates.
 */
export function ClientOnly({
	children,
	fallback = null,
}: {
	children: React.ReactNode;
	fallback?: React.ReactNode;
}) {
	const [mounted, setMounted] = React.useState(false);

	React.useEffect(() => {
		setMounted(true);
	}, []);

	if (!mounted) return fallback;
	return children;
}
