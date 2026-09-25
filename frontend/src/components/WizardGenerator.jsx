import { useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import Icon, { WIZARD_ICON_KEYS } from "./Icon.jsx";

const STEP_COUNTS = [2, 3, 4, 5, 6, 7, 8];

function Field({ label, hint, children }) {
  return (
    <label className="wz-field">
      <span className="wz-field-label">{label}</span>
      {children}
      {hint && <span className="wz-field-hint">{hint}</span>}
    </label>
  );
}

// Create a workflow with AI: the admin describes it, the server drafts the
// whole thing (`POST /admin/wizards/draft`), the admin edits the draft here and
// then creates it — unpublished — in one request with its steps.
export default function WizardGenerator({ onCancel, onCreated }) {
  const { t } = useT();
  const [brief, setBrief] = useState({
    goal: "",
    audience: "",
    step_count: "",
    max_messages: "8",
  });
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(""); // "" | "drafting" | "creating"
  const [error, setError] = useState("");

  async function generate() {
    setBusy("drafting");
    setError("");
    try {
      const d = await api.adminDraftWizard({
        goal: brief.goal.trim(),
        audience: brief.audience.trim(),
        step_count: brief.step_count ? Number(brief.step_count) : null,
        max_messages: brief.max_messages ? Number(brief.max_messages) : null,
      });
      setDraft(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function create() {
    setBusy("creating");
    setError("");
    try {
      const { warnings, steps, ...fields } = draft;
      const created = await api.adminCreateWizard({
        ...fields,
        is_published: false,
        steps: steps.map((s) => ({
          ...s,
          max_messages: s.max_messages ? Number(s.max_messages) : null,
        })),
      });
      onCreated(created.id);
    } catch (e) {
      setError(e.message);
      setBusy("");
    }
  }

  const patch = (field, value) => setDraft((d) => ({ ...d, [field]: value }));
  const patchStep = (i, field, value) =>
    setDraft((d) => ({
      ...d,
      steps: d.steps.map((s, j) => (j === i ? { ...s, [field]: value } : s)),
    }));
  const removeStep = (i) =>
    setDraft((d) => ({ ...d, steps: d.steps.filter((_, j) => j !== i) }));

  const canCreate =
    draft &&
    draft.name.trim() &&
    draft.steps.length > 0 &&
    draft.steps.every((s) => s.guideline_prompt.trim() && (s.name_en.trim() || s.name_fa.trim()));

  return (
    <div className="wz-editor">
      <div className="wz-editor-head">
        <h2>
          <Icon name="sparkles" size={20} /> {t("ai.title")}
        </h2>
        <div className="wz-topbar-actions">
          <button className="wz-btn ghost small" onClick={onCancel} disabled={!!busy}>
            {t("common.cancel")}
          </button>
        </div>
      </div>

      {error && <div className="banner-error">⚠️ {error}</div>}

      {/* The brief stays visible above the draft so "Draft again" can follow a tweak. */}
      <div className="wz-step-card">
        <p className="wz-field-hint">{t("ai.intro")}</p>
        <Field label={t("ai.goal")} hint={t("ai.goalHint")}>
          <textarea
            rows={5}
            autoFocus
            dir="auto"
            value={brief.goal}
            placeholder={t("ai.goalPlaceholder")}
            onChange={(e) => setBrief({ ...brief, goal: e.target.value })}
          />
        </Field>
        <div className="wz-form-grid">
          <Field label={t("ai.audience")}>
            <input
              dir="auto"
              value={brief.audience}
              placeholder={t("ai.audiencePlaceholder")}
              onChange={(e) => setBrief({ ...brief, audience: e.target.value })}
            />
          </Field>
          <Field label={t("ai.stepCount")}>
            <select
              value={brief.step_count}
              onChange={(e) => setBrief({ ...brief, step_count: e.target.value })}
            >
              <option value="">{t("ai.stepCountAuto")}</option>
              {STEP_COUNTS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t("ai.maxMessages")}>
            <input
              type="number"
              min={1}
              max={50}
              value={brief.max_messages}
              onChange={(e) => setBrief({ ...brief, max_messages: e.target.value })}
            />
          </Field>
        </div>
        <div className="wz-step-actions">
          <button
            className="wz-btn primary small"
            onClick={generate}
            disabled={!!busy || brief.goal.trim().length < 10}
          >
            {busy === "drafting"
              ? t("ai.generating")
              : draft
                ? t("ai.regenerate")
                : t("ai.generate")}
          </button>
        </div>
      </div>

      {draft && (
        <>
          <h3 className="wz-section-title small">{t("ai.review")}</h3>
          <p className="wz-field-hint">{t("ai.reviewHint")}</p>

          {draft.warnings?.length > 0 && (
            <div className="banner-error">
              <strong>{t("ai.warnings")}</strong>
              <ul>
                {draft.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="wz-form-grid">
            <Field label={t("admin.internalName")}>
              <input value={draft.name} onChange={(e) => patch("name", e.target.value)} />
            </Field>
            <Field label={t("admin.slug")} hint={t("admin.slugHint")}>
              <input value={draft.slug} onChange={(e) => patch("slug", e.target.value)} />
            </Field>
            <Field label={t("admin.titleEn")}>
              <input value={draft.title_en} onChange={(e) => patch("title_en", e.target.value)} />
            </Field>
            <Field label={t("admin.titleFa")}>
              <input
                dir="rtl"
                lang="fa"
                value={draft.title_fa}
                onChange={(e) => patch("title_fa", e.target.value)}
              />
            </Field>
            <Field label={t("admin.descEn")}>
              <textarea
                rows={3}
                value={draft.short_description_en}
                onChange={(e) => patch("short_description_en", e.target.value)}
              />
            </Field>
            <Field label={t("admin.descFa")}>
              <textarea
                rows={3}
                dir="rtl"
                lang="fa"
                value={draft.short_description_fa}
                onChange={(e) => patch("short_description_fa", e.target.value)}
              />
            </Field>
            <Field label={t("admin.icon")}>
              <div className="wz-icon-picker">
                {WIZARD_ICON_KEYS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`wz-icon-option${draft.icon === key ? " selected" : ""}`}
                    onClick={() => patch("icon", key)}
                    aria-pressed={draft.icon === key}
                    aria-label={key}
                    title={key}
                  >
                    <Icon name={key} size={20} />
                  </button>
                ))}
              </div>
            </Field>
          </div>

          <h3 className="wz-section-title small">{t("admin.steps")}</h3>
          <ol className="wz-step-list">
            {draft.steps.map((step, i) => (
              <li key={i} className="wz-step-card">
                <div className="wz-step-head">
                  <span className="wz-path-num">{i + 1}</span>
                  <button
                    className="wz-btn danger small"
                    onClick={() => removeStep(i)}
                    disabled={draft.steps.length <= 1}
                  >
                    {t("ai.removeStep")}
                  </button>
                </div>
                <div className="wz-form-grid">
                  <Field label={t("admin.stepNameEn")}>
                    <input
                      value={step.name_en}
                      onChange={(e) => patchStep(i, "name_en", e.target.value)}
                    />
                  </Field>
                  <Field label={t("admin.stepNameFa")}>
                    <input
                      dir="rtl"
                      lang="fa"
                      value={step.name_fa}
                      onChange={(e) => patchStep(i, "name_fa", e.target.value)}
                    />
                  </Field>
                </div>
                <Field label={t("admin.guideline")} hint={t("admin.guidelineHint")}>
                  <textarea
                    rows={8}
                    value={step.guideline_prompt}
                    onChange={(e) => patchStep(i, "guideline_prompt", e.target.value)}
                  />
                </Field>
                <Field label={t("admin.maxMessages")} hint={t("admin.maxMessagesHint")}>
                  <input
                    type="number"
                    min={1}
                    value={step.max_messages ?? ""}
                    onChange={(e) => patchStep(i, "max_messages", e.target.value)}
                  />
                </Field>
              </li>
            ))}
          </ol>

          <div className="wz-step-actions">
            <button className="wz-btn primary" onClick={create} disabled={!!busy || !canCreate}>
              {busy === "creating" ? t("ai.creating") : t("ai.create")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
