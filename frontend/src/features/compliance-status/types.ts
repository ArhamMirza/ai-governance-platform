import type { TaggedItem } from "../framework-mapping/types";

export type ComplianceStatusValue = "satisfied" | "partial" | "no_coverage" | "not_applicable";

export interface TaggedItemStatus extends TaggedItem {
  /** Whether this record currently counts toward the control being satisfied. */
  current: boolean;
  detail: string;
}

export interface ControlComplianceStatus {
  id: number;
  framework: string;
  code: string;
  title: string;
  description: string | null;
  category: string;
  status: ComplianceStatusValue;
  reason: string;
  tagged_items: TaggedItemStatus[];
}

export interface ComplianceStatusCounts {
  satisfied: number;
  partial: number;
  no_coverage: number;
  not_applicable: number;
}

export type EuAiActScope = "not_assessed" | "in_scope" | "out_of_scope";

export interface ComplianceStatusSummary {
  iso_42001_clauses: ComplianceStatusCounts;
  iso_42001_annex_a: ComplianceStatusCounts;
  eu_ai_act: ComplianceStatusCounts;
  /** Whether the EU AI Act applies at all -- out of scope means its figures
   * are shown as such rather than as an empty ring. */
  eu_ai_act_scope: EuAiActScope;
}
