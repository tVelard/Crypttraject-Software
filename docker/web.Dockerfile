# CryptTraject landing page (React + Vite) served by nginx.
#
# Two-stage build: node compiles, nginx serves. The final image is ~20 MB
# instead of carrying the whole node toolchain into production.

# ---------- stage 1 — build with Node ----------------------------------------
FROM node:20-alpine AS builder

WORKDIR /web

# Install deps first so they're cached as long as package.json is stable.
COPY web/package.json web/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY web/ ./
RUN npm run build

# ---------- stage 2 — serve with nginx ---------------------------------------
FROM nginx:1.27-alpine AS runtime

# A minimal nginx config: gzip on, SPA fallback to index.html so
# client-side navigation (if added later) doesn't 404.
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /web/dist /usr/share/nginx/html

EXPOSE 80
