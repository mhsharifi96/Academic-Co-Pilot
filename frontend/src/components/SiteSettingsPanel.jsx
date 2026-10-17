import { useCallback, useEffect, useState } from "react";
import * as api from "../api.js";

// The "Site" tab of the admin console: switches that apply to the whole
// deployment. Today that is just whether visitors may register; the backend
// stores it in the singleton `site_settings` row so it survives restarts.
export default function SiteSettingsPanel() {
  const [open, setOpen] = useState(null); // null while loading
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await api.getSiteSettings();
        if (!cancelled) setOpen(!!s.registration_open);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const toggle = useCallback(async () => {
    const next = !open;
    setSaving(true);
    setError(null);
    try {
      const s = await api.setRegistrationOpen(next);
      setOpen(!!s.registration_open);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }, [open]);

  if (loading) return <p className="empty-note">Loading settings…</p>;

  return (
    <>
      <p className="admin-sub">
        Switches that apply to the whole site. They take effect immediately, for
        everyone.
      </p>

      {error && <div className="banner-error">⚠️ {error}</div>}

      <div className="site-setting">
        <div className="site-setting-text">
          <strong>User registration</strong>
          <span className="site-setting-hint">
            {open
              ? "Anyone can create an account from the login screen."
              : "Sign-up is closed — the form is hidden and POST /auth/register is refused. Existing users can still log in, and you can still grant admin or credit here."}
          </span>
        </div>
        <button
          className={`admin-badge-btn${open ? " on" : ""}`}
          role="switch"
          aria-checked={!!open}
          disabled={saving}
          onClick={toggle}
        >
          {open ? "Open" : "Closed"}
        </button>
      </div>
    </>
  );
}
