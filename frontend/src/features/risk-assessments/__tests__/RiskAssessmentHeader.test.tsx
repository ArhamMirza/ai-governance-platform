import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useFrameworkControls } from "../../framework-controls/hooks";
import { useFrameworkTags, useSetFrameworkTags } from "../../framework-tags/hooks";
import { RiskAssessmentHeader } from "../components/RiskAssessmentHeader";
import { useUpdateRiskAssessment } from "../hooks";
import type { RiskAssessment } from "../types";

vi.mock("../hooks");
vi.mock("../../framework-tags/hooks");
vi.mock("../../framework-controls/hooks");

const riskAssessment: RiskAssessment = {
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

function mockFrameworkTagHooks() {
  vi.mocked(useFrameworkTags).mockReturnValue({
    data: [{ id: 1, framework: "iso_42001", code: "8.4", title: "AI system impact assessment", description: null }],
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useFrameworkControls).mockReturnValue({
    data: [
      { id: 1, framework: "iso_42001", code: "8.4", title: "AI system impact assessment", description: null },
    ],
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useSetFrameworkTags).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
}

function renderHeader(assessment: RiskAssessment = riskAssessment) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <RiskAssessmentHeader riskAssessment={assessment} aiSystemName="Resume Screener" />
    </QueryClientProvider>,
  );
}

describe("RiskAssessmentHeader", () => {
  it("renders the linked AI system, framework tags, and overall rating", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);
    mockFrameworkTagHooks();

    renderHeader();

    expect(screen.getByText("AI System: Resume Screener")).toBeInTheDocument();
    expect(screen.getByText("ISO 42001:8.4")).toBeInTheDocument();
    expect(screen.getByText("Overall Risk Rating: 12")).toBeInTheDocument();
  });

  it("shows 'Not yet scored' when overall_risk_rating is null", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);
    mockFrameworkTagHooks();

    renderHeader({ ...riskAssessment, overall_risk_rating: null });

    expect(screen.getByText("Overall Risk Rating: Not yet scored")).toBeInTheDocument();
  });

  it("changing the status select triggers an update", async () => {
    const mutate = vi.fn();
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate } as never);
    mockFrameworkTagHooks();
    const user = userEvent.setup();

    renderHeader();
    await user.selectOptions(screen.getByLabelText("Status"), "completed");

    expect(mutate).toHaveBeenCalledWith({ status: "completed" });
  });
});
