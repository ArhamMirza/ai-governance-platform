import type { Concern, ReporterConcern } from "../types";

export function makeConcern(overrides: Partial<Concern> = {}): Concern {
  return {
    id: 1,
    category: "bias_or_fairness",
    description: "The screener keeps ranking candidates from one university first.",
    ai_system_row_id: null,
    system_note: null,
    channel: "employee_portal",
    received_on: "2026-06-01",
    is_anonymous: false,
    reporter_id: 5,
    reporter_name: "Elena Employee",
    reporter_note: null,
    status: "received",
    handler_id: null,
    acknowledged_on: null,
    closed_on: null,
    outcome: null,
    internal_notes: null,
    closure_note: null,
    reply_to_reporter: null,
    incident_id: null,
    acknowledge_by: "2026-06-08",
    awaiting_triage: false,
    ...overrides,
  };
}

export function makeReporterConcern(overrides: Partial<ReporterConcern> = {}): ReporterConcern {
  return {
    id: 1,
    category: "bias_or_fairness",
    description: "The screener keeps ranking candidates from one university first.",
    received_on: "2026-06-01",
    status: "received",
    acknowledged_on: null,
    closed_on: null,
    outcome: null,
    reply_to_reporter: null,
    is_anonymous: false,
    ...overrides,
  };
}
