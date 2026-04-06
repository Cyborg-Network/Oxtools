# =============================================================================
# Oxtools Project Dockerfile Template
# =============================================================================
#
# Instructions:
#   1. Replace the base image with whatever runtime your project needs.
#      Common choices:
#        - node:20-alpine         (Node.js)
#        - python:3.12-slim       (Python)
#        - golang:1.22-alpine     (Go)
#        - rust:1.78-slim         (Rust)
#
#   2. Update the WORKDIR, COPY, and RUN commands to match your project's
#      build process.
#
#   3. Expose the port your application listens on. This must match the
#      port_number in your oxlo-manifest.json.
#
#   4. Set a non-root USER for security — do not run as root in production.
#
# This example uses Node.js. Adapt it to your stack.
# =============================================================================

# --- Stage 1: Install dependencies ---
FROM node:20-alpine AS deps

WORKDIR /app

# Copy dependency manifests first so Docker can cache this layer.
# If your package files haven't changed, Docker skips this step on rebuild.
COPY package.json package-lock.json* ./

RUN npm ci --omit=dev


# --- Stage 2: Build the application (only needed for compiled/bundled stacks) ---
# Remove this stage entirely if your stack doesn't have a build step.
FROM node:20-alpine AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Add your build command here, e.g. npm run build, cargo build --release, etc.
# RUN npm run build


# --- Stage 3: Production runtime ---
FROM node:20-alpine AS runner

# Create a non-root user to run the application.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy only what the application needs to run.
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/src ./src
COPY package.json ./

# Switch to the non-root user.
USER appuser

# Expose the port your application listens on.
# Update this if your app uses a different port.
EXPOSE 3000

# Start the application.
CMD ["node", "src/index.js"]
