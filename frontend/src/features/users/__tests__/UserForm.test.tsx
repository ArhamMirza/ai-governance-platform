import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UserForm } from "../components/UserForm";
import { useCreateUser } from "../hooks";

vi.mock("../hooks");

describe("UserForm", () => {
  it("submits name, email, password, and the selected role", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    vi.mocked(useCreateUser).mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: false,
    } as never);
    const onCreated = vi.fn();
    const user = userEvent.setup();

    render(<UserForm onCreated={onCreated} />);
    await user.type(screen.getByLabelText("Name"), "Bob");
    await user.type(screen.getByLabelText("Email"), "bob@example.com");
    await user.type(screen.getByLabelText("Temporary password"), "supersecret1");
    await user.selectOptions(screen.getByLabelText("Role"), "viewer");
    await user.click(screen.getByRole("button", { name: "Create User" }));

    expect(mutateAsync).toHaveBeenCalledWith({
      name: "Bob",
      email: "bob@example.com",
      password: "supersecret1",
      role: "viewer",
    });
    expect(onCreated).toHaveBeenCalled();
  });

  it("defaults the role to contributor", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    vi.mocked(useCreateUser).mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: false,
    } as never);
    const user = userEvent.setup();

    render(<UserForm />);
    await user.type(screen.getByLabelText("Name"), "Bob");
    await user.type(screen.getByLabelText("Email"), "bob@example.com");
    await user.type(screen.getByLabelText("Temporary password"), "supersecret1");
    await user.click(screen.getByRole("button", { name: "Create User" }));

    expect(mutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ role: "contributor" }),
    );
  });

  it("validates a minimum password length", async () => {
    vi.mocked(useCreateUser).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
    } as never);
    const user = userEvent.setup();

    render(<UserForm />);
    await user.type(screen.getByLabelText("Name"), "Bob");
    await user.type(screen.getByLabelText("Email"), "bob@example.com");
    await user.type(screen.getByLabelText("Temporary password"), "short");
    await user.click(screen.getByRole("button", { name: "Create User" }));

    expect(
      await screen.findByText("Password must be at least 12 characters"),
    ).toBeInTheDocument();
  });
});
