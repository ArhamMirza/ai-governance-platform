import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "../features/auth/api";
import { App } from "./App";
import { queryClient } from "./queryClient";

vi.mock("../features/auth/api");

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
      created_at: "2026-01-01T00:00:00Z",
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    });
  });

  it("shows a sign-in form when not authenticated", async () => {
    vi.mocked(authApi.me).mockRejectedValue(new Error("Not authenticated"));
    vi.mocked(authApi.registrationStatus).mockResolvedValue({ registration_open: false });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
  });

  it("shows the registration form on first run", async () => {
    vi.mocked(authApi.me).mockRejectedValue(new Error("Not authenticated"));
    vi.mocked(authApi.registrationStatus).mockResolvedValue({ registration_open: true });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
    });
  });
});
