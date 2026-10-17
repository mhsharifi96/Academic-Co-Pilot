import { useEffect, useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import { navigate } from "../router.js";
import LangToggle from "./LangToggle.jsx";
import Icon from "./Icon.jsx";

function RunRow({ run, label }) {
  const { t, lang } = useT();
  const when = run.updated_at ? new Date(run.updated_at).toLocaleString(lang) : "";
  const done = run.status === "completed";

  return (
    <li className="wz-run-row">
      <span className={`wz-run-icon${done ? " done" : ""}`}>
        <Icon name={done ? "check" : "play"} size={18} />
      </span>
      <span className="wz-run-body">
        <span className="wz-run-title">{run.wizard_title}</span>
        <span className="wz-run-meta">
          {label}
          {when && <> · {t("runs.updated", { when })}</>}
        </span>
      </span>
      <button
        className="wz-btn ghost small"
        onClick={() => navigate(`/runs/${encodeURIComponent(run.id)}`)}
      >
        {done ? t("runs.open") : t("wizard.continue")}
      </button>
    </li>
  );
}

// "My workflows": everything the signed-in user has started, split into what is
// still in progress and what is finished.
export default function WizardRunsPage() {
  const { t, lang } = useT();
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .listWizardRuns(null, lang)
      .then((rows) => {
        if (!cancelled) setRuns(rows || []);
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

  const active = runs.filter((r) => r.status === "active");
  const finished = runs.filter((r) => r.status !== "active");

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
            {t("nav.backToApp")}
          </button>
        </div>
      </header>

      <section className="wz-section">
        <h1 className="wz-section-title">{t("runs.title")}</h1>
        <p className="wz-section-sub">{t("runs.subtitle")}</p>

        {error && <div className="banner-error">⚠️ {error}</div>}

        {loading ? (
          <p className="wz-muted">{t("common.loading")}</p>
        ) : runs.length === 0 ? (
          <div className="wz-empty">
            <p>{t("runs.empty")}</p>
            <button className="wz-btn primary" onClick={() => navigate("/")}>
              {t("runs.browse")}
            </button>
          </div>
        ) : (
          <>
            {active.length > 0 && (
              <>
                <h2 className="wz-section-title small">{t("runs.active")}</h2>
                <ul className="wz-run-list">
                  {active.map((r) => (
                    <RunRow
                      key={r.id}
                      run={r}
                      label={t("runner.stepOf", {
                        i: r.current_step_index || 1,
                        n: r.total_steps,
                      })}
                    />
                  ))}
                </ul>
              </>
            )}

            {finished.length > 0 && (
              <>
                <h2 className="wz-section-title small">{t("runs.finished")}</h2>
                <ul className="wz-run-list">
                  {finished.map((r) => (
                    <RunRow
                      key={r.id}
                      run={r}
                      label={
                        r.status === "completed"
                          ? t("runner.completedTitle")
                          : t("runner.abandoned")
                      }
                    />
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </section>
    </div>
  );
}
