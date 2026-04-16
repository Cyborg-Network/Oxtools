import type { ToolDefinition } from "@/types";

export const prSummarizer: ToolDefinition = {
  id: "pr-summarizer",
  name: "PR Summarizer",
  description: "Generate structured summaries from Git diffs",
  category: "developer",
  icon: "GitPullRequest",
  status: "active",

  defaultModel: "llama-3.3-70b",
  requiredFields: ["diff"],
  buildSystemPrompt: () =>
    `You are a senior software engineer writing a pull request summary. Given a Git diff, produce:

1. **Title** - A clear, one-line PR title
2. **Summary** - 2-3 sentences describing the change
3. **Changes** - Categorized list of changes:
   - 🆕 Added
   - 🔄 Modified
   - 🗑️ Removed
4. **Impact Analysis** - What parts of the system are affected
5. **Testing Notes** - Suggested manual test scenarios
6. **Review Notes** - Key areas reviewers should focus on

Use clean markdown formatting. Be concise and specific.`,
  buildUserPrompt: ({ diff }) =>
    `Generate a PR summary for this diff:\n\n\`\`\`diff\n${diff}\n\`\`\``,

  inputs: [
    {
      key: "diff",
      label: "Paste your Git diff",
      type: "code",
      placeholder: "diff --git a/file.ts b/file.ts\n--- a/file.ts\n+++ b/file.ts\n@@ -1,5 +1,7 @@\n ...",
      rows: 14,
    },
  ],
};
