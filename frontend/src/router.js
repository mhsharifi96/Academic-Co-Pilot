// A tiny hash router.
//
// The app has no routing library and doesn't need one: there are a handful of
// destinations and no nested layouts.  Hash routes also keep deep links working
// in every deployment (Vite dev, nginx, file://) without touching server config.
//
// Routes:
//   #/                     public wizard landing page
//   #/wizards/:slug        public wizard detail
//   #/runs/:id             a wizard run (requires sign-in)
//   #/app                  the existing chat application
//   #/runs                 "my workflows"
//
// Wizard administration is NOT a route: it is a tab inside the app's Admin
// page, reached the same way every other in-app view is.

import { useEffect, useState } from "react";

function readHash() {
  const raw = window.location.hash || "";
  return raw.startsWith("#") ? raw.slice(1) : raw;
}

// Parse a path into { name, params }.  Unknown paths fall through to the app,
// so an old bookmark never lands on a blank screen.
export function parseRoute(path) {
  const clean = (path || "/").split("?")[0].replace(/\/+$/, "") || "/";
  const parts = clean.split("/").filter(Boolean);

  if (parts.length === 0) return { name: "landing", params: {} };
  if (parts[0] === "wizards" && parts[1]) {
    return { name: "wizard", params: { slug: decodeURIComponent(parts[1]) } };
  }
  if (parts[0] === "wizards") return { name: "landing", params: {} };
  if (parts[0] === "runs" && parts[1]) {
    return { name: "run", params: { runId: decodeURIComponent(parts[1]) } };
  }
  if (parts[0] === "runs") return { name: "runs", params: {} };
  return { name: "app", params: {} };
}

export function navigate(path) {
  const target = path.startsWith("#") ? path : `#${path}`;
  if (window.location.hash === target) return;
  window.location.hash = target;
}

// Replace the current entry instead of pushing one — used after a redirect so
// the back button doesn't bounce the user through the login gate again.
export function replace(path) {
  const target = path.startsWith("#") ? path : `#${path}`;
  window.history.replaceState(null, "", target);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function useHashRoute() {
  const [path, setPath] = useState(readHash);

  useEffect(() => {
    const onChange = () => setPath(readHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return { path, route: parseRoute(path) };
}
