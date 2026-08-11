import { useState } from "react";
import { useT } from "../i18n.js";
import Icon from "./Icon.jsx";

// Follow-up questions the user could send next, sitting above the composer.
//
// Fetched on demand rather than after every reply: generating them is a second
// LLM call billed to the user's balance, so it only happens when they ask.
// Choosing one sends it verbatim — the model is told to write in the user's
// voice — so nothing here edits the text on the way out.
export default function SuggestedQuestions({
  suggestions,
  loading,
  disabled,
  onRequest,
  onSend,
  onDismiss,
}) {
  const { t } = useT();
  const [openIndex, setOpenIndex] = useState(null);

  const has = suggestions && suggestions.length > 0;

  if (!has) {
    return (
      <div className="suggest-bar">
        <button
          type="button"
          className="suggest-trigger"
          onClick={onRequest}
          disabled={disabled || loading}
        >
          <Icon name="sparkles" size={15} />
          <span>{loading ? t("suggest.loading") : t("suggest.trigger")}</span>
        </button>
      </div>
    );
  }

  return (
    <div className="suggest-panel">
      <div className="suggest-head">
        <span className="suggest-title">
          <Icon name="sparkles" size={14} />
          {t("suggest.title")}
        </span>
        <span className="suggest-head-actions">
          <button
            type="button"
            className="suggest-mini"
            onClick={onRequest}
            disabled={disabled || loading}
          >
            {loading ? t("suggest.loading") : t("suggest.refresh")}
          </button>
          <button
            type="button"
            className="suggest-mini"
            onClick={onDismiss}
            aria-label={t("suggest.dismiss")}
            title={t("suggest.dismiss")}
          >
            <Icon name="close" size={14} />
          </button>
        </span>
      </div>

      <ul className="suggest-list">
        {suggestions.map((s, i) => {
          const open = openIndex === i;
          const panelId = `suggestion-panel-${i}`;
          return (
            <li key={i} className={`suggest-item${open ? " open" : ""}`}>
              <div className="suggest-row">
                {/* The row expands; sending is a separate control so a click
                    can never send something the user hasn't read in full. */}
                <button
                  type="button"
                  className="suggest-toggle"
                  aria-expanded={open}
                  aria-controls={panelId}
                  onClick={() => setOpenIndex(open ? null : i)}
                >
                  <Icon
                    name="chevronDown"
                    size={14}
                    className={`suggest-caret${open ? " open" : ""}`}
                  />
                  <span className="suggest-question">{s.question}</span>
                </button>
                <button
                  type="button"
                  className="suggest-send"
                  onClick={() => onSend(s.question)}
                  disabled={disabled || loading}
                  aria-label={t("suggest.send", { q: s.question })}
                  title={t("suggest.sendShort")}
                >
                  <Icon name="send" size={15} />
                </button>
              </div>

              {/* Expanding lets the question itself wrap to full length (see
                  .suggest-item.open .suggest-question), so the detail carries
                  only the rationale — repeating the question here would be
                  noise for anything that already fits on one line. */}
              {open && s.reason && (
                <div className="suggest-detail" id={panelId}>
                  <p className="suggest-reason">
                    {t("suggest.why")} {s.reason}
                  </p>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
