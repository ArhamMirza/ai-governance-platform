import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useGovernanceRoles } from "../../governance-roles/hooks";
import { useUserDirectory } from "../../users/hooks";
import { competenceApi } from "../api";
import { CompetenceRequirementDetail } from "../components/CompetenceRequirementDetail";
import { makeRequirement } from "./fixtures";

vi.mock("../api");
vi.mock("../../governance-roles/hooks");
vi.mock("../../users/hooks");
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: () => null,
}));
vi.mock("../../evidence/components/DocumentBrowser", () => ({ DocumentBrowser: () => null }));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));

function renderDetail() {
  vi.mocked(useGovernanceRoles).mockReturnValue({ data: [] } as never);
  vi.mocked(useUserDirectory).mockReturnValue({
    data: [
      { id: 7, name: "Jordan Lee", governance_roles: [] },
      { id: 8, name: "Sam Rivera", governance_roles: [] },
    ],
  } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <CompetenceRequirementDetail requirementId={1} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CompetenceRequirementDetail", () => {
  it("shows each required person's standing", async () => {
    vi.mocked(competenceApi.get).mockResolvedValue(
      makeRequirement({
        refresh_interval_months: 12,
        required_count: 2,
        current_count: 1,
        gap_count: 1,
        people: [
          {
            user_id: 7,
            status: "current",
            last_completed_on: "2026-03-01",
            next_due: "2027-03-01",
          },
          { user_id: 8, status: "missing", last_completed_on: null, next_due: null },
        ],
      }),
    );

    renderDetail();

    const jordan = (await screen.findByText("Jordan Lee")).closest("tr")!;
    expect(within(jordan).getByText("2027-03-01")).toBeInTheDocument();
    const sam = screen.getByText("Sam Rivera").closest("tr")!;
    expect(sam).toHaveClass("row-flagged");
    expect(screen.getByText("1 of 2 people competent · Every 12 months")).toBeInTheDocument();
  });

  it("records a completion for a person", async () => {
    vi.mocked(competenceApi.get).mockResolvedValue(
      makeRequirement({
        required_count: 1,
        gap_count: 1,
        people: [{ user_id: 8, status: "missing", last_completed_on: null, next_due: null }],
      }),
    );
    vi.mocked(competenceApi.recordCompletion).mockResolvedValue({} as never);
    const user = userEvent.setup();

    renderDetail();
    const dateInput = await screen.findByLabelText("Completed on for Sam Rivera");
    await user.clear(dateInput);
    await user.type(dateInput, "2026-02-01");
    await user.click(screen.getByRole("button", { name: "Record completion" }));

    expect(competenceApi.recordCompletion).toHaveBeenCalledWith(1, {
      user_id: 8,
      completed_on: "2026-02-01",
    });
  });

  it("explains when nobody is required", async () => {
    vi.mocked(competenceApi.get).mockResolvedValue(makeRequirement());

    renderDetail();

    expect(await screen.findByText(/Nobody is required yet/)).toBeInTheDocument();
  });
});
