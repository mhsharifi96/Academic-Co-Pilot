import { useState } from "react";
import { createDownload } from "../api.js";
import DownloadStatus from "./DownloadStatus.jsx";

export default function DownloadsPage({
  sessionId,
  reloadToken,
  onCreated,
  onIngested,
  onUploadPdf,
  onContinueWithout,
}) {
  const [doi, setDoi] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  async function submit(e) {
    e.preventDefault();
    const trimmed = doi.trim();
    if (!sessionId) {
      setError("Select or start a conversation before requesting a PDF.");
      return;
    }
    if (!trimmed) {
      setError("Enter a DOI.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const resp = await createDownload(sessionId, trimmed);
      setDoi("");
      setNotice(
        resp.deduplicated
          ? `Existing download found. ${resp.quota_remaining} requests left.`
          : `Download queued. ${resp.quota_remaining} requests left.`
      );
      onCreated?.(resp);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="downloads-page">
      <div className="downloads-head">
        <div>
          <h1>Downloads</h1>
          <div className="downloads-session">
            Showing all requests. New downloads attach to:{" "}
            <code>{sessionId || "no selected session"}</code>
          </div>
        </div>
      </div>

      <form className="download-request" onSubmit={submit}>
        <label>
          DOI
          <input
            value={doi}
            onChange={(e) => setDoi(e.target.value)}
            placeholder="10.xxxx/example"
            disabled={submitting}
          />
        </label>
        <button className="primary" disabled={submitting || !sessionId}>
          {submitting ? "Queuing..." : "Queue download"}
        </button>
      </form>

      {error && <div className="download-page-error">{error}</div>}
      {notice && <div className="download-page-notice">{notice}</div>}

      <section className="download-info">
        <div>
          <h2>How it works</h2>
          <p>
            Enter a DOI and PaperAgent queues a provider PDF download. When the
            PDF is found, it is saved, ingested, and attached to the selected
            conversation so the agent can use it like an uploaded paper.
          </p>
        </div>
        <div className="download-info-grid">
          <div>
            <strong>Quota</strong>
            <span>10 requests per user every 24 hours.</span>
          </div>
          <div>
            <strong>Priority</strong>
            <span>First 3 requests are fast; later requests are standard.</span>
          </div>
          <div>
            <strong>Retries</strong>
            <span>Up to 3 attempts, with delayed retries after misses.</span>
          </div>
          <div>
            <strong>Duplicates</strong>
            <span>Active requests for the same DOI reuse the existing job.</span>
          </div>
        </div>
      </section>

      <DownloadStatus
        sessionId={sessionId}
        allSessions
        reloadToken={reloadToken}
        onIngested={onIngested}
        onUploadPdf={onUploadPdf}
        onContinueWithout={onContinueWithout}
        allowDismiss={false}
        emptyMessage="No download requests yet."
      />
    </div>
  );
}
