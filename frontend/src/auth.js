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

export async function register(email, password) {
  const data = await post("/auth/register", { email, password });
  store(data.access_token, data.user);
  return data.user;
}
