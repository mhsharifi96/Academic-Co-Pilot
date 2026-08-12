// Auth state + token storage (localStorage) and the auth API calls.
// A 401 from any request dispatches an "auth:logout" event so App can drop the
// user back to the login screen.

const TOKEN_KEY = "paperagent.token";
const USER_KEY = "paperagent.user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function authHeader() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

function store(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// Persist an updated user object (e.g. after the balance changes) without
// touching the token. Returns the stored user.
export function setUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

// Merge partial fields (e.g. {balance}) into the stored user and persist.
export function patchUser(patch) {
  const current = getUser() || {};
  const merged = { ...current, ...patch };
  localStorage.setItem(USER_KEY, JSON.stringify(merged));
  return merged;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function onUnauthorized() {
  logout();
  window.dispatchEvent(new Event("auth:logout"));
}

async function post(path, body) {
  const res = await fetch(`/api/v1${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* ignore */
  }
  if (!res.ok) {
    throw new Error((data && data.detail) || `Request failed (${res.status})`);
  }
  return data;
}

export async function login(email, password) {
  const data = await post("/auth/login", { email, password });
  store(data.access_token, data.user);
  return data.user;
}

// Public flags for the signed-out login screen (currently: is sign-up open?).
// Never throws — a failure just falls back to showing the sign-up option, and
// the register call itself is the real gate.
export async function fetchAuthConfig() {
  try {
    const res = await fetch("/api/v1/auth/config");
    if (!res.ok) return { registration_open: true };
    return await res.json();
  } catch {
    return { registration_open: true };
  }
}

export async function register(email, password) {
  const data = await post("/auth/register", { email, password });
  store(data.access_token, data.user);
  return data.user;
}
