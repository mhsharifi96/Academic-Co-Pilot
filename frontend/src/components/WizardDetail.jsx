import { useEffect, useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import { navigate } from "../router.js";
import LangToggle from "./LangToggle.jsx";
import Icon from "./Icon.jsx";

// Public detail page for one wizard: what it is and the path it walks you
// through.  "Start" needs an account, so a signed-out visitor is sent to the
// app's login screen with the wizard remembered (`onRequireLogin`).
export default function WizardDetail({ slug, user, onRequireLogin }) {
  const { t, lang } = useT();
  const [wizard, setWizard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .getWizard(slug, lang)
      .then((w) => {
        if (!cancelled) setWizard(w);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug, lang]);

  async function start() {
    if (!user) {
      onRequireLogin?.(slug);
      return;
    }
    setStarting(true);
    setError("");
    try {
      const run = await api.startWizardRun({ slug }, lang);
      navigate(`/runs/${encodeURIComponent(run.id)}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="wz-landing">
      <header className="wz-topbar">
        <a className="wz-brand" href="#/">
          <Icon name="sparkles" size={20} />
          <span>Academic Co-Pilot</span>
        </a>
        <div className="wz-topbar-actions">
          <LangToggle compact />
          <button className="wz-btn ghost" onClick={() => navigate("/")}>
            {t("wizard.back")}
          </button>
        </div>
      </header>

      <section className="wz-detail">
        {loading ? (
          <p className="wz-muted">{t("common.loading")}</p>
        ) : !wizard ? (
          <div className="wz-empty">
            <p>{t("wizard.notFound")}</p>
            <button className="wz-btn ghost" onClick={() => navigate("/")}>
              {t("wizard.back")}
            </button>
          </div>
        ) : (
          <>
            <div className="wz-detail-head">
              <span className="wz-card-icon large">
                <Icon name={wizard.icon} size={28} />
              </span>
              <div>
                <h1 className="wz-detail-title">{wizard.title}</h1>
                <p className="wz-chip">
                  {t("wizard.steps", { n: wizard.step_count })}
                </p>
              </div>
            </div>

            {wizard.short_description && (
              <p className="wz-detail-desc">{wizard.short_description}</p>
            )}

            {error && <div className="banner-error">⚠️ {error}</div>}

            <button
              className="wz-btn primary large"
              onClick={start}
              disabled={starting || wizard.step_count === 0}
            >
              {starting
                ? t("common.loading")
                : !user
                ? t("wizard.signInToStart")
                : t("wizard.startOrContinue")}
              <Icon name="arrow" size={18} className="wz-go-arrow" />
            </button>

            <h2 className="wz-section-title small">{t("wizard.pathTitle")}</h2>
            {wizard.steps.length === 0 ? (
              <p className="wz-muted">{t("wizard.noSteps")}</p>
            ) : (
              <ol className="wz-path">
                {wizard.steps.map((s, i) => (
                  <li key={s.id} className="wz-path-item">
                    <span className="wz-path-num">{i + 1}</span>
                    <span className="wz-path-name">{s.name || `—`}</span>
                    <span className="wz-chip subtle">
                      {s.max_messages
                        ? t("wizard.capped", { n: s.max_messages })
                        : t("wizard.uncapped")}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </section>
    </div>
  );
}
