import { useEffect, useState } from "react";
import * as auth from "../auth.js";
import Turnstile from "./Turnstile.jsx";

export default function LoginPage({ onAuthed }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  // Admins can close sign-up site-wide (GET /auth/config). Assume open until we
  // know otherwise so the form never flickers between states on a slow network.
  const [registrationOpen, setRegistrationOpen] = useState(true);
  // Turnstile CAPTCHA: the site key arrives with /auth/config only when the
  // backend enforces it. Tokens are single-use, so the widget is reset after
  // every attempt (bumping captchaReset).
  const [siteKey, setSiteKey] = useState(null);
  const [captchaToken, setCaptchaToken] = useState(null);
  const [captchaReset, setCaptchaReset] = useState(0);

  useEffect(() => {
    let cancelled = false;
    auth.fetchAuthConfig().then((cfg) => {
      if (cancelled) return;
      const open = cfg?.registration_open !== false;
      setRegistrationOpen(open);
      setSiteKey(cfg?.turnstile_site_key || null);
      // If we were already on the sign-up tab, fall back to logging in.
      if (!open) setMode("login");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const isRegister = mode === "register";

  async function submit(e) {
    e.preventDefault();
    setError(null);
    if (siteKey && !captchaToken) {
      setError("Please complete the CAPTCHA first.");
      return;
    }
    setBusy(true);
    try {
      const user = isRegister
        ? await auth.register(email.trim(), password, captchaToken)
        : await auth.login(email.trim(), password, captchaToken);
      onAuthed(user);
    } catch (err) {
      setError(err.message);
      if (siteKey) setCaptchaReset((n) => n + 1);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <div className="login-brand">
          <span className="logo">📚</span>
          <h1>Academic Co-Pilot</h1>
        </div>
        <p className="login-sub">
          {isRegister ? "Create an account to get started." : "Sign in to continue."}
        </p>

        <label>
          Email
          <input
            type="email"
            value={email}
            autoComplete="email"
            required
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            autoComplete={isRegister ? "new-password" : "current-password"}
            required
            minLength={6}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>

        {siteKey && (
          <Turnstile
            siteKey={siteKey}
            action={isRegister ? "signup" : "login"}
            resetKey={captchaReset}
            onToken={setCaptchaToken}
            onError={setError}
          />
        )}

        {error && <div className="login-error">⚠️ {error}</div>}

        <button
          className="primary login-submit"
          disabled={busy || (siteKey && !captchaToken)}
          type="submit"
        >
          {busy ? "Please wait…" : isRegister ? "Create account" : "Log in"}
        </button>

        {registrationOpen ? (
          <div className="login-toggle">
            {isRegister ? "Already have an account?" : "New here?"}{" "}
            <button
              type="button"
              className="link-btn"
              onClick={() => {
                setError(null);
                setMode(isRegister ? "login" : "register");
              }}
            >
              {isRegister ? "Log in" : "Create one"}
            </button>
          </div>
        ) : (
          <div className="login-toggle login-closed">
            New sign-ups are currently closed. Ask an administrator for an
            account.
          </div>
        )}
      </form>
    </div>
  );
}
