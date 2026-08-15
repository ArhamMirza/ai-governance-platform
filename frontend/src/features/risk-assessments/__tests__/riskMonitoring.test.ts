import { describe, expect, it } from "vitest";

import type { SheetRow } from "../../sheets/types";
import { isRiskItemOverdue } from "../riskMonitoring";

const NOW = new Date("2026-06-15T00:00:00Z");

function makeRow(data: Record<string, unknown>): SheetRow {
  return {
    id: 1,
    sheet_id: 1,
    row_index: 1,
    data,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

describe("isRiskItemOverdue", () => {
  it("is overdue when the deadline has passed and status is untreated", () => {
    const row = makeRow({ treatment_deadline: "2026-01-01", status: "open" });

    expect(isRiskItemOverdue(row, NOW)).toBe(true);
  });

  it("is not overdue when the deadline is in the future", () => {
    const row = makeRow({ treatment_deadline: "2026-12-31", status: "open" });

    expect(isRiskItemOverdue(row, NOW)).toBe(false);
  });

  it("is not overdue when there is no deadline set", () => {
    const row = makeRow({ status: "open" });

    expect(isRiskItemOverdue(row, NOW)).toBe(false);
  });

  it("is not overdue once the status indicates treatment is done", () => {
    const row = makeRow({ treatment_deadline: "2026-01-01", status: "Treated" });

    expect(isRiskItemOverdue(row, NOW)).toBe(false);
  });

  it("recognizes common closed-status synonyms case-insensitively", () => {
    for (const status of ["closed", "RESOLVED", "Completed", "done", "mitigated"]) {
      const row = makeRow({ treatment_deadline: "2026-01-01", status });
      expect(isRiskItemOverdue(row, NOW)).toBe(false);
    }
  });

  it("ignores an unparseable deadline instead of throwing", () => {
    const row = makeRow({ treatment_deadline: "not-a-date", status: "open" });

    expect(isRiskItemOverdue(row, NOW)).toBe(false);
  });
});
