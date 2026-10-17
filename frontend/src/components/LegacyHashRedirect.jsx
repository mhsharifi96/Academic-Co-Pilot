"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// The Vite build used a hash router (#/wizards/x, #/runs/1, #/app). Old
// bookmarks and shared links still arrive at "/" with that hash; forward them to
// the real path. In-page anchors like #why don't start with "#/" and are left
// alone.
export default function LegacyHashRedirect() {
  const router = useRouter();
  useEffect(() => {
    const hash = window.location.hash;
    if (!hash.startsWith("#/")) return;
    const path = hash.slice(1).split("?")[0].replace(/\/+$/, "") || "/";
    const known = ["/wizards/", "/runs", "/app"].some((p) => path.startsWith(p));
    router.replace(path === "/" ? "/" : known ? path : "/app");
  }, [router]);
  return null;
}
