import type { Change } from "../types";

export function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    id: 1,
    title: "Move the screener to a new base model",
    description: null,
    change_type: "ai_system",
    reason: null,
    consequences: null,
    resources_needed: null,
    owner_id: null,
    raised_on: "2026-06-01",
    planned_date: "2026-07-31",
    status: "planned",
    started_on: null,
    closed_on: null,
    closure_note: null,
    ai_system_row_ids: [],
    standing: { state: "planned", overdue: false },
    framework_tags: [],
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    ...overrides,
  };
}
