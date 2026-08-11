import { useEffect, useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import WizardIcon, { WIZARD_ICON_KEYS } from "./WizardIcon.jsx";

const EMPTY_STEP = {
  name_en: "",
  name_fa: "",
  guideline_prompt: "",
  max_messages: "",
};

function Field({ label, hint, children }) {
  return (
    <label className="wz-field">
      <span className="wz-field-label">{label}</span>
      {children}
      {hint && <span className="wz-field-hint">{hint}</span>}
    </label>
  );
}

// Edit one wizard and its steps.
//
// The wizard's own fields save as a whole; each step saves individually, so a
// long prompt can't be lost by a validation error elsewhere on the form. Order
// is changed with the arrows, which PUT the full id list (the API rejects
// anything that isn't a complete permutation).
export default function WizardEditor({ wizardId, onClose, onSaved }) {
  const { t } = useT();

  const [wizard, setWizard] = useState(null);
  const [steps, setSteps] = useState([]);
  const [draftStep, setDraftStep] = useState(null); // EMPTY_STEP | null
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .adminGetWizard(wizardId)
      .then((w) => {
        if (cancelled) return;
        setWizard(w);
        setSteps(w.steps || []);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [wizardId]);

  function patch(field, value) {
    setWizard((w) => ({ ...w, [field]: value }));
  }

  async function saveWizard() {
    setSaving(true);
    setError("");
    try {
      const updated = await api.adminUpdateWizard(wizardId, {
        name: wizard.name,
        slug: wizard.slug,
        title_en: wizard.title_en,
        title_fa: wizard.title_fa,
        short_description_en: wizard.short_description_en,
        short_description_fa: wizard.short_description_fa,
        icon: wizard.icon || null,
        position: Number(wizard.position) || 0,
        is_published: wizard.is_published,
        enforce_scope_guardrail: wizard.enforce_scope_guardrail,
      });
      setWizard((w) => ({ ...w, ...updated }));
      onSaved?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  // `max_messages` is blank-for-unlimited in the form but must be null (not "")
  // on the wire — the API validates it as a positive integer or absent.
  const capOf = (raw) => (raw === "" || raw === null ? null : Number(raw));

  async function addStep() {
    setError("");
    try {
      const created = await api.adminCreateStep(wizardId, {
        ...draftStep,
        max_messages: capOf(draftStep.max_messages),
      });
      setSteps((prev) => [...prev, created]);
      setDraftStep(null);
      onSaved?.();
    } catch (e) {
      setError(e.message);
    }
  }

  async function saveStep(step) {
    setError("");
    try {
      const updated = await api.adminUpdateStep(step.id, {
        name_en: step.name_en,
        name_fa: step.name_fa,
        guideline_prompt: step.guideline_prompt,
        max_messages: capOf(step.max_messages),
      });
      setSteps((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } catch (e) {
      setError(e.message);
    }
  }

  async function removeStep(step) {
    if (!window.confirm(t("admin.stepDeleteConfirm"))) return;
    setError("");
    try {
      await api.adminDeleteStep(step.id);
      setSteps((prev) => prev.filter((s) => s.id !== step.id));
      onSaved?.();
    } catch (e) {
      setError(e.message);
    }
  }

  async function move(index, delta) {
    const target = index + delta;
    if (target < 0 || target >= steps.length) return;
    const next = [...steps];
    [next[index], next[target]] = [next[target], next[index]];
    setSteps(next); // optimistic: the arrows should feel instant
    setError("");
    try {
      const saved = await api.adminReorderSteps(wizardId, next.map((s) => s.id));
      setSteps(saved);
    } catch (e) {
      setError(e.message);
      setSteps(steps); // roll back to the server's order
    }
  }

  function patchStep(id, field, value) {
    setSteps((prev) => prev.map((s) => (s.id === id ? { ...s, [field]: value } : s)));
  }

  if (loading) return <p className="wz-muted">{t("common.loading")}</p>;
  if (!wizard) return <div className="banner-error">⚠️ {error || "Not found"}</div>;

  return (
    <div className="wz-editor">
      <div className="wz-editor-head">
        <h2>{wizard.name}</h2>
        <div className="wz-topbar-actions">
          <button className="wz-btn ghost small" onClick={onClose}>
            {t("common.close")}
          </button>
          <button className="wz-btn primary small" onClick={saveWizard} disabled={saving}>
            {saving ? t("common.saving") : t("common.save")}
          </button>
        </div>
      </div>

      {error && <div className="banner-error">⚠️ {error}</div>}

      <div className="wz-form-grid">
        <Field label={t("admin.internalName")} hint={t("admin.internalNameHint")}>
          <input value={wizard.name} onChange={(e) => patch("name", e.target.value)} />
        </Field>
        <Field label={t("admin.slug")} hint={t("admin.slugHint")}>
          <input value={wizard.slug} onChange={(e) => patch("slug", e.target.value)} />
        </Field>

        <Field label={t("admin.titleEn")}>
          <input
            value={wizard.title_en}
            onChange={(e) => patch("title_en", e.target.value)}
          />
        </Field>
        <Field label={t("admin.titleFa")}>
          <input
            dir="rtl"
            lang="fa"
            value={wizard.title_fa}
            onChange={(e) => patch("title_fa", e.target.value)}
          />
        </Field>

        <Field label={t("admin.descEn")}>
          <textarea
            rows={3}
            value={wizard.short_description_en}
            onChange={(e) => patch("short_description_en", e.target.value)}
          />
        </Field>
        <Field label={t("admin.descFa")}>
          <textarea
            rows={3}
            dir="rtl"
            lang="fa"
            value={wizard.short_description_fa}
            onChange={(e) => patch("short_description_fa", e.target.value)}
          />
        </Field>

        <Field label={t("admin.icon")}>
          <div className="wz-icon-picker">
            {WIZARD_ICON_KEYS.map((key) => (
              <button
                key={key}
                type="button"
                className={`wz-icon-option${wizard.icon === key ? " selected" : ""}`}
                onClick={() => patch("icon", key)}
                aria-pressed={wizard.icon === key}
                aria-label={key}
                title={key}
              >
                <WizardIcon name={key} size={20} />
              </button>
            ))}
          </div>
        </Field>
        <Field label={t("admin.order")}>
          <input
            type="number"
            value={wizard.position}
            onChange={(e) => patch("position", e.target.value)}
          />
        </Field>
      </div>

      <div className="wz-toggles">
        <label className="wz-check">
          <input
            type="checkbox"
            checked={!!wizard.is_published}
            onChange={(e) => patch("is_published", e.target.checked)}
          />
          <span>{t("admin.published")}</span>
        </label>
        <label className="wz-check">
          <input
            type="checkbox"
            checked={!!wizard.enforce_scope_guardrail}
            onChange={(e) => patch("enforce_scope_guardrail", e.target.checked)}
          />
          <span>{t("admin.scopeGuardrail")}</span>
        </label>
        <p className="wz-field-hint">{t("admin.scopeGuardrailHint")}</p>
      </div>

      <h3 className="wz-section-title small">{t("admin.steps")}</h3>

      {steps.length === 0 && !draftStep && (
        <p className="wz-muted">{t("admin.noSteps")}</p>
      )}

      <ol className="wz-step-list">
        {steps.map((step, i) => (
          <li key={step.id} className="wz-step-card">
            <div className="wz-step-head">
              <span className="wz-path-num">{i + 1}</span>
              <div className="wz-step-order">
                <button
                  className="wz-btn icon"
                  onClick={() => move(i, -1)}
                  disabled={i === 0}
                  aria-label={t("admin.moveUp")}
                  title={t("admin.moveUp")}
                >
                  ↑
                </button>
                <button
                  className="wz-btn icon"
                  onClick={() => move(i, 1)}
                  disabled={i === steps.length - 1}
                  aria-label={t("admin.moveDown")}
                  title={t("admin.moveDown")}
                >
                  ↓
                </button>
              </div>
            </div>

            <div className="wz-form-grid">
              <Field label={t("admin.stepNameEn")}>
                <input
                  value={step.name_en}
                  onChange={(e) => patchStep(step.id, "name_en", e.target.value)}
                />
              </Field>
              <Field label={t("admin.stepNameFa")}>
                <input
                  dir="rtl"
                  lang="fa"
                  value={step.name_fa}
                  onChange={(e) => patchStep(step.id, "name_fa", e.target.value)}
                />
              </Field>
            </div>

            <Field label={t("admin.guideline")} hint={t("admin.guidelineHint")}>
              <textarea
                rows={5}
                value={step.guideline_prompt}
                onChange={(e) => patchStep(step.id, "guideline_prompt", e.target.value)}
              />
            </Field>

            <Field label={t("admin.maxMessages")} hint={t("admin.maxMessagesHint")}>
              <input
                type="number"
                min="1"
                value={step.max_messages ?? ""}
                onChange={(e) => patchStep(step.id, "max_messages", e.target.value)}
              />
            </Field>

            <div className="wz-step-actions">
              <button className="wz-btn danger small" onClick={() => removeStep(step)}>
                {t("admin.delete")}
              </button>
              <button className="wz-btn primary small" onClick={() => saveStep(step)}>
                {t("common.save")}
              </button>
            </div>
          </li>
        ))}
      </ol>

      {draftStep ? (
        <div className="wz-step-card">
          <div className="wz-form-grid">
            <Field label={t("admin.stepNameEn")}>
              <input
                value={draftStep.name_en}
                onChange={(e) =>
                  setDraftStep({ ...draftStep, name_en: e.target.value })
                }
              />
            </Field>
            <Field label={t("admin.stepNameFa")}>
              <input
                dir="rtl"
                lang="fa"
                value={draftStep.name_fa}
                onChange={(e) =>
                  setDraftStep({ ...draftStep, name_fa: e.target.value })
                }
              />
            </Field>
          </div>
          <Field label={t("admin.guideline")} hint={t("admin.guidelineHint")}>
            <textarea
              rows={5}
              value={draftStep.guideline_prompt}
              onChange={(e) =>
                setDraftStep({ ...draftStep, guideline_prompt: e.target.value })
              }
            />
          </Field>
          <Field label={t("admin.maxMessages")} hint={t("admin.maxMessagesHint")}>
            <input
              type="number"
              min="1"
              value={draftStep.max_messages}
              onChange={(e) =>
                setDraftStep({ ...draftStep, max_messages: e.target.value })
              }
            />
          </Field>
          <div className="wz-step-actions">
            <button className="wz-btn ghost small" onClick={() => setDraftStep(null)}>
              {t("common.cancel")}
            </button>
            <button
              className="wz-btn primary small"
              onClick={addStep}
              disabled={!draftStep.guideline_prompt.trim()}
            >
              {t("common.save")}
            </button>
          </div>
        </div>
      ) : (
        <button className="wz-btn ghost" onClick={() => setDraftStep({ ...EMPTY_STEP })}>
          + {t("admin.addStep")}
        </button>
      )}
    </div>
  );
}
