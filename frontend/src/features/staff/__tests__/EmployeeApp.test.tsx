import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { authApi } from "../../auth/api";
import { staffAiToolsApi } from "../../ai-tools/api";
import { staffAiUseApi } from "../../ai-use/api";
import { staffApi } from "../api";
import { EmployeeApp } from "../components/EmployeeApp";

vi.mock("../../auth/api");
vi.mock("../../ai-tools/api");
vi.mock("../../ai-use/api");
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
    created_at: "2026-01-01T00:00:00Z", must_change_password: false,
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
    const nav = within(screen.getByRole("navigation"));
    expect(nav.getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Home",
      "Report a concern",
      "My concerns",
      "AI tools",
    ]);
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("has a page for the AI tools staff may use and for asking for another", async () => {
    vi.mocked(staffAiToolsApi.approved).mockResolvedValue([]);
    vi.mocked(staffAiToolsApi.requestable).mockResolvedValue([]);
    vi.mocked(staffAiToolsApi.mine).mockResolvedValue([]);
    vi.mocked(staffAiUseApi.notice).mockResolvedValue({
      staff_notice: "We count visits, never what you type.",
      unapproved_site_action: "warn",
    });
    renderAt("/tools");

    expect(await screen.findByRole("heading", { name: "AI tools" }, SLOW)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Send request" })).toBeInTheDocument();
    expect(await screen.findByText("We count visits, never what you type.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Welcome/ })).not.toBeInTheDocument();
  });

  it("fills in the request from the link on the browser extension's blocked page", async () => {
    vi.mocked(staffAiToolsApi.approved).mockResolvedValue([]);
    vi.mocked(staffAiToolsApi.requestable).mockResolvedValue([]);
    vi.mocked(staffAiToolsApi.mine).mockResolvedValue([]);
    vi.mocked(staffAiUseApi.notice).mockResolvedValue({ staff_notice: null, unapproved_site_action: "block" });
    renderAt("/tools?name=Mystery%20AI&domain=mystery.ai");

    expect(await screen.findByLabelText("Name of the tool")).toHaveValue("Mystery AI");
    expect(screen.getByLabelText("Its website, if you know it")).toHaveValue("mystery.ai");
  });
});

