import { useT } from "../i18n.js";
import Icon from "./Icon.jsx";

// Progress header for a run: where you are, what the step is called, and how
// many turns remain before the workflow moves on.  Progress is expressed both
// as a bar and as text, so it never depends on colour or width alone.
export default function WizardStepper({ run, onFinishStep, finishing, suggested }) {
  const { t } = useT();
  if (!run) return null;

  const total = run.total_steps || 0;
  const index = run.current_step_index || (run.completed_at ? total : 0);
  const done = run.status === "completed";
  const pct = total > 0 ? Math.round(((done ? total : Math.max(0, index - 1)) / total) * 100) : 0;
  const left = run.messages_left_in_step;
  // `steps` is ordered and `index` is 1-based, so the next step sits at [index].
  // Naming where "Finish step" leads makes it a decision rather than a leap.
  const nextStep = !done && index > 0 ? (run.steps || [])[index] : null;

  return (
    <div className="wz-stepper">
      <div className="wz-stepper-head">
        <div className="wz-stepper-where">
          <span className="wz-stepper-count">
            {done ? t("runner.completedTitle") : t("runner.stepOf", { i: index, n: total })}
          </span>
          {!done && run.current_step?.name && (
            <span className="wz-stepper-name">{run.current_step.name}</span>
          )}
        </div>

        {!done && (
          <span className={`wz-chip${left === 0 ? " warn" : ""}`}>
            {left === null || left === undefined
              ? t("runner.uncapped")
              : t("runner.messagesLeft", { n: left })}
          </span>
        )}
        {done && (
          <span className="wz-chip done">
            <Icon name="check" size={14} />
            {t("runner.completedTitle")}
          </span>
        )}

        {/* Always available so a step can end when the work is done rather than
            when its message budget runs out. Highlighted once the agent has
            said the step looks finished — but never auto-advancing: moving on
            stays the user's decision. */}
        {!done && onFinishStep && (
          <span className="wz-finish-group">
            <button
              type="button"
              className={`wz-btn small wz-finish-step${suggested ? " suggested" : " ghost"}`}
              onClick={onFinishStep}
              disabled={finishing}
              title={
                nextStep?.name
                  ? t("runner.finishStepToHint", { name: nextStep.name })
                  : t(index >= total ? "runner.finishWorkflowHint" : "runner.finishStepHint")
              }
            >
              {finishing
                ? t("common.saving")
                : t(index >= total ? "runner.finishWorkflow" : "runner.finishStep")}
              <Icon name="arrow" size={15} className="wz-go-arrow" />
            </button>
            {nextStep?.name && (
              <span className="wz-next-step" title={nextStep.name}>
                {t("runner.nextIs", { name: nextStep.name })}
              </span>
            )}
          </span>
        )}
      </div>

      <div
        className="wz-progress"
        role="progressbar"
        aria-valuenow={done ? total : Math.max(0, index - 1)}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label={t("runner.stepOf", { i: index, n: total })}
      >
        <div className="wz-progress-fill" style={{ width: `${pct}%` }} />
      </div>

      {total > 0 && total <= 12 && (
        <ol className="wz-dots">
          {Array.from({ length: total }, (_, i) => {
            const n = i + 1;
            const state = done || n < index ? "done" : n === index ? "current" : "todo";
            return <li key={n} className={`wz-dot ${state}`} title={`${n}`} />;
          })}
        </ol>
      )}
    </div>
  );
}
