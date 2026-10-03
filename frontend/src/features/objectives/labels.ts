import type {
  Objective,
  ObjectiveKind,
  ObjectiveState,
  ObjectiveStatus,
  TargetDirection,
} from "./types";

export const KIND_OPTIONS: { value: ObjectiveKind; label: string; hint: string }[] = [
  {
    value: "measured",
    label: "Measured",
    hint: "A metric with a target; on or off track is worked out from the readings you record.",
  },
  {
    value: "milestone",
    label: "Milestone",
    hint: "A goal that's done or not, tracked by its target date.",
  },
];

export const DIRECTION_OPTIONS: { value: TargetDirection; label: string }[] = [
  { value: "at_least", label: "At least" },
  { value: "at_most", label: "At most" },
];

export const CLOSE_OPTIONS: { value: Exclude<ObjectiveStatus, "active">; label: string }[] = [
  { value: "achieved", label: "Achieved" },
  { value: "not_achieved", label: "Not achieved" },
  { value: "withdrawn", label: "Withdrawn" },
];

const STATE_LABELS: Record<ObjectiveState, string> = {
  not_measured: "Not measured yet",
  on_track: "On track",
  off_track: "Off track",
  missed: "Target missed",
  in_progress: "In progress",
  achieved: "Achieved",
  not_achieved: "Not achieved",
  withdrawn: "Withdrawn",
};

export function stateLabel(state: ObjectiveState): string {
  return STATE_LABELS[state];
}

export function formatValue(value: number, unit: string | null): string {
  // Readings are stored as floats; show 96.5 as "96.5" and 95 as "95".
  const number = Number.isInteger(value) ? value.toString() : value.toFixed(2).replace(/0+$/, "");
  if (!unit) return number;
  return unit === "%" ? `${number}%` : `${number} ${unit}`;
}

/** "≥ 95%" -- the target as one phrase. */
export function targetLabel(
  direction: TargetDirection | null,
  target: number | null,
  unit: string | null,
): string {
  if (direction === null || target === null) return "—";
  return `${direction === "at_least" ? "≥" : "≤"} ${formatValue(target, unit)}`;
}

/** Needs someone's attention: short of its target, or a reading is due. */
export function isFlagged(objective: Objective): boolean {
  const { state, measurement_overdue } = objective.standing;
  return state === "off_track" || state === "missed" || measurement_overdue;
}
