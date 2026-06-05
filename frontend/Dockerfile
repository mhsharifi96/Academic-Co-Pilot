# ---------- build stage ----------
FROM node:20-alpine AS build
WORKDIR /app

# Install deps first (better layer caching). No lockfile is committed yet, so
# use `npm install` rather than `npm ci`.
COPY package.json ./
RUN npm install

# Build the production bundle into /app/dist
COPY . .
RUN npm run build

# ---------- serve stage ----------
FROM nginx:1.27-alpine

# SPA routing + /api reverse-proxy to the backend service.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static assets produced by the build stage.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
