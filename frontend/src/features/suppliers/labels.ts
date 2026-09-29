import type { SupplierReviewOutcome, SupplierType } from "./types";

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

export function supplierTypeLabel(type: SupplierType): string {
  return SUPPLIER_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}
