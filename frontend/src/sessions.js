// Browser-local registry of chat sessions the user has seen, kept in
// localStorage.  Each entry is { id, title, lastUsed } (lastUsed = ms epoch).
// The backend persists the actual conversation; this is just the list the UI
// shows so you can switch between past sessions on this device.

const KEY = "paperagent.sessions";

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function write(list) {
  localStorage.setItem(KEY, JSON.stringify(list));
}

// Newest-first by lastUsed.
export function listSessions() {
  return read().sort((a, b) => (b.lastUsed || 0) - (a.lastUsed || 0));
}

// Insert or update a session; preserves an existing custom title unless one is
// explicitly provided.
export function upsertSession(id, { title } = {}) {
  const list = read();
  const existing = list.find((s) => s.id === id);
  const now = Date.now();
  if (existing) {
    if (title) existing.title = title;
    existing.lastUsed = now;
  } else {
    list.push({ id, title: title || "New chat", lastUsed: now });
  }
  write(list);
  return listSessions();
}

export function touchSession(id) {
  const list = read();
  const s = list.find((x) => x.id === id);
  if (s) {
    s.lastUsed = Date.now();
    write(list);
  }
  return listSessions();
}

export function renameSession(id, title) {
  const list = read();
  const s = list.find((x) => x.id === id);
  if (s) {
    s.title = title;
    write(list);
  }
  return listSessions();
}

export function removeSession(id) {
  write(read().filter((s) => s.id !== id));
  return listSessions();
}

// Build a short title from the first user message.
export function titleFromMessage(text, max = 48) {
  const clean = (text || "").trim().replace(/\s+/g, " ");
  if (!clean) return "New chat";
  return clean.length > max ? clean.slice(0, max - 1) + "…" : clean;
}
