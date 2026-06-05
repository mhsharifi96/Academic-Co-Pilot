// Thin wrappers around the PaperAgent FastAPI endpoints.
// Requests use relative /api paths; in dev these are proxied to :8000 by Vite
// (see vite.config.js).

const BASE = "/api/v1";

async function jsonOrThrow(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : res.statusText;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return body;
}

export async function sendChat(message, sessionId) {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId || undefined }),
  });
  return jsonOrThrow(res);
}

export async function resumeChat(sessionId, decision, { editedArgs, reason } = {}) {
  const res = await fetch(`${BASE}/chat/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      decision,
      edited_args: editedArgs,
      reason,
    }),
  });
  return jsonOrThrow(res);
}

export async function uploadFiles(files, sessionId) {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  if (sessionId) form.append("session_id", sessionId);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  return jsonOrThrow(res);
}

export async function listFiles(sessionId) {
  const res = await fetch(`${BASE}/sessions/${encodeURIComponent(sessionId)}/files`);
  return jsonOrThrow(res);
}

export async function getHistory(sessionId) {
  const res = await fetch(
    `${BASE}/sessions/${encodeURIComponent(sessionId)}/history`
  );
  return jsonOrThrow(res);
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${BASE}/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  return jsonOrThrow(res);
}
