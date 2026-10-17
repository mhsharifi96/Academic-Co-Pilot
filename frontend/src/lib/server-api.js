import "server-only";
import { cache } from "react";

// Server-side reads of the public wizard catalogue, used to render the landing
// and wizard pages as real HTML for crawlers. These talk to FastAPI directly
// (not through the /api rewrite) and never carry a token.

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const TIMEOUT_MS = 8000;

async function get(path) {
  return fetch(`${BACKEND_URL}/api/v1${path}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
}

// Published wizards for the landing grid. Returns `{ wizards, error }` rather
// than throwing so a backend hiccup degrades to a message, not a 500 page.
export async function fetchWizards(lang) {
  try {
    const res = await get(`/wizards?lang=${encodeURIComponent(lang)}`);
    if (!res.ok) return { wizards: [], error: `Error ${res.status}` };
    return { wizards: (await res.json()) || [], error: "" };
  } catch (e) {
    return { wizards: [], error: e?.message || "Could not reach the server." };
  }
}

// One published wizard, or `null` when it doesn't exist (→ a real 404). Any
// other failure throws so the error page renders instead of a false "not found".
// Wrapped in `cache` so generateMetadata and the page share one request.
export const fetchWizard = cache(async function fetchWizard(slug, lang) {
  const res = await get(
    `/wizards/${encodeURIComponent(slug)}?lang=${encodeURIComponent(lang)}`
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load wizard (${res.status})`);
  return res.json();
});

// Canonical origin for absolute URLs (canonical links, Open Graph, sitemap).
export const SITE_URL = (process.env.SITE_URL || "https://academic.hiagent.me").replace(
  /\/+$/,
  ""
);
