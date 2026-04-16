import type { ToolDefinition } from "@/types";

export const pdfSummarizer: ToolDefinition = {
  id: "pdf-summarizer",
  name: "PDF / Document Summarizer",
  description:
    "Paste document text and get a structured executive summary with key findings, action items, and highlights.",
  category: "documentation",
  icon: "FileSearch",
  status: "active",

  requiredFields: ["documentText"],
  defaultModel: "deepseek-r1-0528",

  buildSystemPrompt: () =>
    `You are an executive assistant and document analyst. Summarize the provided document text into a structured report:

1. **Executive Summary** - 2-3 sentence overview
2. **Key Findings** - Bulleted list of the most important points
3. **Data & Numbers** - Extract all specific numbers, dates, amounts, percentages
4. **Action Items** - Any tasks, deadlines, or next steps mentioned
5. **Notable Quotes** - Direct quotes worth highlighting
6. **Risk Factors** - Any concerns or warnings mentioned

Be concise but comprehensive. Use markdown formatting.`,

  buildUserPrompt: ({ documentText, focus }) =>
    `${focus ? `**FOCUS AREA:** ${focus}\n\n` : ""}**DOCUMENT TEXT:**\n\`\`\`\n${documentText}\n\`\`\`\n\nSummarize this document.`,

  inputs: [
    {
      key: "documentText",
      label: "Document Text",
      type: "code",
      placeholder: "Paste the text content of your document here...",
      rows: 14,
    },
    {
      key: "focus",
      label: "Focus Area (optional)",
      type: "textarea",
      placeholder: "E.g. 'Focus on financial projections and risks'",
      rows: 2,
    },
  ],
};
