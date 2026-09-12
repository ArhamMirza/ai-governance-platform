import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { useCurrentUser } from "../../auth/hooks";
import { UsersList } from "../components/UsersList";
import { useUpdateUser, useUserAccountabilities, useUsers } from "../hooks";
import type { ManagedUser, UserAccountabilities } from "../types";

vi.mock("../hooks");
vi.mock("../../auth/hooks");

const me: ManagedUser = {
  id: 1,
  name: "Admin",
  email: "admin@example.com",
  role: "admin",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

const contributor: ManagedUser = {
  id: 2,
  name: "Bob",
  email: "bob@example.com",
  role: "contributor",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

const NOTHING_OWNED: UserAccountabilities = {
  governance_roles: [],
  ai_systems_owned: [],
  datasets_owned: [],
  open_risk_items: 0,
};

function mockHooks(
  users: ManagedUser[],
  mutateAsync = vi.fn(),
  accountabilities: UserAccountabilities = NOTHING_OWNED,
) {
  vi.mocked(useUsers).mockReturnValue({ data: users, isLoading: false, isError: false } as never);
  vi.mocked(useCurrentUser).mockReturnValue({ data: me } as never);
  vi.mocked(useUpdateUser).mockReturnValue({ mutateAsync, isPending: false } as never);
  vi.mocked(useUserAccountabilities).mockReturnValue({ data: accountabilities } as never);
  return { mutateAsync };
}

/** Deactivation is behind a confirmation now, so the tests have to confirm. */
async function clickDeactivateAndConfirm(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Deactivate" }));
  const dialog = screen.getByRole("alertdialog");
  await user.click(within(dialog).getByRole("button", { name: "Deactivate" }));
}

describe("UsersList", () => {
  it("renders every user with their role and status", () => {
    mockHooks([me, contributor]);

    render(<UsersList />);

    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByText("bob@example.com")).toBeInTheDocument();
    expect(screen.getAllByText("Active")).toHaveLength(2);
  });

  it("does not let the current user change their own role", () => {
    mockHooks([me, contributor]);

    render(<UsersList />);

    expect(screen.queryByLabelText(`Role for ${me.name}`)).not.toBeInTheDocument();
    expect(screen.getByLabelText(`Role for ${contributor.name}`)).toBeInTheDocument();
  });

  it("does not show a deactivate button on the current user's own row", () => {
    mockHooks([me, contributor]);

    render(<UsersList />);

    expect(screen.getAllByRole("button", { name: "Deactivate" })).toHaveLength(1);
  });

  it("changes another user's role", async () => {
    const { mutateAsync } = mockHooks([me, contributor]);
    const user = userEvent.setup();

    render(<UsersList />);
    await user.selectOptions(screen.getByLabelText(`Role for ${contributor.name}`), "admin");

    expect(mutateAsync).toHaveBeenCalledWith({ id: contributor.id, data: { role: "admin" } });
  });

  it("deactivates another user", async () => {
    const { mutateAsync } = mockHooks([me, contributor]);
    const user = userEvent.setup();

    render(<UsersList />);
    await clickDeactivateAndConfirm(user);

    expect(mutateAsync).toHaveBeenCalledWith({
      id: contributor.id,
      data: { is_active: false },
    });
  });

  it("shows reactivate for a deactivated user", () => {
    mockHooks([me, { ...contributor, is_active: false }]);

    render(<UsersList />);

    expect(screen.getByRole("button", { name: "Reactivate" })).toBeInTheDocument();
    expect(screen.getByText("Deactivated")).toBeInTheDocument();
  });

  it("shows the server error on a failed update", async () => {
    const mutateAsync = vi.fn().mockRejectedValue(new Error("nope"));
    mockHooks([me, contributor], mutateAsync);
    const user = userEvent.setup();

    render(<UsersList />);
    await clickDeactivateAndConfirm(user);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("warns what a deactivated owner is holding before confirming", async () => {
    mockHooks([me, contributor], vi.fn(), {
      governance_roles: ["Chief AI Governance Officer"],
      ai_systems_owned: ["Resume Screener"],
      datasets_owned: [],
      open_risk_items: 2,
    });
    const user = userEvent.setup();

    render(<UsersList />);
    await user.click(screen.getByRole("button", { name: "Deactivate" }));

    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent("Chief AI Governance Officer");
    expect(dialog).toHaveTextContent("Resume Screener");
    expect(dialog).toHaveTextContent("2 open risk item(s)");
  });

  it("does not deactivate if the confirmation is cancelled", async () => {
    const { mutateAsync } = mockHooks([me, contributor]);
    const user = userEvent.setup();

    render(<UsersList />);
    await user.click(screen.getByRole("button", { name: "Deactivate" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("reactivates without a confirmation", async () => {
    const { mutateAsync } = mockHooks([me, { ...contributor, is_active: false }]);
    const user = userEvent.setup();

    render(<UsersList />);
    await user.click(screen.getByRole("button", { name: "Reactivate" }));

    expect(mutateAsync).toHaveBeenCalledWith({ id: contributor.id, data: { is_active: true } });
  });
});
