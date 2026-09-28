import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { frameworkTagsApi } from "../../framework-tags/api";
import { incidentsApi } from "../api";
import { IncidentDetail } from "../components/IncidentDetail";
import { aiSystemInventory, makeIncident } from "./makeIncident";

vi.mock("../api");
vi.mock("../../ai-system-inventory/hooks");
vi.mock("../../framework-tags/api");
vi.mock("../../evidence/components/DocumentBrowser", () => ({ DocumentBrowser: () => null }));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));

function renderDetail() {
  vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: aiSystemInventory } as never);
  vi.mocked(frameworkTagsApi.get).mockResolvedValue([]);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <IncidentDetail incidentId={1} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("IncidentDetail", () => {
  it("hides the Art. 73 fields until the incident is marked serious", async () => {
    vi.mocked(incidentsApi.get).mockResolvedValue(makeIncident());

    renderDetail();

    expect(await screen.findByText(/must be reported to the authority/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Kind of serious incident")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Authority notified on")).not.toBeInTheDocument();
  });

  it("shows the reporting deadline for a serious incident", async () => {
    vi.mocked(incidentsApi.get).mockResolvedValue(
      makeIncident({
        is_serious: true,
        serious_category: "death",
        reporting_deadline: "2026-03-11",
      }),
    );

    renderDetail();

    expect(await screen.findByText("2026-03-11")).toBeInTheDocument();
    expect(screen.getByLabelText("Kind of serious incident")).toHaveValue("death");
    expect(screen.getByLabelText("Authority notified on")).toBeInTheDocument();
  });

  it("marks an incident serious with a default category", async () => {
    vi.mocked(incidentsApi.get).mockResolvedValue(makeIncident());
    vi.mocked(incidentsApi.update).mockResolvedValue(makeIncident({ is_serious: true }));
    const user = userEvent.setup();

    renderDetail();
    await user.click(await screen.findByRole("checkbox"));

    expect(incidentsApi.update).toHaveBeenCalledWith(1, {
      is_serious: true,
      serious_category: "other",
    });
  });

  it("links corrective actions raised from it", async () => {
    vi.mocked(incidentsApi.get).mockResolvedValue(makeIncident({ corrective_action_ids: [12] }));

    renderDetail();

    expect(
      await screen.findByRole("link", { name: "Corrective action #12" }),
    ).toHaveAttribute("href", "/corrective-actions/12");
  });
});
