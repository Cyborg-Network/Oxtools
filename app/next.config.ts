import type { NextConfig } from "next";

const OXCODE = "https://www.oxcode.ai";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Proxy tier2 streaming tool requests directly to the Python runner,
  // bypassing the Next.js API route runtime which kills long-lived streams.
  async rewrites() {
    const runnerUrl = process.env.TOOL_RUNNER_URL || "http://localhost:9080";
    return [
      {
        source: "/api/tools-stream/:toolId",
        destination: `${runnerUrl}/api/tools/:toolId`,
      },
    ];
  },
  async redirects() {
    return [
      // Root needs its own rule: the catch-all param below cannot match an empty path.
      { source: "/", destination: OXCODE, permanent: false },
      // api/ is excluded because redirects run before rewrites — catching it
      // would disable the tool route handler and the streaming proxy above.
      { source: "/:path((?!api/).*)", destination: OXCODE, permanent: false },
    ];
  },
};

export default nextConfig;
