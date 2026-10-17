"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import * as auth from "../auth.js";

// Client-side auth for the app routes. The JWT lives in localStorage, so the
// server can't know who is signed in: these hooks report `ready: false` until
// mounted, and callers render nothing until then (no login-screen flash).

export function useAuthUser() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setUser(auth.getUser());
    setReady(true);
    // The 401 handler fires from anywhere in the app; clearing `user` here is
    // what swaps the tree back to the login screen.
    const onLogout = () => setUser(null);
    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, []);
  return { user, setUser, ready };
}

// Only same-site paths are honoured as a post-login destination, so a crafted
// `?next=https://evil.example` link can't bounce a fresh login off-site.
export function safeNext(raw) {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) {
    return null;
  }
  return raw;
}

// Wraps a page that needs an account: a signed-out visitor is sent to the login
// screen at /app with this page as `next`, and comes straight back afterwards.
export default function RequireAuth({ children }) {
  const { user, ready } = useAuthUser();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (ready && !user) router.replace(`/app?next=${encodeURIComponent(pathname)}`);
  }, [ready, user, pathname, router]);

  if (!ready || !user) return null;
  return children;
}
