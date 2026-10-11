import type { Communication, CommunicationDetail, CommunicationRecord } from "../types";

export function makeCommunication(overrides: Partial<Communication> = {}): Communication {
  return {
    id: 1,
    topic: "Quarterly AI governance update",
    audience: "Leadership team",
    direction: "internal",
    method: "Board pack",
    responsible_id: null,
    notes: null,
    status: "active",
    interval_months: 3,
    first_due: "2026-03-31",
    last_communicated_on: null,
    next_due: "2026-03-31",
    overdue: false,
    framework_tags: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeCommunicationDetail(
  overrides: Partial<CommunicationDetail> = {},
): CommunicationDetail {
  return { ...makeCommunication(), records: [], ...overrides };
}

export function makeRecord(overrides: Partial<CommunicationRecord> = {}): CommunicationRecord {
  return {
    id: 1,
    communication_id: 1,
    communicated_on: "2026-06-01",
    summary: null,
    recorded_by: null,
    created_at: "2026-06-01T00:00:00Z",
    ...overrides,
  };
}
