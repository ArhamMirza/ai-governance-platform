import type { AITool, AIToolAction, AIToolStatus, DataClassification } from "./types";

export const CLASSIFICATION_OPTIONS: { value: DataClassification; label: string; hint: string }[] =
  [
    { value: "public", label: "Public", hint: "Nothing that isn't already public" },
    { value: "internal", label: "Internal", hint: "Everyday work, no personal or client data" },
    { value: "confidential", label: "Confidential", hint: "Sensitive business or personal data" },
  ];

export function classificationLabel(value: DataClassification): string {
  return CLASSIFICATION_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

/** What each status means, in the words the people using it would. */
export const STATUS_LABELS: Record<AIToolStatus, string> = {
  catalogued: "Not approved",
  approved: "Approved",
  restricted: "Approved with limits",
  revoked: "Access withdrawn",
};

export const ACTION_LABELS: Record<AIToolAction, string> = {
  approve: "Approve",
  restrict: "Approve with Limits",
  revoke: "Withdraw Access",
};

/** The decisions available from a status -- anything but the one it's in, and
 * nothing to withdraw from a tool that was never approved. */
export function actionsFor(status: AIToolStatus): AIToolAction[] {
  switch (status) {
    case "catalogued":
      return ["approve", "restrict"];
    case "approved":
      return ["restrict", "revoke"];
    case "restricted":
      return ["approve", "revoke"];
    default:
      return ["approve", "restrict"];
  }
}

/** Needs someone's attention: approved, and past its review date. */
export function isFlagged(tool: AITool): boolean {
  return tool.standing.review_overdue;
}

/** One address per line, or separated by commas or spaces. */
export function splitDomains(text: string): string[] {
  return text
    .split(/[\s,]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}
