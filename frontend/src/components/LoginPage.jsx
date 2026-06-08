import { useState } from "react";
import * as auth from "../auth.js";

export default function LoginPage({ onAuthed }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const isRegister = mode === "register";

  async function submit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const user = isRegister
        ? await auth.register(email.trim(), password)
        : await auth.login(email.trim(), password);
      onAuthed(user);
    } catch (err) {
      setError(err.message);
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

        {error && <div className="login-error">⚠️ {error}</div>}

        <button className="primary login-submit" disabled={busy} type="submit">
          {busy ? "Please wait…" : isRegister ? "Create account" : "Log in"}
        </button>

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
      </form>
    </div>
  );
}
