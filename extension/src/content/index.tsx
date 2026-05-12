// @ts-ignore
import '../index.css';

let overlayEl: HTMLDivElement | null = null;
let customCursor: HTMLDivElement | null = null;
let styleTag: HTMLStyleElement | null = null;
let isActive = false;

console.log("Oxtools: Content Script injected successfully!");
(window as any).__oxtools_injected = true;

const STYLE_ID = 'oxtools-siri-styles';

function injectStyles() {
  if (document.getElementById(STYLE_ID)) return;

  styleTag = document.createElement('style');
  styleTag.id = STYLE_ID;
  styleTag.textContent = `
    /* ─── Siri border: outline-only, zero fill ───────────────────────────── */
    .oxtools-box {
      position: fixed;
      pointer-events: none;
      border-radius: 6px;
      z-index: 2147483646;

      /* outline draws OUTSIDE the element — no content overlap */
      outline: 2.5px solid #00c6ff;
      outline-offset: 1px;

      /* glow matches current outline colour */
      box-shadow:
        0 0 0 1px rgba(0, 198, 255, 0.15),
        0 0  8px 2px rgba(0, 198, 255, 0.35),
        0 0 20px 4px rgba(0, 198, 255, 0.15);

      /* smooth position tracking */
      transition:
        top    0.10s cubic-bezier(0.22, 1, 0.36, 1),
        left   0.10s cubic-bezier(0.22, 1, 0.36, 1),
        width  0.10s cubic-bezier(0.22, 1, 0.36, 1),
        height 0.10s cubic-bezier(0.22, 1, 0.36, 1);

      animation: oxtools-siri 3s linear infinite;
    }

    /* Cycling Siri colour palette — one vivid hue at a time with a glow */
    @keyframes oxtools-siri {
       0% { outline-color: #00c6ff; box-shadow: 0 0 0 1px rgba(0,198,255,.12), 0 0  8px 3px rgba(0,198,255,.40), 0 0 24px 6px rgba(0,198,255,.15); }
      16% { outline-color: #a855f7; box-shadow: 0 0 0 1px rgba(168,85,247,.12), 0 0  8px 3px rgba(168,85,247,.40), 0 0 24px 6px rgba(168,85,247,.15); }
      33% { outline-color: #ec4899; box-shadow: 0 0 0 1px rgba(236,72,153,.12), 0 0  8px 3px rgba(236,72,153,.40), 0 0 24px 6px rgba(236,72,153,.15); }
      50% { outline-color: #f97316; box-shadow: 0 0 0 1px rgba(249,115,22,.12), 0 0  8px 3px rgba(249,115,22,.40), 0 0 24px 6px rgba(249,115,22,.15); }
      66% { outline-color: #facc15; box-shadow: 0 0 0 1px rgba(250,204,21,.12), 0 0  8px 3px rgba(250,204,21,.40), 0 0 24px 6px rgba(250,204,21,.15); }
      83% { outline-color: #22c55e; box-shadow: 0 0 0 1px rgba(34,197,94,.12), 0 0  8px 3px rgba(34,197,94,.40), 0 0 24px 6px rgba(34,197,94,.15); }
     100% { outline-color: #00c6ff; box-shadow: 0 0 0 1px rgba(0,198,255,.12), 0 0  8px 3px rgba(0,198,255,.40), 0 0 24px 6px rgba(0,198,255,.15); }
    }

    /* ─── Custom cursor dot ───────────────────────────────────────────────── */
    .oxtools-cursor {
      position: fixed;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      pointer-events: none;
      z-index: 2147483647;
      transform: translate(-50%, -50%);

      /* white core with soft coloured halo */
      background: #ffffff;
      box-shadow:
        0 0  6px 2px rgba(255,255,255,0.9),
        0 0 14px 4px rgba(168,85,247,0.6);

      animation: oxtools-cursor-pulse 1.4s ease-in-out infinite;
    }

    @keyframes oxtools-cursor-pulse {
      0%, 100% {
        transform: translate(-50%, -50%) scale(1);
        box-shadow: 0 0  6px 2px rgba(255,255,255,0.9), 0 0 14px 4px rgba(168,85,247,0.6);
      }
      50% {
        transform: translate(-50%, -50%) scale(1.35);
        box-shadow: 0 0 10px 3px rgba(255,255,255,0.8), 0 0 22px 8px rgba(0,198,255,0.5);
      }
    }
  `;

  document.head.appendChild(styleTag);
}

function activateWand() {
  if (isActive) return;
  isActive = true;
  document.body.style.cursor = 'none';

  injectStyles();

  overlayEl = document.createElement('div');
  overlayEl.className = 'oxtools-box';
  document.body.appendChild(overlayEl);

  customCursor = document.createElement('div');
  customCursor.className = 'oxtools-cursor';
  document.body.appendChild(customCursor);

  document.addEventListener('mousemove', handleMouseMove, true);
  document.addEventListener('click', handleClick, true);
}

function deactivateWand() {
  isActive = false;
  document.body.style.cursor = '';

  overlayEl?.parentNode?.removeChild(overlayEl);
  customCursor?.parentNode?.removeChild(customCursor);
  overlayEl = null;
  customCursor = null;

  document.removeEventListener('mousemove', handleMouseMove, true);
  document.removeEventListener('click', handleClick, true);
}

function handleMouseMove(e: MouseEvent) {
  if (!isActive) return;

  // Move cursor dot
  if (customCursor) {
    customCursor.style.top  = `${e.clientY}px`;
    customCursor.style.left = `${e.clientX}px`;
  }

  // Fit outline box to hovered element
  if (overlayEl) {
    const target = e.target as HTMLElement;
    // Skip our own injected elements
    if (target === overlayEl || target === customCursor) return;

    const rect = target.getBoundingClientRect();

    // Guard: skip zero-size or full-viewport elements (body, html, etc.)
    const isFullPage =
      rect.width  >= window.innerWidth  * 0.95 &&
      rect.height >= window.innerHeight * 0.95;

    if (isFullPage || rect.width === 0 || rect.height === 0) {
      overlayEl.style.opacity = '0';
      return;
    }

    overlayEl.style.opacity = '1';
    overlayEl.style.top    = `${rect.top}px`;
    overlayEl.style.left   = `${rect.left}px`;
    overlayEl.style.width  = `${rect.width}px`;
    overlayEl.style.height = `${rect.height}px`;
  }
}

function handleClick(e: MouseEvent) {
  if (!isActive) return;
  e.preventDefault();
  e.stopPropagation();

  const rect = (e.target as HTMLElement).getBoundingClientRect();
  deactivateWand();

  console.log("Oxtools: Element captured — sending geometry to Side Panel.");
  chrome.runtime.sendMessage({
    action: "ELEMENT_CLICKED",
    payload: {
      top:             rect.top,
      left:            rect.left,
      width:           rect.width,
      height:          rect.height,
      devicePixelRatio: window.devicePixelRatio || 1,
      innerWidth:      window.innerWidth,
      innerHeight:     window.innerHeight,
    }
  });
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === "ACTIVATE_WAND") {
    activateWand();
    sendResponse({ success: true });
    return true;
  }
});
