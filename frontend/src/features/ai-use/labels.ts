import type { DLPAction, DLPRule } from "./types";

export const ACTION_OPTIONS: { value: DLPAction; label: string; hint: string }[] = [
  { value: "monitor", label: "Monitor", hint: "Count it and let it through" },
  { value: "warn", label: "Warn", hint: "Tell the person; they can go on and give a reason" },
  { value: "block", label: "Block", hint: "Stop it, and say why" },
];

export function actionLabel(action: DLPAction): string {
  return ACTION_OPTIONS.find((option) => option.value === action)?.label ?? action;
}

export const KIND_LABELS = {
  builtin: "Built-in detector",
  keywords: "Words and phrases",
  regex: "Pattern",
} as const;

/** One line saying what a rule looks for, without printing a client's name
 * or a long pattern in full on the list. */
export function describeRule(rule: DLPRule, detectorLabel: (key: string) => string): string {
  if (rule.kind === "builtin") return detectorLabel(rule.builtin_key ?? "");
  if (rule.kind === "keywords") {
    const words = rule.keywords ?? [];
    return `${words.length} word${words.length === 1 ? "" : "s"} or phrase${words.length === 1 ? "" : "s"}`;
  }
  const pattern = rule.pattern ?? "";
  return pattern.length > 40 ? `${pattern.slice(0, 40)}…` : pattern;
}

/** One keyword per line, or separated by commas or semicolons. */
export function splitKeywords(text: string): string[] {
  return text
    .split(/[\n,;]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}
