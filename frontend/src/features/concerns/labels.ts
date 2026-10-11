import type {
  ConcernAction,
  ConcernCategory,
  ConcernChannel,
  ConcernOutcome,
  ConcernStatus,
} from "./types";

export const CATEGORY_OPTIONS: { value: ConcernCategory; label: string; hint: string }[] = [
  { value: "bias_or_fairness", label: "Unfair treatment", hint: "Results that favour or disadvantage some people." },
  { value: "accuracy_or_reliability", label: "Wrong or unreliable results", hint: "Answers or decisions that are often wrong." },
  { value: "safety_or_harm", label: "Risk of harm", hint: "Something that could hurt a person or the business." },
  { value: "privacy_or_data", label: "Privacy or data", hint: "Personal data used or shared in a way that worries you." },
  { value: "misuse_or_breach", label: "Misuse or a broken rule", hint: "A system used for something it shouldn't be." },
  { value: "transparency", label: "Not being told", hint: "People not knowing an AI is involved, or why." },
  { value: "other", label: "Something else", hint: "Anything that doesn't fit the others." },
];

export function categoryLabel(category: ConcernCategory): string {
  return CATEGORY_OPTIONS.find((option) => option.value === category)?.label ?? category;
}

export const CHANNEL_OPTIONS: { value: Exclude<ConcernChannel, "employee_portal">; label: string }[] = [
  { value: "phone", label: "Phone call" },
  { value: "email", label: "Email" },
  { value: "in_person", label: "In person" },
  { value: "other", label: "Another way" },
];

export function channelLabel(channel: ConcernChannel): string {
  if (channel === "employee_portal") return "Staff home";
  return CHANNEL_OPTIONS.find((option) => option.value === channel)?.label ?? channel;
}

export const OUTCOME_OPTIONS: { value: ConcernOutcome; label: string }[] = [
  { value: "substantiated", label: "Substantiated" },
  { value: "partly_substantiated", label: "Partly substantiated" },
  { value: "not_substantiated", label: "Not substantiated" },
  { value: "no_finding", label: "No finding either way" },
];

export function outcomeLabel(outcome: ConcernOutcome): string {
  return OUTCOME_OPTIONS.find((option) => option.value === outcome)?.label ?? outcome;
}

/** In the reporter's words: what's happening to what they raised. */
export function reporterStatusLabel(status: ConcernStatus): string {
  switch (status) {
    case "received":
      return "Received";
    case "under_review":
      return "Being looked into";
    case "resolved":
      return "Resolved";
    case "not_actioned":
      return "Closed without further action";
  }
}

export const ACTION_LABELS: Record<ConcernAction, string> = {
  acknowledge: "Acknowledge",
  resolve: "Resolve",
  dismiss: "Close without action",
  reopen: "Reopen",
};

/** The moves available from a status. */
export function actionsFor(status: ConcernStatus): ConcernAction[] {
  switch (status) {
    case "received":
      return ["acknowledge", "resolve", "dismiss"];
    case "under_review":
      return ["resolve", "dismiss"];
    default:
      return ["reopen"];
  }
}
