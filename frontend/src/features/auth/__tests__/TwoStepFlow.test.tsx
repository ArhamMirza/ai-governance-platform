// Real hooks and a real query cache, with only the network faked. The unit tests
// for these screens mock the hooks, so they cannot see what happens when the
// account refreshes underneath them -- which is exactly where the recovery
// codes were once being thrown away.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "../api";
import { AuthGate } from "../components/AuthGate";
import { TwoStepPanel } from "../components/TwoStepPanel";
import type { AuthUser } from "../types";

vi.mock("../api");

const CODES = ["AAAAA-BBBBB", "CCCCC-DDDDD"];

/** A tiny stand-in for the server: two-step sign-in is off until a code is confirmed. */
function fakeServer({ required }: { required: boolean }) {
  const state = { enabled: false };
  const user = (): AuthUser =>
    ({
      id: 1,
      name: "Ada",
      email: "ada@example.com",
      role: "admin",
      is_active: true,
      created_at: "",
      must_change_password: false,
      mfa_enabled: state.enabled,
      mfa_setup_required: required && !state.enabled,
    }) as AuthUser;

  vi.mocked(authApi.me).mockImplementation(async () => user());
  vi.mocked(authApi.registrationStatus).mockResolvedValue({
    registration_open: false,
    setup_code_required: false,
  });
  vi.mocked(authApi.twoStepStatus).mockImplementation(async () => ({
    enabled: state.enabled,
    recovery_codes_remaining: state.enabled ? CODES.length : 0,
    setup_required: required && !state.enabled,
  }));
  vi.mocked(authApi.startTwoStepSetup).mockResolvedValue({
    secret: "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
    otpauth_uri: "otpauth://totp/AI:ada@example.com?secret=ABC",
  });
  vi.mocked(authApi.confirmTwoStep).mockImplementation(async () => {
    state.enabled = true; // from this moment, every read says "on"
    return { recovery_codes: CODES };
  });
  return state;
}

function wrap(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{children}</QueryClientProvider>);
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("turning on two-step sign-in from the account page", () => {
  it("keeps showing the recovery codes after the code is accepted, until they are saved", async () => {
    fakeServer({ required: false });
    const user = userEvent.setup();

    wrap(<TwoStepPanel />);
    await user.click(await screen.findByRole("button", { name: "Set up two-step sign-in" }));
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await user.type(await screen.findByLabelText(/Enter the 6-digit code/), "123456");
    await user.click(screen.getByRole("button", { name: "Turn on" }));

    const list = await screen.findByRole("list", { name: "Recovery codes" });
    expect(within(list).getByText("AAAAA-BBBBB")).toBeInTheDocument();
    // Give any refresh a chance to land: the codes must still be there.
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(screen.getByRole("list", { name: "Recovery codes" })).toBeInTheDocument();
    expect(screen.queryByText("On")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("I have saved these codes"));
    await user.click(screen.getByRole("button", { name: "Done" }));

    expect(await screen.findByText("On")).toBeInTheDocument();
    expect(screen.getByText(/2 recovery codes left/)).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Recovery codes" })).not.toBeInTheDocument();
  });

  it("does not tell the app it is on until the codes are saved", async () => {
    fakeServer({ required: false });
    const user = userEvent.setup();

    wrap(<TwoStepPanel />);
    await user.click(await screen.findByRole("button", { name: "Set up two-step sign-in" }));
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await user.type(await screen.findByLabelText(/Enter the 6-digit code/), "123456");
    await user.click(screen.getByRole("button", { name: "Turn on" }));
    await screen.findByRole("list", { name: "Recovery codes" });
    const statusReadsBefore = vi.mocked(authApi.twoStepStatus).mock.calls.length;

    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(vi.mocked(authApi.twoStepStatus).mock.calls.length).toBe(statusReadsBefore);

    await user.click(screen.getByLabelText("I have saved these codes"));
    await user.click(screen.getByRole("button", { name: "Done" }));
    await waitFor(() =>
      expect(vi.mocked(authApi.twoStepStatus).mock.calls.length).toBeGreaterThan(statusReadsBefore),
    );
  });
});

describe("the required set-up an administrator is held at", () => {
  it("keeps the recovery codes on screen, and only then lets them into the app", async () => {
    fakeServer({ required: true });
    const user = userEvent.setup();

    wrap(
      <AuthGate>
        <div>Protected content</div>
      </AuthGate>,
    );
    expect(await screen.findByRole("heading", { name: "Set up two-step sign-in" })).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await user.type(await screen.findByLabelText(/Enter the 6-digit code/), "123456");
    await user.click(screen.getByRole("button", { name: "Turn on" }));

    expect(await screen.findByRole("list", { name: "Recovery codes" })).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 100));
    // The server now says they are set up, yet they have not seen their codes saved.
    expect(screen.getByRole("list", { name: "Recovery codes" })).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("I have saved these codes"));
    await user.click(screen.getByRole("button", { name: "Done" }));

    expect(await screen.findByText("Protected content")).toBeInTheDocument();
  });
});
