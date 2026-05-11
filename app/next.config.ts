import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    allowedDevOrigins: [
      "chrome-extension://poaainbnlkonlkjiiemhfoflbkobamec"
    ]
  },
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
};

export default nextConfig;
