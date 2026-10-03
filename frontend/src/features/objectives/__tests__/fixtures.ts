import type { Measurement, Objective, ObjectiveDetail, ObjectiveStanding } from "../types";

export function makeStanding(overrides: Partial<ObjectiveStanding> = {}): ObjectiveStanding {
  return {
    state: "not_measured",
    latest_value: null,
    latest_on: null,
    next_measurement_due: null,
    measurement_overdue: false,
    ...overrides,
  };
}

export function makeObjective(overrides: Partial<Objective> = {}): Objective {
  return {
    id: 1,
    title: "Bias test pass rate",
    description: null,
    kind: "measured",
    owner_id: null,
    policy_id: null,
    established_on: "2026-01-01",
    target_date: "2026-12-31",
    planned_actions: null,
    resources: null,
    evaluation_method: null,
    metric_name: "Pass rate",
    unit: "%",
    direction: "at_least",
    target_value: 95,
    baseline_value: null,
    measurement_interval_months: null,
    first_measurement_due: null,
    status: "active",
    closed_on: null,
    closure_note: null,
    ai_system_row_ids: [],
    standing: makeStanding(),
    framework_tags: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeObjectiveDetail(overrides: Partial<ObjectiveDetail> = {}): ObjectiveDetail {
  return { ...makeObjective(), measurements: [], ...overrides };
}

export function makeMeasurement(overrides: Partial<Measurement> = {}): Measurement {
  return {
    id: 1,
    objective_id: 1,
    measured_on: "2026-03-01",
    value: 90,
    note: null,
    recorded_by: null,
    created_at: "2026-03-01T00:00:00Z",
    ...overrides,
  };
}
