/**
 * SSR placeholder matching sidebar width to limit layout shift while the real sidebar mounts.
 */
export function SidebarPlaceholder() {
	return (
		<div
			className="hidden w-64 shrink-0 border-r border-border/50 bg-sidebar md:block"
			aria-hidden
		/>
	);
}
