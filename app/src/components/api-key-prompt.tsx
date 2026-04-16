"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
} from "@ansospace/ui";
import { AlertTriangle, ExternalLink, Key } from "lucide-react";

export function ApiKeyPrompt() {
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const pathname = usePathname();

  // Show modal only on the tools pages if no key is set yet
  useEffect(() => {
    // Only trigger on actual app routes, not the landing page
    if (!pathname?.startsWith("/tools")) return;

    const existingKey = localStorage.getItem("oxloApiKey");
    const hasSkipped = sessionStorage.getItem("skippedApiKey");

    if (!existingKey && !hasSkipped) {
      // Small delay so it doesn't flash instantly
      const t = setTimeout(() => setOpen(true), 1500);
      return () => clearTimeout(t);
    }
  }, [pathname]);

  const handleSave = () => {
    if (apiKey.trim()) {
      localStorage.setItem("oxloApiKey", apiKey.trim());
      setOpen(false);
    }
  };

  const handleSkip = () => {
    sessionStorage.setItem("skippedApiKey", "true");
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5 text-primary" />
            Set Up Your API Key
          </DialogTitle>
          <DialogDescription>
            Oxtools is powered by the Oxlo.ai platform. To ensure unrestricted limits and faster
            responses, please provide your own free API key.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="promptApiKey">Oxlo API Key</Label>
            <Input
              id="promptApiKey"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="ox-..."
              type="password"
              autoFocus
            />
          </div>

          <div className="rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-600 dark:text-amber-400">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="space-y-1 text-xs">
                <p>
                  <strong>Why do I need a key?</strong> Shared keys hit rate limits quickly. Getting
                  your own takes 10 seconds and is permanently free.
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-md bg-muted p-3 text-xs leading-relaxed text-muted-foreground">
            <p className="mb-2">Don&apos;t have an API key? Grab one instantly!</p>
            <p>
              Use promo code <code className="font-bold text-foreground">OXZ54MPIYV</code> during
              signup to get your free tier activated at:
            </p>
            <a
              href="https://portal.oxlo.ai/signup"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 flex items-center gap-1 font-medium text-primary hover:underline"
            >
              portal.oxlo.ai/signup <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="ghost" onClick={handleSkip} className="w-full sm:w-auto">
            Skip for now
          </Button>
          <Button onClick={handleSave} className="w-full sm:w-auto" disabled={!apiKey.trim()}>
            Save & Continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
