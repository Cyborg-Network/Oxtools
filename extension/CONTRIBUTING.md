# Oxtools Chrome Extension — Architecture Guide for Contributors

## 🏗️ Current Structure (Single Extension)

```
Oxtools/extension/
├── manifest.json          ← Chrome Extension manifest (ONE per extension)
├── vite.config.ts         ← Build config
├── tailwind.config.js     ← Styling config
├── package.json           ← Dependencies
├── public/
│   └── icon128.png        ← Extension icon
└── src/
    ├── index.css          ← Global Tailwind CSS
    ├── background/
    │   └── index.ts       ← Service Worker (runs in Chrome background)
    ├── content/
    │   ├── index.tsx      ← Content Script (injected into web pages)
    │   └── authSync.ts    ← Auth sync content script
    └── sidepanel/
        ├── index.html     ← Side Panel HTML shell
        └── index.tsx      ← Side Panel React UI
```

---

## ✅ Yes — Multiple Tools CAN Be Built In One Extension

Each tool is just a new "mode" in the Side Panel. No new extension needed.

---

## 📐 Recommended Multi-Tool Architecture

```
Oxtools/extension/src/
└── sidepanel/
    ├── index.tsx             ← Router (registers all tools)
    └── tools/
        ├── screenshot-to-code/
        │   └── Panel.tsx     ← ✅ Dev A edits ONLY this file
        ├── color-picker/
        │   └── Panel.tsx     ← ✅ Dev B edits ONLY this file
        └── css-inspector/
            └── Panel.tsx     ← ✅ Dev C edits ONLY this file
```

---

## 🗂️ Which File Does Each Role Edit?

| Role | File(s) to Edit | Never Touch |
|---|---|---|
| Tool Developer | src/sidepanel/tools/<your-tool>/Panel.tsx | manifest.json, background/, content/ |
| UI/Design | src/sidepanel/tools/<your-tool>/Panel.tsx, src/index.css | background/, content/ |
| Content Script Feature | src/content/index.tsx | manifest.json, sidepanel/ |
| Background / Permissions | src/background/index.ts, manifest.json | All tool panels |

---

## 🔌 How to Add a New Tool

### Step 1: Create your tool folder
```
mkdir -p src/sidepanel/tools/my-new-tool
touch src/sidepanel/tools/my-new-tool/Panel.tsx
```

### Step 2: Write your Panel component
```tsx
// src/sidepanel/tools/my-new-tool/Panel.tsx
export default function MyNewToolPanel() {
  return <div>My New Tool UI here</div>;
}
```

### Step 3: Register it in src/sidepanel/index.tsx
```tsx
import MyNewToolPanel from './tools/my-new-tool/Panel';

const TOOLS = [
  { id: 'screenshot-to-code', label: 'Screenshot to Code', Panel: ScreenshotPanel },
  { id: 'my-new-tool',        label: 'My New Tool',        Panel: MyNewToolPanel  },
];
```

### Step 4: Rebuild
```
rm -rf dist && npm run build
```

---

## 📡 Content Script Messaging API

| Message (Side Panel → Content) | Effect |
|---|---|
| { action: "ACTIVATE_WAND" } | Activates the element picker overlay |

| Message (Content → Side Panel) | Data |
|---|---|
| { action: "ELEMENT_CLICKED", payload: rect } | Element geometry |

Add new content actions in src/content/index.tsx inside the message listener:
```typescript
if (request.action === "MY_TOOL_ACTION") {
  // interact with the page
  sendResponse({ success: true });
  return true;
}
```

---

## ⚠️ Contributor Rules

1. Never modify manifest.json unless adding a Chrome permission (discuss first).
2. Never modify background/index.ts unless adding a background capability.
3. Your tool Panel is self-contained — all UI and API calls live inside Panel.tsx.
4. Backend tools go in Oxtools/services/python-tools/tools/<your-tool>/tool.py
5. Always run: npm run build and test in Chrome before a PR.

---

## 🏁 Quick Start

```
cd Oxtools/extension
npm install
npm run build
# Chrome → chrome://extensions → Developer Mode → Load Unpacked → select dist/
```
