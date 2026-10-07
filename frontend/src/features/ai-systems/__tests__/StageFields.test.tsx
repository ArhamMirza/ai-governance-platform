import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { useCanApprove } from "../../audit-log/useCanApprove";
import { useUserDirectory } from "../../users/hooks";
import { DeploymentRecordFields, OwnerField, RetirementFields } from "../components/StageFields";
import {
  useApproveDeployment,
  useApproveRetirement,
  useRequestDeploymentApproval,
  useRequestRetirementApproval,
  useSetDeploymentRecord,
  useSetOwner,
  useSetRetirement,
} from "../hooks";
import type { AISystemLifecycle } from "../types";

vi.mock("../hooks");
vi.mock("../../users/hooks");
vi.mock("../../audit-log/useCanApprove");

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
    requirements: [],
    can_advance: false,
    can_archive: false,
    ...overrides,
  };
}

describe("OwnerField", () => {
  it("labels a directory user with their governance role and saves the chosen owner", async () => {
    const save = vi.fn();
    vi.mocked(useSetOwner).mockReturnValue({ mutate: save, isPending: false } as never);
    vi.mocked(useUserDirectory).mockReturnValue({
      data: [{ id: 7, name: "Arham Mirza", governance_roles: ["AI System Owner"] }],
    } as never);
    const user = userEvent.setup();

    render(<OwnerField rowId={1} lifecycle={makeLifecycle()} />);

    expect(
      screen.getByRole("option", { name: "Arham Mirza (AI System Owner)" }),
    ).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("AI System Owner"), "7");

    await waitFor(() => expect(save).toHaveBeenCalledWith({ owner_id: 7 }));
  });

  it("shows the currently assigned owner as selected", () => {
    vi.mocked(useSetOwner).mockReturnValue({ mutate: vi.fn(), isPending: false } as never);
    vi.mocked(useUserDirectory).mockReturnValue({
      data: [{ id: 7, name: "Arham Mirza", governance_roles: [] }],
    } as never);

    render(<OwnerField rowId={1} lifecycle={makeLifecycle({ owner_id: 7 })} />);

    expect(screen.getByLabelText("AI System Owner")).toHaveValue("7");
  });
});

describe("DeploymentRecordFields approval gating", () => {
  function mockDeploymentHooks() {
    vi.mocked(useSetDeploymentRecord).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useRequestDeploymentApproval).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useApproveDeployment).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
  }

  it("shows the approve button when the current user can approve", () => {
    mockDeploymentHooks();
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: true, reason: null });

    render(<DeploymentRecordFields rowId={1} lifecycle={makeLifecycle()} />);

    expect(screen.getByRole("button", { name: "Approve release" })).toBeInTheDocument();
  });

  it("hides the approve button and shows the reason when the user can't approve", () => {
    mockDeploymentHooks();
    vi.mocked(useCanApprove).mockReturnValue({
      canApprove: false,
      reason: "Only the Chief AI Governance Officer can approve.",
    });

    render(<DeploymentRecordFields rowId={1} lifecycle={makeLifecycle()} />);

    expect(screen.queryByRole("button", { name: "Approve release" })).not.toBeInTheDocument();
    expect(
      screen.getByText("Only the Chief AI Governance Officer can approve."),
    ).toBeInTheDocument();
  });
});

describe("RetirementFields approval gating", () => {
  function mockRetirementHooks() {
    vi.mocked(useSetRetirement).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useRequestRetirementApproval).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useApproveRetirement).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
  }

  it("shows the approve button when the current user can approve", () => {
    mockRetirementHooks();
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: true, reason: null });

    render(<RetirementFields rowId={1} lifecycle={makeLifecycle()} />);

    expect(screen.getByRole("button", { name: "Approve retirement" })).toBeInTheDocument();
  });

  it("hides the approve button and shows the reason when the user can't approve", () => {
    mockRetirementHooks();
    vi.mocked(useCanApprove).mockReturnValue({
      canApprove: false,
      reason: "Only the Chief AI Governance Officer can approve.",
    });

    render(<RetirementFields rowId={1} lifecycle={makeLifecycle()} />);

    expect(screen.queryByRole("button", { name: "Approve retirement" })).not.toBeInTheDocument();
    expect(
      screen.getByText("Only the Chief AI Governance Officer can approve."),
    ).toBeInTheDocument();
  });
});
