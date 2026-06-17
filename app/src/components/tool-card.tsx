import { Badge } from "@ansospace/ui";
import { ArrowRight, Clock } from "lucide-react";
import Link from "next/link";
import { getToolIcon } from "@/lib/icons";
import type { ToolDefinition } from "@/types";

interface ToolCardProps {
	tool: ToolDefinition;
}

export function ToolCard({ tool }: ToolCardProps) {
	const isActive = tool.status === "active";
	const toolHref = `/tools/${tool.id}`;

	const content = (
		<div
			className={`group relative h-full rounded-xl border border-border bg-card p-5 transition-all duration-300 ${
				isActive
					? "hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 cursor-pointer"
					: "opacity-50 cursor-not-allowed"
			}`}
		>
			{/* Left accent border */}
			<div className="absolute left-0 top-4 bottom-4 w-[2px] rounded-full bg-primary/30 group-hover:bg-primary transition-colors duration-300" />

			{/* Icon badge */}
			<div className="flex items-start gap-3 mb-3">
				<span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20 text-primary">
					{getToolIcon(tool.icon, "h-5 w-5")}
				</span>
				{!isActive && (
					<Badge variant="outline" className="shrink-0 text-[10px]">
						<Clock className="mr-1 h-3 w-3" />
						Soon
					</Badge>
				)}
			</div>

			{/* Title */}
			<h3
				className="font-semibold text-[15px] text-foreground mb-1.5 line-clamp-1"
				style={{ fontFamily: "var(--font-unbounded), sans-serif" }}
			>
				{tool.name}
			</h3>

			{/* Description */}
			<p className="text-[13px] text-muted-foreground line-clamp-2 mb-4 leading-relaxed">
				{tool.description}
			</p>

			{/* Footer */}
			{isActive ? (
				<span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary group-hover:gap-2 transition-all">
					Open tool
					<ArrowRight className="h-3.5 w-3.5" />
				</span>
			) : (
				<span className="text-[12px] text-muted-foreground/60">Coming soon</span>
			)}
		</div>
	);

	if (!isActive) {
		return <div>{content}</div>;
	}

	return (
		<Link href={toolHref} className="block">
			{content}
		</Link>
	);
}
