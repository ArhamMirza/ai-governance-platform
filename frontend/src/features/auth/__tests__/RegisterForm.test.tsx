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
      await screen.findByText("Password must be at least 12 characters"),
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

  describe("setup code", () => {
    function mockRegister() {
      const mutateAsync = vi.fn().mockResolvedValue({});
      vi.mocked(useRegister).mockReturnValue({
        mutateAsync,
        isPending: false,
        isError: false,
      } as never);
      return mutateAsync;
    }

    async function fillRest(user: ReturnType<typeof userEvent.setup>) {
      await user.type(screen.getByLabelText("Name"), "Ada Lovelace");
      await user.type(screen.getByLabelText("Email"), "ada@example.com");
      await user.type(screen.getByLabelText("Password"), "tangerine-lantern-47");
    }

    it("is not asked for on a development machine, and not sent", async () => {
      const mutateAsync = mockRegister();
      const user = userEvent.setup();

      render(<RegisterForm />);
      await fillRest(user);
      await user.click(screen.getByRole("button", { name: "Create account" }));

      expect(screen.queryByLabelText("Setup code")).not.toBeInTheDocument();
      expect(mutateAsync).toHaveBeenCalledWith({
        name: "Ada Lovelace",
        email: "ada@example.com",
        password: "tangerine-lantern-47",
      });
    });

    it("is asked for on a real deployment, and sent trimmed", async () => {
      const mutateAsync = mockRegister();
      const user = userEvent.setup();

      render(<RegisterForm setupCodeRequired />);
      await fillRest(user);
      await user.type(screen.getByLabelText("Setup code"), "  abc-123-xyz  ");
      await user.click(screen.getByRole("button", { name: "Create account" }));

      expect(mutateAsync).toHaveBeenCalledWith({
        name: "Ada Lovelace",
        email: "ada@example.com",
        password: "tangerine-lantern-47",
        setup_code: "abc-123-xyz",
      });
      expect(screen.getByLabelText("Setup code")).toHaveAccessibleDescription(/server's log/);
    });

    it("cannot be left empty or blank", async () => {
      const mutateAsync = mockRegister();
      const user = userEvent.setup();

      render(<RegisterForm setupCodeRequired />);
      await fillRest(user);
      await user.type(screen.getByLabelText("Setup code"), "   ");
      await user.click(screen.getByRole("button", { name: "Create account" }));

      expect(await screen.findByText("Enter the setup code from the server's log")).toBeInTheDocument();
      expect(mutateAsync).not.toHaveBeenCalled();
    });
  });
});
