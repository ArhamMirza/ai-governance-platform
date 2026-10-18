import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { LoginForm } from "../components/LoginForm";
import { useLogin, useLoginTwoStep } from "../hooks";

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

  describe("an account with two-step sign-in", () => {
    function mockLogin(result: unknown) {
      const mutateAsync = vi.fn().mockResolvedValue(result);
      vi.mocked(useLogin).mockReturnValue({
        mutateAsync,
        isPending: false,
        isError: false,
      } as never);
      vi.mocked(useLoginTwoStep).mockReturnValue({
        mutateAsync: vi.fn().mockResolvedValue({}),
        isPending: false,
        isError: false,
      } as never);
      return mutateAsync;
    }

    async function enterPassword(user: ReturnType<typeof userEvent.setup>) {
      await user.type(screen.getByLabelText("Email"), "ada@example.com");
      await user.type(screen.getByLabelText("Password"), "supersecret1");
      await user.click(screen.getByRole("button", { name: "Sign in" }));
    }

    it("asks for the code once the password is accepted", async () => {
      mockLogin({ mfa_required: true, ticket: "the-ticket" });
      const user = userEvent.setup();

      render(<LoginForm />);
      await enterPassword(user);

      expect(await screen.findByRole("heading", { name: "Two-step sign-in" })).toBeInTheDocument();
      expect(screen.getByLabelText("Authentication code")).toBeInTheDocument();
      expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
    });

    it("goes straight in for an account without it, with no second step", async () => {
      mockLogin({ id: 1, name: "Ada", mfa_enabled: false });
      const user = userEvent.setup();

      render(<LoginForm />);
      await enterPassword(user);

      await waitFor(() => expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument());
      expect(screen.queryByLabelText("Authentication code")).not.toBeInTheDocument();
    });

    it("can go back to the password step", async () => {
      mockLogin({ mfa_required: true, ticket: "the-ticket" });
      const user = userEvent.setup();

      render(<LoginForm />);
      await enterPassword(user);
      await user.click(await screen.findByRole("button", { name: "Back to password" }));

      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
      expect(screen.getByLabelText("Password")).toHaveValue("");
      expect(screen.getByLabelText("Email")).toHaveValue("ada@example.com");
    });
  });
});
