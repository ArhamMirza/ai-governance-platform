import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { dashboardApi } from "../api";
import { DashboardSummaryView } from "../components/DashboardSummaryView";
import type { DashboardSummary } from "../types";

vi.mock("../api");

const criteria = {
  medium_min_score: 5,
  high_min_score: 13,
  is_default: true,
  min_score: 1,
  max_score: 25,
  updated_at: null,
};

const summary: DashboardSummary = {
  policies: { total: 3, by_status: { draft: 2, approved: 1 } },
  procedures: { total: 1, by_status: { in_review: 1 } },
  ai_systems: { total: 2, by_risk_tier: { high: 1, unspecified: 1 } },
  risk_assessments: { total: 2, by_status: { draft: 1, completed: 1 }, high_risk_count: 1 },
  risk_items: {
    total: 6,
    by_severity: { high: 2, medium: 3, low: 1 },
    overdue_count: 2,
    untreated_count: 4,
    average_inherent_score: 12,
    average_residual_score: 6,
  },
  coverage: {
    ai_systems_total: 2,
    ai_systems_assessed: 1,
    ai_systems_impact_assessed: 2,
    assessments_review_overdue: 0,
    policies_total: 3,
    policies_approved: 1,
    procedures_total: 1,
    procedures_approved: 0,
  },
  attention: [
    { key: "overdue_treatments", label: "Risk treatments overdue", count: 2, severity: "danger" },
  ],
  matrix: [{ likelihood: 4, impact: 4, count: 2 }],
  criteria,
  my_risk_items: [
    {
      risk_assessment_id: 7,
      row_id: 42,
      category: "Bias",
      description: "Model may rank candidates unevenly.",
      status: "open",
      treatment_deadline: "2026-01-01",
      overdue: true,
    },
  ],
  pending_approvals: [
    {
      entity_type: "Policy",
      entity_id: 3,
      title: "Vendor Policy",
      stage_label: "Awaiting your approval as Chief AI Governance Officer",
      submitted_at: "2026-01-01T00:00:00Z",
    },
  ],
};

const emptySummary: DashboardSummary = {
  policies: { total: 0, by_status: {} },
  procedures: { total: 0, by_status: {} },
  ai_systems: { total: 0, by_risk_tier: {} },
  risk_assessments: { total: 0, by_status: {}, high_risk_count: 0 },
  risk_items: {
    total: 0,
    by_severity: { high: 0, medium: 0, low: 0 },
    overdue_count: 0,
    untreated_count: 0,
    average_inherent_score: null,
    average_residual_score: null,
  },
  coverage: {
    ai_systems_total: 0,
    ai_systems_assessed: 0,
    ai_systems_impact_assessed: 0,
    assessments_review_overdue: 0,
    policies_total: 0,
    policies_approved: 0,
    procedures_total: 0,
    procedures_approved: 0,
  },
  attention: [],
  matrix: [],
  criteria,
  my_risk_items: [],
  pending_approvals: [],
};

function renderView() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DashboardSummaryView />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DashboardSummaryView", () => {
  it("renders risk item severity counts", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(summary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Risk items")).toBeInTheDocument();
    });

    const severityLegend = screen.getByLabelText("High: 2, Medium: 3, Low: 1");
    expect(severityLegend).toBeInTheDocument();
  });

  it("surfaces overdue treatments in the attention panel", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(summary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Needs Attention")).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: "Risk treatments overdue" })).toBeInTheDocument();
  });

  it("surfaces accountability coverage gaps in the attention panel", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue({
      ...summary,
      attention: [
        ...summary.attention,
        {
          key: "vacant_governance_roles",
          label: "Governance roles with no one assigned",
          count: 2,
          severity: "warning",
        },
        {
          key: "ai_systems_without_owner",
          label: "AI systems without an owner",
          count: 1,
          severity: "warning",
        },
      ],
    });

    renderView();

    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: "Governance roles with no one assigned" }),
      ).toHaveAttribute("href", "/governance");
    });
    expect(
      screen.getByRole("link", { name: "AI systems without an owner" }),
    ).toHaveAttribute("href", "/ai-systems");
  });

  it("reports the risk reduction achieved by mitigation", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(summary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText(/50% lower after mitigation/)).toBeInTheDocument();
    });
  });

  it("labels the high-risk threshold using the configured criteria", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue({
      ...summary,
      criteria: { ...criteria, high_min_score: 9, is_default: false },
    });

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Rated 9 or above")).toBeInTheDocument();
    });
  });

  it("shows coverage ratios", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(summary);

    renderView();

    await waitFor(() => {
      expect(screen.getByLabelText("Risk assessed: 1 of 2 (50%)")).toBeInTheDocument();
      expect(screen.getByLabelText("Impact assessed: 2 of 2 (100%)")).toBeInTheDocument();
    });
  });

  it("shows my open risk items, linking to their assessment", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(summary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText("My Risk Items")).toBeInTheDocument();
    });
    const link = screen.getByRole("link", { name: "Bias" });
    expect(link).toHaveAttribute("href", "/risk-assessments/7");
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("shows pending approvals, linking to the right record", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(summary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Pending My Approval")).toBeInTheDocument();
    });
    const link = screen.getByRole("link", { name: "Vendor Policy" });
    expect(link).toHaveAttribute("href", "/policies/3");
    expect(
      screen.getByText("Awaiting your approval as Chief AI Governance Officer"),
    ).toBeInTheDocument();
  });

  it("hides the Pending My Approval panel when there is nothing pending", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(emptySummary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Nothing needs attention")).toBeInTheDocument();
    });
    expect(screen.queryByText("Pending My Approval")).not.toBeInTheDocument();
  });

  it("hides the My Risk Items panel when there are none", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(emptySummary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Nothing needs attention")).toBeInTheDocument();
    });
    expect(screen.queryByText("My Risk Items")).not.toBeInTheDocument();
  });

  it("shows an all-clear state when nothing needs attention", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(emptySummary);

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Nothing needs attention")).toBeInTheDocument();
    });
  });

  it("shows a placeholder when a breakdown has no entries", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValue(emptySummary);

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
