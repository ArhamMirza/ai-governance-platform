import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { authApi } from "../../auth/api";
import { staffApi } from "../api";
import { EmployeeApp } from "../components/EmployeeApp";

vi.mock("../../auth/api");
vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { staffApi: { ...actual.staffApi, library: vi.fn() } };
});

// The name comes from a query; allow for a loaded machine.
const SLOW = { timeout: 5000 };

function renderAt(path: string) {
  vi.mocked(authApi.me).mockResolvedValue({
    id: 7,
    name: "Elena Employee",
    email: "elena@example.com",
    role: "employee",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  });
  vi.mocked(staffApi.library).mockResolvedValue([]);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <EmployeeApp />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("EmployeeApp", () => {
  it.each(["/", "/risk-assessments/5", "/users", "/dashboard"])(
    "lands on the staff home at %s",
    async (path) => {
      renderAt(path);

      expect(
        await screen.findByRole("heading", { name: "Welcome, Elena Employee" }, SLOW),
      ).toBeInTheDocument();
    },
  );

  it("offers a way home and a way out, and nothing else", async () => {
    renderAt("/");

    await screen.findByRole("heading", { name: "Welcome, Elena Employee" }, SLOW);
    expect(screen.getAllByRole("link").map((link) => link.textContent)).toEqual(["Home"]);
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });
});
