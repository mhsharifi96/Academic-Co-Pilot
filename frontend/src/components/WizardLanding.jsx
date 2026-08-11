import { useEffect, useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import { navigate } from "../router.js";
import LangToggle from "./LangToggle.jsx";
import WizardCard from "./WizardCard.jsx";
import Icon from "./Icon.jsx";

// The public landing page: hero, the catalogue of published wizards, and a
// short "how it works" band.  Renders for signed-out visitors, so it is mounted
// ahead of the app's auth gate and its data call carries no token.
export default function WizardLanding({ user }) {
  const { t, lang } = useT();
  const [wizards, setWizards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .listWizards(lang)
      .then((rows) => {
        if (!cancelled) setWizards(rows || []);
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
  }, [lang]);

  const steps = [
    { icon: "compass", title: t("landing.how1Title"), body: t("landing.how1Body") },
    { icon: "layers", title: t("landing.how2Title"), body: t("landing.how2Body") },
    { icon: "clock", title: t("landing.how3Title"), body: t("landing.how3Body") },
  ];

  return (
    <div className="wz-landing">
      <header className="wz-topbar">
        <a className="wz-brand" href="#/">
          <Icon name="sparkles" size={20} />
          <span>Academic Co-Pilot</span>
        </a>
        <div className="wz-topbar-actions">
          <LangToggle compact />
          <button className="wz-btn ghost" onClick={() => navigate("/app")}>
            {user ? t("nav.backToApp") : t("nav.signIn")}
          </button>
        </div>
      </header>

      <section className="wz-hero">
        <div className="wz-hero-aura" aria-hidden="true" />
        <p className="wz-eyebrow">{t("landing.eyebrow")}</p>
        <h1 className="wz-hero-title">{t("landing.title")}</h1>
        <p className="wz-hero-sub">{t("landing.subtitle")}</p>
        <div className="wz-hero-actions">
          <a className="wz-btn primary" href="#catalog">
            {t("landing.cta")}
            <Icon name="arrow" size={16} className="wz-go-arrow" />
          </a>
          {user && (
            <button className="wz-btn ghost" onClick={() => navigate("/runs")}>
              {t("nav.myRuns")}
            </button>
          )}
        </div>
      </section>

      <section className="wz-section" id="catalog">
        <h2 className="wz-section-title">{t("landing.catalogTitle")}</h2>
        <p className="wz-section-sub">{t("landing.catalogSubtitle")}</p>

        {error && <div className="banner-error">⚠️ {error}</div>}

        {loading ? (
          <p className="wz-muted">{t("landing.loading")}</p>
        ) : wizards.length === 0 ? (
          <div className="wz-empty">
            <p>{t("landing.empty")}</p>
            <p className="wz-muted">{t("landing.emptyHint")}</p>
          </div>
        ) : (
          <div className="wz-grid">
            {wizards.map((w, i) => (
              <WizardCard
                key={w.id}
                wizard={w}
                index={i}
                onOpen={(x) => navigate(`/wizards/${encodeURIComponent(x.slug)}`)}
              />
            ))}
          </div>
        )}
      </section>

      <section className="wz-section wz-how">
        <h2 className="wz-section-title">{t("landing.howTitle")}</h2>
        <ol className="wz-how-list">
          {steps.map((s, i) => (
            <li key={s.title} className="wz-how-item">
              <span className="wz-how-num">{i + 1}</span>
              <span className="wz-how-icon">
                <Icon name={s.icon} size={20} />
              </span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <footer className="wz-footer">
        <span>{t("landing.footer")}</span>
        <LangToggle compact />
      </footer>
    </div>
  );
}
