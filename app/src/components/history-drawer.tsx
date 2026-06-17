"use client";

import {
	Button,
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	ScrollArea,
	Sheet,
	SheetContent,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from "@ansospace/ui";
import { Clock, FileText, History, RotateCcw, Trash2 } from "lucide-react";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { clearToolHistory, getToolHistory, type HistoryItem } from "@/lib/history-db";

import { ResultViewer } from "./result-viewer";

interface HistoryDrawerProps {
	onRestore?: (body: Record<string, unknown>, result: string) => void;
}

export function HistoryDrawer({ onRestore }: HistoryDrawerProps) {
	const pathname = usePathname();
	const [history, setHistory] = useState<HistoryItem[]>([]);
	const [open, setOpen] = useState(false);
	const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

	const handleRestore = () => {
		if (!selectedItem || !onRestore) return;
		onRestore(selectedItem.body || {}, selectedItem.result);
		setSelectedItem(null);
		setOpen(false);
	};

	const pathToolId = pathname?.split("/").pop() || "";
	const toolEndpointId = pathToolId; // Use consistent tool ID

	const loadHistory = useCallback(async () => {
		if (toolEndpointId) {
			const data = await getToolHistory(toolEndpointId);
			setHistory(data);
		}
	}, [toolEndpointId]);

	useEffect(() => {
		if (open) {
			loadHistory();
		}
	}, [open, loadHistory]);

	const handleClear = async () => {
		await clearToolHistory(toolEndpointId);
		setHistory([]);
	};

	// Don't show on dashboard overview
	if (pathname === "/tools") return null;

	return (
		<>
			<Sheet open={open} onOpenChange={setOpen}>
				<SheetTrigger className="inline-flex h-9 items-center gap-2 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium shadow-xs transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
					<History className="h-4 w-4" />
					History
				</SheetTrigger>

				<SheetContent className="flex w-[400px] flex-col sm:w-[540px]">
					<SheetHeader className="border-b pb-4">
						<div className="flex items-center justify-between">
							<SheetTitle className="flex items-center gap-2">
								<Clock className="h-5 w-5" />
								Previous Results
							</SheetTitle>
							{history.length > 0 && (
								<Button
									variant="ghost"
									size="sm"
									onClick={handleClear}
									className="h-8 px-2 text-destructive hover:bg-destructive/10 hover:text-destructive"
								>
									<Trash2 className="mr-2 h-4 w-4" /> Clear
								</Button>
							)}
						</div>
					</SheetHeader>

					<ScrollArea className="flex-1">
						<div className="flex flex-col gap-3 px-1 py-4">
							{history.length === 0 ? (
								<div className="py-12 text-center text-muted-foreground">
									<History className="mx-auto mb-4 h-12 w-12 opacity-20" />
									<p>No history found for this tool.</p>
									<p className="mt-2 text-xs opacity-60">Generate some results to see them here.</p>
								</div>
							) : (
								history.map((item) => (
									<button
										key={item.id}
										type="button"
										onClick={() => setSelectedItem(item)}
										className="group flex flex-col gap-1.5 rounded-lg border bg-card p-3 text-left transition-colors hover:bg-accent hover:text-accent-foreground"
									>
										<div className="flex w-full items-start justify-between">
											<span className="max-w-[280px] truncate text-sm font-medium">
												{(Object.values(item.body || {}).find(
													(v) => typeof v === "string" && v.length > 0
												) as string) || "Result"}
											</span>
											<span className="whitespace-nowrap text-xs text-muted-foreground opacity-60">
												{new Date(item.timestamp).toLocaleTimeString()}
											</span>
										</div>
										<div className="line-clamp-2 text-xs text-muted-foreground opacity-80 group-hover:opacity-100">
											{item.result}
										</div>
									</button>
								))
							)}
						</div>
					</ScrollArea>
				</SheetContent>
			</Sheet>

			<Dialog open={!!selectedItem} onOpenChange={(val) => !val && setSelectedItem(null)}>
				<DialogContent className="flex max-h-[90vh] min-h-[60vh] !w-[95vw] !max-w-6xl flex-col">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2">
							<FileText className="h-5 w-5" />
							Restored Result
						</DialogTitle>
					</DialogHeader>

					{selectedItem && (
						<div className="mb-2 rounded-lg border bg-muted/40 p-3 text-sm">
							<div className="flex flex-wrap gap-x-6 gap-y-1 text-muted-foreground">
								{selectedItem.model && (
									<span>
										<strong className="text-foreground">Model:</strong> {selectedItem.model}
									</span>
								)}
								<span>
									<strong className="text-foreground">Time:</strong>{" "}
									{new Date(selectedItem.timestamp).toLocaleString()}
								</span>
							</div>
							{Object.entries(selectedItem.body || {}).map(([key, val]) => {
								if (key === "model" || typeof val !== "string" || !val.trim()) return null;
								return (
									<details key={key} className="mt-2">
										<summary className="cursor-pointer text-xs font-medium text-foreground capitalize">
											{key.replace(/([A-Z])/g, " $1")}
										</summary>
										<pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-muted p-2 text-xs">
											{val}
										</pre>
									</details>
								);
							})}
						</div>
					)}

					<div className="flex-1 overflow-y-auto">
						<ResultViewer result={selectedItem?.result || ""} />
					</div>

					{onRestore && selectedItem && (
						<div className="flex items-center justify-end gap-3 border-t pt-4">
							<Button variant="outline" onClick={() => setSelectedItem(null)}>
								Close
							</Button>
							<Button onClick={handleRestore} className="gap-2">
								<RotateCcw className="h-4 w-4" />
								Restore & Continue
							</Button>
						</div>
					)}
				</DialogContent>
			</Dialog>
		</>
	);
}
