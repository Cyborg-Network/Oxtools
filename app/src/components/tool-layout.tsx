"use client";

import type { ReactNode } from "react";

import { Separator } from "@ansospace/ui";

import { HistoryDrawer } from "./history-drawer";

interface ToolLayoutProps {
  title: string;
  description: string;
  icon: ReactNode;
  children: ReactNode;
  onRestore?: (body: Record<string, unknown>, result: string) => void;
}

export function ToolLayout({ title, description, icon, children, onRestore }: ToolLayoutProps) {
  return (
    <div className="p-6">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {icon}
          </span>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">{title}</h1>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </div>
        <HistoryDrawer onRestore={onRestore} />
      </div>
      <Separator className="mb-6" />
      <div className="mx-auto max-w-4xl">{children}</div>
    </div>
  );
}
