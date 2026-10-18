import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { useChangePassword, useCurrentUser, useSignOutEverywhere } from "../../features/auth/hooks";
import { AccountPage } from "../AccountPage";

vi.mock("../../features/auth/hooks");

function mockHooks(signOut: Record<string, unknown> = {}) {
  const mutate = vi.fn();
  vi.mocked(useCurrentUser).mockReturnValue({
    data: { id: 1, name: "Ada Admin", email: "ada@example.com", role: "admin" },
  } as never);
  vi.mocked(useChangePassword).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
  } as never);
  vi.mocked(useSignOutEverywhere).mockReturnValue({
    mutate,
    isPending: false,
    isSuccess: false,
    isError: false,
    ...signOut,
  } as never);
  return mutate;
}

describe("AccountPage", () => {
  it("shows who you are signed in as, and the password form", () => {
    mockHooks();

    render(<AccountPage />);

    expect(screen.getByText("Ada Admin · ada@example.com")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Change your password" })).toBeInTheDocument();
  });

  it("signs out of other devices on request", async () => {
    const mutate = mockHooks();
    const user = userEvent.setup();

    render(<AccountPage />);
    await user.click(screen.getByRole("button", { name: "Sign out of other devices" }));

    expect(mutate).toHaveBeenCalledTimes(1);
  });

  it("says how many other sessions were ended", () => {
    mockHooks({ isSuccess: true, data: { other_sessions_ended: 3 } });

    render(<AccountPage />);

    expect(screen.getByRole("status")).toHaveTextContent("Signed out of 3 other session(s).");
  });

  it("says so when there was nowhere else to sign out of", () => {
    mockHooks({ isSuccess: true, data: { other_sessions_ended: 0 } });

    render(<AccountPage />);

    expect(screen.getByRole("status")).toHaveTextContent("You weren't signed in anywhere else.");
  });

  it("reports a failure", () => {
    mockHooks({ isError: true });

    render(<AccountPage />);

    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't sign out of other devices.");
  });
});
