import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { useUserDirectory, useUsers } from "../../users/hooks";
import { GovernanceRoleCard } from "../components/GovernanceRoleCard";
import {
  useAssignGovernanceRole,
  useCaigoDelegation,
  useDeleteGovernanceRole,
  useRevokeCaigoDelegation,
  useSetCaigoDelegation,
  useUnassignGovernanceRole,
  useUpdateGovernanceRole,
} from "../hooks";
import type { CaigoDelegation, GovernanceRole } from "../types";

vi.mock("../hooks");
vi.mock("../../users/hooks");

const caigoRole: GovernanceRole = {
  id: 1,
  name: "Chief AI Governance Officer",
  responsibilities: "Owns the AI governance program.",
  max_holders: 1,
  parent_role_id: null,
  holders: [{ id: 5, name: "Alex Admin" }],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function mockHooks({
  delegation = null as CaigoDelegation | null,
  admins = [{ id: 7, name: "Backup Bailey", email: "b@example.com", role: "admin", is_active: true, created_at: "" }],
  setDelegation = vi.fn(),
  revokeDelegation = vi.fn(),
} = {}) {
  vi.mocked(useUpdateGovernanceRole).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
  vi.mocked(useDeleteGovernanceRole).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
  vi.mocked(useAssignGovernanceRole).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
  vi.mocked(useUnassignGovernanceRole).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
  vi.mocked(useUserDirectory).mockReturnValue({ data: [] } as never);
  vi.mocked(useUsers).mockReturnValue({ data: admins } as never);
  vi.mocked(useCaigoDelegation).mockReturnValue({ data: delegation, isLoading: false } as never);
  vi.mocked(useSetCaigoDelegation).mockReturnValue({
    mutateAsync: setDelegation,
    isPending: false,
  } as never);
  vi.mocked(useRevokeCaigoDelegation).mockReturnValue({
    mutateAsync: revokeDelegation,
    isPending: false,
  } as never);
  return { setDelegation, revokeDelegation };
}

describe("GovernanceRoleCard CAIGO backup approver", () => {
  it("shows no active delegate when none is set", () => {
    mockHooks();

    render(<GovernanceRoleCard role={caigoRole} allRoles={[caigoRole]} canManage />);

    expect(screen.getByText("No backup approver is currently active.")).toBeInTheDocument();
  });

  it("shows the active delegate and lets an admin revoke it", async () => {
    const { revokeDelegation } = mockHooks({
      delegation: {
        id: 1,
        delegate_user_id: 7,
        delegate_name: "Backup Bailey",
        starts_at: "2026-01-01T00:00:00Z",
        ends_at: "2026-01-05T00:00:00Z",
      },
    });
    const user = userEvent.setup();

    render(<GovernanceRoleCard role={caigoRole} allRoles={[caigoRole]} canManage />);
    expect(screen.getByText(/Backup Bailey covers this role until/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Revoke" }));

    await waitFor(() => expect(revokeDelegation).toHaveBeenCalled());
  });

  it("lets an admin set a new backup approver", async () => {
    const { setDelegation } = mockHooks();
    const user = userEvent.setup();

    render(<GovernanceRoleCard role={caigoRole} allRoles={[caigoRole]} canManage />);
    await user.selectOptions(screen.getByLabelText("Backup approver"), "7");
    await user.type(screen.getByLabelText("Backup approver expires at"), "2026-06-01T12:00");
    await user.click(screen.getByRole("button", { name: "Set Backup Approver" }));

    await waitFor(() =>
      expect(setDelegation).toHaveBeenCalledWith(
        expect.objectContaining({ delegate_user_id: 7 }),
      ),
    );
  });

  it("hides the backup approver form for a non-manager", () => {
    mockHooks();

    render(<GovernanceRoleCard role={caigoRole} allRoles={[caigoRole]} canManage={false} />);

    expect(screen.getByText("Backup approver")).toBeInTheDocument();
    expect(screen.queryByLabelText("Backup approver")).not.toBeInTheDocument();
  });

  it("does not render the backup approver section for a non-CAIGO role", () => {
    mockHooks();
    const riskOwner: GovernanceRole = { ...caigoRole, id: 2, name: "Risk Owner", max_holders: null };

    render(<GovernanceRoleCard role={riskOwner} allRoles={[riskOwner]} canManage />);

    expect(screen.queryByText("Backup approver")).not.toBeInTheDocument();
  });
});

describe("GovernanceRoleCard responsibilities textarea", () => {
  it("picks up a remote edit to responsibilities instead of showing stale text", () => {
    mockHooks();
    const riskOwner: GovernanceRole = {
      id: 2,
      name: "Risk Owner",
      responsibilities: "Original text.",
      max_holders: null,
      parent_role_id: null,
      holders: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    const { rerender } = render(
      <GovernanceRoleCard role={riskOwner} allRoles={[riskOwner]} canManage />,
    );
    expect(screen.getByLabelText("Responsibilities for Risk Owner")).toHaveValue(
      "Original text.",
    );

    rerender(
      <GovernanceRoleCard
        role={{ ...riskOwner, responsibilities: "Updated by someone else." }}
        allRoles={[riskOwner]}
        canManage
      />,
    );

    expect(screen.getByLabelText("Responsibilities for Risk Owner")).toHaveValue(
      "Updated by someone else.",
    );
  });
});
