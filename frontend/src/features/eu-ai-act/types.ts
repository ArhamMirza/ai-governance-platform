import type { EuAiActScope } from "../compliance-status/types";

export interface EuAiActApplicability {
  scope: EuAiActScope;
  in_scope: boolean | null;
  scope_justification: string | null;
  is_provider: boolean;
  is_deployer: boolean;
  is_importer: boolean;
  is_distributor: boolean;
  has_high_risk_systems: boolean | null;
  /** From the inventory's Risk Tier column -- a hint, never used to decide. */
  high_risk_system_count: number;
  /** EU role keys (provider, deployer ...) the organization's AI roles point
   * to -- offered only until it records any of its own. */
  suggested_roles: string[];
  updated_by: number | null;
  updated_at: string | null;
}

export type EuAiActApplicabilityInput = Omit<
  EuAiActApplicability,
  "scope" | "high_risk_system_count" | "suggested_roles" | "updated_by" | "updated_at"
>;

export type Applicability = "applicable" | "not_applicable";

export interface EuAiActArticle {
  id: number;
  code: string;
  title: string;
  automatic_applicable: boolean;
  automatic_reason: string;
  override_applicability: Applicability | null;
  override_justification: string | null;
  applicable: boolean;
  reason: string;
}
