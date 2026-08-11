import { useT } from "../i18n.js";
import WizardIcon from "./WizardIcon.jsx";

// One wizard in the landing grid.  The whole card is a single button so there
// is one focus stop and one 44px+ target, rather than a card with a small link
// buried inside it.  `index` staggers the reveal animation.
export default function WizardCard({ wizard, index = 0, onOpen }) {
  const { t } = useT();

  return (
    <button
      type="button"
      className="wz-card"
      style={{ "--wz-stagger": `${Math.min(index, 11) * 60}ms` }}
      onClick={() => onOpen(wizard)}
    >
      <span className="wz-card-glow" aria-hidden="true" />

      <span className="wz-card-icon">
        <WizardIcon name={wizard.icon} size={22} />
      </span>

      <span className="wz-card-body">
        <span className="wz-card-title">{wizard.title}</span>
        {wizard.short_description && (
          <span className="wz-card-desc">{wizard.short_description}</span>
        )}
      </span>

      <span className="wz-card-foot">
        <span className="wz-chip">
          {t("wizard.steps", { n: wizard.step_count })}
        </span>
        <span className="wz-card-go">
          {t("wizard.start")}
          <WizardIcon name="arrow" size={16} className="wz-go-arrow" />
        </span>
      </span>
    </button>
  );
}
