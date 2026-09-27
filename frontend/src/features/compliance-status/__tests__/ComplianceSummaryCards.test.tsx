import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ComplianceSummaryCards } from "../components/ComplianceSummaryCards";
import { useComplianceStatusSummary } from "../hooks";
import type { ComplianceStatusSummary } from "../types";

vi.mock("../hooks");

function mockSummary(summary: ComplianceStatusSummary) {
  vi.mocked(useComplianceStatusSummary).mockReturnValue({
    data: summary,
    isLoading: false,
    isError: false,
  } as never);
}

describe("ComplianceSummaryCards", () => {
  it("shows satisfied-of-applicable for each framework group", () => {
    mockSummary({
      iso_42001_clauses: { satisfied: 3, partial: 1, no_coverage: 2, not_applicable: 0 },
      iso_42001_annex_a: { satisfied: 0, partial: 0, no_coverage: 0, not_applicable: 38 },
      eu_ai_act: { satisfied: 0, partial: 0, no_coverage: 8, not_applicable: 0 },
    });

    render(<ComplianceSummaryCards />);

    // Clauses: 3 satisfied out of 6 applicable (3 + 1 + 2).
    expect(screen.getByText("3/6")).toBeInTheDocument();
    // EU AI Act: 0 satisfied out of 8 applicable.
    expect(screen.getByText("0/8")).toBeInTheDocument();
  });

  it("shows a dash when every Annex A control has been excluded", () => {
    mockSummary({
      iso_42001_clauses: { satisfied: 0, partial: 0, no_coverage: 24, not_applicable: 0 },
      iso_42001_annex_a: { satisfied: 0, partial: 0, no_coverage: 0, not_applicable: 38 },
      eu_ai_act: { satisfied: 0, partial: 0, no_coverage: 8, not_applicable: 0 },
    });

    render(<ComplianceSummaryCards />);

    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText("No applicable controls yet.")).toBeInTheDocument();
  });

  it("shows the three framework groups by label", () => {
    mockSummary({
      iso_42001_clauses: { satisfied: 0, partial: 0, no_coverage: 24, not_applicable: 0 },
      iso_42001_annex_a: { satisfied: 0, partial: 0, no_coverage: 38, not_applicable: 0 },
      eu_ai_act: { satisfied: 0, partial: 0, no_coverage: 8, not_applicable: 0 },
    });

    render(<ComplianceSummaryCards />);

    expect(screen.getByText("ISO 42001 Clauses")).toBeInTheDocument();
    expect(screen.getByText("ISO 42001 Annex A")).toBeInTheDocument();
    expect(screen.getByText("EU AI Act")).toBeInTheDocument();
  });
});
