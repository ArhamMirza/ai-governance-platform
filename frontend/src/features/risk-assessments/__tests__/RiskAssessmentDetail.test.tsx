import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { auditLogApi } from "../../audit-log/api";
import { createTestQueryClient } from "../../../test/testQueryClient";
import type { SheetWithRows } from "../../sheets/types";
import { makeRiskAssessmentSheetAdapter } from "../api";
import { RiskAssessmentDetail } from "../components/RiskAssessmentDetail";
import { useAISystemInventoryRows, useRiskAssessment } from "../hooks";
import type { RiskAssessment } from "../types";

vi.mock("../hooks", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../hooks")>();
  return { ...actual, useRiskAssessment: vi.fn(), useAISystemInventoryRows: vi.fn() };
});
vi.mock("../api");
vi.mock("../../audit-log/api");

const riskAssessment: RiskAssessment = {
  id: 1,
  ai_system_row_id: 5,
  sheet_id: 2,
  framework_tags: [],
  status: "draft",
  assessor_id: null,
  assessment_date: null,
  next_review_date: null,
  review_overdue: false,
  overall_risk_rating: 12,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockInventory = {
  id: 1,
  entity_type: "AISystemInventory",
  title: "AI System Inventory",
  columns: [],
  rows: [
    {
      id: 5,
      sheet_id: 1,
      row_index: 1,
      data: { name: "Resume Screener" },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const riskSheet: SheetWithRows = {
  id: 2,
  entity_type: "RiskAssessment",
  title: "Risk Items",
  columns: [
    { key: "category", label: "Category", data_type: "text" },
    { key: "likelihood", label: "Likelihood", data_type: "number" },
    { key: "impact", label: "Impact", data_type: "number" },
    { key: "inherent_risk_score", label: "Inherent Risk Score", data_type: "number" },
  ],
  rows: [
    {
      id: 10,
      sheet_id: 2,
      row_index: 1,
      data: { category: "Bias", likelihood: 3, impact: 4, inherent_risk_score: 12 },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("RiskAssessmentDetail", () => {
  it("renders the header, the risk items grid, and the risk matrix", async () => {
    vi.mocked(useRiskAssessment).mockReturnValue({
      data: riskAssessment,
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: mockInventory } as never);
    vi.mocked(makeRiskAssessmentSheetAdapter).mockReturnValue({
      get: vi.fn().mockResolvedValue(riskSheet),
      setColumns: vi.fn(),
      addRow: vi.fn(),
      updateRow: vi.fn(),
      deleteRow: vi.fn(),
      upload: vi.fn(),
      exportUrl: vi.fn().mockReturnValue("http://localhost:8000/api/v1/risk-assessments/1/export"),
    });
    vi.mocked(auditLogApi.list).mockResolvedValue([]);
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <RiskAssessmentDetail riskAssessmentId={1} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("AI System: Resume Screener")).toBeInTheDocument();
      expect(screen.getByLabelText("Category for row 10")).toHaveValue("Bias");
      expect(
        screen.getByLabelText("Likelihood 3, Impact 4, 1 risk(s)"),
      ).toHaveTextContent("1");
    });

    // Computed column renders read-only (span, not input)
    expect(screen.queryByLabelText("Remove Inherent Risk Score")).not.toBeInTheDocument();
  });
});
