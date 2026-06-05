import { useState } from "react";

// Renders the human-in-the-loop approval panel for the tool call(s) the agent
// wants to run, and turns the user's choice into a /chat/resume decision.
export default function InterruptCard({ interrupt, loading, onResume }) {
  const actions = interrupt?.pending_actions || [];
  const first = actions[0] || {};

  const [mode, setMode] = useState("idle"); // idle | edit | reject
  const [argsText, setArgsText] = useState(() =>
    JSON.stringify(first.args || {}, null, 2)
  );
  const [reason, setReason] = useState("");
  const [jsonErr, setJsonErr] = useState(null);

  function submitEdit() {
    let parsed;
    try {
      parsed = JSON.parse(argsText);
    } catch (e) {
      setJsonErr(`Invalid JSON: ${e.message}`);
      return;
    }
    setJsonErr(null);
    onResume("edit", { editedArgs: parsed });
  }

  return (
    <div className="interrupt">
      <h4>⚠️ Approval required</h4>
      <div className="desc">
        The agent wants to run{" "}
        {actions.map((a, i) => (
          <span key={i}>
            <span className="tool-name">{a.tool}</span>
            {i < actions.length - 1 ? ", " : ""}
          </span>
        ))}
        . Review the arguments and choose how to proceed.
      </div>

      {first.description && <div className="desc">{first.description}</div>}

      {mode === "edit" ? (
        <>
          <textarea
            className="args"
            value={argsText}
            onChange={(e) => setArgsText(e.target.value)}
            spellCheck={false}
          />
          {jsonErr && <div className="json-err">{jsonErr}</div>}
          <div className="actions">
            <button className="primary" disabled={loading} onClick={submitEdit}>
              Run with edits
            </button>
            <button className="ghost" disabled={loading} onClick={() => setMode("idle")}>
              Cancel
            </button>
          </div>
        </>
      ) : mode === "reject" ? (
        <>
          <pre>{JSON.stringify(first.args || {}, null, 2)}</pre>
          <textarea
            className="reason"
            placeholder="Why are you rejecting? (optional — fed back to the agent)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="actions">
            <button
              className="danger"
              disabled={loading}
              onClick={() => onResume("reject", { reason: reason || undefined })}
            >
              Confirm reject
            </button>
            <button className="ghost" disabled={loading} onClick={() => setMode("idle")}>
              Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <pre>{JSON.stringify(first.args || {}, null, 2)}</pre>
          <div className="actions">
            <button
              className="success"
              disabled={loading}
              onClick={() => onResume("approve")}
            >
              ✓ Approve
            </button>
            <button className="primary" disabled={loading} onClick={() => setMode("edit")}>
              ✎ Edit args
            </button>
            <button className="danger" disabled={loading} onClick={() => setMode("reject")}>
              ✕ Reject
            </button>
          </div>
        </>
      )}
    </div>
  );
}
