import type { SheetRow } from "../sheets/types";
import type { IncidentSeverity, SeriousIncidentCategory } from "./types";

export const SEVERITY_OPTIONS: { value: IncidentSeverity; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

/** Ordered by how little time each leaves -- the reporting deadline is what
 * the person choosing needs to see. */
export const SERIOUS_CATEGORY_OPTIONS: { value: SeriousIncidentCategory; label: string }[] = [
  {
    value: "widespread_or_critical_infrastructure",
    label: "Widespread infringement or critical infrastructure disruption (2 days)",
  },
  { value: "death", label: "Death of a person (10 days)" },
  { value: "other", label: "Other serious incident (15 days)" },
];

export function aiSystemName(row: SheetRow | undefined, id: number): string {
  const name = row?.data.name;
  return typeof name === "string" && name ? name : `System #${id}`;
}
