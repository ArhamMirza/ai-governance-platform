import type { AIUseSettings, BuiltinDetector, DLPRule, UsageSummary } from "../types";

export function makeRule(overrides: Partial<DLPRule> = {}): DLPRule {
  return {
    id: 1,
    name: "Payment card numbers",
    description: null,
    kind: "builtin",
    builtin_key: "credit_card",
    keywords: null,
    pattern: null,
    classification: "confidential",
    action: "block",
    enabled: true,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    ...overrides,
  };
}

export function makeSettings(overrides: Partial<AIUseSettings> = {}): AIUseSettings {
  return {
    id: 1,
    unapproved_site_action: "monitor",
    retention_days: 90,
    staff_notice: null,
    enrollment_key_issued: false,
    enrollment_key_hint: null,
    enrollment_key_created_on: null,
    framework_tags: [],
    ...overrides,
  };
}

export const DETECTORS: BuiltinDetector[] = [
  { key: "credit_card", label: "Payment card number", description: "13 to 19 digits." },
  { key: "api_key", label: "API key or access token", description: "Well-known key formats." },
  { key: "pk_cnic", label: "Pakistan CNIC number", description: "Thirteen digits." },
];

export function makeUsage(overrides: Partial<UsageSummary> = {}): UsageSummary {
  return {
    days: 30,
    by_type: [
      { event_type: "unapproved_site", count: 14 },
      { event_type: "dlp_match", count: 6 },
    ],
    by_domain: [
      {
        domain: "claude.ai",
        tool_name: "Claude",
        status: "catalogued",
        unapproved: 9,
        blocked: 0,
        dlp_matches: 6,
      },
      {
        domain: "grok.com",
        tool_name: null,
        status: null,
        unapproved: 5,
        blocked: 2,
        dlp_matches: 0,
      },
    ],
    by_rule: [{ rule_id: 1, rule_name: "Payment card numbers", matches: 6, blocked: 5 }],
    by_user: [
      { user_ref: "elena@example.com", user_name: "Elena Employee", unapproved: 9, dlp_matches: 6 },
      { user_ref: "bob@example.com", user_name: null, unapproved: 5, dlp_matches: 0 },
    ],
    by_day: [
      { day: "2026-06-01", unapproved: 4, dlp_matches: 0 },
      { day: "2026-06-02", unapproved: 10, dlp_matches: 6 },
    ],
    ...overrides,
  };
}
