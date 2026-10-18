import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { TwoStepCodeForm } from "../components/TwoStepCodeForm";
import { useLoginTwoStep } from "../hooks";

vi.mock("../hooks");

function mockHook(overrides: Record<string, unknown> = {}) {
  const mutateAsync = vi.fn().mockResolvedValue({});
  vi.mocked(useLoginTwoStep).mockReturnValue({
    mutateAsync,
    isPending: false,
    isError: false,
    ...overrides,
  } as never);
  return mutateAsync;
}

describe("TwoStepCodeForm", () => {
  it("sends the ticket with the code, trimmed", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(<TwoStepCodeForm ticket="the-ticket" onBack={vi.fn()} />);
    await user.type(screen.getByLabelText("Authentication code"), "  123456 ");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({ ticket: "the-ticket", code: "123456" }),
    );
  });

  it("asks for the code before sending anything", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(<TwoStepCodeForm ticket="t" onBack={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Verify" }));

    expect(await screen.findByText("Enter the code")).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("is set up for a one-time code: numeric keyboard and browser autofill", () => {
    mockHook();

    render(<TwoStepCodeForm ticket="t" onBack={vi.fn()} />);

    const field = screen.getByLabelText("Authentication code");
    expect(field).toHaveAttribute("autocomplete", "one-time-code");
    expect(field).toHaveAttribute("inputmode", "numeric");
  });

  it("switches to a recovery code and back, clearing what was typed", async () => {
    mockHook();
    const user = userEvent.setup();

    render(<TwoStepCodeForm ticket="t" onBack={vi.fn()} />);
    await user.type(screen.getByLabelText("Authentication code"), "123");
    await user.click(screen.getByRole("button", { name: "Use a recovery code instead" }));

    const recovery = screen.getByLabelText("Recovery code");
    expect(recovery).toHaveValue("");
    expect(recovery).toHaveAttribute("inputmode", "text");
    expect(screen.getByText(/Each works once/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Use my authenticator app instead" }));
    expect(screen.getByLabelText("Authentication code")).toBeInTheDocument();
  });

  it("sends a recovery code the same way", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(<TwoStepCodeForm ticket="t" onBack={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Use a recovery code instead" }));
    await user.type(screen.getByLabelText("Recovery code"), "ABCDE-FGHJK");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({ ticket: "t", code: "ABCDE-FGHJK" }),
    );
  });

  it("goes back to the password step", async () => {
    mockHook();
    const onBack = vi.fn();
    const user = userEvent.setup();

    render(<TwoStepCodeForm ticket="t" onBack={onBack} />);
    await user.click(screen.getByRole("button", { name: "Back to password" }));

    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("shows why a code was refused", () => {
    const error = new ApiError(401, JSON.stringify({ detail: "That code isn't right." }));
    mockHook({ isError: true, error });

    render(<TwoStepCodeForm ticket="t" onBack={vi.fn()} />);

    expect(screen.getByRole("alert")).toHaveTextContent("That code isn't right.");
  });

  it("shows the lockout message", () => {
    const error = new ApiError(
      429,
      JSON.stringify({ detail: "Too many incorrect codes. Try again in 15 minutes." }),
    );
    mockHook({ isError: true, error });

    render(<TwoStepCodeForm ticket="t" onBack={vi.fn()} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Too many incorrect codes");
  });

  it("disables the button while checking", () => {
    mockHook({ isPending: true });

    render(<TwoStepCodeForm ticket="t" onBack={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Checking..." })).toBeDisabled();
  });
});
