import { useCallback, useEffect, useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import WizardEditor from "./WizardEditor.jsx";
import WizardIcon from "./WizardIcon.jsx";

// Admin panel for guided workflows: the list, plus create / publish / delete.
// Editing a wizard's fields and steps happens in WizardEditor.
//
// This is a panel, not a page — it renders inside AdminPage's "Wizards" tab and
// so brings no shell of its own (no topbar, no back button).
export default function WizardAdminPanel() {
  const { t } = useT();
  const [wizards, setWizards] = useState([]);
  const [editing, setEditing] = useState(null); // wizard id
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      setWizards(await api.adminListWizards());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function create() {
    const name = newName.trim();
    if (!name) return;
    setError("");
    try {
      const created = await api.adminCreateWizard({ name, title_en: name });
      setNewName("");
      setCreating(false);
      await refresh();
      setEditing(created.id); // straight into the editor — it has no steps yet
    } catch (e) {
      setError(e.message);
    }
  }

  async function togglePublish(w) {
    setError("");
    try {
      await api.adminUpdateWizard(w.id, { is_published: !w.is_published });
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  async function remove(w) {
    if (!window.confirm(t("admin.deleteConfirm"))) return;
    setError("");
    try {
      await api.adminDeleteWizard(w.id);
      await refresh();
    } catch (e) {
      // The API refuses (409) once a wizard has runs — surface that verbatim.
      setError(e.message);
    }
  }

  return (
    <div className="wizard-admin-panel">
      {editing ? (
        <WizardEditor
          wizardId={editing}
          onClose={() => {
            setEditing(null);
            refresh();
          }}
          onSaved={refresh}
        />
      ) : (
        <>
          <div className="wz-editor-head">
            <p className="wz-section-sub">{t("admin.subtitle")}</p>
            {!creating && (
              <button className="wz-btn primary" onClick={() => setCreating(true)}>
                + {t("admin.new")}
              </button>
            )}
          </div>

          {error && <div className="banner-error">⚠️ {error}</div>}

          {creating && (
            <div className="wz-step-card">
              <label className="wz-field">
                <span className="wz-field-label">{t("admin.internalName")}</span>
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && create()}
                />
                <span className="wz-field-hint">{t("admin.internalNameHint")}</span>
              </label>
              <div className="wz-step-actions">
                <button
                  className="wz-btn ghost small"
                  onClick={() => {
                    setCreating(false);
                    setNewName("");
                  }}
                >
                  {t("common.cancel")}
                </button>
                <button
                  className="wz-btn primary small"
                  onClick={create}
                  disabled={!newName.trim()}
                >
                  {t("common.save")}
                </button>
              </div>
            </div>
          )}

          {loading ? (
            <p className="wz-muted">{t("common.loading")}</p>
          ) : wizards.length === 0 ? (
            <p className="wz-muted">{t("admin.empty")}</p>
          ) : (
            <ul className="wz-run-list">
              {wizards.map((w) => (
                <li key={w.id} className="wz-run-row">
                  <span className="wz-run-icon">
                    <WizardIcon name={w.icon} size={18} />
                  </span>
                  <span className="wz-run-body">
                    <span className="wz-run-title">{w.name}</span>
                    <span className="wz-run-meta">
                      <code>{w.slug}</code> · {t("wizard.steps", { n: w.step_count })}{" "}
                      · {t("admin.runCount", { n: w.run_count })}
                    </span>
                  </span>
                  <span className={`wz-chip${w.is_published ? " done" : " subtle"}`}>
                    {w.is_published ? t("admin.published") : t("admin.draft")}
                  </span>
                  <button className="wz-btn ghost small" onClick={() => togglePublish(w)}>
                    {w.is_published ? t("admin.unpublish") : t("admin.publish")}
                  </button>
                  <button className="wz-btn ghost small" onClick={() => setEditing(w.id)}>
                    {t("admin.edit")}
                  </button>
                  <button className="wz-btn danger small" onClick={() => remove(w)}>
                    {t("admin.delete")}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
