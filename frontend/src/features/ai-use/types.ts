import type { FrameworkControl } from "../framework-controls/types";
import type { DataClassification, AIToolStatus } from "../ai-tools/types";

export type DLPRuleKind = "builtin" | "keywords" | "regex";
export type DLPAction = "monitor" | "warn" | "block";

export interface DLPRule {
  id: number;
  name: string;
  description: string | null;
  kind: DLPRuleKind;
  builtin_key: string | null;
  keywords: string[] | null;
  pattern: string | null;
  classification: DataClassification;
  action: DLPAction;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface DLPRuleInput {
  name: string;
  description: string | null;
  kind: DLPRuleKind;
  builtin_key: string | null;
  keywords: string[] | null;
  pattern: string | null;
  classification: DataClassification;
  action: DLPAction;
  enabled: boolean;
}

/** The kind of a rule can't be changed after it is made. */
export type DLPRuleUpdateInput = Partial<Omit<DLPRuleInput, "kind">>;

export interface BuiltinDetector {
  key: string;
  label: string;
  description: string;
}

export interface AIUseSettings {
  id: number;
  unapproved_site_action: DLPAction;
  retention_days: number;
  staff_notice: string | null;
  enrollment_key_issued: boolean;
  enrollment_key_hint: string | null;
  enrollment_key_created_on: string | null;
  framework_tags: FrameworkControl[];
}

export interface AIUseSettingsInput {
  unapproved_site_action?: DLPAction;
  retention_days?: number;
  staff_notice?: string | null;
}

/** The only time the key is ever shown. */
export interface EnrollmentKeyIssued {
  key: string;
  hint: string;
}

export interface UsageByType {
  event_type: "unapproved_site" | "blocked_site" | "dlp_match" | "request_started";
  count: number;
}

export interface UsageByDomain {
  domain: string;
  tool_name: string | null;
  status: AIToolStatus | null;
  unapproved: number;
  blocked: number;
  dlp_matches: number;
  overrides: number;
}

export interface UsageByRule {
  rule_id: number;
  rule_name: string | null;
  matches: number;
  blocked: number;
}

export interface UsageByUser {
  user_ref: string;
  user_name: string | null;
  unapproved: number;
  dlp_matches: number;
  overrides: number;
}

export interface UsageByDay {
  day: string;
  unapproved: number;
  dlp_matches: number;
}

export interface UsageSummary {
  days: number;
  /** Times someone went ahead past a warning. */
  overrides: number;
  by_type: UsageByType[];
  by_domain: UsageByDomain[];
  by_rule: UsageByRule[];
  by_user: UsageByUser[];
  by_day: UsageByDay[];
}

/** What staff are told about how their AI use is monitored. */
export interface StaffAIUseNotice {
  staff_notice: string | null;
  unapproved_site_action: DLPAction;
}

export interface CoveragePerson {
  user_id: number;
  name: string;
  email: string;
  last_seen: string | null;
  extension_version: string | null;
  status: "reporting" | "quiet" | "never";
}

/** Whose browser has the extension and is reaching the platform. */
export interface Coverage {
  days: number;
  active_people: number;
  reporting: number;
  people: CoveragePerson[];
  unmatched_reporters: number;
}
