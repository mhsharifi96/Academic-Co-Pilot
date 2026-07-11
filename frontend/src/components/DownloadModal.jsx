import { useState } from "react";
import { createDownload } from "../api.js";

// Confirmation modal shown when the user clicks "Get PDF" on a detected DOI.
// Displays the DOI and submits a download request to the queue.
export default function DownloadModal({ doi, sessionId, onClose, onCreated }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function submit() {
    if (!sessionId) {
      setError("Send a message first so this download has a conversation to attach to.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const resp = await createDownload(sessionId, doi);
      onCreated?.(resp);
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h4>📄 Download PDF</h4>
        <p className="modal-desc">
          Request the full-text PDF for this paper. It will be fetched in the
          background and, once ready, ingested and attached to this conversation —
          you can keep chatting while it downloads.
        </p>
        <div className="modal-doi">
          <span className="modal-doi-label">DOI</span>
          <code>{doi}</code>
        </div>

        {error && <div className="modal-err">{error}</div>}

        <div className="modal-actions">
          <button className="primary" disabled={submitting} onClick={submit}>
            {submitting ? "Submitting…" : "Request PDF download"}
          </button>
          <button className="ghost" disabled={submitting} onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
