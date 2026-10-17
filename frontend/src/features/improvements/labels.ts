import type {
  ImprovementAction,
  ImprovementSource,
  ImprovementSourceType,
  ImprovementStatus,
} from "./types";

export const SOURCE_OPTIONS: { value: ImprovementSource; label: string }[] = [
  { value: "internal_audit", label: "An internal audit" },
  { value: "management_review", label: "A management review" },
  { value: "concern", label: "A concern raised by staff" },
  { value: "incident", label: "An AI incident" },
  { value: "corrective_action", label: "A corrective action" },
  { value: "objective", label: "An AI objective" },
  { value: "stakeholder_feedback", label: "Feedback from an interested party" },
  { value: "idea", label: "An idea from someone in the organization" },
  { value: "other", label: "Something else" },
];

export function sourceLabel(source: ImprovementSource): string {
  return SOURCE_OPTIONS.find((option) => option.value === source)?.label ?? source;
}

/** Where a source record's own page is. */
export function sourcePath(type: ImprovementSourceType, id: number): string | null {
  switch (type) {
    case "Concern":
      return `/concerns/${id}`;
    case "AIIncident":
      return `/incidents/${id}`;
    case "CorrectiveAction":
      return `/corrective-actions/${id}`;
    case "AIObjective":
      return `/objectives/${id}`;
    case "ManagementReviewMeeting":
      return `/management-review/${id}`;
    default:
      // An audit finding has no page of its own; its audit lists it.
      return null;
  }
}

/** What each move is called on the button. */
export const ACTION_LABELS: Record<ImprovementAction, string> = {
  accept: "Accept",
  implement: "Mark Implemented",
  decline: "Decline",
  reopen: "Reopen",
};

/** The moves available from a status. */
export function actionsFor(status: ImprovementStatus): ImprovementAction[] {
  switch (status) {
    case "proposed":
      return ["accept", "decline"];
    case "accepted":
      return ["implement", "decline"];
    default:
      return ["reopen"];
  }
}
