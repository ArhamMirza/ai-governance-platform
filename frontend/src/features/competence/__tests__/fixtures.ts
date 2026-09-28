import type { CompetenceRequirement, CompetenceRequirementSummary } from "../types";

export function makeSummary(
  overrides: Partial<CompetenceRequirementSummary> = {},
): CompetenceRequirementSummary {
  return {
    id: 1,
    title: "Bias testing fundamentals",
    description: null,
    governance_role_id: null,
    refresh_interval_months: null,
    required_count: 0,
    current_count: 0,
    gap_count: 0,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeRequirement(
  overrides: Partial<CompetenceRequirement> = {},
): CompetenceRequirement {
  return {
    ...makeSummary(),
    people: [],
    records: [],
    framework_tags: [],
    ...overrides,
  };
}
