// @ts-ignore
import '../index.css';
import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Wand2, Copy, Check } from 'lucide-react';

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
      resolve(base64.replace(/^data:image\/(png|jpeg|jpg);base64,/, ''));
    };
    img.src = dataUrl;
  });
}

export default function SidePanel() {
  const [loading, setLoading] = useState(false);
  const [resultHtml, setResultHtml] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');
  const [copied, setCopied] = useState(false);


  useEffect(() => {
    const messageListener = async (request: any) => {
      if (request.action === "ELEMENT_CLICKED") {
        setLoading(true);
        setResultHtml(null);
        setStatus('Capturing screenshot...');

        try {
          const rect: ElementRect = request.payload;

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

          setStatus('Cropping element...');
          const croppedBase64 = await cropImage(dataUrl, rect);
          
          setStatus('AI generating code...');
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
            setResultHtml(data.code as string);
            setStatus('');
          } else if (data.error) {
            throw new Error(`Backend: ${data.error}`);
          } else {
            throw new Error('Backend returned no code and no error');
          }
        } catch (error: any) {
          console.error('Pipeline failed:', error);
          setStatus('');
          setResultHtml(
            `<!-- Error -->\n<div style="color:#ff4a4a;padding:1rem;font-family:monospace;font-size:13px;">` +
            `<b>Error</b><br><br>${error.message}</div>`
          );
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
      console.error('No valid tab found.');
      return;
    }

    const tabId = targetTab.id;

    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => (window as any).__oxtools_injected === true,
      });

      const alreadyInjected = results?.[0]?.result === true;

      if (!alreadyInjected) {
        const manifest = chrome.runtime.getManifest();
        const contentScriptFile = manifest.content_scripts?.[0]?.js?.[0];

        if (contentScriptFile) {
          await chrome.scripting.executeScript({ target: { tabId }, files: [contentScriptFile] });
          await new Promise(r => setTimeout(r, 150));
        }
      }
    } catch (err) {
      console.error('Failed to inject content script:', err);
      return;
    }

    try {
      await chrome.tabs.sendMessage(tabId, { action: 'ACTIVATE_WAND' });
    } catch (err) {
      console.error('Could not reach content script:', err);
    }
  };

  const copyToClipboard = async () => {
    if (!resultHtml) return;
    try {
      await navigator.clipboard.writeText(resultHtml);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-oled text-zinc-200 font-sans relative overflow-hidden">
      
      {/* Background Meshes */}
      <div className="mesh-bg">
        <div className="mesh-flare" />
        <div className="mesh-flare-2" />
      </div>

      {/* Main Glassmorphism Container */}
      <div className="relative z-10 flex flex-col h-full glass-container">
        
        {/* Header removed to avoid duplication with Chrome's native panel header */}

        {/* State 1: Ready */}
        {!resultHtml && !loading && (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-8 animate-fade-up">
            <div className="space-y-3 max-w-[280px]">
              <p className="text-[13px] leading-relaxed text-[#a1a1aa]">
                Click the wand, then hover and click any element on the page. The AI will convert it to pixel-perfect HTML.
              </p>
            </div>
            <button
              onClick={activateMagicWand}
              className="flex items-center gap-2.5 px-6 py-3 rounded-lg text-sm font-medium tracking-wide wand-button wand-button-breathing"
            >
              <Wand2 size={16} className="text-white/80" />
              Activate Magic Wand
            </button>
          </div>
        )}

        {/* State 2: Loading */}
        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center space-y-5 animate-fade-up">
            <div className="w-8 h-8 border-[2px] border-white/10 border-t-white/80 rounded-full animate-spin" />
            <p className="text-[13px] font-medium tracking-wide text-[#a1a1aa] animate-pulse">
              {status || 'Working...'}
            </p>
          </div>
        )}

        {/* State 3: Results */}
        {resultHtml && !loading && (
          <div className="flex flex-col flex-1 overflow-hidden animate-fade-up">
            
            {/* Top Half: Preview — full desktop width scaled to fit panel */}
            {/* 
            <div className="flex-shrink-0 h-[45%] flex flex-col border-b border-white/5">
              <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between bg-[#050505]">
                <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Preview</span>
                <span className="text-[10px] text-zinc-600">Live render · {Math.round(previewScale * 100)}%</span>
              </div>
              <div ref={previewContainerRef} className="flex-1 relative overflow-hidden bg-[#111]">
                <div style={{ width: DESKTOP_WIDTH, height: `${100 / previewScale}%`, transform: `scale(${previewScale})`, transformOrigin: 'top left' }}>
                  <iframe
                    ref={iframeRef}
                    src={chrome.runtime.getURL("src/sandbox/frame.html")}
                    style={{ width: '100%', height: '100%', border: 'none', display: 'block' }}
                    title="Live Preview"
                    onLoad={() => {
                      if (resultHtml && tailwindScript && iframeRef.current?.contentWindow) {
                        iframeRef.current.contentWindow.postMessage({ html: resultHtml, tailwind: tailwindScript }, '*');
                      }
                    }}
                  />
                </div>
              </div>
            </div>
            */}

            {/* Bottom Half: Code Editor */}
            <div className="flex-1 flex flex-col min-h-0 bg-[#0d0d0d]">
              <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-[#050505]">
                <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Source Code</span>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={copyToClipboard}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 transition-colors text-zinc-300 hover:text-white"
                  >
                    {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    <span className="text-[11px] font-medium tracking-wide">{copied ? 'Copied!' : 'Copy Code'}</span>
                  </button>

                  <button
                    onClick={() => chrome.tabs.create({ url: 'https://html.onlineviewer.net/' })}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 transition-colors text-zinc-300 hover:text-white"
                  >
                    <span className="text-[11px] font-medium tracking-wide">Open Preview ↗</span>
                  </button>
                </div>
              </div>
              
              <div className="flex-1 overflow-auto relative">
                <SyntaxHighlighter
                  language="html"
                  style={vscDarkPlus}
                  customStyle={{
                    margin: 0,
                    padding: '16px',
                    fontSize: '12px',
                    fontFamily: "'JetBrains Mono', 'Fira Code', 'Menlo', monospace",
                    background: 'transparent',
                    lineHeight: '1.6'
                  }}
                  wrapLines={true}
                  wrapLongLines={true}
                >
                  {resultHtml}
                </SyntaxHighlighter>
              </div>
            </div>

            <div className="p-4 border-t border-white/5 bg-[#050505]">
              <button
                onClick={() => { 
                  setResultHtml(null); 
                  setStatus(''); 
                }}
                className="w-full py-2.5 bg-white/5 hover:bg-white/10 text-white text-sm font-medium tracking-wide rounded-lg transition-colors border border-white/5"
              >
                Clear & Start Over
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const container = document.getElementById('root');
if (container) createRoot(container).render(<SidePanel />);
