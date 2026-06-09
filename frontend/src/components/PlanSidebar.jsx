const STATUS_ICON = {
  done: "✓",
  in_progress: "◔",
  pending: "○",
};

export default function PlanSidebar({ plan }) {
  if (!plan || plan.length === 0) return null;

  const done = plan.filter((p) => p.status === "done").length;

  return (
    <section className="plan-section">
      <h3>
        Plan <span className="plan-progress">{done}/{plan.length}</span>
      </h3>
      <ul className="plan-list">
        {plan.map((item, i) => (
          <li className={`plan-item ${item.status}`} key={i}>
            <span className="plan-icon">{STATUS_ICON[item.status] || "○"}</span>
            <span className="plan-text">{item.text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
