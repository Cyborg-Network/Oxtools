"use client";

import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	ThemeToggle,
} from "@ansospace/ui";
import {
	ChevronDown,
	Code2,
	Database,
	ExternalLink,
	FileText,
	Home,
	Palette,
	PenTool,
	Server,
	Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToolIcon } from "@/lib/icons";
import { categories, tools } from "@/lib/tools/registry";
import { useAuth } from "@/providers/auth-provider";
import type { ToolCategory } from "@/types";

/**
 * Category icons for sidebar - shown next to category names AND in collapsed mode
 */
const categoryIcons: Record<ToolCategory, React.ReactNode> = {
	developer: <Code2 className="h-4 w-4" />,
	data: <Database className="h-4 w-4" />,
	documentation: <FileText className="h-4 w-4" />,
	design: <Palette className="h-4 w-4" />,
	devops: <Server className="h-4 w-4" />,
	content: <PenTool className="h-4 w-4" />,
};

/**
 * Collapsible category section matching docs_site sidebar.
 * Features: uppercase titles, SVG icons, chevron rotation, teal active border
 */
function CollapsibleCategory({
	categoryKey,
	categoryInfo,
	defaultOpen,
}: {
	categoryKey: ToolCategory;
	categoryInfo: { name: string; icon: string; description: string };
	defaultOpen: boolean;
}) {
	const pathname = usePathname();
	const categoryTools = tools.filter((t) => t.category === categoryKey);
	const hasActiveChild = categoryTools.some((t) => pathname === `/tools/${t.id}`);
	const [isOpen, setIsOpen] = useState(defaultOpen || hasActiveChild);

	useEffect(() => {
		if (hasActiveChild && !isOpen) {
			setIsOpen(true);
		}
	}, [hasActiveChild, isOpen]);

	const router = useRouter();

	return (
		<div className="group-data-[collapsible=icon]:hidden">
			{/* Category header with icon */}
			<button
				type="button"
				onClick={() => {
					setIsOpen(!isOpen);
					router.push(`/tools#${categoryKey}`);
				}}
				className="flex items-center justify-between w-full px-3 mb-2 group rounded-md py-1"
			>
				<div className="flex items-center gap-2">
					<span className="text-muted-foreground group-hover:text-primary transition-colors">
						{categoryIcons[categoryKey]}
					</span>
					<span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider group-hover:text-foreground transition-colors">
						{categoryInfo.name}
					</span>
				</div>
				<ChevronDown
					size={12}
					className={`text-muted-foreground transition-transform duration-200 ${
						!isOpen ? "-rotate-90" : ""
					}`}
				/>
			</button>

			{/* Collapsible tool list */}
			<div
				className={`space-y-0.5 overflow-hidden transition-all duration-300 ${
					isOpen ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"
				}`}
			>
				{categoryTools.map((tool) => {
					const toolHref = `/tools/${tool.id}`;
					const isActive = pathname === toolHref;
					const isComingSoon = tool.status === "coming-soon";

					if (isComingSoon) {
						return (
							<span
								key={tool.id}
								className="flex items-center gap-2.5 px-3 py-1.5 ml-3 rounded-lg text-[13px] text-muted-foreground/50 cursor-not-allowed border-l-2 border-transparent"
							>
								<span className="opacity-40">{getToolIcon(tool.icon, "h-3.5 w-3.5")}</span>
								<span className="truncate">{tool.name}</span>
								<span className="ml-auto text-[9px] uppercase tracking-wider opacity-60">Soon</span>
							</span>
						);
					}

					return (
						<Link
							key={tool.id}
							href={toolHref}
							className={`group flex items-center gap-2.5 px-3 py-1.5 ml-3 rounded-lg text-[13px] transition-all duration-200 border-l-2 ${
								isActive
									? "text-primary font-medium bg-primary/10 border-primary"
									: "text-foreground/80 hover:text-foreground hover:!bg-transparent border-transparent"
							}`}
						>
							<span className={isActive ? "text-primary" : "text-muted-foreground"}>
								{getToolIcon(tool.icon, "h-3.5 w-3.5")}
							</span>
							<span className="truncate">{tool.name}</span>
						</Link>
					);
				})}
			</div>
		</div>
	);
}

export function AppSidebar() {
	const pathname = usePathname();
	const toolsByCategory = Object.entries(categories) as [
		ToolCategory,
		(typeof categories)[ToolCategory],
	][];

	return (
		<Sidebar collapsible="icon" variant="sidebar">
			{/* Header - Logo only, text hidden on icon mode via SidebarMenuButton */}
			<SidebarHeader>
				<SidebarMenu>
					<SidebarMenuItem>
						<SidebarMenuButton size="lg" render={<Link href="/tools" />} tooltip="Oxtools">
							<span className="flex h-8 w-8 items-center justify-center rounded-lg overflow-hidden shrink-0">
								<img src="/logo-icon-teal.png" alt="Oxlo" className="h-7 w-7 object-contain" />
							</span>
							<div className="grid flex-1 text-left text-sm leading-tight">
								<span
									className="truncate font-semibold text-foreground tracking-tight"
									style={{ fontFamily: "var(--font-unbounded), sans-serif" }}
								>
									Oxtools
								</span>
								<span className="truncate text-[11px] text-muted-foreground">by Oxlo.ai</span>
							</div>
						</SidebarMenuButton>
					</SidebarMenuItem>
				</SidebarMenu>
			</SidebarHeader>

			<SidebarContent className="scrollbar-thin px-2">
				{/* All Tools - using SidebarMenuButton for proper icon collapse */}
				<SidebarMenu>
					<SidebarMenuItem>
						<SidebarMenuButton
							render={<Link href="/tools" />}
							isActive={pathname === "/tools"}
							tooltip="All Tools"
						>
							<Home className="h-4 w-4" />
							<span>All Tools</span>
						</SidebarMenuButton>
					</SidebarMenuItem>
				</SidebarMenu>

				{/* Separator - hidden in icon mode */}
				<div className="mx-2 my-2 border-t border-border/50 group-data-[collapsible=icon]:hidden" />

				{/* Category sections - in expanded mode: collapsible categories */}
				<div className="space-y-3 group-data-[collapsible=icon]:hidden">
					{toolsByCategory.map(([categoryKey, categoryInfo]) => {
						const categoryTools = tools.filter((t) => t.category === categoryKey);
						if (categoryTools.length === 0) return null;

						return (
							<CollapsibleCategory
								key={categoryKey}
								categoryKey={categoryKey}
								categoryInfo={categoryInfo}
								defaultOpen={false}
							/>
						);
					})}
				</div>

				{/* Category icons - shown ONLY in collapsed icon mode */}
				<div className="hidden group-data-[collapsible=icon]:block space-y-1">
					<SidebarMenu>
						{toolsByCategory.map(([categoryKey, categoryInfo]) => {
							const categoryTools = tools.filter((t) => t.category === categoryKey);
							if (categoryTools.length === 0) return null;
							const hasActive = categoryTools.some((t) => pathname === `/tools/${t.id}`);

							return (
								<SidebarMenuItem key={categoryKey}>
									<SidebarMenuButton
										tooltip={categoryInfo.name}
										isActive={hasActive}
										render={<Link href={`/tools#${categoryKey}`} />}
									>
										{categoryIcons[categoryKey]}
										<span>{categoryInfo.name}</span>
									</SidebarMenuButton>
								</SidebarMenuItem>
							);
						})}
					</SidebarMenu>
				</div>
			</SidebarContent>

			{/* Footer */}
			<SidebarFooter className="pb-4">
				{/* Usage counter - hidden in icon mode */}
				<UsageCounter />

				<div className="flex items-center justify-between px-3 pt-2 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:gap-3">
					<a
						href="https://portal.oxlo.ai"
						target="_blank"
						rel="noopener noreferrer"
						className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-primary transition-colors group-data-[collapsible=icon]:hidden rounded-md px-2 py-1.5"
					>
						<Settings className="h-3.5 w-3.5" />
						Oxlo Console
						<ExternalLink className="h-3 w-3 ml-1 opacity-50" />
					</a>

					<div className="group-data-[collapsible=icon]:w-full group-data-[collapsible=icon]:flex group-data-[collapsible=icon]:justify-center">
						<ThemeToggle />
					</div>
				</div>
			</SidebarFooter>
		</Sidebar>
	);
}

/**
 * Usage counter widget for sidebar footer.
 * Shows plan name, per-tool limit, and total executions today.
 */
function UsageCounter() {
	const { usage, planId, redirectToUpgrade } = useAuth();
	const limitPerTool = usage.limit;

	return (
		<div className="group-data-[collapsible=icon]:hidden px-3 py-2">
			<div className="rounded-lg border border-border/50 bg-card/50 p-3 space-y-2.5">
				{/* Plan badge */}
				<div className="flex items-center justify-between">
					<span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">
						{usage.plan} plan
					</span>
					<span className="text-[10px] text-muted-foreground">
						{usage.used} run{usage.used !== 1 ? "s" : ""} today
					</span>
				</div>

				{/* Per-tool limit info */}
				<p className="text-[10px] text-muted-foreground leading-relaxed">
					{limitPerTool} uses per tool / day
				</p>

				{/* Upgrade link for free users */}
				{planId === "free" && (
					<button
						type="button"
						onClick={redirectToUpgrade}
						className="w-full text-[10px] text-center text-primary hover:underline underline-offset-2"
					>
						Upgrade for more →
					</button>
				)}
			</div>
		</div>
	);
}
