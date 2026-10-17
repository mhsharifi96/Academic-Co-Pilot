import { useEffect, useRef } from "react";

// Cloudflare Turnstile widget, rendered explicitly so the login screen (which
// stays mounted after a failed attempt) can reset it: tokens are single-use, so
// every submit needs a fresh one. Bump `resetKey` after each request.
const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

let scriptPromise = null;

function loadScript() {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = SCRIPT_SRC;
      s.async = true;
      s.defer = true;
      s.onload = () => resolve(window.turnstile);
      s.onerror = () => {
        scriptPromise = null;
        reject(new Error("Could not load the CAPTCHA. Check your connection and reload."));
      };
      document.head.appendChild(s);
    });
  }
  return scriptPromise;
}

export default function Turnstile({ siteKey, action, resetKey, onToken, onError, theme = "dark" }) {
  const boxRef = useRef(null);
  const widgetRef = useRef(null);
  // Callbacks in refs so a parent's inline functions don't re-render the widget.
  const onTokenRef = useRef(onToken);
  const onErrorRef = useRef(onError);
  onTokenRef.current = onToken;
  onErrorRef.current = onError;

  // (Re)render whenever the site key or action changes.
  useEffect(() => {
    let cancelled = false;
    loadScript()
      .then((ts) => {
        if (cancelled || !boxRef.current) return;
        widgetRef.current = ts.render(boxRef.current, {
          sitekey: siteKey,
          action,
          theme,
          callback: (token) => onTokenRef.current?.(token),
          "expired-callback": () => onTokenRef.current?.(null),
          "error-callback": () => {
            onTokenRef.current?.(null);
            onErrorRef.current?.("The CAPTCHA could not be completed. Please try again.");
          },
        });
      })
      .catch((e) => onErrorRef.current?.(e.message));
    return () => {
      cancelled = true;
      if (widgetRef.current != null && window.turnstile) {
        window.turnstile.remove(widgetRef.current);
      }
      widgetRef.current = null;
    };
  }, [siteKey, action, theme]);

  // Fresh challenge after each submit.
  useEffect(() => {
    if (!resetKey || widgetRef.current == null || !window.turnstile) return;
    onTokenRef.current?.(null);
    window.turnstile.reset(widgetRef.current);
  }, [resetKey]);

  return <div ref={boxRef} className="turnstile-box" />;
}
