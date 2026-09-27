import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { useCanApproveAsOwner } from "../../audit-log/useCanApproveAsOwner";
import { useUserDirectory } from "../../users/hooks";
import { ImpactAssessmentForm } from "../components/ImpactAssessmentForm";
import {
  useApproveImpactAssessmentCaigoStage,
  useApproveImpactAssessmentOwnerStage,
  useDeleteImpactAssessment,
  useSubmitImpactAssessmentForOwnerApproval,
  useUpdateImpactAssessment,
} from "../hooks";
import type { ImpactAssessment } from "../types";

// Drafting has its own tests; here it only needs to render as it does with
// no provider configured -- which is nothing.
vi.mock("../../ai-assist/components/DraftWithAiButton", () => ({
  DraftWithAiButton: () => null,
}));
vi.mock("../components/AssessmentDraftPanel", () => ({
  AssessmentDraftPanel: () => null,
}));
vi.mock("../hooks");
vi.mock("../../users/hooks");
vi.mock("../../audit-log/useCanApprove");
vi.mock("../../audit-log/useCanApproveAsOwner");
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: () => <div>Framework tags</div>,
}));
vi.mock("../../evidence/components/DocumentBrowser", () => ({
  DocumentBrowser: () => <div>Documents</div>,
}));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({
  AuditLogViewer: () => <div>Audit log</div>,
}));
vi.mock("./ImpactFactorCard", () => ({
  ImpactFactorCard: () => <div>Factor</div>,
}));

function makeAssessment(overrides: Partial<ImpactAssessment> = {}): ImpactAssessment {
  return {
    id: 1,
    ai_system_row_id: 7,
    status: "draft",
    assessor_id: null,
    assessment_date: null,
    next_review_date: null,
    review_overdue: false,
    system_description: null,
    intended_purpose: null,
    foreseeable_misuse: null,
    data_and_model_info: null,
    deployment_environment: null,
    affected_interested_parties: null,
    human_oversight_role: null,
    conclusion: null,
    owner_approved_by: null,
    owner_approved_at: null,
    caigo_approved_by: null,
    caigo_approved_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    framework_tags: [],
    factors: [],
    ...overrides,
  };
}

function mockHooks() {
  vi.mocked(useUpdateImpactAssessment).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useDeleteImpactAssessment).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useSubmitImpactAssessmentForOwnerApproval).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useApproveImpactAssessmentOwnerStage).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useApproveImpactAssessmentCaigoStage).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useUserDirectory).mockReturnValue({ data: [] } as never);
  vi.mocked(useCanApproveAsOwner).mockReturnValue({ canApprove: false, reason: null });
  vi.mocked(useCanApprove).mockReturnValue({ canApprove: false, reason: null });
}

describe("ImpactAssessmentForm approval workflow", () => {
  it("shows Submit for Approval while draft", () => {
    mockHooks();

    render(
      <ImpactAssessmentForm
        riskAssessmentId={null}
        assessment={makeAssessment({ status: "draft" })}
        onDeleted={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Submit for Approval" })).toBeInTheDocument();
  });

  it("shows the server's reason when a submission is refused", async () => {
    mockHooks();
    const message =
      "Can't submit: Conclusion is empty and 3 factors are unscored (Fairness, Privacy, Safety).";
    vi.mocked(useSubmitImpactAssessmentForOwnerApproval).mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(new ApiError(400, JSON.stringify({ detail: message }))),
      isPending: false,
    } as never);

    render(
      <ImpactAssessmentForm
        riskAssessmentId={null}
        assessment={makeAssessment({ status: "draft" })}
        onDeleted={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Submit for Approval" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: "Submit for Approval" })).toBeInTheDocument();
  });

  it("shows the server's reason when an approval is refused", async () => {
    mockHooks();
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: true, reason: null });
    const message = "Can't approve: 1 factor has no harms written (Safety).";
    vi.mocked(useApproveImpactAssessmentCaigoStage).mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(new ApiError(400, JSON.stringify({ detail: message }))),
      isPending: false,
    } as never);

    render(
      <ImpactAssessmentForm
        riskAssessmentId={null}
        assessment={makeAssessment({ status: "pending_caigo_approval" })}
        onDeleted={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("shows an Approve button for the owner during the owner-approval stage", () => {
    mockHooks();
    vi.mocked(useCanApproveAsOwner).mockReturnValue({ canApprove: true, reason: null });

    render(
      <ImpactAssessmentForm
        riskAssessmentId={null}
        assessment={makeAssessment({ status: "pending_owner_approval" })}
        onDeleted={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
  });

  it("shows the reason instead of a button when the owner can't approve", () => {
    mockHooks();
    vi.mocked(useCanApproveAsOwner).mockReturnValue({
      canApprove: false,
      reason: "Only this AI system's owner can approve this stage.",
    });

    render(
      <ImpactAssessmentForm
        riskAssessmentId={null}
        assessment={makeAssessment({ status: "pending_owner_approval" })}
        onDeleted={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(
      screen.getByText("Only this AI system's owner can approve this stage."),
    ).toBeInTheDocument();
  });

  it("shows an Approve button for CAIGO during the CAIGO-approval stage", () => {
    mockHooks();
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: true, reason: null });

    render(
      <ImpactAssessmentForm
        riskAssessmentId={null}
        assessment={makeAssessment({ status: "pending_caigo_approval" })}
        onDeleted={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
  });

  it("shows no approval action once completed", () => {
    mockHooks();

    render(
      <ImpactAssessmentForm
        riskAssessmentId={null}
        assessment={makeAssessment({ status: "completed" })}
        onDeleted={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit for Approval" }),
    ).not.toBeInTheDocument();
  });
});
