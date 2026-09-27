import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthGate } from "../components/AuthGate";
import { useCurrentUser, useLogin, useRegister, useRegistrationStatus } from "../hooks";

vi.mock("../hooks");

function mockHooks({
  user = undefined,
  userLoading = false,
  isSuccess = false,
  registrationOpen = false,
  statusError = false,
}: {
  user?: unknown;
  userLoading?: boolean;
  isSuccess?: boolean;
  registrationOpen?: boolean;
  statusError?: boolean;
} = {}) {
  vi.mocked(useCurrentUser).mockReturnValue({
    data: user,
    isLoading: userLoading,
    isSuccess,
  } as never);
  vi.mocked(useRegistrationStatus).mockReturnValue({
    data: statusError ? undefined : { registration_open: registrationOpen },
    isLoading: false,
    isError: statusError,
  } as never);
  // LoginForm/RegisterForm render as real children of AuthGate (not
  // stubbed out), so their own hooks need a usable return value too.
  vi.mocked(useLogin).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
  } as never);
  vi.mocked(useRegister).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
  } as never);
}

describe("AuthGate", () => {
  it("shows children once authenticated", () => {
    mockHooks({ user: { id: 1, name: "Ada" }, isSuccess: true });

    render(
      <AuthGate>
        <div>Protected content</div>
      </AuthGate>,
    );

    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });

  it("shows the login form when not authenticated and registration is closed", async () => {
    mockHooks({ registrationOpen: false });

    render(
      <AuthGate>
        <div>Protected content</div>
      </AuthGate>,
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("shows the registration form on first run", async () => {
    mockHooks({ registrationOpen: true });

    render(
      <AuthGate>
        <div>Protected content</div>
      </AuthGate>,
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
    });
  });

  it("shows a loading state while the session check is in flight", () => {
    mockHooks({ userLoading: true });

    render(
      <AuthGate>
        <div>Protected content</div>
      </AuthGate>,
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("never silently guesses login-vs-register when the registration check fails", () => {
    mockHooks({ statusError: true });

    render(
      <AuthGate>
        <div>Protected content</div>
      </AuthGate>,
    );

    expect(
      screen.getByText("Couldn't reach the server. Check your connection and reload."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Create your account" })).not.toBeInTheDocument();
  });
});
