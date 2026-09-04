import { STAGES } from "../stages";

interface LifecycleStageTrackerProps {
  currentStage: string;
}

export function LifecycleStageTracker({ currentStage }: LifecycleStageTrackerProps) {
  const currentIndex = STAGES.findIndex((stage) => stage.key === currentStage);

  return (
    <ol className="stage-tracker" aria-label="Life cycle stage">
      {STAGES.map((stage, index) => {
        const state =
          index < currentIndex ? "done" : index === currentIndex ? "current" : "upcoming";
        return (
          <li
            key={stage.key}
            className={`stage-step is-${state}`}
            aria-current={state === "current" ? "step" : undefined}
          >
            <span className="stage-step-marker">{state === "done" ? "✓" : index + 1}</span>
            <span className="stage-step-label">{stage.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
