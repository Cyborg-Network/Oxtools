// @ts-ignore
import '../index.css';

let overlay: HTMLDivElement | null = null;
let isActive = false;

console.log("✅ Oxtools: Content Script injected successfully!");
(window as any).__oxtools_injected = true;

function activateWand() {
  if (isActive) return;
  isActive = true;
  document.body.style.cursor = 'crosshair';

  overlay = document.createElement('div');
  overlay.style.position = 'fixed';
  overlay.style.border = '2px solid #3b82f6';
  overlay.style.backgroundColor = 'rgba(59, 130, 246, 0.15)';
  overlay.style.zIndex = '2147483647';
  overlay.style.pointerEvents = 'none';
  overlay.style.transition = 'all 0.1s ease';
  document.body.appendChild(overlay);

  document.addEventListener('mousemove', handleMouseMove, true);
  document.addEventListener('click', handleClick, true);
}

function deactivateWand() {
  isActive = false;
  document.body.style.cursor = '';
  if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
  overlay = null;
  document.removeEventListener('mousemove', handleMouseMove, true);
  document.removeEventListener('click', handleClick, true);
}

function handleMouseMove(e: MouseEvent) {
  if (!isActive || !overlay) return;
  const rect = (e.target as HTMLElement).getBoundingClientRect();
  overlay.style.top = `${rect.top}px`;
  overlay.style.left = `${rect.left}px`;
  overlay.style.width = `${rect.width}px`;
  overlay.style.height = `${rect.height}px`;
}

function handleClick(e: MouseEvent) {
  if (!isActive) return;
  e.preventDefault();
  e.stopPropagation();

  const target = e.target as HTMLElement;
  const rect = target.getBoundingClientRect();
  deactivateWand();

  console.log("📐 Element captured. Sending geometry to Side Panel for screenshot...");

  // NEW ARCHITECTURE: Send the element rect to the Side Panel.
  // The Side Panel will call captureVisibleTab directly — this bypasses
  // the Chrome bug where captureVisibleTab fails from background when
  // a Side Panel is open and focused.
  chrome.runtime.sendMessage({
    action: "ELEMENT_CLICKED",
    payload: {
      top: rect.top,
      left: rect.left,
      width: rect.width,
      height: rect.height,
      devicePixelRatio: window.devicePixelRatio || 1,
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
    }
  });
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === "ACTIVATE_WAND") {
    console.log("🪄 Wand activated by Side Panel!");
    activateWand();
    sendResponse({ success: true });
    return true;
  }
});
