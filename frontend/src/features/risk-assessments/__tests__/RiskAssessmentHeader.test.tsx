import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { useCanApproveAsOwner } from "../../audit-log/useCanApproveAsOwner";
import { useFrameworkControls } from "../../framework-controls/hooks";
import { useFrameworkTags, useSetFrameworkTags } from "../../framework-tags/hooks";
import { RiskAssessmentHeader } from "../components/RiskAssessmentHeader";
import {
  useApproveRiskAssessmentCaigoStage,
  useApproveRiskAssessmentOwnerStage,
  useSubmitRiskAssessmentForOwnerApproval,
  useUpdateRiskAssessment,
} from "../hooks";
import type { RiskAssessment } from "../types";

vi.mock("../hooks");
vi.mock("../../framework-tags/hooks");
vi.mock("../../framework-controls/hooks");
vi.mock("../../audit-log/useCanApprove");
vi.mock("../../audit-log/useCanApproveAsOwner");

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
  owner_approved_by: null,
  owner_approved_at: null,
  caigo_approved_by: null,
  caigo_approved_at: null,
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

function mockApprovalHooks() {
  vi.mocked(useSubmitRiskAssessmentForOwnerApproval).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useApproveRiskAssessmentOwnerStage).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useApproveRiskAssessmentCaigoStage).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useCanApproveAsOwner).mockReturnValue({ canApprove: false, reason: null });
  vi.mocked(useCanApprove).mockReturnValue({ canApprove: false, reason: null });
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
    mockApprovalHooks();

    renderHeader();

    expect(screen.getByText("AI System: Resume Screener")).toBeInTheDocument();
    expect(screen.getByText("ISO 42001:8.4")).toBeInTheDocument();
    expect(screen.getByText("Overall Risk Rating: 12")).toBeInTheDocument();
  });

  it("shows 'Not yet scored' when overall_risk_rating is null", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);
    mockFrameworkTagHooks();
    mockApprovalHooks();

    renderHeader({ ...riskAssessment, overall_risk_rating: null });

    expect(screen.getByText("Overall Risk Rating: Not yet scored")).toBeInTheDocument();
  });

  it("changing the work status select triggers an update", async () => {
    const mutate = vi.fn();
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate } as never);
    mockFrameworkTagHooks();
    mockApprovalHooks();
    const user = userEvent.setup();

    renderHeader();
    await user.selectOptions(screen.getByLabelText("Work status"), "in_progress");

    expect(mutate).toHaveBeenCalledWith({ status: "in_progress" });
  });

  it("shows a Submit for Approval button while draft or in progress", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);
    mockFrameworkTagHooks();
    mockApprovalHooks();

    renderHeader();

    expect(screen.getByRole("button", { name: "Submit for Approval" })).toBeInTheDocument();
  });

  it("shows an Approve button for the owner during the owner-approval stage", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);
    mockFrameworkTagHooks();
    mockApprovalHooks();
    vi.mocked(useCanApproveAsOwner).mockReturnValue({ canApprove: true, reason: null });

    renderHeader({ ...riskAssessment, status: "pending_owner_approval" });

    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
  });

  it("shows the reason instead of a button when the owner can't approve", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);
    mockFrameworkTagHooks();
    mockApprovalHooks();
    vi.mocked(useCanApproveAsOwner).mockReturnValue({
      canApprove: false,
      reason: "Only this AI system's owner can approve this stage.",
    });

    renderHeader({ ...riskAssessment, status: "pending_owner_approval" });

    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(
      screen.getByText("Only this AI system's owner can approve this stage."),
    ).toBeInTheDocument();
  });

  it("shows an Approve button for CAIGO during the CAIGO-approval stage", () => {
    vi.mocked(useUpdateRiskAssessment).mockReturnValue({ mutate: vi.fn() } as never);
    mockFrameworkTagHooks();
    mockApprovalHooks();
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: true, reason: null });

    renderHeader({ ...riskAssessment, status: "pending_caigo_approval" });

    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
  });
});
