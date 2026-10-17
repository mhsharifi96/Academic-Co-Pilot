import Link from "next/link";
import { localePath, translate } from "../i18n/strings.js";
import { jsonLdScript, wizardJsonLd } from "../lib/seo.js";
import LangToggle from "./LangToggle.jsx";
import StartWizardButton from "./StartWizardButton.jsx";
import Icon from "./Icon.jsx";

// Public detail page for one wizard: what it is and the path it walks you
// through.  Server-rendered from the wizard fetched in the route; the "Start"
// button is the only client island (it needs the stored login).
export default function WizardDetail({ lang, wizard }) {
  const t = (key, vars) => translate(lang, key, vars);
  const path = `/wizards/${encodeURIComponent(wizard.slug)}`;
  const langHrefs = { en: localePath("en", path), fa: localePath("fa", path) };

  return (
    <div className="wz-landing">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={jsonLdScript(wizardJsonLd(lang, wizard))}
      />
      <header className="wz-topbar">
        <Link className="wz-brand" href={localePath(lang, "/")}>
          <Icon name="sparkles" size={20} />
          <span>Academic Co-Pilot</span>
        </Link>
        <div className="wz-topbar-actions">
          <LangToggle compact hrefs={langHrefs} />
          <Link className="wz-btn ghost" href={`${localePath(lang, "/")}#catalog`}>
            {t("wizard.back")}
          </Link>
        </div>
      </header>

      <main className="wz-detail">
        <div className="wz-detail-head">
          <span className="wz-card-icon large">
            <Icon name={wizard.icon} size={28} />
          </span>
          <div>
            <h1 className="wz-detail-title">{wizard.title}</h1>
            <p className="wz-chip">{t("wizard.steps", { n: wizard.step_count })}</p>
          </div>
        </div>

        {wizard.short_description && (
          <p className="wz-detail-desc">{wizard.short_description}</p>
        )}

        <StartWizardButton
          slug={wizard.slug}
          returnPath={localePath(lang, path)}
          disabled={wizard.step_count === 0}
        />

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
      </main>
    </div>
  );
}
