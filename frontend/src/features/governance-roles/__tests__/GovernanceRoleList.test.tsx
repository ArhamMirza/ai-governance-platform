import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { useUserDirectory } from "../../users/hooks";
import { GovernanceRoleList } from "../components/GovernanceRoleList";
import {
  useAssignGovernanceRole,
  useCreateGovernanceRole,
  useDeleteGovernanceRole,
  useGovernanceRoles,
  useUnassignGovernanceRole,
  useUpdateGovernanceRole,
} from "../hooks";
import type { GovernanceRole } from "../types";

vi.mock("../hooks");
vi.mock("../../users/hooks");

function makeRole(overrides: Partial<GovernanceRole> = {}): GovernanceRole {
  return {
    id: 1,
    name: "Risk Owner",
    responsibilities: "Responsible for specific risk treatment and monitoring.",
    max_holders: null,
    parent_role_id: null,
    holders: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function mockHooks({
  roles = [makeRole()],
  create = vi.fn(),
  update = vi.fn(),
  remove = vi.fn(),
  assign = vi.fn(),
  unassign = vi.fn(),
  directory = [{ id: 9, name: "Priya Shah", governance_roles: [] }],
} = {}) {
  vi.mocked(useGovernanceRoles).mockReturnValue({
    data: roles,
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useCreateGovernanceRole).mockReturnValue({
    mutateAsync: create,
    isPending: false,
  } as never);
  vi.mocked(useUpdateGovernanceRole).mockReturnValue({
    mutateAsync: update,
    isPending: false,
  } as never);
  vi.mocked(useDeleteGovernanceRole).mockReturnValue({
    mutateAsync: remove,
    isPending: false,
  } as never);
  vi.mocked(useAssignGovernanceRole).mockReturnValue({
    mutateAsync: assign,
    isPending: false,
  } as never);
  vi.mocked(useUnassignGovernanceRole).mockReturnValue({
    mutateAsync: unassign,
    isPending: false,
  } as never);
  vi.mocked(useUserDirectory).mockReturnValue({ data: directory } as never);
  return { create, update, remove, assign, unassign };
}

describe("GovernanceRoleList", () => {
  it("shows each role's name, responsibilities, and holder count", () => {
    mockHooks({ roles: [makeRole({ max_holders: 1 })] });

    render(<GovernanceRoleList canManage={false} />);

    expect(screen.getByText("Risk Owner")).toBeInTheDocument();
    expect(screen.getByText("0 of 1")).toBeInTheDocument();
  });

  it("hides management controls for a viewer", () => {
    mockHooks();

    render(<GovernanceRoleList canManage={false} />);

    expect(screen.queryByRole("button", { name: "Add Role" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Role" })).not.toBeInTheDocument();
  });

  it("lets an admin assign an unheld role to a directory user", async () => {
    const { assign } = mockHooks();
    const user = userEvent.setup();

    render(<GovernanceRoleList canManage />);
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Assign a user to Risk Owner" }),
      "9",
    );
    await user.click(screen.getByRole("button", { name: "Assign" }));

    await waitFor(() =>
      expect(assign).toHaveBeenCalledWith({ roleId: 1, userId: 9 }),
    );
  });

  it("does not offer assignment once a role is at capacity", () => {
    mockHooks({
      roles: [makeRole({ max_holders: 1, holders: [{ id: 9, name: "Priya Shah" }] })],
    });

    render(<GovernanceRoleList canManage />);

    expect(
      screen.queryByRole("combobox", { name: "Assign a user to Risk Owner" }),
    ).not.toBeInTheDocument();
  });

  it("creates a new role reporting to an existing one", async () => {
    const { create } = mockHooks({ roles: [makeRole({ id: 1, name: "Data Owner" })] });
    const user = userEvent.setup();

    render(<GovernanceRoleList canManage />);
    await user.click(screen.getByRole("button", { name: "Add Role" }));
    await user.type(screen.getByLabelText("Role name"), "Vendor Manager");
    await user.type(
      screen.getByLabelText("Responsibilities"),
      "Owns vendor relationships.",
    );
    await user.selectOptions(screen.getByLabelText("Reports to for the new role"), "1");
    await user.click(screen.getByRole("button", { name: "Create Role" }));

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith({
        name: "Vendor Manager",
        responsibilities: "Owns vendor relationships.",
        parent_role_id: 1,
      }),
    );
  });
});
