import { Badge, Button } from "@ansospace/ui";
import {
	ArrowRight,
	Code2,
	Database,
	ExternalLink,
	FileText,
	GitBranch,
	Palette,
	PenTool,
	Server,
	Sparkles,
	Users,
} from "lucide-react";
import Link from "next/link";

import { ToolCard } from "@/components/tool-card";
import { getToolIcon } from "@/lib/icons";
import { categories, tools } from "@/lib/tools/registry";
import type { ToolCategory } from "@/types";

const categoryIconMap: Record<ToolCategory, React.ReactNode> = {
	developer: <Code2 className="h-5 w-5 text-primary" />,
	data: <Database className="h-5 w-5 text-primary" />,
	documentation: <FileText className="h-5 w-5 text-primary" />,
	design: <Palette className="h-5 w-5 text-primary" />,
	devops: <Server className="h-5 w-5 text-primary" />,
	content: <PenTool className="h-5 w-5 text-primary" />,
};

export default function ToolsDashboard() {
	const activeTools = tools.filter((t) => t.status === "active");
	const activeCount = activeTools.length;

	return (
		<div className="p-6 space-y-10">
			{/* Welcome Banner */}
			<div className="relative overflow-hidden rounded-xl border border-border bg-card p-6 sm:p-8">
				<div className="absolute top-0 right-0 h-40 w-40 rounded-full bg-primary/5 blur-3xl" />
				<div className="relative">
					<div className="flex items-center gap-2">
						<Sparkles className="h-5 w-5 text-primary" />
						<Badge className="text-[10px] bg-primary/10 text-primary border-primary/20 hover:bg-primary/15">
							Open Source
						</Badge>
						<Badge variant="outline" className="text-[10px]">
							Community Driven
						</Badge>
					</div>
					<h1
						className="mt-3 text-2xl font-bold tracking-tight text-foreground sm:text-3xl"
						style={{ fontFamily: "var(--font-unbounded), sans-serif" }}
					>
						Welcome to Oxtools
					</h1>
					<p className="mt-2 max-w-lg text-[14px] text-muted-foreground leading-relaxed">
						{activeCount} AI-powered developer tools built by the{" "}
						<a
							href="https://oxlo.ai"
							target="_blank"
							rel="noopener noreferrer"
							className="text-primary hover:underline underline-offset-2 font-medium"
						>
							Oxlo.ai
						</a>{" "}
						community. Pick a tool from the sidebar or explore below.
					</p>
					<div className="mt-4 flex gap-3">
						<a
							href="https://github.com/Cyborg-Network/Oxtools"
							target="_blank"
							rel="noopener noreferrer"
						>
							<Button variant="outline" size="sm" className="gap-1.5">
								<GitBranch className="h-4 w-4" />
								Contribute a Tool
							</Button>
						</a>
						<a href="https://oxlo.ai" target="_blank" rel="noopener noreferrer">
							<Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
								<ExternalLink className="h-4 w-4" />
								Oxlo.ai
							</Button>
						</a>
					</div>
				</div>
			</div>

			{/* Quick Access */}
			<div className="space-y-4">
				<div className="flex items-center justify-between">
					<h2
						className="text-lg font-semibold text-foreground"
						style={{ fontFamily: "var(--font-unbounded), sans-serif" }}
					>
						Quick Access
					</h2>
					<Badge variant="outline" className="gap-1">
						<Users className="h-3 w-3" />
						{activeCount} tools
					</Badge>
				</div>
				<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{activeTools.slice(0, 8).map((tool) => (
						<Link key={tool.id} href={`/tools/${tool.id}`} className="group block">
							<div className="h-full rounded-xl border border-border bg-card p-4 transition-all duration-300 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 relative">
								<div className="absolute left-0 top-3 bottom-3 w-[2px] rounded-full bg-primary/20 group-hover:bg-primary transition-colors duration-300" />
								<div className="flex items-center gap-2.5 mb-2">
									<span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20 text-primary">
										{getToolIcon(tool.icon, "h-4 w-4")}
									</span>
									<span
										className="text-[14px] font-semibold text-foreground truncate"
										style={{ fontFamily: "var(--font-unbounded), sans-serif" }}
									>
										{tool.name}
									</span>
								</div>
								<p className="text-[12px] text-muted-foreground line-clamp-2 leading-relaxed">
									{tool.description}
								</p>
							</div>
						</Link>
					))}
				</div>
				{activeTools.length > 8 && (
					<div className="text-center">
						<a
							href="#all-tools"
							className="inline-flex items-center gap-1 text-[13px] font-medium text-primary hover:gap-2 transition-all"
						>
							View all {activeCount} tools
							<ArrowRight className="h-3.5 w-3.5" />
						</a>
					</div>
				)}
			</div>

			{/* All Tools by Category */}
			<div className="space-y-8" id="all-tools">
				<h2
					className="text-lg font-semibold text-foreground"
					style={{ fontFamily: "var(--font-unbounded), sans-serif" }}
				>
					All Tools
				</h2>
				{(Object.entries(categories) as [ToolCategory, (typeof categories)[ToolCategory]][]).map(
					([categoryKey, categoryInfo]) => {
						const categoryTools = tools.filter((t) => t.category === categoryKey);
						if (categoryTools.length === 0) return null;

						const activeInCategory = categoryTools.filter((t) => t.status === "active").length;

						return (
							<section key={categoryKey} id={categoryKey} className="space-y-4 pt-4 scroll-mt-20">
								<div className="flex items-center gap-3">
									<span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
										{categoryIconMap[categoryKey]}
									</span>
									<div>
										<h3
											className="text-[15px] font-semibold text-foreground"
											style={{ fontFamily: "var(--font-unbounded), sans-serif" }}
										>
											{categoryInfo.name}
										</h3>
										<p className="text-[12px] text-muted-foreground">{categoryInfo.description}</p>
									</div>
									<Badge variant="outline" className="ml-auto">
										{activeInCategory}/{categoryTools.length}
									</Badge>
								</div>
								<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
									{categoryTools.map((tool) => (
										<ToolCard key={tool.id} tool={tool} />
									))}
								</div>
							</section>
						);
					}
				)}
			</div>
		</div>
	);
}
