import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { LoginForm } from "../components/LoginForm";
import { useLogin } from "../hooks";

vi.mock("../hooks");

describe("LoginForm", () => {
  it("submits email and password", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    vi.mocked(useLogin).mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: false,
    } as never);
    const user = userEvent.setup();

    render(<LoginForm />);
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "supersecret1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(mutateAsync).toHaveBeenCalledWith({
      email: "ada@example.com",
      password: "supersecret1",
    });
  });

  it("shows the server's error message on failure", async () => {
    const mutateAsync = vi
      .fn()
      .mockRejectedValue(new ApiError(401, JSON.stringify({ detail: "Incorrect email or password." })));
    vi.mocked(useLogin).mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: true,
      error: new ApiError(401, JSON.stringify({ detail: "Incorrect email or password." })),
    } as never);
    const user = userEvent.setup();

    render(<LoginForm />);
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Incorrect email or password.");
    });
  });

  it("requires both fields", async () => {
    vi.mocked(useLogin).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
    } as never);
    const user = userEvent.setup();

    render(<LoginForm />);
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Email is required")).toBeInTheDocument();
  });
});
