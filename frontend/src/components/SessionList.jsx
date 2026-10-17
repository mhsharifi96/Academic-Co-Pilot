import { useState } from "react";
import Icon from "./Icon.jsx";

// Left-rail list of past sessions (sourced from localStorage in App).
// Click to load, double-click or the pencil to rename inline, the cross to delete.
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
          <Icon name="plus" size={14} />
          New
        </button>
      </div>

      <div className="open-by-key">
        <input
          value={keyInput}
          aria-label="Open a chat by session key"
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
                {/* SVG, not "✎"/"✕": those are font-dependent glyphs that can't
                    take a colour token and mean nothing to a screen reader.
                    The name of the chat goes in the label so the action is
                    unambiguous when read out of context. */}
                <button
                  className="icon"
                  title="Rename"
                  aria-label={`Rename “${s.title || "Untitled chat"}”`}
                  onClick={() => startRename(s)}
                >
                  <Icon name="pencil" size={15} />
                </button>
                <button
                  className="icon danger"
                  title="Delete chat"
                  aria-label={`Delete “${s.title || "Untitled chat"}”`}
                  onClick={() => onDelete(s.id)}
                >
                  <Icon name="close" size={15} />
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
