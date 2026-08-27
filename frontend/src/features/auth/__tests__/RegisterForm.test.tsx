import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { RegisterForm } from "../components/RegisterForm";
import { useRegister } from "../hooks";

vi.mock("../hooks");

describe("RegisterForm", () => {
  it("submits name, email, and password", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    vi.mocked(useRegister).mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: false,
    } as never);
    const user = userEvent.setup();

    render(<RegisterForm />);
    await user.type(screen.getByLabelText("Name"), "Ada Lovelace");
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "supersecret1");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(mutateAsync).toHaveBeenCalledWith({
      name: "Ada Lovelace",
      email: "ada@example.com",
      password: "supersecret1",
    });
  });

  it("validates a minimum password length", async () => {
    vi.mocked(useRegister).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
    } as never);
    const user = userEvent.setup();

    render(<RegisterForm />);
    await user.type(screen.getByLabelText("Name"), "Ada Lovelace");
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(
      await screen.findByText("Password must be at least 8 characters"),
    ).toBeInTheDocument();
  });

  it("shows the server's error message when registration is closed", async () => {
    const error = new ApiError(
      409,
      JSON.stringify({ detail: "Registration is closed; an account already exists." }),
    );
    vi.mocked(useRegister).mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(error),
      isPending: false,
      isError: true,
      error,
    } as never);
    const user = userEvent.setup();

    render(<RegisterForm />);
    await user.type(screen.getByLabelText("Name"), "Ada Lovelace");
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "supersecret1");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Registration is closed; an account already exists.",
      );
    });
  });
});
