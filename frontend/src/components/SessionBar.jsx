export default function SessionBar({
  sessionId,
  onNewSession,
  view,
  onNavigate,
  user,
  onLogout,
}) {
  const shortId = sessionId
    ? sessionId.length > 14
      ? `${sessionId.slice(0, 8)}…${sessionId.slice(-4)}`
      : sessionId
    : "not started";

  return (
    <header className="topbar">
      <div className="brand">
        <span className="logo">📚</span>
        <span>Academic Co-Pilot</span>
      </div>

      <nav className="topnav">
        <button
          className={`nav-link${view === "chat" ? " active" : ""}`}
          onClick={() => onNavigate("chat")}
        >
          Chat
        </button>
        <button
          className={`nav-link${view === "guidelines" ? " active" : ""}`}
          onClick={() => onNavigate("guidelines")}
        >
          Guidelines
        </button>
      </nav>

      <div className="session-meta">
        <span
          className="session-id"
          title={sessionId || "A session starts on your first message or upload"}
        >
          {shortId}
        </span>
        {user && <span className="user-email" title={user.email}>{user.email}</span>}
        <button className="ghost" onClick={onLogout}>
          Log out
        </button>
      </div>
    </header>
  );
}
