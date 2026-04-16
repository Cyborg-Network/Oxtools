import type { Metadata } from "next";
import { Inter, Unbounded, JetBrains_Mono } from "next/font/google";

import { ThemeProvider, Toaster, TooltipProvider } from "@ansospace/ui";
import "@ansospace/ui/globals.css";
import "./oxtools-theme.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const unbounded = Unbounded({
  subsets: ["latin"],
  variable: "--font-unbounded",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: {
    default: "Oxtools - AI-Powered Developer Tools by Oxlo.ai",
    template: "%s | Oxtools",
  },
  description:
    "The open-source AI tools hub for developers. Debug code, generate tests, scan for vulnerabilities, convert data, and more - all powered by Oxlo.ai.",
  keywords: [
    "AI tools",
    "developer tools",
    "code debugger",
    "security scanner",
    "unit test generator",
    "SQL converter",
    "Oxlo.ai",
    "Oxtools",
    "open source",
    "LLM",
  ],
  authors: [{ name: "Cyborg Network" }, { name: "Oxlo.ai" }],
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    apple: "/favicon.ico",
  },
  openGraph: {
    title: "Oxtools - AI-Powered Developer Tools by Oxlo.ai",
    description:
      "25+ AI-powered developer tools in one place. Debug, test, scan, convert, and generate - powered by Oxlo.ai. Open source and community-driven.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${unbounded.variable} ${mono.variable}`}
    >
      <body className="min-h-screen bg-background font-sans antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider>{children}</TooltipProvider>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
