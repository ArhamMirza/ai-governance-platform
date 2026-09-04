import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { StageGateChecklist } from "../components/StageGateChecklist";
import { useAdvanceStage, useRevertStage, useUploadStageDocument } from "../hooks";
import type { AISystemLifecycle } from "../types";

vi.mock("../hooks");

function makeLifecycle(overrides: Partial<AISystemLifecycle> = {}): AISystemLifecycle {
  return {
    ai_system_row_id: 1,
    current_stage: "inception",
    current_stage_label: "Inception",
    next_stage: "design",
    next_stage_label: "Design",
    entered_stage_at: "2026-01-01T00:00:00Z",
    deployment_environment: null,
    deployment_version: null,
    deployed_at: null,
    deployment_approved_by: null,
    deployment_approved_at: null,
    monitoring_owner_id: null,
    incident_escalation_path: null,
    requirements: [
      {
        key: "impact_assessment_completed",
        label: "Impact assessment completed",
        satisfied: false,
        detail: "Perform the impact assessment and mark it completed.",
      },
    ],
    can_advance: false,
    ...overrides,
  };
}

function mockHooks({ advance = vi.fn(), revert = vi.fn(), upload = vi.fn() } = {}) {
  vi.mocked(useAdvanceStage).mockReturnValue({
    mutateAsync: advance,
    isPending: false,
  } as never);
  vi.mocked(useRevertStage).mockReturnValue({
    mutateAsync: revert,
    isPending: false,
  } as never);
  vi.mocked(useUploadStageDocument).mockReturnValue({
    mutate: upload,
    isPending: false,
  } as never);
  return { advance, revert, upload };
}

describe("StageGateChecklist", () => {
  it("names the stage being left and lists its requirements", () => {
    mockHooks();

    render(<StageGateChecklist rowId={1} lifecycle={makeLifecycle()} />);

    expect(screen.getByText("To leave Inception")).toBeInTheDocument();
    expect(screen.getByText("Impact assessment completed")).toBeInTheDocument();
    expect(
      screen.getByText("Perform the impact assessment and mark it completed."),
    ).toBeInTheDocument();
  });

  it("disables Advance while a requirement is unmet", () => {
    mockHooks();

    render(<StageGateChecklist rowId={1} lifecycle={makeLifecycle()} />);

    expect(screen.getByRole("button", { name: "Advance to Design" })).toBeDisabled();
  });

  it("enables Advance once the gate passes", async () => {
    const { advance } = mockHooks();
    const user = userEvent.setup();
    const lifecycle = makeLifecycle({
      can_advance: true,
      requirements: [
        {
          key: "impact_assessment_completed",
          label: "Impact assessment completed",
          satisfied: true,
          detail: "Completed.",
        },
      ],
    });

    render(<StageGateChecklist rowId={1} lifecycle={lifecycle} />);
    const button = screen.getByRole("button", { name: "Advance to Design" });
    expect(button).toBeEnabled();
    await user.click(button);

    await waitFor(() => expect(advance).toHaveBeenCalled());
  });

  it("offers an upload for a document requirement, and not for other kinds", () => {
    mockHooks();
    const lifecycle = makeLifecycle({
      current_stage: "design",
      current_stage_label: "Design",
      requirements: [
        {
          key: "design_document",
          label: "Design document uploaded",
          satisfied: false,
          detail: "Upload a design document for this AI system.",
        },
      ],
    });

    render(<StageGateChecklist rowId={1} lifecycle={lifecycle} />);

    expect(screen.getByLabelText("Upload design document")).toBeInTheDocument();
    // The inception requirement is not document-backed, so no uploader there.
    expect(screen.queryByLabelText(/Upload impact/)).not.toBeInTheDocument();
  });

  it("requires a reason before moving a stage back", async () => {
    const { revert } = mockHooks();
    const user = userEvent.setup();

    render(<StageGateChecklist rowId={1} lifecycle={makeLifecycle()} />);
    await user.click(screen.getByRole("button", { name: "Move back a stage" }));

    const confirm = screen.getByRole("button", { name: "Confirm move back" });
    expect(confirm).toBeDisabled();

    await user.type(screen.getByLabelText("Why is this system moving back?"), "Scope changed");
    await user.click(screen.getByRole("button", { name: "Confirm move back" }));

    await waitFor(() => expect(revert).toHaveBeenCalledWith("Scope changed"));
  });

  it("shows no Advance button at the final stage", () => {
    mockHooks();
    const lifecycle = makeLifecycle({
      current_stage: "retirement",
      current_stage_label: "Retirement",
      next_stage: null,
      next_stage_label: null,
      requirements: [],
    });

    render(<StageGateChecklist rowId={1} lifecycle={lifecycle} />);

    expect(screen.getByText("Retirement — final stage")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Advance/ })).not.toBeInTheDocument();
  });
});
