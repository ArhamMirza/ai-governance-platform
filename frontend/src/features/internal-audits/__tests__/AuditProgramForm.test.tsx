import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { auditProgramsApi } from "../api";
import { AuditProgramForm } from "../components/AuditProgramForm";
import type { AuditProgram } from "../types";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeProgram(overrides: Partial<AuditProgram> = {}): AuditProgram {
  return {
    id: 1,
    title: "AI System Audit",
    description: null,
    schedule_type: "interval",
    interval_months: 6,
    start_date: "2026-01-01",
    owner_id: null,
    status: "active",
    next_due_date: "2026-01-01",
    overdue: false,
    framework_tags: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("AuditProgramForm", () => {
  it("shows the interval field by default and hides it for an ad hoc program", async () => {
    const user = userEvent.setup();

    renderWithProviders(<AuditProgramForm />);

    expect(screen.getByLabelText("Every how many months")).toBeInTheDocument();

    await user.click(screen.getByLabelText("Ad hoc -- a one-off audit"));

    expect(screen.queryByLabelText("Every how many months")).not.toBeInTheDocument();
  });

  it("requires an interval when the schedule is interval-based", async () => {
    const user = userEvent.setup();

    renderWithProviders(<AuditProgramForm />);

    await user.type(screen.getByLabelText("Title"), "AI System Audit");
    await user.click(screen.getByRole("button", { name: "Create Audit Program" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "An interval-based program needs an interval",
    );
    expect(auditProgramsApi.create).not.toHaveBeenCalled();
  });

  it("submits an ad hoc program with no interval", async () => {
    vi.mocked(auditProgramsApi.create).mockResolvedValue(
      makeProgram({ schedule_type: "ad_hoc", interval_months: null }),
    );
    const onCreated = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(<AuditProgramForm onCreated={onCreated} />);

    await user.type(screen.getByLabelText("Title"), "Vendor Audit");
    await user.click(screen.getByLabelText("Ad hoc -- a one-off audit"));
    await user.click(screen.getByRole("button", { name: "Create Audit Program" }));

    await vi.waitFor(() => {
      expect(auditProgramsApi.create).toHaveBeenCalledWith(
        expect.objectContaining({ schedule_type: "ad_hoc", interval_months: null }),
      );
      expect(onCreated).toHaveBeenCalledWith(1);
    });
  });
});
