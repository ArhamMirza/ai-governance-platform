import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { TwoStepSetup } from "../components/TwoStepSetup";
import { useConfirmTwoStep, useRefreshAccount, useStartTwoStepSetup } from "../hooks";

vi.mock("../hooks");

const SETUP = {
  secret: "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
  otpauth_uri: "otpauth://totp/AI%20Governance%20Platform:ada%40example.com?secret=ABC",
};

function mockHooks({
  start = vi.fn().mockResolvedValue(SETUP),
  confirm = vi.fn().mockResolvedValue({ recovery_codes: ["AAAAA-BBBBB", "CCCCC-DDDDD"] }),
  startState = {},
  confirmState = {},
}: {
  start?: ReturnType<typeof vi.fn>;
  confirm?: ReturnType<typeof vi.fn>;
  startState?: Record<string, unknown>;
  confirmState?: Record<string, unknown>;
} = {}) {
  vi.mocked(useStartTwoStepSetup).mockReturnValue({
    mutateAsync: start,
    isPending: false,
    isError: false,
    ...startState,
  } as never);
  vi.mocked(useConfirmTwoStep).mockReturnValue({
    mutateAsync: confirm,
    isPending: false,
    isError: false,
    ...confirmState,
  } as never);
  const refresh = vi.fn().mockResolvedValue(undefined);
  vi.mocked(useRefreshAccount).mockReturnValue(refresh);
  return { start, confirm, refresh };
}

describe("TwoStepSetup", () => {
  it("explains what is needed before anything is created", () => {
    const { start } = mockHooks();

    render(<TwoStepSetup />);

    expect(screen.getByText(/authenticator app on your phone/)).toBeInTheDocument();
    expect(start).not.toHaveBeenCalled();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("shows the QR code and the key, grouped for typing, once started", async () => {
    mockHooks();
    const user = userEvent.setup();

    render(<TwoStepSetup />);
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));

    expect(await screen.findByRole("img", { name: /QR code/ })).toBeInTheDocument();
    expect(screen.getByTestId("setup-key")).toHaveTextContent(
      "ABCD EFGH IJKL MNOP QRST UVWX YZ23 4567",
    );
  });

  it("sends the code, trimmed, and then shows the recovery codes", async () => {
    const { confirm } = mockHooks();
    const user = userEvent.setup();

    render(<TwoStepSetup />);
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await user.type(await screen.findByLabelText(/Enter the 6-digit code/), " 123456 ");
    await user.click(screen.getByRole("button", { name: "Turn on" }));

    await waitFor(() => expect(confirm).toHaveBeenCalledWith("123456"));
    expect(await screen.findByRole("list", { name: "Recovery codes" })).toHaveTextContent(
      "AAAAA-BBBBB",
    );
    // The key and QR code are gone once it is on.
    expect(screen.queryByTestId("setup-key")).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("refreshes the account only once the codes are confirmed saved, then calls onDone", async () => {
    const { refresh } = mockHooks();
    const onDone = vi.fn();
    const user = userEvent.setup();

    render(<TwoStepSetup onDone={onDone} />);
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await user.type(await screen.findByLabelText(/Enter the 6-digit code/), "123456");
    await user.click(screen.getByRole("button", { name: "Turn on" }));
    await screen.findByRole("list", { name: "Recovery codes" });
    expect(onDone).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();

    await user.click(screen.getByLabelText("I have saved these codes"));
    await user.click(screen.getByRole("button", { name: "Done" }));
    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("asks for a code before sending anything", async () => {
    const { confirm } = mockHooks();
    const user = userEvent.setup();

    render(<TwoStepSetup />);
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await screen.findByRole("img");
    await user.click(screen.getByRole("button", { name: "Turn on" }));

    expect(await screen.findByText("Enter the code from the app")).toBeInTheDocument();
    expect(confirm).not.toHaveBeenCalled();
  });

  it("shows the server's reason when the code is wrong and stays on the scan step", async () => {
    const error = new ApiError(400, JSON.stringify({ detail: "That code isn't right." }));
    mockHooks({
      confirm: vi.fn().mockRejectedValue(error),
      confirmState: { isError: true, error },
    });
    const user = userEvent.setup();

    render(<TwoStepSetup />);
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await user.type(await screen.findByLabelText(/Enter the 6-digit code/), "000000");
    await user.click(screen.getByRole("button", { name: "Turn on" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("That code isn't right.");
    expect(screen.getByTestId("setup-key")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Recovery codes" })).not.toBeInTheDocument();
  });

  it("starts again from the beginning on request", async () => {
    mockHooks();
    const user = userEvent.setup();

    render(<TwoStepSetup />);
    await user.click(screen.getByRole("button", { name: "Set up two-step sign-in" }));
    await screen.findByRole("img");
    await user.click(screen.getByRole("button", { name: "Start again" }));

    expect(screen.getByRole("button", { name: "Set up two-step sign-in" })).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("says why it could not start", () => {
    const error = new ApiError(
      409,
      JSON.stringify({ detail: "Two-step sign-in is already on." }),
    );
    mockHooks({ startState: { isError: true, error } });

    render(<TwoStepSetup />);

    expect(screen.getByRole("alert")).toHaveTextContent("already on");
  });

  it("offers cancel only when it can be cancelled", async () => {
    mockHooks();
    const onCancel = vi.fn();
    const user = userEvent.setup();

    const { rerender } = render(<TwoStepSetup />);
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();

    rerender(<TwoStepSetup onCancel={onCancel} />);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
