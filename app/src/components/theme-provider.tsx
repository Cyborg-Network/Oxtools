"use client";

import * as React from "react";

type Theme = "light" | "dark" | "system";

export function ThemeProvider({
	children,
	attribute = "class",
	defaultTheme = "dark",
	enableSystem = false,
	disableTransitionOnChange = false,
}: {
	children: React.ReactNode;
	attribute?: "class";
	defaultTheme?: Exclude<Theme, "system">;
	enableSystem?: boolean;
	disableTransitionOnChange?: boolean;
}) {
	React.useEffect(() => {
		const root = document.documentElement;

		const getSystemTheme = () =>
			window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";

		const readStored = (): Theme | null => {
			try {
				return (localStorage.getItem("theme") as Theme | null) ?? null;
			} catch {
				return null;
			}
		};

		const resolveTheme = (): Exclude<Theme, "system"> => {
			const stored = readStored();
			if (stored === "light" || stored === "dark") return stored;
			if (stored === "system" && enableSystem) return getSystemTheme();
			return defaultTheme;
		};

		const applyTheme = (theme: Exclude<Theme, "system">) => {
			if (disableTransitionOnChange) {
				const style = document.createElement("style");
				style.appendChild(
					document.createTextNode(
						"*{transition:none!important;animation:none!important}",
					),
				);
				document.head.appendChild(style);
				// remove on next frame so the style takes effect
				requestAnimationFrame(() => {
					style.remove();
				});
			}

			if (attribute === "class") {
				root.classList.remove("light", "dark");
				root.classList.add(theme);
			}

			root.style.colorScheme = theme;
		};

		applyTheme(resolveTheme());

		if (!enableSystem) return;

		const media = window.matchMedia?.("(prefers-color-scheme: dark)");
		if (!media) return;

		const onChange = () => {
			const stored = readStored();
			if (stored === "system") applyTheme(getSystemTheme());
		};

		media.addEventListener?.("change", onChange);
		return () => media.removeEventListener?.("change", onChange);
	}, [attribute, defaultTheme, disableTransitionOnChange, enableSystem]);

	return <>{children}</>;
}

