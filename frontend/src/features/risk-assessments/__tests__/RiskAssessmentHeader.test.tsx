import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RiskAssessmentHeader } from "../components/RiskAssessmentHeader";
import { useUpdateRiskAssessment } from "../hooks";
import type { RiskAssessment } from "../types";

vi.mock("../hooks");

const riskAssessment: RiskAssessment = {
  id: 1,
  ai_system_row_id: 5,
  sheet_id: 2,
  framework_tags: ["ISO42001:8.4"],
  status: "draft",
  assessor_id: null,
  assessment_date: null,
  overall_risk_rating: 12,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("RiskAssessmentHeader", () => {
  it("renders the linked AI system, framework tags, and overall rating", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);

    render(<RiskAssessmentHeader riskAssessment={riskAssessment} aiSystemName="Resume Screener" />);

    expect(screen.getByText("AI System: Resume Screener")).toBeInTheDocument();
    expect(screen.getByText("Framework Tags: ISO42001:8.4")).toBeInTheDocument();
    expect(screen.getByText("Overall Risk Rating: 12")).toBeInTheDocument();
  });

  it("shows 'Not yet scored' when overall_risk_rating is null", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);

    render(
      <RiskAssessmentHeader
        riskAssessment={{ ...riskAssessment, overall_risk_rating: null }}
        aiSystemName="Resume Screener"
      />,
    );

    expect(screen.getByText("Overall Risk Rating: Not yet scored")).toBeInTheDocument();
  });

  it("changing the status select triggers an update", async () => {
    const mutate = vi.fn();
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate } as never);
    const user = userEvent.setup();

    render(<RiskAssessmentHeader riskAssessment={riskAssessment} aiSystemName="Resume Screener" />);
    await user.selectOptions(screen.getByLabelText("Status"), "completed");

    expect(mutate).toHaveBeenCalledWith({ status: "completed" });
  });
});
