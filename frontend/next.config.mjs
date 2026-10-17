// The browser always calls the API with same-origin relative paths (/api/...),
// exactly as it did under Vite + nginx; Next forwards them to FastAPI.
//
// BACKEND_URL is read at BUILD time for the rewrite (Next bakes rewrites into
// the build manifest) — the Dockerfile passes it as a build arg. Server
// Components read it again at runtime for their own server-side fetches.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server bundle for the Docker image (.next/standalone).
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  experimental: {
    // Agent + LLM turns can run for minutes; the proxy default is 30s.
    proxyTimeout: 600_000,
  },
};

export default nextConfig;
