# =============================================================================
# Oxtools — Unified Docker Image
# =============================================================================
# This single container serves ALL Oxtools (12+ AI tools) on one port.
# No more per-tool Docker deployments!
#
# Build:  docker build -t oxtools .
# Run:    docker run -p 3000:3000 -e OXLO_API_KEY=your_key oxtools
# =============================================================================

FROM node:22-alpine AS base
WORKDIR /app

# Enable pnpm via corepack
RUN corepack enable pnpm

# ---------------------------------------------------------------------------
# Dependencies layer (cached unless lock file changes)
# ---------------------------------------------------------------------------
FROM base AS deps
COPY pnpm-lock.yaml package.json ./
RUN pnpm install --frozen-lockfile

# ---------------------------------------------------------------------------
# Build layer
# ---------------------------------------------------------------------------
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

# ---------------------------------------------------------------------------
# Production image
# ---------------------------------------------------------------------------
FROM base AS runner
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
