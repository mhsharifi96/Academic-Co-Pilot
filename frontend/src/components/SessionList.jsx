import { useState } from "react";

// Left-rail list of past sessions (sourced from localStorage in App).
// Click to load, double-click / ✎ to rename inline, ✕ to delete.
export default function SessionList({
  sessions,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onOpenKey,
}) {
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState("");
  const [keyInput, setKeyInput] = useState("");

  function startRename(s) {
    setEditingId(s.id);
    setDraft(s.title || "");
  }

  function commitRename(id) {
    const t = draft.trim();
    if (t) onRename(id, t);
    setEditingId(null);
  }

  function submitKey() {
    const k = keyInput.trim();
    if (!k) return;
    onOpenKey(k);
    setKeyInput("");
  }

  return (
    <div className="session-list">
      <div className="session-list-head">
        <h3>Chats</h3>
        <button className="new-chat" onClick={onNew} title="Start a new chat">
          + New
        </button>
      </div>

      <div className="open-by-key">
        <input
          value={keyInput}
          placeholder="Paste session key…"
          onChange={(e) => setKeyInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitKey();
          }}
        />
        <button
          className="open-key-btn"
          disabled={!keyInput.trim()}
          onClick={submitKey}
          title="Load a session by its id"
        >
          Open
        </button>
      </div>

      {sessions.length === 0 ? (
        <p className="empty-note">No saved chats yet.</p>
      ) : (
        <ul>
          {sessions.map((s) => (
            <li
              key={s.id}
              className={`session-row${s.id === activeId ? " active" : ""}`}
            >
              {editingId === s.id ? (
                <input
                  className="rename-input"
                  value={draft}
                  autoFocus
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={() => commitRename(s.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitRename(s.id);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                />
              ) : (
                <button
                  className="session-title"
                  title={s.title}
                  onClick={() => onSelect(s.id)}
                  onDoubleClick={() => startRename(s)}
                >
                  {s.title || "Untitled chat"}
                </button>
              )}

              <span className="session-actions">
                <button
                  className="icon"
                  title="Rename"
                  onClick={() => startRename(s)}
                >
                  ✎
                </button>
                <button
                  className="icon danger"
                  title="Delete chat"
                  onClick={() => onDelete(s.id)}
                >
                  ✕
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
