import { useEffect, useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import { navigate } from "../router.js";
import LangToggle from "./LangToggle.jsx";
import WizardCard from "./WizardCard.jsx";
import Icon from "./Icon.jsx";

// The public landing page: hero, "why us", the catalogue of published wizards,
// a "how it works" band and how to top up the wallet.  Renders for signed-out
// visitors, so it is mounted ahead of the app's auth gate and its data call
// carries no token.

// In-page links scroll rather than set `href="#id"`: the app uses a hash
// router, so `#catalog` would parse as an unknown route and open the app.
function scrollToSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

// Keep <title> and the meta description in the visitor's language. The static
// English copies in index.html are what non-JS crawlers see.
function useDocumentMeta(title, description) {
  useEffect(() => {
    const prevTitle = document.title;
    document.title = title;
    const meta = document.querySelector('meta[name="description"]');
    const prevDesc = meta?.getAttribute("content");
    meta?.setAttribute("content", description);
    return () => {
      document.title = prevTitle;
      if (meta && prevDesc != null) meta.setAttribute("content", prevDesc);
    };
  }, [title, description]);
}
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

  useDocumentMeta(t("landing.metaTitle"), t("landing.metaDescription"));

  const reasons = [
    { icon: "quote", title: t("landing.why1Title"), body: t("landing.why1Body") },
    { icon: "search", title: t("landing.why2Title"), body: t("landing.why2Body") },
    { icon: "document", title: t("landing.why3Title"), body: t("landing.why3Body") },
    { icon: "chart", title: t("landing.why4Title"), body: t("landing.why4Body") },
    { icon: "layers", title: t("landing.why5Title"), body: t("landing.why5Body") },
    { icon: "globe", title: t("landing.why6Title"), body: t("landing.why6Body") },
  ];

  const chargeSteps = [
    {
      icon: "sparkles",
      title: t("landing.charge1Title"),
      body: t("landing.charge1Body"),
    },
    { icon: "wallet", title: t("landing.charge2Title"), body: t("landing.charge2Body") },
    { icon: "layers", title: t("landing.charge3Title"), body: t("landing.charge3Body") },
    { icon: "check", title: t("landing.charge4Title"), body: t("landing.charge4Body") },
  ];

  const navLinks = [
    { id: "why", label: t("landing.navWhy") },
    { id: "catalog", label: t("landing.navWorkflows") },
    { id: "pricing", label: t("landing.navPricing") },
  ];

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
        <nav className="wz-topnav" aria-label={t("landing.navLabel")}>
          {navLinks.map((l) => (
            <button
              key={l.id}
              type="button"
              className="wz-topnav-link"
              onClick={() => scrollToSection(l.id)}
            >
              {l.label}
            </button>
          ))}
        </nav>
        <div className="wz-topbar-actions">
          <LangToggle compact />
          <button className="wz-btn ghost" onClick={() => navigate("/app")}>
            {user ? t("nav.backToApp") : t("nav.signIn")}
          </button>
        </div>
      </header>

      <main>
        <section className="wz-hero">
          <div className="wz-hero-aura" aria-hidden="true" />
          <p className="wz-eyebrow">{t("landing.eyebrow")}</p>
          <h1 className="wz-hero-title">{t("landing.title")}</h1>
          <p className="wz-hero-sub">{t("landing.subtitle")}</p>
          <div className="wz-hero-actions">
            <button
              type="button"
              className="wz-btn primary"
              onClick={() => scrollToSection("catalog")}
            >
              {t("landing.cta")}
              <Icon name="arrow" size={16} className="wz-go-arrow" />
            </button>
            {user && (
              <button className="wz-btn ghost" onClick={() => navigate("/runs")}>
                {t("nav.myRuns")}
              </button>
            )}
          </div>
        </section>

        <section className="wz-section" id="why" aria-labelledby="why-title">
          <h2 className="wz-section-title" id="why-title">
            {t("landing.whyTitle")}
          </h2>
          <p className="wz-section-sub">{t("landing.whySubtitle")}</p>
          <ul className="wz-why-grid">
            {reasons.map((r) => (
              <li key={r.title} className="wz-why-item">
                <span className="wz-why-icon">
                  <Icon name={r.icon} size={20} />
                </span>
                <h3>{r.title}</h3>
                <p>{r.body}</p>
              </li>
            ))}
          </ul>
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

        <section
          className="wz-section wz-charge"
          id="pricing"
          aria-labelledby="pricing-title"
        >
          <div className="wz-charge-head">
            <span className="wz-charge-badge">
              <Icon name="wallet" size={22} />
            </span>
            <div>
              <h2 className="wz-section-title" id="pricing-title">
                {t("landing.chargeTitle")}
              </h2>
              <p className="wz-section-sub">{t("landing.chargeSubtitle")}</p>
            </div>
          </div>
          <ol className="wz-how-list wz-charge-list">
            {chargeSteps.map((s, i) => (
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
          <p className="wz-charge-note">
            <Icon name="shield" size={18} />
            <span>{t("landing.chargeNote")}</span>
          </p>
        </section>

        <section className="wz-section wz-cta-band">
          <h2 className="wz-section-title">{t("landing.ctaTitle")}</h2>
          <p className="wz-section-sub">{t("landing.ctaBody")}</p>
          <button className="wz-btn primary" onClick={() => navigate("/app")}>
            {user ? t("nav.backToApp") : t("landing.chargeCta")}
            <Icon name="arrow" size={16} className="wz-go-arrow" />
          </button>
        </section>
      </main>

      <footer className="wz-footer">
        <span>{t("landing.footer")}</span>
        <LangToggle compact />
      </footer>
    </div>
  );
}
