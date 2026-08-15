import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { RiskAssessmentList } from "../components/RiskAssessmentList";
import { useAISystemInventoryRows, useRiskAssessments } from "../hooks";
import type { RiskAssessment } from "../types";

vi.mock("../hooks");

const mockRiskAssessment: RiskAssessment = {
  id: 1,
  ai_system_row_id: 5,
  sheet_id: 2,
  framework_tags: [],
  status: "draft",
  assessor_id: null,
  assessment_date: null,
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

function renderList() {
  return render(
    <MemoryRouter>
      <RiskAssessmentList />
    </MemoryRouter>,
  );
}

describe("RiskAssessmentList", () => {
  it("resolves and renders the linked AI system's name", async () => {
    vi.mocked(useRiskAssessments).mockReturnValue({
      data: [mockRiskAssessment],
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: mockInventory } as never);

    renderList();

    await waitFor(() => {
      expect(screen.getByText("Resume Screener")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
    });
  });

  it("falls back to a placeholder name when the AI system row can't be resolved", async () => {
    vi.mocked(useRiskAssessments).mockReturnValue({
      data: [mockRiskAssessment],
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useAISystemInventoryRows).mockReturnValue({
      data: { ...mockInventory, rows: [] },
    } as never);

    renderList();

    await waitFor(() => {
      expect(screen.getByText("AI System #5")).toBeInTheDocument();
    });
  });

  it("shows an empty state when there are no risk assessments", async () => {
    vi.mocked(useRiskAssessments).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: mockInventory } as never);

    renderList();

    await waitFor(() => {
      expect(screen.getByText("No risk assessments yet.")).toBeInTheDocument();
    });
  });
});
