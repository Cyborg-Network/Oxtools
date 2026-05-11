console.log("Oxtools: Background Service Worker initialized!");

// 1. Auto-open Side Panel when the extension icon is clicked
chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);
});

// 2. Handle Screenshot Requests
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "TAKE_SCREENSHOT") {
    console.log("📸 Screenshot requested by tab:", sender.tab?.id, "window:", sender.tab?.windowId);

    const targetWindowId = sender.tab?.windowId;
    if (!targetWindowId) {
      console.error("❌ No windowId found on sender!");
      sendResponse({ error: "No windowId found on sender tab" });
      return true;
    }

    try {
      chrome.tabs.captureVisibleTab(
        targetWindowId,
        { format: "png" },
        (dataUrl) => {
          if (chrome.runtime.lastError) {
            console.error("❌ Capture failed:", chrome.runtime.lastError.message);
            sendResponse({ error: chrome.runtime.lastError.message });
            return;
          }
          if (!dataUrl) {
            console.error("❌ Capture succeeded but dataUrl is undefined/empty!");
            sendResponse({ error: "Capture succeeded but dataUrl is empty" });
            return;
          }
          console.log("✅ Screenshot captured. Length:", dataUrl.length);
          sendResponse({ dataUrl: dataUrl });
        }
      );
    } catch (err: any) {
      console.error("❌ Sync exception during capture:", err);
      sendResponse({ error: err.message || "Unknown synchronous error in background" });
    }
    return true; 
  }
});
