"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import ChatApp from "../../../../components/ChatApp.jsx";
import { safeNext, useAuthUser } from "../../../../components/AuthGate.jsx";

// /app — the chat application, and the login screen for every signed-in route.
// A page that needed an account sends the visitor here with `?next=<path>`;
// once signed in (or if they already were) they continue there.
export default function AppPage() {
  const { user, setUser, ready } = useAuthUser();
  const router = useRouter();

  useEffect(() => {
    if (!user) return;
    const next = safeNext(new URLSearchParams(window.location.search).get("next"));
    if (next) router.replace(next);
  }, [user, router]);

  if (!ready) return null;
  return <ChatApp user={user} setUser={setUser} />;
}
