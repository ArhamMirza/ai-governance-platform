import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { incidentsApi } from "../api";
import { IncidentList } from "../components/IncidentList";
import { aiSystemInventory, makeIncident } from "./makeIncident";

vi.mock("../api");
vi.mock("../../ai-system-inventory/hooks");

function renderList() {
  vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: aiSystemInventory } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <IncidentList />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("IncidentList", () => {
  it("links each incident and names its AI system", async () => {
    vi.mocked(incidentsApi.list).mockResolvedValue([
      makeIncident({ id: 4, ai_system_row_id: 7 }),
    ]);

    renderList();

    expect(
      await screen.findByRole("link", { name: "Screener rejected older applicants" }),
    ).toHaveAttribute("href", "/incidents/4");
    expect(screen.getByText("Resume Screener")).toBeInTheDocument();
    expect(screen.queryByText("Serious")).not.toBeInTheDocument();
  });

  it("flags a serious incident whose report is overdue", async () => {
    vi.mocked(incidentsApi.list).mockResolvedValue([
      makeIncident({ is_serious: true, serious_category: "death", reporting_overdue: true }),
    ]);

    renderList();

    expect(await screen.findByText("Report overdue")).toBeInTheDocument();
    expect(screen.getByText("Serious")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    vi.mocked(incidentsApi.list).mockResolvedValue([]);

    renderList();

    expect(await screen.findByText("No incidents logged.")).toBeInTheDocument();
  });
});
