import type { ToolDefinition } from "@/types";

export const seoWriter: ToolDefinition = {
  id: "seo-writer",
  name: "Bulk SEO Writer",
  description:
    "Generate SEO-optimized meta titles, descriptions, and Open Graph tags for multiple pages at once.",
  category: "content",
  icon: "Globe",
  status: "active",

  requiredFields: ["pages"],
  defaultModel: "llama-3.3-70b",

  buildSystemPrompt: () =>
    `You are an SEO specialist and conversion copywriter. Generate optimized SEO metadata for each page. For each page, provide:

1. **Meta Title** - 50-60 characters, includes primary keyword, compelling
2. **Meta Description** - 150-160 characters, includes CTA, keyword-rich
3. **Open Graph Title** - optimized for social sharing
4. **Open Graph Description** - slightly different from meta, more engaging
5. **Target Keywords** - 3-5 primary and secondary keywords
6. **Schema Markup Suggestion** - recommended structured data type (Article, Product, FAQ, etc.)

Output as a clean table or structured list per page. Ensure every character count is within limits.`,

  buildUserPrompt: ({ pages, brand, industry }) =>
    `**BRAND:** ${brand || "Not specified"}\n**INDUSTRY:** ${industry || "Not specified"}\n\n**PAGES TO OPTIMIZE:**\n${pages}\n\nGenerate SEO metadata for each page.`,

  inputs: [
    {
      key: "pages",
      label: "Page List",
      type: "code",
      placeholder: `Homepage - Our AI platform for developers
Pricing - Free, Pro, and Enterprise plans
Blog - Latest articles about AI and development
API Docs - Complete API reference
About Us - Our mission and team`,
      rows: 8,
    },
    {
      key: "brand",
      label: "Brand Name",
      type: "text",
      placeholder: "E.g. 'Oxlo.ai'",
    },
    {
      key: "industry",
      label: "Industry",
      type: "text",
      placeholder: "E.g. 'AI/ML Developer Tools'",
    },
  ],
};
