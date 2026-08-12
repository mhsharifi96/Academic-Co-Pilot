// Thin wrappers around the PaperAgent FastAPI endpoints.
// Requests use relative /api paths; in dev these are proxied to :8000 by Vite
// (see vite.config.js).  Every request carries the JWT; a 401 logs the user out.

import { authHeader, onUnauthorized } from "./auth.js";

const BASE = "/api/v1";

async function request(path, { method = "GET", body, isForm = false, anon = false } = {}) {
  // `anon` requests are for the public wizard catalogue: they must work for a
  // signed-out visitor, so they carry no token and never trigger a logout.
  const headers = anon ? {} : { ...authHeader() };
  let payload = body;
  if (body && !isForm) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload });

  if (res.status === 401 && !anon) {
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

// ----- Wizards (guided workflows) -----
//
// `lang` selects which language's content columns the server resolves; it is
// not a UI-only concern, so every wizard call carries it.

const lq = (lang) => `lang=${encodeURIComponent(lang || "en")}`;

// Public: no token needed, works for signed-out visitors on the landing page.
export async function listWizards(lang) {
  return request(`/wizards?${lq(lang)}`, { anon: true });
}

export async function getWizard(slug, lang) {
  return request(`/wizards/${encodeURIComponent(slug)}?${lq(lang)}`, { anon: true });
}

// Starts a run, or returns the caller's existing active run of the same wizard
// (with its transcript), which is what "continue" uses.
export async function startWizardRun({ wizardId, slug }, lang) {
  return request(`/wizard-runs?${lq(lang)}`, {
    method: "POST",
    body: { wizard_id: wizardId, slug },
  });
}

export async function listWizardRuns(status, lang) {
  const s = status ? `&status=${encodeURIComponent(status)}` : "";
  return request(`/wizard-runs?${lq(lang)}${s}`);
}

export async function getWizardRun(runId, lang) {
  return request(`/wizard-runs/${encodeURIComponent(runId)}?${lq(lang)}`);
}

export async function sendWizardMessage(runId, message, lang) {
  return request(`/wizard-runs/${encodeURIComponent(runId)}/messages?${lq(lang)}`, {
    method: "POST",
    body: { message },
  });
}

// Ask for follow-up questions the user could send next. This IS an LLM call and
// is billed, so it is only ever fired from an explicit user action.
export async function suggestWizardQuestions(runId, lang) {
  return request(`/wizard-runs/${encodeURIComponent(runId)}/suggestions?${lq(lang)}`, {
    method: "POST",
  });
}

// Finish the current step now, without spending its remaining messages. Costs
// nothing — no agent call.
export async function advanceWizardRun(runId, lang) {
  return request(`/wizard-runs/${encodeURIComponent(runId)}/advance?${lq(lang)}`, {
    method: "POST",
  });
}

export async function resumeWizardRun(runId, decision, { editedArgs, reason } = {}, lang) {
  return request(`/wizard-runs/${encodeURIComponent(runId)}/resume?${lq(lang)}`, {
    method: "POST",
    body: { decision, edited_args: editedArgs, reason },
  });
}

export async function abandonWizardRun(runId) {
  return request(`/wizard-runs/${encodeURIComponent(runId)}`, { method: "DELETE" });
}

// ----- Wizard admin -----

export async function adminListWizards() {
  return request("/admin/wizards");
}

export async function adminGetWizard(wizardId) {
  return request(`/admin/wizards/${encodeURIComponent(wizardId)}`);
}

export async function adminCreateWizard(fields) {
  return request("/admin/wizards", { method: "POST", body: fields });
}

export async function adminUpdateWizard(wizardId, fields) {
  return request(`/admin/wizards/${encodeURIComponent(wizardId)}`, {
    method: "PATCH",
    body: fields,
  });
}

export async function adminDeleteWizard(wizardId) {
  return request(`/admin/wizards/${encodeURIComponent(wizardId)}`, { method: "DELETE" });
}

export async function adminCreateStep(wizardId, fields) {
  return request(`/admin/wizards/${encodeURIComponent(wizardId)}/steps`, {
    method: "POST",
    body: fields,
  });
}

// Append a whole outline (one step name per line) in one request. Returns the
// created steps, in order.
export async function adminCreateSteps(wizardId, fields) {
  return request(`/admin/wizards/${encodeURIComponent(wizardId)}/steps/bulk`, {
    method: "POST",
    body: fields,
  });
}

export async function adminUpdateStep(stepId, fields) {
  return request(`/admin/wizard-steps/${encodeURIComponent(stepId)}`, {
    method: "PATCH",
    body: fields,
  });
}

export async function adminDeleteStep(stepId) {
  return request(`/admin/wizard-steps/${encodeURIComponent(stepId)}`, {
    method: "DELETE",
  });
}

export async function adminReorderSteps(wizardId, stepIds) {
  return request(`/admin/wizards/${encodeURIComponent(wizardId)}/steps/reorder`, {
    method: "PUT",
    body: { step_ids: stepIds },
  });
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
