import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useUserDirectory } from "../../users/hooks";
import { correctiveActionsApi } from "../api";
import { CorrectiveActionForm } from "../components/CorrectiveActionForm";
import type { CorrectiveAction } from "../types";

vi.mock("../api");
vi.mock("../../users/hooks");

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeCorrectiveAction(overrides: Partial<CorrectiveAction> = {}): CorrectiveAction {
  return {
    id: 1,
    title: "Fix ranking drift",
    nonconformity_description: "x",
    root_cause: null,
    action_description: null,
    source_type: null,
    source_id: null,
    assignee_id: null,
    due_date: "2026-06-01",
    status: "open",
    overdue: false,
    framework_tags: [],
    closed_by: null,
    closed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("CorrectiveActionForm", () => {
  it("pre-fills from a source, and passes the source through on submit while still requiring an assignee and due date", async () => {
    vi.mocked(useUserDirectory).mockReturnValue({
      data: [{ id: 9, name: "Priya Shah", governance_roles: [] }],
    } as never);
    vi.mocked(correctiveActionsApi.create).mockResolvedValue(makeCorrectiveAction({ id: 7 }));
    const onCreated = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(
      <CorrectiveActionForm
        onCreated={onCreated}
        initialTitle="Finding: risk items closed without evidence"
        initialNonconformityDescription="Risk items were closed without evidence attached."
        sourceType="AuditFinding"
        sourceId={9}
      />,
    );

    expect(screen.getByLabelText("Title")).toHaveValue(
      "Finding: risk items closed without evidence",
    );
    expect(screen.getByLabelText("Nonconformity")).toHaveValue(
      "Risk items were closed without evidence attached.",
    );

    // Assignee and due date are never pre-filled -- still a deliberate choice.
    await user.click(screen.getByRole("button", { name: "Create Corrective Action" }));
    expect(
      await screen.findByText("Assign someone to this corrective action"),
    ).toBeInTheDocument();
    expect(correctiveActionsApi.create).not.toHaveBeenCalled();

    await user.selectOptions(screen.getByLabelText("Assignee"), "9");
    await user.type(screen.getByLabelText("Due date"), "2026-08-01");
    await user.click(screen.getByRole("button", { name: "Create Corrective Action" }));

    await vi.waitFor(() => {
      expect(correctiveActionsApi.create).toHaveBeenCalledWith(
        expect.objectContaining({ source_type: "AuditFinding", source_id: 9, assignee_id: 9 }),
      );
      expect(onCreated).toHaveBeenCalledWith(7);
    });
  });
});
