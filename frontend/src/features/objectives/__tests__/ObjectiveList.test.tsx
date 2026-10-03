import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { objectivesApi } from "../api";
import { AISystemObjectives } from "../components/AISystemObjectives";
import { ObjectiveList } from "../components/ObjectiveList";
import { ObjectivesAsOf } from "../components/ObjectivesAsOf";
import { makeObjective, makeStanding } from "./fixtures";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ObjectiveList", () => {
  it("shows each objective's standing and flags the ones needing attention", async () => {
    vi.mocked(objectivesApi.list).mockResolvedValue([
      makeObjective({
        id: 1,
        title: "Bias test pass rate",
        standing: makeStanding({ state: "on_track", latest_value: 96.5 }),
      }),
      makeObjective({
        id: 2,
        title: "Vendors assessed",
        standing: makeStanding({ state: "off_track", latest_value: 80 }),
      }),
      makeObjective({
        id: 3,
        title: "Incident closure",
        standing: makeStanding({ state: "not_measured", measurement_overdue: true }),
      }),
      makeObjective({
        id: 4,
        title: "Transparency notice",
        kind: "milestone",
        direction: null,
        target_value: null,
        standing: makeStanding({ state: "in_progress" }),
      }),
    ]);

    renderWithProviders(<ObjectiveList />);

    const rows = await screen.findAllByRole("row");
    const byTitle = (title: string) => rows.find((row) => row.textContent?.includes(title))!;
    expect(byTitle("Bias test pass rate")).not.toHaveClass("row-flagged");
    expect(byTitle("Bias test pass rate")).toHaveTextContent("96.5%");
    expect(byTitle("Vendors assessed")).toHaveClass("row-flagged");
    expect(byTitle("Incident closure")).toHaveClass("row-flagged");
    expect(byTitle("Incident closure")).toHaveTextContent("Measurement overdue");
    expect(byTitle("Transparency notice")).toHaveTextContent("Milestone");
    expect(byTitle("Transparency notice")).not.toHaveClass("row-flagged");
  });

  it("shows an empty state", async () => {
    vi.mocked(objectivesApi.list).mockResolvedValue([]);

    renderWithProviders(<ObjectiveList />);

    expect(await screen.findByText("No AI objectives yet.")).toBeInTheDocument();
  });
});

describe("AISystemObjectives", () => {
  it("lists the objectives linked to one AI system", async () => {
    vi.mocked(objectivesApi.list).mockResolvedValue([
      makeObjective({ title: "Bias test pass rate", standing: makeStanding({ state: "on_track" }) }),
    ]);

    renderWithProviders(<AISystemObjectives rowId={7} />);

    expect(await screen.findByRole("link", { name: "Bias test pass rate" })).toHaveAttribute(
      "href",
      "/objectives/1",
    );
    expect(screen.getByText("on track")).toBeInTheDocument();
    expect(objectivesApi.list).toHaveBeenCalledWith(7);
  });
});

describe("ObjectivesAsOf", () => {
  it("shows each objective as it stood on the meeting's date", async () => {
    vi.mocked(objectivesApi.standingAsOf).mockResolvedValue([
      {
        id: 1,
        title: "Bias test pass rate",
        kind: "measured",
        metric_name: "Pass rate",
        unit: "%",
        direction: "at_least",
        target_value: 95,
        target_date: "2026-12-31",
        owner_id: null,
        standing: makeStanding({
          state: "off_track",
          latest_value: 93,
          latest_on: "2026-08-14",
        }),
      },
    ]);

    renderWithProviders(<ObjectivesAsOf asOf="2026-09-13" />);

    expect(await screen.findByText("93% (2026-08-14)")).toBeInTheDocument();
    expect(screen.getByText("off track")).toBeInTheDocument();
    expect(screen.getByText("≥ 95%")).toBeInTheDocument();
    expect(objectivesApi.standingAsOf).toHaveBeenCalledWith("2026-09-13");
  });

  it("says when no objective had been set yet", async () => {
    vi.mocked(objectivesApi.standingAsOf).mockResolvedValue([]);

    renderWithProviders(<ObjectivesAsOf asOf="2025-01-01" />);

    expect(
      await screen.findByText("No AI objectives had been set by this date."),
    ).toBeInTheDocument();
  });
});
