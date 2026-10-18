import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { ChangePasswordForm } from "../components/ChangePasswordForm";
import { useChangePassword } from "../hooks";

vi.mock("../hooks");

function mockHook(overrides: Record<string, unknown> = {}) {
  const mutateAsync = vi.fn().mockResolvedValue({});
  vi.mocked(useChangePassword).mockReturnValue({
    mutateAsync,
    isPending: false,
    isError: false,
    isSuccess: false,
    ...overrides,
  } as never);
  return mutateAsync;
}

async function fill(
  user: ReturnType<typeof userEvent.setup>,
  {
    current = "old-passphrase-1",
    next = "a-much-better-passphrase",
    confirm = undefined as string | undefined,
  } = {},
) {
  await user.type(screen.getByLabelText("Current password"), current);
  await user.type(screen.getByLabelText("New password"), next);
  await user.type(screen.getByLabelText("Confirm new password"), confirm ?? next);
  await user.click(screen.getByRole("button", { name: "Change password" }));
}

describe("ChangePasswordForm", () => {
  it("sends the current and new password, and not the confirmation", async () => {
    const mutateAsync = mockHook();
    const onChanged = vi.fn();
    const user = userEvent.setup();

    render(<ChangePasswordForm onChanged={onChanged} />);
    await fill(user);

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(mutateAsync).toHaveBeenCalledWith({
      current_password: "old-passphrase-1",
      new_password: "a-much-better-passphrase",
    });
  });

  it("refuses a short new password before sending anything", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(<ChangePasswordForm />);
    await fill(user, { next: "short" });

    expect(
      await screen.findByText("Password must be at least 12 characters"),
    ).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("accepts a new password of exactly twelve characters", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(<ChangePasswordForm />);
    await fill(user, { next: "abcdefghijk1" });

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
  });

  it("refuses when the two new passwords differ", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(<ChangePasswordForm />);
    await fill(user, { next: "a-much-better-passphrase", confirm: "a-much-better-passphrasE" });

    expect(await screen.findByText("The two new passwords don't match")).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("needs the current password", async () => {
    const mutateAsync = mockHook();
    const user = userEvent.setup();

    render(<ChangePasswordForm />);
    await user.type(screen.getByLabelText("New password"), "a-much-better-passphrase");
    await user.type(screen.getByLabelText("Confirm new password"), "a-much-better-passphrase");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByText("Enter your current password")).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("shows the server's reason, such as a password that is too common", async () => {
    const error = new ApiError(400, JSON.stringify({ detail: "That password is too common." }));
    mockHook({ mutateAsync: vi.fn().mockRejectedValue(error), isError: true, error });
    const user = userEvent.setup();

    render(<ChangePasswordForm />);
    await fill(user);

    expect(await screen.findByRole("alert")).toHaveTextContent("That password is too common.");
  });

  it("explains the rules next to the field", () => {
    mockHook();

    render(<ChangePasswordForm />);

    expect(screen.getByLabelText("New password")).toHaveAccessibleDescription(
      /At least 12 characters/,
    );
  });

  it("says why when the change is forced, and confirms when it is not", () => {
    mockHook({ isSuccess: true });
    const { rerender } = render(<ChangePasswordForm />);
    expect(screen.getByRole("heading", { name: "Change your password" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Password changed.");

    rerender(<ChangePasswordForm forced />);
    expect(screen.getByRole("heading", { name: "Choose a new password" })).toBeInTheDocument();
    expect(screen.getByText(/set by someone else/)).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("disables the button while saving", () => {
    mockHook({ isPending: true });

    render(<ChangePasswordForm />);

    expect(screen.getByRole("button", { name: "Saving..." })).toBeDisabled();
  });
});
