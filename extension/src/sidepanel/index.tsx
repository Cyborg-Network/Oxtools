// @ts-ignore
import '../index.css';
import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

interface ElementRect {
  top: number;
  left: number;
  width: number;
  height: number;
  devicePixelRatio: number;
  innerWidth: number;
  innerHeight: number;
}

function cropImage(dataUrl: string, rect: ElementRect): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      // Use the captured image dimensions vs the page viewport to compute scale
      const scaleX = img.width / rect.innerWidth;
      const scaleY = img.height / rect.innerHeight;

      canvas.width = rect.width * scaleX;
      canvas.height = rect.height * scaleY;

      const ctx = canvas.getContext('2d');
      ctx?.drawImage(
        img,
        rect.left * scaleX,
        rect.top * scaleY,
        rect.width * scaleX,
        rect.height * scaleY,
        0, 0,
        canvas.width,
        canvas.height
      );

      const base64 = canvas.toDataURL('image/jpeg', 0.95);
      // Strip the data URI prefix before sending to the API
      resolve(base64.replace(/^data:image\/(png|jpeg|jpg);base64,/, ''));
    };
    img.src = dataUrl;
  });
}

export default function SidePanel() {
  const [loading, setLoading] = useState(false);
  const [resultHtml, setResultHtml] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'preview' | 'code'>('preview');
  const [status, setStatus] = useState<string>('');

  useEffect(() => {
    const messageListener = async (request: any) => {

      // ── ELEMENT_CLICKED: content script clicked an element ──────────────────
      // This is the NEW architecture. The side panel captures the screenshot
      // directly, bypassing the Chrome bug where captureVisibleTab returns
      // undefined when the Side Panel is the focused window.
      if (request.action === "ELEMENT_CLICKED") {
        setLoading(true);
        setResultHtml(null);
        setStatus('📸 Capturing screenshot...');

        try {
          const rect: ElementRect = request.payload;

          // Find the tab that has the content script (the active web page)
          const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
          const targetTab = tabs.find(t =>
            t.url &&
            !t.url.startsWith('chrome://') &&
            !t.url.startsWith('devtools://') &&
            !t.url.startsWith('chrome-extension://')
          );

          if (!targetTab?.windowId) {
            throw new Error('Could not find the web page window to screenshot');
          }

          console.log(`📸 Capturing window ${targetTab.windowId} (tab: ${targetTab.id})`);

          // Capture the screenshot directly from the Side Panel.
          // This works because the side panel calls captureVisibleTab with the
          // explicit windowId of the web page, not the side panel's own window.
          const dataUrl = await new Promise<string>((resolve, reject) => {
            chrome.tabs.captureVisibleTab(
              targetTab.windowId!,
              { format: 'png' },
              (url) => {
                if (chrome.runtime.lastError) {
                  reject(new Error(chrome.runtime.lastError.message));
                } else if (!url) {
                  reject(new Error('captureVisibleTab returned empty dataUrl'));
                } else {
                  resolve(url);
                }
              }
            );
          });

          console.log(`✅ Screenshot captured (${dataUrl.length} chars). Cropping...`);
          setStatus('✂️ Cropping element...');

          const croppedBase64 = await cropImage(dataUrl, rect);
          console.log(`✅ Cropped (${croppedBase64.length} chars). Sending to backend...`);
          setStatus('🤖 AI is generating code...');

          const response = await fetch('http://localhost:9080/api/tools/screenshot-to-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: croppedBase64 }),
          });

          if (!response.ok) {
            const text = await response.text();
            throw new Error(`Backend error ${response.status}: ${text}`);
          }

          const data = await response.json();

          if (data.code) {
            setResultHtml(data.code);
            setActiveTab('preview');
            setStatus('');
          } else if (data.error) {
            throw new Error(`Backend: ${data.error}`);
          } else {
            throw new Error('Backend returned no code and no error');
          }
        } catch (error: any) {
          console.error('❌ Pipeline failed:', error);
          setStatus('');
          setResultHtml(
            `<!-- Error -->\n<div style="color:#ef4444;padding:1rem;font-family:monospace;font-size:13px;background:#1a1a1a;height:100vh">` +
            `<b>❌ Error</b><br><br>${error.message}</div>`
          );
          setActiveTab('code');
        } finally {
          setLoading(false);
        }
      }
    };

    chrome.runtime.onMessage.addListener(messageListener);
    return () => chrome.runtime.onMessage.removeListener(messageListener);
  }, []);

  const activateMagicWand = async () => {
    const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    const targetTab = tabs.find(t =>
      t.url &&
      !t.url.startsWith('chrome://') &&
      !t.url.startsWith('devtools://') &&
      !t.url.startsWith('chrome-extension://')
    );

    if (!targetTab?.id) {
      console.error('❌ No valid tab found:', tabs.map(t => t.url));
      return;
    }

    const tabId = targetTab.id;
    console.log(`🎯 Targeting tab ${tabId}: ${targetTab.url}`);

    // Inject the content script if it isn't already in this tab
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => (window as any).__oxtools_injected === true,
      });

      const alreadyInjected = results?.[0]?.result === true;

      if (!alreadyInjected) {
        console.log('💉 Injecting content script...');
        const manifest = chrome.runtime.getManifest();
        const contentScriptFile = manifest.content_scripts?.[0]?.js?.[0];

        if (!contentScriptFile) {
          console.error('❌ Cannot find content script file in manifest');
          return;
        }

        await chrome.scripting.executeScript({ target: { tabId }, files: [contentScriptFile] });
        await new Promise(r => setTimeout(r, 150));
      } else {
        console.log('✅ Content script already present.');
      }
    } catch (err) {
      console.error('❌ Failed to inject content script:', err);
      return;
    }

    // Send ACTIVATE_WAND to the injected content script
    try {
      const response = await chrome.tabs.sendMessage(tabId, { action: 'ACTIVATE_WAND' });
      console.log('✅ Wand activated!', response);
    } catch (err) {
      console.error('❌ Still could not reach content script after injection:', err);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-zinc-900 text-white font-sans">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-zinc-800 bg-zinc-950">
        <h1 className="text-base font-semibold tracking-tight text-zinc-100">
          Oxtools: Screen to Code
        </h1>
      </div>

      {/* State 1: Ready */}
      {!resultHtml && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-6">
          <div className="space-y-2">
            <p className="text-sm text-zinc-400">
              Click the wand, then hover and click any element on the page.
            </p>
            <p className="text-xs text-zinc-600">
              The AI will convert it to pixel-perfect HTML.
            </p>
          </div>
          <button
            onClick={activateMagicWand}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 active:scale-95 text-white text-sm font-medium rounded-lg shadow-lg transition-all duration-150"
          >
            🪄 Activate Magic Wand
          </button>
        </div>
      )}

      {/* State 2: Loading */}
      {loading && (
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium text-zinc-400 animate-pulse">{status || 'Working...'}</p>
        </div>
      )}

      {/* State 3: Results */}
      {resultHtml && !loading && (
        <div className="flex flex-col h-full overflow-hidden">
          <div className="flex bg-zinc-950 border-b border-zinc-800">
            <button
              onClick={() => setActiveTab('preview')}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'preview' ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/5' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              Preview
            </button>
            <button
              onClick={() => setActiveTab('code')}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'code' ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/5' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              Code
            </button>
          </div>

          <div className="flex-1 overflow-hidden relative bg-zinc-950">
            {activeTab === 'preview' ? (
              <div className="absolute inset-0 p-4">
                <div className="w-full h-full bg-white rounded-xl shadow-inner border border-zinc-800 overflow-hidden">
                  <iframe srcDoc={resultHtml} className="w-full h-full border-0" sandbox="allow-scripts" />
                </div>
              </div>
            ) : (
              <div className="absolute inset-0 p-4">
                <div className="w-full h-full bg-[#0d0d0d] rounded-xl border border-zinc-800 overflow-auto">
                  <pre className="p-4 text-xs font-mono text-green-400 whitespace-pre-wrap">
                    {resultHtml}
                  </pre>
                </div>
              </div>
            )}
          </div>

          <div className="p-4 border-t border-zinc-800 bg-zinc-950">
            <button
              onClick={() => { setResultHtml(null); setStatus(''); }}
              className="w-full py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm font-medium rounded-lg transition-colors"
            >
              Clear & Start Over
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const container = document.getElementById('root');
if (container) createRoot(container).render(<SidePanel />);
