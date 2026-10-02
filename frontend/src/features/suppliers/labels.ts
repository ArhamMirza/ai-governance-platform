import type { SheetRow } from "../sheets/types";
import type { SupplierReviewOutcome, SupplierRole, SupplierType } from "./types";

export const SUPPLIER_TYPE_OPTIONS: { value: SupplierType; label: string }[] = [
  { value: "model_provider", label: "Model provider" },
  { value: "data_provider", label: "Data provider" },
  { value: "infrastructure", label: "Infrastructure / hosting" },
  { value: "software", label: "Software" },
  { value: "services", label: "Services / consultancy" },
  { value: "other", label: "Other" },
];

export const REVIEW_OUTCOME_OPTIONS: { value: SupplierReviewOutcome; label: string }[] = [
  { value: "satisfactory", label: "Satisfactory" },
  { value: "concerns", label: "Concerns raised" },
  { value: "unsatisfactory", label: "Unsatisfactory" },
];

export const SUPPLIER_ROLE_OPTIONS: { value: SupplierRole; label: string }[] = [
  { value: "provider", label: "Provider of the AI system" },
  { value: "component_supplier", label: "Component, tool or data supplier" },
  { value: "importer", label: "Importer" },
  { value: "distributor", label: "Distributor" },
];

/** EU AI Act Art. 25(1): doing any of these makes your organization the
 * provider of the supplier's system. */
export const ART25_TRIGGERS: {
  key: "rebranded" | "substantially_modified" | "repurposed_to_high_risk";
  label: string;
}[] = [
  { key: "rebranded", label: "We put our own name or trademark on it" },
  { key: "substantially_modified", label: "We substantially modified it" },
  { key: "repurposed_to_high_risk", label: "We changed its purpose so it became high-risk" },
];

export const ART25_WARNING =
  "Your organization may be this system's provider under EU AI Act Art. 25(1), with the provider's obligations.";

export function supplierTypeLabel(type: SupplierType): string {
  return SUPPLIER_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

export function supplierRoleLabel(role: SupplierRole | null): string {
  if (role === null) return "Role not recorded";
  return SUPPLIER_ROLE_OPTIONS.find((option) => option.value === role)?.label ?? role;
}

export function aiSystemName(row: SheetRow | undefined, id: number): string {
  const name = row?.data.name;
  return typeof name === "string" && name ? name : `System #${id}`;
}
