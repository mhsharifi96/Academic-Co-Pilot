"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import * as auth from "../auth.js";
import { useT } from "../i18n.js";
import Icon from "./Icon.jsx";

// Small client islands for the server-rendered public pages: the only parts of
// those pages that depend on whether the visitor is signed in. The JWT lives in
// localStorage, which the server can't see, so these render the signed-out
// variant first (matching the server HTML) and update after mount.

export function useStoredUser() {
  const [user, setUser] = useState(null);
  useEffect(() => {
    setUser(auth.getUser());
    const onLogout = () => setUser(null);
    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, []);
  return user;
}

// "Sign in" for visitors, "Open the app" for signed-in users.
export function AppLink({ className = "wz-btn ghost", signedOutKey = "nav.signIn", arrow = false }) {
  const { t } = useT();
  const user = useStoredUser();
  return (
    <Link className={className} href="/app" prefetch={false}>
      {user ? t("nav.backToApp") : t(signedOutKey)}
      {arrow && <Icon name="arrow" size={16} className="wz-go-arrow" />}
    </Link>
  );
}

// Only shown to signed-in users.
export function MyRunsLink({ className = "wz-btn ghost" }) {
  const { t } = useT();
  const user = useStoredUser();
  if (!user) return null;
  return (
    <Link className={className} href="/runs" prefetch={false}>
      {t("nav.myRuns")}
    </Link>
  );
}
