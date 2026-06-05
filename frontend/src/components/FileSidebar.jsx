import { useRef, useState } from "react";

export default function FileSidebar({ files, onUpload, onInsertPath, busy }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState(null); // per-file upload progress/results

  async function doUpload(fileList) {
    // Show every selected file as "processing" right away — the backend
    // handles them in one request, so we optimistically mark them all pending
    // and then reconcile with the per-file results when the response arrives.
    setStatus(
      Array.from(fileList).map((f) => ({
        filename: f.name,
        status: "processing",
      }))
    );
    const resp = await onUpload(fileList);
    if (resp && resp.files) {
      setStatus(resp.files);
    } else {
      // Request failed before returning per-file results (App shows the error).
      setStatus((prev) =>
        prev
          ? prev.map((r) => ({ ...r, status: "error", message: "Upload failed" }))
          : prev
      );
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) doUpload(e.dataTransfer.files);
  }

  function onPick(e) {
    if (e.target.files?.length) doUpload(e.target.files);
    e.target.value = ""; // allow re-selecting the same file
  }

  return (
    <section className="file-section">
      <h3>Files</h3>

      <div
        className={`dropzone${dragging ? " drag" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        <div>
          Drop files or <strong>browse</strong>
        </div>
        <div className="hint">PDF or CSV · multiple allowed</div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.csv"
          multiple
          hidden
          onChange={onPick}
          disabled={busy}
        />
      </div>

      {files.length === 0 ? (
        <p className="empty-note">No files yet. Upload PDFs/CSVs, then type “@” in the message box to reference them.</p>
      ) : (
        <ul className="file-list">
          {files.map((f) => (
            <li className="file-item" key={f.path}>
              <span className={`tag ${f.type}`}>{f.type}</span>
              <span className="name" title={f.path}>
                {f.filename}
              </span>
              <button
                className="insert"
                title={`Insert ${f.path} into the message`}
                onClick={() => onInsertPath(f.path)}
              >
                insert
              </button>
            </li>
          ))}
        </ul>
      )}

      {status && (
        <div className="upload-status">
          {status.map((r, i) => {
            if (r.status === "processing") {
              return (
                <span key={i} className="processing">
                  <span className="spinner" /> {r.filename} — processing…
                </span>
              );
            }
            const ok = r.status !== "error";
            return (
              <span key={i} className={ok ? "ok" : "err"}>
                {ok ? "✓" : "✗"} {r.filename}
                {ok ? "" : `: ${r.message}`}
              </span>
            );
          })}
        </div>
      )}
    </section>
  );
}
