"use client";

import { useEffect, useState } from "react";

import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Label,
} from "@ansospace/ui";
import { AlertTriangle, ExternalLink, Key, Settings } from "lucide-react";

export function SettingsDialog() {
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    if (open) {
      setApiKey(localStorage.getItem("oxloApiKey") || "");
    }
  }, [open]);

  useEffect(() => {
    const handleOpen = () => setOpen(true);
    window.addEventListener("open-settings", handleOpen);
    return () => window.removeEventListener("open-settings", handleOpen);
  }, []);

  const handleSave = () => {
    localStorage.setItem("oxloApiKey", apiKey.trim());
    setOpen(false);
  };

  const handleClear = () => {
    setApiKey("");
    localStorage.removeItem("oxloApiKey");
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors group-data-[collapsible=icon]:hidden">
        <Settings className="h-4 w-4" />
        <span>Settings</span>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Configuration
          </DialogTitle>
          <DialogDescription>
            Oxtools is powered by the Oxlo.ai platform. Provide your own API key to bypass public
            limits.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="apiKey">Oxlo API Key</Label>
            <Input
              id="apiKey"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="ox-..."
              type="password"
            />
          </div>

          <div className="rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-600 dark:text-amber-400">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="space-y-1 text-xs">
                <p>
                  <strong>Disclaimer:</strong> Your API key is stored locally in your browser&apos;s
                  <code> localStorage</code>. It is never stored on our servers.
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-md bg-muted p-3 text-xs leading-relaxed text-muted-foreground">
            <p className="mb-2">Don&apos;t have an API key? Getting one is completely free!</p>
            <p>
              Use promo code <code className="font-bold text-foreground">OXZ54MPIYV</code> during
              signup to grab your free API key at:
            </p>
            <a
              href="https://portal.oxlo.ai/signup"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 flex items-center gap-1 font-medium text-primary hover:underline block"
            >
              portal.oxlo.ai/signup <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleClear} className="w-full sm:w-auto">
            Clear Key
          </Button>
          <Button onClick={handleSave} className="w-full sm:w-auto">
            Save Settings
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
