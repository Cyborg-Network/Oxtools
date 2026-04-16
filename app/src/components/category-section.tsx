import { Badge } from "@ansospace/ui";

import { categories } from "@/lib/tools";
import type { Tool, ToolCategory } from "@/types";

import { ToolCard } from "./tool-card";

interface CategorySectionProps {
  category: ToolCategory;
  tools: Tool[];
}

export function CategorySection({ category, tools }: CategorySectionProps) {
  const categoryInfo = categories[category];

  return (
    <section className="space-y-5">
      <div className="flex items-center gap-3">
        <span className="text-2xl">{categoryInfo.icon}</span>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          {categoryInfo.name}
        </h2>
        <Badge variant="secondary" className="ml-1">
          {tools.length}
        </Badge>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tools.map((tool) => (
          <ToolCard key={tool.id} tool={tool} />
        ))}
      </div>
    </section>
  );
}
