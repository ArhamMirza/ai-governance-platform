import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { auditProgramsApi } from "../api";
import { AuditProgramList } from "../components/AuditProgramList";
import type { AuditProgram } from "../types";

vi.mock("../api");

const overdueProgram: AuditProgram = {
  id: 1,
  title: "AI System Audit",
  description: null,
  schedule_type: "interval",
  interval_months: 6,
  start_date: "2020-01-01",
  owner_id: null,
  status: "active",
  next_due_date: "2020-01-01",
  overdue: true,
  framework_tags: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AuditProgramList", () => {
  it("flags an overdue program", async () => {
    vi.mocked(auditProgramsApi.list).mockResolvedValue([overdueProgram]);

    renderWithProviders(<AuditProgramList />);

    await waitFor(() => {
      expect(screen.getByText("AI System Audit")).toBeInTheDocument();
    });
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    expect(screen.getByText("Every 6 month(s)")).toBeInTheDocument();
  });

  it("shows an empty state when there are no programs", async () => {
    vi.mocked(auditProgramsApi.list).mockResolvedValue([]);

    renderWithProviders(<AuditProgramList />);

    await waitFor(() => {
      expect(screen.getByText("No audit programs yet.")).toBeInTheDocument();
    });
  });
});
