// Agent picker shown before a chat starts. The choice is bound to the session
// on the first message, so once a session exists this renders a read-only badge
// instead of the picker (see ChatWindow).

const AGENTS = [
  {
    id: "academic",
    icon: "🎓",
    name: "Academic Co-Pilot",
    blurb:
      "Guided assistant for screening, ingesting, planning and drafting papers. " +
      "Supports step-by-step approval of sensitive actions.",
  },
  {
    id: "deep",
    icon: "🧠",
    name: "Deep Agent",
    blurb:
      "Autonomous deep-research agent. Plans its own steps, keeps working memory, " +
      "and runs your whole request end-to-end without stopping for approval.",
  },
];

export default function AgentSelector({ value, onChange, locked = false }) {
  if (locked) {
    const active = AGENTS.find((a) => a.id === value) || AGENTS[0];
    return (
      <div className="agent-badge" title={active.blurb}>
        <span className="agent-badge-icon">{active.icon}</span>
        <span>
          Agent: <strong>{active.name}</strong>
        </span>
      </div>
    );
  }

  return (
    <div className="agent-selector">
      <p className="agent-selector-label">Choose an agent for this chat:</p>
      <div className="agent-options">
        {AGENTS.map((a) => (
          <button
            key={a.id}
            type="button"
            className={`agent-card${value === a.id ? " selected" : ""}`}
            onClick={() => onChange(a.id)}
            aria-pressed={value === a.id}
          >
            <div className="agent-card-head">
              <span className="agent-card-icon">{a.icon}</span>
              <span className="agent-card-name">{a.name}</span>
            </div>
            <p className="agent-card-blurb">{a.blurb}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
