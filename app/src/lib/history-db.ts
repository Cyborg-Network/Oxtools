import { get, update } from "idb-keyval";

export interface HistoryItem {
	id: string;
	toolId: string;
	model?: string;
	body: Record<string, unknown>;
	result: string;
	timestamp: number;
}

export async function getToolHistory(toolId: string): Promise<HistoryItem[]> {
	try {
		const history = await get<HistoryItem[]>(`devkernel-history-${toolId}`);
		return history || [];
	} catch (error) {
		console.error("Failed to get history:", error);
		return [];
	}
}

export async function saveToolHistory(item: HistoryItem) {
	try {
		await update(`devkernel-history-${item.toolId}`, (oldVal: HistoryItem[] | undefined) => {
			const history = oldVal || [];
			// Don't save empty results
			if (!item.result.trim()) return history;

			history.unshift(item);
			// Keep only latest 50 entries
			return history.slice(0, 50);
		});
	} catch (error) {
		console.error("Failed to save history:", error);
	}
}

export async function clearToolHistory(toolId: string) {
	try {
		await update(`devkernel-history-${toolId}`, () => []);
	} catch (error) {
		console.error("Failed to clear history:", error);
	}
}
