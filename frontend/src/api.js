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

export async function sendChat(message, sessionId, agentType) {
  return request("/chat", {
    method: "POST",
    body: {
      message,
      session_id: sessionId || undefined,
      // Only honoured when starting a new session; ignored otherwise.
      agent_type: agentType || undefined,
    },
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

export async function getPlan(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/plan`);
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

// ----- Provider PDF downloads -----

// Queue a PDF download for a DOI, attaching the result to the conversation.
// Throws with the server message on quota (429) / invalid DOI (400).
export async function createDownload(sessionId, doi) {
  return request("/downloads", {
    method: "POST",
    body: { session_id: sessionId, doi },
  });
}

export async function getDownload(jobId) {
  return request(`/downloads/${encodeURIComponent(jobId)}`);
}

export async function listDownloads(sessionId) {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  return request(`/downloads${qs}`);
}

// ----- Account / admin -----

export async function fetchMe() {
  return request("/auth/me");
}

export async function listUsers() {
  return request("/admin/users");
}

export async function updateUser(userId, { balance, isAdmin } = {}) {
  return request(`/admin/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: { balance, is_admin: isAdmin },
  });
}

export async function adjustBalance(userId, amount) {
  return request(`/admin/users/${encodeURIComponent(userId)}/adjust-balance`, {
    method: "POST",
    body: { amount },
  });
}
