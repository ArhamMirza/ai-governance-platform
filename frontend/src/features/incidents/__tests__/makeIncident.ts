import type { SheetWithRows } from "../../sheets/types";
import type { Incident } from "../types";

export function makeIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: 1,
    title: "Screener rejected older applicants",
    description: "Age-correlated features drove rejections for a week.",
    ai_system_row_id: null,
    detected_on: "2026-03-01",
    occurred_on: null,
    severity: "medium",
    status: "open",
    owner_id: null,
    impact_description: null,
    immediate_actions: null,
    root_cause: null,
    is_serious: false,
    serious_category: null,
    authority_notified_on: null,
    authority_reference: null,
    reporting_deadline: null,
    reporting_overdue: false,
    corrective_action_ids: [],
    framework_tags: [],
    resolved_at: null,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
    ...overrides,
  };
}

export const aiSystemInventory: SheetWithRows = {
  id: 2,
  entity_type: "AISystemInventory",
  title: "AI System Inventory",
  columns: [{ key: "name", label: "Name", data_type: "text" }],
  rows: [
    {
      id: 7,
      sheet_id: 2,
      row_index: 1,
      data: { name: "Resume Screener" },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
