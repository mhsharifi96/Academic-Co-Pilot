export default function MentionDropdown({ items, activeIndex, onPick }) {
  if (items.length === 0) {
    return (
      <div className="mention-dropdown">
        <div className="mention-empty">No matching files. Upload one on the left.</div>
      </div>
    );
  }

  return (
    <div className="mention-dropdown">
      {items.map((f, i) => (
        <div
          key={f.path}
          className={`mention-item${i === activeIndex ? " active" : ""}`}
          // onMouseDown (not onClick) so it fires before the textarea blurs.
          onMouseDown={(e) => {
            e.preventDefault();
            onPick(f);
          }}
        >
          <span className={`tag ${f.type}`}>{f.type}</span>
          <span className="m-name">{f.filename}</span>
          <span className="m-path">{f.path}</span>
        </div>
      ))}
    </div>
  );
}
