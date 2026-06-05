import { useEffect, useLayoutEffect, useRef, useState } from "react";
import MentionDropdown from "./MentionDropdown.jsx";

// Detect an in-progress "@mention" immediately before the caret.
// Returns { start, query } where `start` is the index of the "@", or null.
function detectMention(value, caret) {
  const upToCaret = value.slice(0, caret);
  const match = /(^|\s)@([^\s@]*)$/.exec(upToCaret);
  if (!match) return null;
  const query = match[2];
  const start = caret - query.length - 1; // position of "@"
  return { start, query };
}

export default function MessageInput({
  value,
  onChange,
  onSend,
  files,
  disabled,
  interrupted,
}) {
  const taRef = useRef(null);
  const caretToRestore = useRef(null);

  const [mention, setMention] = useState(null); // { start, query } | null
  const [activeIndex, setActiveIndex] = useState(0);

  const matches = mention
    ? files.filter((f) => {
        const q = mention.query.toLowerCase();
        if (!q) return true;
        return (
          f.filename.toLowerCase().includes(q) ||
          f.path.toLowerCase().includes(q)
        );
      })
    : [];

  const open = !!mention && files.length > 0;

  // Keep the active row in range as the filtered list changes.
  useEffect(() => {
    setActiveIndex((i) => Math.min(i, Math.max(0, matches.length - 1)));
  }, [matches.length]);

  // Restore caret position after a programmatic value change (mention insert).
  useLayoutEffect(() => {
    if (caretToRestore.current != null && taRef.current) {
      const pos = caretToRestore.current;
      taRef.current.focus();
      taRef.current.setSelectionRange(pos, pos);
      caretToRestore.current = null;
    }
  });

  // Auto-grow the textarea up to its CSS max-height.
  useLayoutEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }, [value]);

  function refreshMention() {
    const ta = taRef.current;
    if (!ta) return;
    setMention(detectMention(ta.value, ta.selectionStart));
  }

  function handleChange(e) {
    onChange(e.target.value);
    // selectionStart reflects the post-change caret here.
    setMention(detectMention(e.target.value, e.target.selectionStart));
    setActiveIndex(0);
  }

  function pick(file) {
    if (!mention) return;
    const caret = taRef.current.selectionStart;
    const before = value.slice(0, mention.start);
    const after = value.slice(caret);
    const insert = `${file.path} `;
    const next = before + insert + after;
    caretToRestore.current = (before + insert).length;
    onChange(next);
    setMention(null);
  }

  function handleKeyDown(e) {
    if (open && matches.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => (i + 1) % matches.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => (i - 1 + matches.length) % matches.length);
        return;
      }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        pick(matches[activeIndex]);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setMention(null);
        return;
      }
    }

    // Plain Enter sends; Shift+Enter inserts a newline.
    if (e.key === "Enter" && !e.shiftKey && !open) {
      e.preventDefault();
      onSend(value);
    }
  }

  const placeholder = interrupted
    ? "Resolve the approval above to continue…"
    : "Ask anything — type “@” to reference a file. Enter to send, Shift+Enter for newline.";

  return (
    <div className="composer">
      {open && (
        <MentionDropdown
          items={matches}
          activeIndex={activeIndex}
          onPick={pick}
        />
      )}
      <span className="hint">@ to reference files</span>
      <div className="composer-inner">
        <textarea
          ref={taRef}
          rows={1}
          value={value}
          placeholder={placeholder}
          disabled={disabled}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onClick={refreshMention}
          onKeyUp={(e) => {
            // Keep mention state in sync when moving the caret with arrows/home/end.
            if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
              refreshMention();
            }
          }}
        />
        <button
          className="primary"
          disabled={disabled || !value.trim()}
          onClick={() => onSend(value)}
        >
          Send
        </button>
      </div>
    </div>
  );
}
