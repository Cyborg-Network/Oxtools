// Local types for the sql-converter custom page.
// Do NOT import from here in any shared component.

export interface ColumnDef {
	name: string;
	type: string;
	isPrimary?: boolean;
	isForeign?: boolean;
	isNotNull?: boolean;
}

export interface TableDef {
	name: string;
	columns: ColumnDef[];
}

export interface ParsedSchema {
	raw: string;
	tables: TableDef[];
	tableCount: number;
}

export type ExecutionMode = "A" | "B";

export type ExecutionStatus = "idle" | "running" | "success" | "error";

export interface ExecutionState {
	status: ExecutionStatus;
	/** 0–6: which pipeline step is active (mirrors backend [N/6] logs) */
	currentStep: number;
	stepLabel: string;
	resultText: string; // full streaming text accumulator
	logs: string[]; // individual log lines parsed from stream
}
