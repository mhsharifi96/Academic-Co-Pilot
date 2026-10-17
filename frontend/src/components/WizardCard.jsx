import Link from "next/link";
import { localePath, translate } from "../i18n/strings.js";
import Icon from "./Icon.jsx";

// One wizard in the landing grid.  The whole card is a single link so there is
// one focus stop and one 44px+ target, rather than a card with a small link
// buried inside it — and crawlers can follow it to the wizard's own page.
// `index` staggers the reveal animation.  Server-rendered: translates with the
// page's `lang` instead of the client context.
export default function WizardCard({ wizard, lang, index = 0 }) {
  const t = (key, vars) => translate(lang, key, vars);

  return (
    <Link
      className="wz-card"
      href={localePath(lang, `/wizards/${encodeURIComponent(wizard.slug)}`)}
      style={{ "--wz-stagger": `${Math.min(index, 11) * 60}ms` }}
    >
      <span className="wz-card-glow" aria-hidden="true" />

      <span className="wz-card-icon">
        <Icon name={wizard.icon} size={22} />
      </span>

      <span className="wz-card-body">
        <span className="wz-card-title">{wizard.title}</span>
        {wizard.short_description && (
          <span className="wz-card-desc">{wizard.short_description}</span>
        )}
      </span>

      <span className="wz-card-foot">
        <span className="wz-chip">{t("wizard.steps", { n: wizard.step_count })}</span>
        <span className="wz-card-go">
          {t("wizard.start")}
          <Icon name="arrow" size={16} className="wz-go-arrow" />
        </span>
      </span>
    </Link>
  );
}
