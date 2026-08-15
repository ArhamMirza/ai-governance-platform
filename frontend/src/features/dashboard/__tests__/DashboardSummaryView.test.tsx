import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { dashboardApi } from "../api";
import { DashboardSummaryView } from "../components/DashboardSummaryView";
import type { DashboardSummary } from "../types";

vi.mock("../api");

const summary: DashboardSummary = {
  policies: { total: 3, by_status: { draft: 2, approved: 1 } },
  procedures: { total: 1, by_status: { in_review: 1 } },
  ai_systems: { total: 2, by_risk_tier: { high: 1, unspecified: 1 } },
  risk_assessments: { total: 2, by_status: { draft: 1, completed: 1 }, high_risk_count: 1 },
};

function renderView() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardSummaryView />
    </QueryClientProvider>,
  );
}

describe("DashboardSummaryView", () => {
  it("renders totals and status breakdowns for every entity", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(summary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Total: 3")).toBeInTheDocument();
      expect(screen.getByText("draft: 2")).toBeInTheDocument();
      expect(screen.getByText("approved: 1")).toBeInTheDocument();
    });

    expect(screen.getByText("High Risk: 1")).toBeInTheDocument();
    expect(screen.getByText("high: 1")).toBeInTheDocument();
  });

  it("shows a placeholder when a breakdown has no entries", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue({
      policies: { total: 0, by_status: {} },
      procedures: { total: 0, by_status: {} },
      ai_systems: { total: 0, by_risk_tier: {} },
      risk_assessments: { total: 0, by_status: {}, high_risk_count: 0 },
    });

    renderView();

    await waitFor(() => {
      expect(screen.getAllByText("None yet.").length).toBeGreaterThan(0);
    });
  });

  it("shows an error state when the request fails", async () => {
    vi.mocked(dashboardApi.getSummary).mockRejectedValue(new Error("network error"));

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Failed to load dashboard.")).toBeInTheDocument();
    });
  });
});
