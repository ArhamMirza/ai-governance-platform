import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { RiskAssessmentList } from "../components/RiskAssessmentList";
import { useAISystemInventoryRows, useRiskPortfolioSummary } from "../hooks";
import type { RiskAssessmentStats, RiskPortfolioSummary } from "../types";

vi.mock("../hooks");

const criteria = {
  medium_min_score: 5,
  high_min_score: 13,
  is_default: true,
  min_score: 1,
  max_score: 25,
  updated_at: null,
};

const stats: RiskAssessmentStats = {
  id: 1,
  ai_system_row_id: 5,
  status: "draft",
  overall_risk_rating: 12,
  item_count: 3,
  high_count: 0,
  medium_count: 2,
  low_count: 1,
  overdue_count: 0,
};

function makeSummary(assessments: RiskAssessmentStats[]): RiskPortfolioSummary {
  return {
    total_assessments: assessments.length,
    by_status: {},
    high_risk_count: 0,
    risk_items: {
      total: 0,
      by_severity: { high: 0, medium: 0, low: 0 },
      overdue_count: 0,
      untreated_count: 0,
      average_inherent_score: null,
      average_residual_score: null,
    },
    matrix: [],
    assessments,
    criteria,
  };
}

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

function mockHooks(summary: RiskPortfolioSummary, inventory: unknown = mockInventory) {
  vi.mocked(useRiskPortfolioSummary).mockReturnValue({
    data: summary,
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: inventory } as never);
}

function renderList() {
  return render(
    <MemoryRouter>
      <RiskAssessmentList />
    </MemoryRouter>,
  );
}

describe("RiskAssessmentList", () => {
  it("resolves and renders the linked AI system's name", async () => {
    mockHooks(makeSummary([stats]));

    renderList();

    await waitFor(() => {
      expect(screen.getByText("Resume Screener")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
    });
  });

  it("falls back to a placeholder name when the AI system row can't be resolved", async () => {
    mockHooks(makeSummary([stats]), { ...mockInventory, rows: [] });

    renderList();

    await waitFor(() => {
      expect(screen.getByText("AI System #5")).toBeInTheDocument();
    });
  });

  it("shows the item count and highlights high-risk items", async () => {
    mockHooks(makeSummary([{ ...stats, item_count: 4, high_count: 2 }]));

    renderList();

    await waitFor(() => {
      expect(screen.getByText("4")).toBeInTheDocument();
      expect(screen.getByText("2 high")).toBeInTheDocument();
    });
  });

  it("flags rows that have overdue treatments", async () => {
    // item_count stays 3, so use a distinct overdue count to keep the query unambiguous.
    mockHooks(makeSummary([{ ...stats, overdue_count: 7 }]));

    const { container } = renderList();

    await waitFor(() => {
      expect(screen.getByText("7")).toBeInTheDocument();
    });
    expect(container.querySelector("tr.row-flagged")).not.toBeNull();
  });

  it("scores the rating pill against the configured criteria", async () => {
    const summary = makeSummary([stats]);
    // A rating of 12 is medium by default, but high once the band drops to 9.
    summary.criteria = { ...criteria, high_min_score: 9, is_default: false };
    mockHooks(summary);

    const { container } = renderList();

    await waitFor(() => {
      expect(container.querySelector('[data-severity="high"]')).not.toBeNull();
    });
  });

  it("shows an empty state when there are no risk assessments", async () => {
    mockHooks(makeSummary([]));

    renderList();

    await waitFor(() => {
      expect(screen.getByText("No risk assessments yet.")).toBeInTheDocument();
    });
  });
});
