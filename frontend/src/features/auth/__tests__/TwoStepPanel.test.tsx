import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { TwoStepPanel } from "../components/TwoStepPanel";
import {
  useConfirmTwoStep,
  useDisableTwoStep,
  useNewRecoveryCodes,
  useRefreshAccount,
  useStartTwoStepSetup,
  useTwoStepStatus,
} from "../hooks";

vi.mock("../hooks");

function mockHooks({
  status = { enabled: false, recovery_codes_remaining: 0, setup_required: false } as
    | { enabled: boolean; recovery_codes_remaining: number; setup_required: boolean }
    | undefined,
  query = {},
  disable = vi.fn().mockResolvedValue(undefined),
  disableState = {},
  newCodes = vi.fn().mockResolvedValue({ recovery_codes: ["NEWAA-BBBBB"] }),
  newCodesState = {},
} = {}) {
  vi.mocked(useTwoStepStatus).mockReturnValue({
    data: status,
    isLoading: false,
    isError: false,
    ...query,
  } as never);
  vi.mocked(useDisableTwoStep).mockReturnValue({
    mutateAsync: disable,
    reset: vi.fn(),
    isPending: false,
    error: null,
    ...disableState,
  } as never);
  vi.mocked(useNewRecoveryCodes).mockReturnValue({
    mutateAsync: newCodes,
    reset: vi.fn(),
    isPending: false,
    error: null,
    ...newCodesState,
  } as never);
  vi.mocked(useStartTwoStepSetup).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
  } as never);
  vi.mocked(useConfirmTwoStep).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
  } as never);
  vi.mocked(useRefreshAccount).mockReturnValue(vi.fn().mockResolvedValue(undefined));
  return { disable, newCodes };
}

const ON = { enabled: true, recovery_codes_remaining: 8, setup_required: false };

describe("TwoStepPanel", () => {
  it("shows it is off, and offers to set it up", async () => {
    mockHooks();
    const user = userEvent.setup();

    render(<TwoStepPanel />);

    expect(screen.getByText("Off")).toBeInTheDocument();
    expect(screen.getByText(/a stolen password isn't enough/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    // The explanation step of the set-up flow (a second button of the same name starts it).
    expect(screen.getByText(/authenticator app on your phone/)).toBeInTheDocument();
  });

  it("goes back from set-up with cancel", async () => {
    mockHooks();
    const user = userEvent.setup();

    render(<TwoStepPanel />);
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByText(/Signing in needs only your password/)).toBeInTheDocument();
  });

  it("shows it is on, with the recovery codes left", () => {
    mockHooks({ status: ON });

    render(<TwoStepPanel />);

    expect(screen.getByText("On")).toBeInTheDocument();
    expect(screen.getByText("8 recovery codes left.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Set up two-step sign-in" })).not.toBeInTheDocument();
  });

  it.each([
    [3, "3 recovery codes left. Make new ones before you run out."],
    [1, "1 recovery code left. Make new ones before you run out."],
    [0, "0 recovery codes left. Make new ones before you run out."],
    [4, "4 recovery codes left."],
  ])("says so when %i recovery codes are left", (remaining, text) => {
    mockHooks({ status: { ...ON, recovery_codes_remaining: remaining } });

    render(<TwoStepPanel />);

    expect(screen.getByText(text)).toBeInTheDocument();
  });

  it("turns it off only with the password and a code", async () => {
    const { disable } = mockHooks({ status: ON });
    const user = userEvent.setup();

    render(<TwoStepPanel />);
    await user.click(screen.getByRole("button", { name: "Turn off" }));
    await user.click(screen.getByRole("button", { name: "Turn off" }));
    expect(await screen.findByText("Enter your password")).toBeInTheDocument();
    expect(disable).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("Your password"), "my-password-here");
    await user.type(screen.getByLabelText(/Code from your app/), "123456");
    await user.click(screen.getByRole("button", { name: "Turn off" }));

    await waitFor(() =>
      expect(disable).toHaveBeenCalledWith({ password: "my-password-here", code: "123456" }),
    );
  });

  it("shows the server's reason when turning it off is refused", async () => {
    const error = new ApiError(
      409,
      JSON.stringify({ detail: "Your organization requires two-step sign-in for administrators." }),
    );
    mockHooks({ status: ON, disableState: { error } });
    const user = userEvent.setup();

    render(<TwoStepPanel />);
    await user.click(screen.getByRole("button", { name: "Turn off" }));

    expect(screen.getByRole("alert")).toHaveTextContent("requires two-step sign-in");
  });

  it("makes new recovery codes and shows them once", async () => {
    const { newCodes } = mockHooks({ status: ON });
    const user = userEvent.setup();

    render(<TwoStepPanel />);
    await user.click(screen.getByRole("button", { name: "Make new recovery codes" }));
    expect(screen.getByText(/the old ones stop working/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Your password"), "my-password-here");
    await user.type(screen.getByLabelText(/Code from your app/), "123456");
    await user.click(screen.getByRole("button", { name: "Make new codes" }));

    await waitFor(() =>
      expect(newCodes).toHaveBeenCalledWith({ password: "my-password-here", code: "123456" }),
    );
    const list = await screen.findByRole("list", { name: "Recovery codes" });
    expect(within(list).getByText("NEWAA-BBBBB")).toBeInTheDocument();

    await user.click(screen.getByLabelText("I have saved these codes"));
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(screen.queryByRole("list", { name: "Recovery codes" })).not.toBeInTheDocument();
    expect(screen.getByText("On")).toBeInTheDocument();
  });

  it("cancels out of either form", async () => {
    mockHooks({ status: ON });
    const user = userEvent.setup();

    render(<TwoStepPanel />);
    await user.click(screen.getByRole("button", { name: "Turn off" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByText("On")).toBeInTheDocument();
    expect(screen.queryByLabelText("Your password")).not.toBeInTheDocument();
  });

  it("copes with loading and with an error", () => {
    mockHooks({ status: undefined, query: { isLoading: true } });
    const { rerender } = render(<TwoStepPanel />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();

    mockHooks({ status: undefined, query: { isError: true } });
    rerender(<TwoStepPanel />);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load");
  });
});
