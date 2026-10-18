import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "../features/auth/api";
import { staffApi } from "../features/staff/api";
import { App } from "./App";
import { queryClient } from "./queryClient";

vi.mock("../features/auth/api");
vi.mock("../features/staff/api");

describe("App", () => {
  // queryClient is a module-level singleton shared with App, so cached
  // results (e.g. a resolved "me") would otherwise leak between tests.
  beforeEach(() => {
    queryClient.clear();
  });


  it("renders the navigation and dashboard heading once authenticated", async () => {
    vi.mocked(authApi.me).mockResolvedValue({
      id: 1,
      name: "Ada Lovelace",
      email: "ada@example.com",
      role: "admin",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z", must_change_password: false,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    });
  });

  it("gives an employee the staff home and none of the platform", async () => {
    vi.mocked(authApi.me).mockResolvedValue({
      id: 7,
      name: "Elena Employee",
      email: "elena@example.com",
      role: "employee",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z", must_change_password: false,
    });
    vi.mocked(staffApi.library).mockResolvedValue([]);

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Welcome, Elena Employee" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Policies and information" })).toBeInTheDocument();
    // None of the platform's navigation, and no assistant.
    expect(screen.queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Policies" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Suppliers" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("shows a sign-in form when not authenticated", async () => {
    vi.mocked(authApi.me).mockRejectedValue(new Error("Not authenticated"));
    vi.mocked(authApi.registrationStatus).mockResolvedValue({ registration_open: false, setup_code_required: false });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
  });

  it("shows the registration form on first run", async () => {
    vi.mocked(authApi.me).mockRejectedValue(new Error("Not authenticated"));
    vi.mocked(authApi.registrationStatus).mockResolvedValue({ registration_open: true, setup_code_required: false });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
    });
  });
});
