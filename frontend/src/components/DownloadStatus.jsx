import { useCallback, useEffect, useRef, useState } from "react";
import { listDownloads } from "../api.js";

const ACTIVE = ["QUEUED", "RUNNING", "RETRY_SCHEDULED"];
const POLL_MS = 4000;

function label(job) {
  switch (job.status) {
    case "QUEUED":
      return "Queued — waiting for its turn…";
    case "RUNNING":
      return "Downloading from provider…";
    case "RETRY_SCHEDULED": {
      const when = new Date(job.available_at).toLocaleTimeString();
      return `Not found yet — retry ${job.attempt_count + 1} scheduled around ${when}.`;
    }
    case "SUCCEEDED":
      return "Downloaded, ingested, and attached to this conversation.";
    case "FAILED":
      return job.failure_code === "PDF_NOT_FOUND"
        ? "Automatic retrieval failed after 3 attempts."
        : "Download failed (provider error).";
    default:
      return job.status;
  }
}

function icon(status) {
  if (status === "SUCCEEDED") return "✓";
  if (status === "FAILED") return "✕";
  return "⏳";
}

// Per-session panel that polls download-job status and renders the terminal
// failure choices (upload your own PDF / continue without it).
export default function DownloadStatus({
  sessionId,
  allSessions = false,
  reloadToken,
  onIngested,
  onUploadPdf,
  onContinueWithout,
  allowDismiss = true,
  emptyMessage = null,
}) {
  const [jobs, setJobs] = useState([]);
  const [dismissed, setDismissed] = useState({}); // jobId -> true
  const succeededSeen = useRef(new Set());
  const uploadRef = useRef(null);
  const uploadForRef = useRef(null); // job whose "upload" was clicked

  useEffect(() => {
    if (!sessionId && !allSessions) {
      setJobs([]);
      return;
    }
    let cancelled = false;
    let timer = null;

    async function poll() {
      try {
        const resp = await listDownloads(allSessions ? undefined : sessionId);
        if (cancelled) return;
        const list = resp.jobs || [];
        setJobs(list);
        // Fire onIngested once per newly-succeeded job (refreshes the sidebar).
        for (const j of list) {
          if (j.status === "SUCCEEDED" && !succeededSeen.current.has(j.id)) {
            succeededSeen.current.add(j.id);
            onIngested?.(j);
          }
        }
        if (!cancelled && list.some((j) => ACTIVE.includes(j.status))) {
          timer = setTimeout(poll, POLL_MS);
        }
      } catch {
        /* transient — try again next cycle */
        if (!cancelled) timer = setTimeout(poll, POLL_MS);
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [sessionId, allSessions, reloadToken, onIngested]);

  const onPickUpload = useCallback(
    (e) => {
      const files = e.target.files;
      if (files?.length) {
        onUploadPdf?.(files);
        if (uploadForRef.current) {
          setDismissed((d) => ({ ...d, [uploadForRef.current]: true }));
        }
      }
      e.target.value = "";
      uploadForRef.current = null;
    },
    [onUploadPdf]
  );

  const visible = jobs.filter((j) => !dismissed[j.id]);
  if (visible.length === 0) {
    return emptyMessage ? <div className="download-empty">{emptyMessage}</div> : null;
  }

  return (
    <div className="download-status">
      <input
        ref={uploadRef}
        type="file"
        accept=".pdf"
        hidden
        onChange={onPickUpload}
      />
      {visible.map((job) => {
        const notFound = job.status === "FAILED" && job.failure_code === "PDF_NOT_FOUND";
        return (
          <div key={job.id} className={`dl-job dl-${job.status.toLowerCase()}`}>
            <div className="dl-head">
              <span className="dl-icon">{icon(job.status)}</span>
              <code className="dl-doi">{job.doi}</code>
              {allSessions && (
                <code className="dl-session" title={job.session_id}>
                  {job.session_id}
                </code>
              )}
              <span className="dl-tier">{job.service_tier}</span>
            </div>
            <div className="dl-label">{label(job)}</div>

            {notFound && (
              <>
                <p className="dl-fail-msg">
                  Unfortunately, the PDF could not be retrieved after three
                  attempts. You can obtain it from a trusted source and upload it
                  here so its content can be used in this conversation, or continue
                  without the full paper (responses will be based only on the
                  information currently available).
                </p>
                <div className="dl-actions">
                  <button
                    className="primary"
                    onClick={() => {
                      uploadForRef.current = job.id;
                      uploadRef.current?.click();
                    }}
                  >
                    Upload PDF
                  </button>
                  <button
                    className="ghost"
                    onClick={() => {
                      setDismissed((d) => ({ ...d, [job.id]: true }));
                      onContinueWithout?.(job);
                    }}
                  >
                    Continue without PDF
                  </button>
                </div>
              </>
            )}

            {allowDismiss &&
              (job.status === "SUCCEEDED" ||
                (job.status === "FAILED" && !notFound)) && (
              <div className="dl-actions">
                <button
                  className="ghost"
                  onClick={() => setDismissed((d) => ({ ...d, [job.id]: true }))}
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
