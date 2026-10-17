import Link from "next/link";
import { localePath, translate } from "../i18n/strings.js";
import { jsonLdScript, siteJsonLd } from "../lib/seo.js";
import LangToggle from "./LangToggle.jsx";
import LegacyHashRedirect from "./LegacyHashRedirect.jsx";
import { AppLink, MyRunsLink } from "./UserAware.jsx";
import WizardCard from "./WizardCard.jsx";
import Icon from "./Icon.jsx";

// The public landing page: hero, "why us", the catalogue of published wizards,
// a "how it works" band and how to top up the wallet.  A Server Component: the
// catalogue is fetched on the server (see app/(en)/page.js) so crawlers get the
// full page as HTML.  Only the signed-in-aware buttons hydrate on the client.
export default function WizardLanding({ lang, wizards, error }) {
  const t = (key, vars) => translate(lang, key, vars);

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

  const langHrefs = { en: localePath("en", "/"), fa: localePath("fa", "/") };

  return (
    <div className="wz-landing">
      <LegacyHashRedirect />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLdScript(siteJsonLd(lang))}
      />

      <header className="wz-topbar">
        <Link className="wz-brand" href={localePath(lang, "/")}>
          <Icon name="sparkles" size={20} />
          <span>Academic Co-Pilot</span>
        </Link>
        <nav className="wz-topnav" aria-label={t("landing.navLabel")}>
          {navLinks.map((l) => (
            <a key={l.id} className="wz-topnav-link" href={`#${l.id}`}>
              {l.label}
            </a>
          ))}
        </nav>
        <div className="wz-topbar-actions">
          <LangToggle compact hrefs={langHrefs} />
          <AppLink />
        </div>
      </header>

      <main>
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
            <MyRunsLink />
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

          {wizards.length === 0 ? (
            !error && (
              <div className="wz-empty">
                <p>{t("landing.empty")}</p>
                <p className="wz-muted">{t("landing.emptyHint")}</p>
              </div>
            )
          ) : (
            <div className="wz-grid">
              {wizards.map((w, i) => (
                <WizardCard key={w.id} wizard={w} lang={lang} index={i} />
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
          <AppLink className="wz-btn primary" signedOutKey="landing.chargeCta" arrow />
        </section>
      </main>

      <footer className="wz-footer">
        <span>{t("landing.footer")}</span>
        <LangToggle compact hrefs={langHrefs} />
      </footer>
    </div>
  );
}
