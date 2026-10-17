"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import { useStoredUser } from "./UserAware.jsx";
import Icon from "./Icon.jsx";

// "Start" on a wizard's public page. Needs an account, so a signed-out visitor
// is sent to the app's login screen with this page as `next`, and lands back
// here after signing in.
export default function StartWizardButton({ slug, returnPath, disabled }) {
  const { t, lang } = useT();
  const router = useRouter();
  const user = useStoredUser();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  async function start() {
    if (!user) {
      router.push(`/app?next=${encodeURIComponent(returnPath)}`);
      return;
    }
    setStarting(true);
    setError("");
    try {
      const run = await api.startWizardRun({ slug }, lang);
      router.push(`/runs/${encodeURIComponent(run.id)}`);
    } catch (e) {
      setError(e.message);
      setStarting(false);
    }
  }

  return (
    <>
      {error && <div className="banner-error">⚠️ {error}</div>}
      <button
        className="wz-btn primary large"
        onClick={start}
        disabled={starting || disabled}
      >
        {starting
          ? t("common.loading")
          : !user
          ? t("wizard.signInToStart")
          : t("wizard.startOrContinue")}
        <Icon name="arrow" size={18} className="wz-go-arrow" />
      </button>
    </>
  );
}
