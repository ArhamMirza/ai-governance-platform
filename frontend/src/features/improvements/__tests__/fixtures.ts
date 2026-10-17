import type { Improvement } from "../types";

export function makeImprovement(overrides: Partial<Improvement> = {}): Improvement {
  return {
    id: 1,
    title: "Name risk owners as individuals",
    description: null,
    expected_benefit: null,
    source: "idea",
    source_type: null,
    source_id: null,
    source_label: null,
    owner_id: null,
    raised_on: "2026-06-01",
    target_date: "2026-08-01",
    status: "proposed",
    decided_on: null,
    closed_on: null,
    outcome: null,
    decline_reason: null,
    change_id: null,
    standing: { state: "proposed", overdue: false },
    framework_tags: [],
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    ...overrides,
  };
}
