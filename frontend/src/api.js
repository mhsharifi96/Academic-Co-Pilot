// Thin wrappers around the PaperAgent FastAPI endpoints.
// Requests use relative /api paths; in dev these are proxied to :8000 by Vite
// (see vite.config.js).  Every request carries the JWT; a 401 logs the user out.

import { authHeader, onUnauthorized } from "./auth.js";

const BASE = "/api/v1";

async function request(path, { method = "GET", body, isForm = false } = {}) {
  const headers = { ...authHeader() };
  let payload = body;
  if (body && !isForm) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload });

  if (res.status === 401) {
    onUnauthorized();
    throw new Error("Your session expired — please log in again.");
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON / empty body */
  }
  if (!res.ok) {
    throw new Error((data && data.detail) || res.statusText || `Error ${res.status}`);
  }
  return data;
}

export async function sendChat(message, sessionId) {
  return request("/chat", {
    method: "POST",
    body: { message, session_id: sessionId || undefined },
  });
}

export async function resumeChat(sessionId, decision, { editedArgs, reason } = {}) {
  return request("/chat/resume", {
    method: "POST",
    body: { session_id: sessionId, decision, edited_args: editedArgs, reason },
  });
}

export async function uploadFiles(files, sessionId) {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  if (sessionId) form.append("session_id", sessionId);
  return request("/upload", { method: "POST", body: form, isForm: true });
}

export async function listFiles(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/files`);
}

export async function getHistory(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/history`);
}

export async function deleteSession(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

export async function listSessions() {
  return request("/sessions");
}

export async function renameSession(sessionId, title) {
  return request(`/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    body: { title },
  });
}
