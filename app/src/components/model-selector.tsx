"use client";

import {
	Badge,
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@ansospace/ui";

import { AVAILABLE_MODELS } from "@/lib/models";

interface ModelSelectorProps {
	value: string;
	onChange: (value: string) => void;
	category?: "general" | "coding" | "reasoning";
}

const tierColors: Record<string, string> = {
	Premium: "text-amber-600 dark:text-amber-400",
	Pro: "text-blue-600 dark:text-blue-400",
	Free: "text-green-600 dark:text-green-400",
};

export function ModelSelector({ value, onChange, category }: ModelSelectorProps) {
	const models = category
		? AVAILABLE_MODELS.filter((m) => m.category === category || m.category === "general")
		: AVAILABLE_MODELS;

	return (
		<Select value={value} onValueChange={(val) => val && onChange(val)}>
			<SelectTrigger className="w-full">
				<SelectValue placeholder="Select model" />
			</SelectTrigger>
			<SelectContent>
				{models.map((model) => (
					<SelectItem key={model.id} value={model.id}>
						<div className="flex items-center gap-2">
							<span>{model.name}</span>
							<Badge
								variant="outline"
								className={`text-[9px] px-1 py-0 ${tierColors[model.tier] || ""}`}
							>
								{model.tier}
							</Badge>
						</div>
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}
