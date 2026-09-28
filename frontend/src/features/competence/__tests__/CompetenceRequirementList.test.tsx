import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useGovernanceRoles } from "../../governance-roles/hooks";
import { competenceApi } from "../api";
import { CompetenceRequirementList } from "../components/CompetenceRequirementList";
import { makeSummary } from "./fixtures";

vi.mock("../api");
vi.mock("../../governance-roles/hooks");

function renderList() {
  vi.mocked(useGovernanceRoles).mockReturnValue({
    data: [{ id: 3, name: "AI System Owner" }],
  } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <CompetenceRequirementList />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CompetenceRequirementList", () => {
  it("shows who a requirement applies to, how often, and how many are competent", async () => {
    vi.mocked(competenceApi.list).mockResolvedValue([
      makeSummary({
        id: 4,
        governance_role_id: 3,
        refresh_interval_months: 12,
        required_count: 5,
        current_count: 3,
        gap_count: 2,
      }),
      makeSummary({ id: 5, title: "AI policy awareness", required_count: 2, current_count: 2 }),
    ]);

    renderList();

    expect(await screen.findByRole("link", { name: "Bias testing fundamentals" })).toHaveAttribute(
      "href",
      "/competence/4",
    );
    expect(screen.getByText("AI System Owner")).toBeInTheDocument();
    expect(screen.getByText("Every 12 months")).toBeInTheDocument();
    expect(screen.getByText("2 outstanding")).toBeInTheDocument();
    expect(screen.getByText("Everyone")).toBeInTheDocument();
    expect(screen.getByText("Once")).toBeInTheDocument();
    expect(screen.getAllByText("outstanding", { exact: false })).toHaveLength(1);
  });

  it("shows an empty state", async () => {
    vi.mocked(competenceApi.list).mockResolvedValue([]);

    renderList();

    expect(await screen.findByText("No competence requirements yet.")).toBeInTheDocument();
  });
});
