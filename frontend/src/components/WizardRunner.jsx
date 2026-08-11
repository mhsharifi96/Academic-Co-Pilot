import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api.js";
import { useT } from "../i18n.js";
import { navigate } from "../router.js";
import InterruptCard from "./InterruptCard.jsx";
import LangToggle from "./LangToggle.jsx";
import Message from "./Message.jsx";
import Icon from "./Icon.jsx";
import WizardStepper from "./WizardStepper.jsx";

// The guided chat for one run.
//
// Unlike plain chat, the transcript is authoritative in the database, so it is
// loaded from GET /wizard-runs/{id} rather than reconstructed from the graph.
// The step advances server-side once a step's message cap is used up; every
// turn response carries the updated step state, which is what drives the
// stepper above the conversation.
export default function WizardRunner({ runId }) {
  const { t, lang } = useT();

  const [run, setRun] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [interrupt, setInterrupt] = useState(null);
  const [notice, setNotice] = useState("");
  // The agent said this step's goal is met. Advisory only — the run stays put
  // until the user chooses to move on.
  const [suggested, setSuggested] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState("");

  const endRef = useRef(null);
  const taRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, interrupt]);

  // Auto-grow the composer, matching MessageInput's behaviour.
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }, [draft]);

  const load = useCallback(async () => {
    setBooting(true);
    setError("");
    try {
      const data = await api.getWizardRun(runId, lang);
      setRun(data);
      setMessages(
        (data.messages || []).map((m) => ({ role: m.role, content: m.content }))
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBooting(false);
    }
  }, [runId, lang]);

  useEffect(() => {
    load();
  }, [load]);

  // Fold a turn response back into local state: transcript, step position, and
  // the "you've moved on" notice.
  function applyTurn(res, sentText) {
    if (sentText != null) {
      setMessages((prev) => [...prev, { role: "user", content: sentText }]);
    }
    if (res.response) {
      setMessages((prev) => [...prev, { role: "assistant", content: res.response }]);
    }
    setInterrupt(res.status === "interrupted" ? res.interrupt : null);
    setRun((prev) =>
      prev
        ? {
            ...prev,
            status: res.run_status,
            current_step: res.current_step,
            current_step_index: res.current_step_index,
            total_steps: res.total_steps || prev.total_steps,
            messages_left_in_step: res.messages_left_in_step,
          }
        : prev
    );
    // A step that just advanced can't also be pending completion.
    setSuggested(!!res.step_complete_suggested);
    if (res.completed) {
      setNotice("");
    } else if (res.step_advanced && res.current_step?.name) {
      setNotice(t("runner.advanced", { name: res.current_step.name }));
    } else {
      setNotice("");
    }
  }

  async function finishStep() {
    if (finishing) return;
    setFinishing(true);
    setError("");
    try {
      const res = await api.advanceWizardRun(runId, lang);
      applyTurn(res, null); // response is empty — no agent call was made
    } catch (e) {
      setError(e.message);
    } finally {
      setFinishing(false);
    }
  }

  async function send() {
    const text = draft.trim();
    if (!text || loading) return;
    setDraft("");
    setLoading(true);
    setError("");
    try {
      const res = await api.sendWizardMessage(runId, text, lang);
      applyTurn(res, text);
    } catch (e) {
      setError(e.message);
      setDraft(text); // give the message back rather than losing it
    } finally {
      setLoading(false);
    }
  }

  async function resume(decision, opts) {
    setLoading(true);
    setError("");
    try {
      const res = await api.resumeWizardRun(runId, decision, opts, lang);
      applyTurn(res, null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function discard() {
    if (!window.confirm(t("runner.discardConfirm"))) return;
    try {
      await api.abandonWizardRun(runId);
      navigate("/runs");
    } catch (e) {
      setError(e.message);
    }
  }

  const done = run?.status === "completed";
  const abandoned = run?.status === "abandoned";
  const composerDisabled = loading || !!interrupt || done || abandoned;

  return (
    <div className="wz-runner">
      <header className="wz-topbar">
        <button className="wz-back" onClick={() => navigate("/runs")}>
          <Icon name="arrow" size={16} className="wz-back-arrow" />
          <span>{t("nav.myRuns")}</span>
        </button>
        <span className="wz-runner-title">{run?.wizard_title || ""}</span>
        <div className="wz-topbar-actions">
          <LangToggle compact />
          {!done && !abandoned && (
            <button className="wz-btn ghost small" onClick={discard}>
              {t("runner.discard")}
            </button>
          )}
        </div>
      </header>

      {run && (
        <WizardStepper
          run={run}
          onFinishStep={done || abandoned ? null : finishStep}
          finishing={finishing}
          suggested={suggested}
        />
      )}

      <div className="wz-thread">
        {error && <div className="banner-error">⚠️ {error}</div>}

        {booting ? (
          <p className="wz-muted">{t("runner.loading")}</p>
        ) : (
          <>
            {messages.length === 0 && !interrupt && (
              <div className="wz-thread-welcome">
                <Icon name="play" size={22} />
                <p>{t("runner.welcome")}</p>
                {run?.current_step?.name && <strong>{run.current_step.name}</strong>}
              </div>
            )}

            {messages.map((m, i) => (
              <Message key={i} role={m.role} content={m.content} />
            ))}

            {notice && (
              <div className="wz-notice" role="status">
                <Icon name="check" size={16} />
                <span>{notice}</span>
              </div>
            )}

            {/* The agent thinks this step is done. Offered inline as well as in
                the header, because that's where the user is reading. */}
            {suggested && !done && !abandoned && (
              <div className="wz-suggest" role="status">
                <Icon name="check" size={18} />
                <div className="wz-suggest-body">
                  <strong>{t("runner.suggestTitle")}</strong>
                  <span>{t("runner.suggestBody")}</span>
                </div>
                <div className="wz-suggest-actions">
                  <button
                    className="wz-btn ghost small"
                    onClick={() => setSuggested(false)}
                  >
                    {t("runner.suggestStay")}
                  </button>
                  <button
                    className="wz-btn primary small"
                    onClick={finishStep}
                    disabled={finishing}
                  >
                    {finishing ? t("common.saving") : t("runner.suggestGo")}
                    <Icon name="arrow" size={15} className="wz-go-arrow" />
                  </button>
                </div>
              </div>
            )}

            {interrupt && (
              <InterruptCard
                key={JSON.stringify(interrupt.pending_actions)}
                interrupt={interrupt}
                loading={loading}
                onResume={resume}
              />
            )}

            {loading && <div className="typing">{t("runner.thinking")}</div>}

            {done && (
              <div className="wz-complete">
                <Icon name="check" size={28} />
                <h2>{t("runner.completedTitle")}</h2>
                <p>{t("runner.completedBody")}</p>
                <div className="wz-hero-actions">
                  <button className="wz-btn ghost" onClick={() => navigate("/")}>
                    {t("runs.browse")}
                  </button>
                  <button className="wz-btn ghost" onClick={() => navigate("/app")}>
                    {t("nav.backToApp")}
                  </button>
                </div>
              </div>
            )}

            {abandoned && <div className="wz-notice">{t("runner.abandoned")}</div>}
          </>
        )}

        <div ref={endRef} />
      </div>

      {!done && !abandoned && (
        <div className="composer wz-composer">
          <div className="composer-inner">
            <textarea
              ref={taRef}
              rows={1}
              value={draft}
              placeholder={t("runner.placeholder")}
              disabled={composerDisabled}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <button className="primary" disabled={composerDisabled || !draft.trim()} onClick={send}>
              {t("runner.send")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
