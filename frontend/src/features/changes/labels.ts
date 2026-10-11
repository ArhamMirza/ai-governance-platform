import type { Change, ChangeAction, ChangeStatus, ChangeType } from "./types";

export const CHANGE_TYPE_OPTIONS: { value: ChangeType; label: string }[] = [
  { value: "ai_system", label: "An AI system" },
  { value: "process", label: "A process or control" },
  { value: "policy", label: "A policy or procedure" },
  { value: "organization", label: "The organization or its roles" },
  { value: "other", label: "Something else" },
];

export function changeTypeLabel(type: ChangeType): string {
  return CHANGE_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

/** What each move is called on the button, and what it needs a note for. */
export const ACTION_LABELS: Record<ChangeAction, string> = {
  start: "Start",
  implement: "Mark Implemented",
  cancel: "Cancel Change",
  reopen: "Reopen",
};

/** The moves available from a status. */
export function actionsFor(status: ChangeStatus): ChangeAction[] {
  switch (status) {
    case "planned":
      return ["start", "implement", "cancel"];
    case "in_progress":
      return ["implement", "cancel"];
    default:
      return ["reopen"];
  }
}

/** Needs someone's attention: still open and past its planned date. */
export function isFlagged(change: Change): boolean {
  return change.standing.overdue;
}
