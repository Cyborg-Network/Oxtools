/**
 * Parses streaming result text from the sql-converter backend.
 * Backend formats:
 *   Mode A (generate): ---RESULT--- + SQL block + ## Explanation/Performance/Dialect + ## Sandbox Test
 *   Mode B (sandbox):  ---RESULT--- + # SQL Sandbox Result + ## Sandbox Test + ### Mock Data Preview
 */

/** Extract the fenced SQL block from a generation response. */
export function extractSqlFromGeneration(text: string): string {
	const beforeSandbox = text.split("## Sandbox Test")[0];
	const match = beforeSandbox.match(/```(?:sql)?\s*\n([\s\S]*?)```/i);
	return match ? match[1].trim() : "";
}

/** Split Mode A output into generation content (excludes sandbox section). */
export function parseGenerationOutput(postResult: string): string {
	const idx = postResult.indexOf("## Sandbox Test");
	return (idx === -1 ? postResult : postResult.slice(0, idx)).trim();
}

/** Split Mode B output into sandbox execution result and mock data preview. */
export function parseSandboxOutput(postResult: string): {
	sandboxMarkdown: string;
	mockPreviewMarkdown: string;
} {
	let content = postResult.trim();
	content = content.replace(/^#\s*SQL Sandbox Result\s*\n?/i, "");

	const mockIdx = content.indexOf("### Mock Data Preview");
	if (mockIdx === -1) {
		return { sandboxMarkdown: content.trim(), mockPreviewMarkdown: "" };
	}

	return {
		sandboxMarkdown: content.slice(0, mockIdx).trim(),
		mockPreviewMarkdown: content.slice(mockIdx).trim(),
	};
}
