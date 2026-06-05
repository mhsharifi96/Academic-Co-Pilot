export default function SessionBar({ sessionId, onNewSession }) {
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
      <div className="session-meta">
        <span>session</span>
        <span className="session-id" title={sessionId || "A session starts on your first message or upload"}>
          {shortId}
        </span>
        <button className="ghost" onClick={onNewSession}>
          New session
        </button>
      </div>
    </header>
  );
}
