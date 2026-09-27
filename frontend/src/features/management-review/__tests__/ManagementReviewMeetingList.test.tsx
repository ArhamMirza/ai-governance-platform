import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { usersApi } from "../../users/api";
import { managementReviewApi } from "../api";
import { ManagementReviewMeetingList } from "../components/ManagementReviewMeetingList";
import type { ManagementReviewMeeting } from "../types";

vi.mock("../api");
vi.mock("../../users/api");

function makeMeeting(overrides: Partial<ManagementReviewMeeting> = {}): ManagementReviewMeeting {
  return {
    id: 1,
    meeting_date: "2026-01-01",
    chaired_by: null,
    attendees: null,
    previous_actions_status: null,
    context_changes: null,
    performance_summary: null,
    stakeholder_feedback: null,
    resource_adequacy: null,
    improvement_opportunities: null,
    decisions_and_actions: null,
    framework_tags: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ManagementReviewMeetingList", () => {
  it("renders meetings linked to their detail page, with their chair", async () => {
    vi.mocked(managementReviewApi.listMeetings).mockResolvedValue([
      makeMeeting({ id: 5, meeting_date: "2026-03-01", chaired_by: 7 }),
    ]);
    vi.mocked(usersApi.directory).mockResolvedValue([
      { id: 7, name: "Jordan Lee", governance_roles: [] },
    ]);

    renderWithProviders(<ManagementReviewMeetingList />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "2026-03-01" })).toHaveAttribute(
        "href",
        "/management-review/5",
      );
    });
    expect(screen.getByText("Jordan Lee")).toBeInTheDocument();
  });

  it("shows an empty state when there are no meetings", async () => {
    vi.mocked(managementReviewApi.listMeetings).mockResolvedValue([]);
    vi.mocked(usersApi.directory).mockResolvedValue([]);

    renderWithProviders(<ManagementReviewMeetingList />);

    await waitFor(() => {
      expect(
        screen.getByText("No management review meetings recorded yet."),
      ).toBeInTheDocument();
    });
  });
});
