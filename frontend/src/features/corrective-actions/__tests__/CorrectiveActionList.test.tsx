import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { usersApi } from "../../users/api";
import { correctiveActionsApi } from "../api";
import { CorrectiveActionList } from "../components/CorrectiveActionList";
import type { CorrectiveAction } from "../types";

vi.mock("../api");
vi.mock("../../users/api");

const mockCorrectiveAction: CorrectiveAction = {
  id: 1,
  title: "Resume screener ranking drift",
  nonconformity_description: "Model favors one demographic group.",
  root_cause: null,
  action_description: null,
  source_type: null,
  source_id: null,
  assignee_id: 7,
  due_date: "2020-01-01",
  status: "open",
  overdue: true,
  framework_tags: [],
  closed_by: null,
  closed_at: null,
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

describe("CorrectiveActionList", () => {
  it("renders corrective actions, their assignee, and an overdue flag", async () => {
    vi.mocked(correctiveActionsApi.list).mockResolvedValue([mockCorrectiveAction]);
    vi.mocked(usersApi.directory).mockResolvedValue([
      { id: 7, name: "Jordan Lee", governance_roles: [] },
    ]);

    renderWithProviders(<CorrectiveActionList />);

    await waitFor(() => {
      expect(screen.getByText("Resume screener ranking drift")).toBeInTheDocument();
    });
    expect(screen.getByText("Jordan Lee")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("shows an empty state when there are no corrective actions", async () => {
    vi.mocked(correctiveActionsApi.list).mockResolvedValue([]);
    vi.mocked(usersApi.directory).mockResolvedValue([]);

    renderWithProviders(<CorrectiveActionList />);

    await waitFor(() => {
      expect(screen.getByText("No corrective actions yet.")).toBeInTheDocument();
    });
  });
});
