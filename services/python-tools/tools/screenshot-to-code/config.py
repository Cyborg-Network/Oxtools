import logging


logger = logging.getLogger("screenshot-to-code")


MANIFEST = {
    "id": "screenshot-to-code",
    "name": "Screenshot to Code",
    "description": "Upload a UI screenshot and get Tailwind/HTML code via Multi-Agent Consensus Pipeline",
    "author": "ArunMadhavan EVR",
    "version": "9.0.0",
}


COMPRESS_MAX_PX       = 1920


COMPRESS_JPEG_QUALITY = 90


MODEL_CODER = "kimi-k2.5"


MODEL_JUDGE = "kimi-k2.5"


OXLO_BASE_URL = "https://api.oxlo.ai/v1"


MAX_TOKENS_EXTRACT = 12000


MAX_TOKENS_CODE    = 16000


MAX_TOKENS_JUDGE   = 2048


SWARM_STRATEGIES = [
    {
        "name": "structure-first",
        "temperature": 0.0,
        "prefix": (
            "═══ STRATEGY: STRUCTURE-FIRST ═══\n"
            "Before writing a single HTML tag, reason through:\n"
            "  1. What is the outermost container? (full-width, fixed-width, mobile?)\n"
            "  2. What are the major layout sections? (header, sidebar, main, footer?)\n"
            "  3. What CSS layout system governs each section? (flex-row, flex-col, grid?)\n"
            "  4. What are the background colors of each section? (sample exact hex)\n"
            "Only then write the HTML, outside-in from largest container to smallest leaf.\n\n"
        ),
    },
    {
        "name": "typography-first",
        "temperature": 0.0,
        "prefix": (
            "═══ STRATEGY: TYPOGRAPHY-FIRST ═══\n"
            "Before writing a single HTML tag, inventory every text element:\n"
            "  1. List every visible string, its approximate px size, weight, and color.\n"
            "  2. Identify heading hierarchy (h1/h2/h3) from visual prominence.\n"
            "  3. Note any monospace, italic, or special-weight text.\n"
            "  4. Mark interactive text (links, buttons, labels) separately.\n"
            "Build the HTML by placing text elements first, then wrap them in layout containers.\n\n"
        ),
    },
    {
        "name": "component-first",
        "temperature": 0.0,
        "prefix": (
            "═══ STRATEGY: COMPONENT-FIRST ═══\n"
            "Before writing a single HTML tag, decompose the UI into components:\n"
            "  1. Identify discrete, reusable UI components (navbar, card, badge, list-row, tab-bar).\n"
            "  2. For each component: note its exact background, border, shadow, and padding.\n"
            "  3. Identify which components repeat (list items, table rows, grid cards).\n"
            "  4. Note the exact count of repeating items — do NOT truncate lists.\n"
            "Implement each component as a self-contained HTML block, then compose the full page.\n\n"
        ),
    },
]


SSIM_SHIP_THRESHOLD  = 92.0


SSIM_HEAL_THRESHOLD  = 55.0


MAX_HEALING_PASSES   = 3


DIFF_PIXEL_THRESHOLD = 12.0


SLICE_ASPECT_THRESHOLD = 2.5


SLICE_N                = 3


FONT_INJECT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Inter:wght@400;500;600;700&'
    'family=Roboto:wght@400;500;700&'
    'family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap" rel="stylesheet">'
    '<style>*,*::before,*::after{font-family:"Inter","Roboto","DM Sans",ui-sans-serif,system-ui,sans-serif;}</style>'
)


EXTRACTOR_USER = (
    "Extract the COMPLETE JSON layout from this screenshot. "
    "Include every visible list item, link, and text string — do not skip any rows. "
    "Output ONLY the raw JSON array. No explanation, no markdown."
)


CODER_SYSTEM_BASE = """You are a pixel-perfect UI compiler with vision capabilities.
You will be shown a UI screenshot. Reproduce it as HTML using Tailwind CSS.

CRITICAL RULES — violations will cause rejection:
1. Examine the screenshot at maximum detail before writing a single line of HTML.
2. Use Tailwind arbitrary values for EVERY color, size, spacing: bg-[#1a1a2e] text-[13px] w-[340px] gap-[12px].
3. Copy ALL visible text character-for-character. Never invent, paraphrase, or omit any text.
4. Reproduce exact background colors, text colors, border colors from the screenshot.
5. Match layout structure exactly: if it is a mobile screen, use a mobile-width container. If it is a desktop, use full width.
6. Render EVERY visible row, list item, and element. Do not truncate dense lists under any circumstances.
7. Simple icons (back arrow, checkmark, search, hamburger): inline SVG matching the screenshot shape exactly.
8. Profile photos, product images, logos: <img src="https://placehold.co/WxH/bgHex/fgHex"> with correct dimensions and colors.
9. Status bar elements (time, battery, signal): reproduce as text/SVG, never skip.
10. Bottom navigation bars: reproduce all tabs with correct icons and labels.
11. Include <script src="https://cdn.tailwindcss.com"></script> in <head>. No other scripts.
12. No JavaScript. No invented content whatsoever.
13. CRITICAL: If the screenshot shows a browser window with tabs/address bar, reproduce ONLY the inner page content — not the browser chrome.
14. Shadows, borders, border-radius: match exactly using arbitrary Tailwind values.
15. Gradients: reproduce using Tailwind bg-gradient-to-* classes with exact from/via/to hex values.
16. Opacity: match exactly using opacity-[N] or text-[#rrggbbAA] where relevant.

OUTPUT: Raw HTML only, starting with <!DOCTYPE html>. Zero explanation. Zero markdown fences."""


CODER_USER = (
    "Study this screenshot in full detail. "
    "Before writing HTML, mentally note:\n"
    "  - The exact background color of the page and each section\n"
    "  - Every text string, its size, weight, and color\n"
    "  - Every UI component and its precise spacing\n"
    "  - The layout system (flex/grid) used at each level\n"
    "  - Any gradients, shadows, borders, or special effects\n\n"
    "Then produce pixel-perfect HTML with Tailwind CSS that is indistinguishable from the screenshot.\n"
    "Output ONLY raw HTML starting with <!DOCTYPE html>. No explanation."
)


HEALER_SYSTEM = """You are a pixel-perfect UI debugger with vision capabilities.
You are given three images in order:
  IMAGE 1 — The ORIGINAL UI screenshot (ground truth target)
  IMAGE 2 — Your PREVIOUS HTML rendered in a browser
  IMAGE 3 — A DIFF MASK: red pixels = wrong, green tint = correct

Your ONLY job: fix the HTML so every red zone disappears.

CRITICAL RULES:
1. DO NOT rewrite sections that are correct (green zones). Touch only what is broken.
2. For each red zone, compare IMAGE 1 vs IMAGE 2 and diagnose the root cause:
   - Wrong spacing?         → Fix padding/margin/gap arbitrary value precisely.
   - Wrong color?           → Sample the exact hex from IMAGE 1 and correct bg-[#xxx] or text-[#xxx].
   - Wrong font size/weight? → Fix text-[Npx] or font-weight class.
   - Missing element?       → Add the complete missing HTML block.
   - Wrong layout?          → Fix flex-row ↔ flex-col or grid column count.
   - Wrong border/shadow?   → Correct border-[#xxx], rounded-[Npx], or shadow class.
   - Wrong gradient?        → Fix from-[#xxx] via-[#xxx] to-[#xxx] and direction.
   - Wrong image dimensions? → Fix the placehold.co URL with correct W×H.
3. Be surgical. The goal is zero red pixels in the next render.
4. Preserve ALL text strings exactly — do not alter any text content.
5. Return the COMPLETE corrected HTML starting with <!DOCTYPE html>.

OUTPUT: Raw HTML only, starting with <!DOCTYPE html>. Zero explanation. Zero markdown fences."""


JUDGE_SYSTEM = """You are a UI fidelity judge with vision capabilities.
You are given the original UI screenshot and 2-3 complete HTML candidates.
Your job: select the candidate that most faithfully reproduces the screenshot.

Evaluate each candidate on these criteria IN ORDER OF IMPORTANCE:
  1. TEXT ACCURACY     — every visible string present, verbatim, correct position
  2. COLOR ACCURACY    — exact background, text, border, and accent colors
  3. LAYOUT FIDELITY   — correct flex/grid structure, correct hierarchy
  4. COMPLETENESS      — no missing rows, nav items, icons, or sections
  5. SPACING           — correct padding, margin, gap values
  6. VISUAL EFFECTS    — shadows, borders, gradients, border-radius

Think through each candidate systematically. Then on the VERY LAST LINE of your
response, write ONLY the single digit 1, 2, or 3 — nothing else on that line."""
