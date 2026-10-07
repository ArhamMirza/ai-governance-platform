import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { StageGateChecklist } from "../components/StageGateChecklist";
import {
  useAdvanceStage,
  useArchiveSystem,
  useRevertStage,
  useUploadStageDocument,
} from "../hooks";
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
    owner_id: null,
    ai_roles: null,
    effective_ai_roles: [],
    deployment_environment: null,
    deployment_version: null,
    deployed_at: null,
    deployment_approved_by: null,
    deployment_approved_at: null,
    monitoring_owner_id: null,
    incident_escalation_path: null,
    retirement_reason: null,
    retirement_approved_by: null,
    retirement_approved_at: null,
    retired_at: null,
    retention_until: null,
    archived_at: null,
    is_archived: false,
    retention_expired: false,
    requirements: [
      {
        key: "impact_assessment_completed",
        label: "Impact assessment completed",
        satisfied: false,
        detail: "Perform the impact assessment and mark it completed.",
      },
    ],
    can_advance: false,
    can_archive: false,
    ...overrides,
  };
}

function mockHooks({
  advance = vi.fn(),
  revert = vi.fn(),
  upload = vi.fn(),
  archive = vi.fn(),
} = {}) {
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
  vi.mocked(useArchiveSystem).mockReturnValue({
    mutateAsync: archive,
    isPending: false,
  } as never);
  return { advance, revert, upload, archive };
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

  it("offers Archive instead of Advance at the final stage", () => {
    mockHooks();
    const lifecycle = makeLifecycle({
      current_stage: "retirement",
      current_stage_label: "Retirement",
      next_stage: null,
      next_stage_label: null,
      requirements: [
        {
          key: "retention_until",
          label: "Retention period set",
          satisfied: false,
          detail: "Set how long this system's record must be kept.",
        },
      ],
    });

    render(<StageGateChecklist rowId={1} lifecycle={lifecycle} />);

    expect(screen.getByText("To archive this system")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Advance/ })).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Complete retirement & archive" }),
    ).toBeDisabled();
  });

  it("archives once the retirement requirements pass", async () => {
    const { archive } = mockHooks();
    const user = userEvent.setup();
    const lifecycle = makeLifecycle({
      current_stage: "retirement",
      next_stage: null,
      next_stage_label: null,
      can_archive: true,
      requirements: [
        {
          key: "retention_until",
          label: "Retention period set",
          satisfied: true,
          detail: "Kept until 2030-01-01.",
        },
      ],
    });

    render(<StageGateChecklist rowId={1} lifecycle={lifecycle} />);
    await user.click(screen.getByRole("button", { name: "Complete retirement & archive" }));

    await waitFor(() => expect(archive).toHaveBeenCalled());
  });

  it("shows a read-only archived notice with the retention date", () => {
    mockHooks();
    const lifecycle = makeLifecycle({
      current_stage: "retirement",
      next_stage: null,
      next_stage_label: null,
      is_archived: true,
      archived_at: "2026-01-01T00:00:00Z",
      retired_at: "2026-01-01",
      retention_until: "2031-01-01",
      requirements: [],
    });

    render(<StageGateChecklist rowId={1} lifecycle={lifecycle} />);

    expect(screen.getByText("Archived")).toBeInTheDocument();
    expect(screen.getByText(/2031-01-01/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
