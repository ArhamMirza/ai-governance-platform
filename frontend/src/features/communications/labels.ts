import type { Communication, CommunicationDirection } from "./types";

export const DIRECTION_OPTIONS: { value: CommunicationDirection; label: string }[] = [
  { value: "internal", label: "Internal" },
  { value: "external", label: "External" },
];

export function directionLabel(direction: CommunicationDirection): string {
  return DIRECTION_OPTIONS.find((option) => option.value === direction)?.label ?? direction;
}

/** Says how often it happens, or that it's done only when needed. */
export function cadenceLabel(item: Communication): string {
  if (item.interval_months === null) return "When needed";
  return item.interval_months === 1 ? "Monthly" : `Every ${item.interval_months} months`;
}
