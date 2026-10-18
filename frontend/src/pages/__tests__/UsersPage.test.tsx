import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useCurrentUser } from "../../features/auth/hooks";
import {
  useResetPassword,
  useResetTwoStep,
  useSecuritySettings,
  useUpdateSecuritySettings,
  useUpdateUser,
  useUserAccountabilities,
  useUsers,
} from "../../features/users/hooks";
import { UsersPage } from "../UsersPage";

vi.mock("../../features/auth/hooks");
vi.mock("../../features/users/hooks");

describe("UsersPage", () => {
  it("shows a not-permitted message for a non-admin", () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      data: { id: 1, name: "Bob", email: "bob@example.com", role: "contributor", is_active: true, created_at: "" },
    } as never);

    render(<UsersPage />);

    expect(screen.getByText("Only admins can manage user accounts.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New User" })).not.toBeInTheDocument();
  });

  it("shows the management UI for an admin", () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      data: { id: 1, name: "Admin", email: "admin@example.com", role: "admin", is_active: true, created_at: "" },
    } as never);
    vi.mocked(useUsers).mockReturnValue({
      data: [
        { id: 1, name: "Admin", email: "admin@example.com", role: "admin", is_active: true, created_at: "" },
      ],
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useUpdateUser).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
    vi.mocked(useUserAccountabilities).mockReturnValue({ data: undefined } as never);
    vi.mocked(useResetPassword).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
    vi.mocked(useResetTwoStep).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
    vi.mocked(useSecuritySettings).mockReturnValue({
      data: { require_mfa_for_admins: false, admins_without_mfa: 1 },
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useUpdateSecuritySettings).mockReturnValue({ mutate: vi.fn(), isPending: false } as never);

    render(<UsersPage />);

    expect(screen.getByRole("button", { name: "New User" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Sign-in security" })).toBeInTheDocument();
  });
});
