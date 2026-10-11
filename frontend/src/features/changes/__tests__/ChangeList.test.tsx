import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { changesApi } from "../api";
import { AISystemChanges } from "../components/AISystemChanges";
import { ChangeList } from "../components/ChangeList";
import { ChangesAsOf } from "../components/ChangesAsOf";
import { makeChange } from "./fixtures";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ChangeList", () => {
  it("shows each change's status and flags only the overdue ones", async () => {
    vi.mocked(changesApi.list).mockResolvedValue([
      makeChange({ id: 1, title: "On time" }),
      makeChange({
        id: 2,
        title: "Late",
        standing: { state: "in_progress", overdue: true },
      }),
      makeChange({
        id: 3,
        title: "Done",
        status: "implemented",
        standing: { state: "implemented", overdue: false },
      }),
    ]);

    renderWithProviders(<ChangeList />);

    const rows = await screen.findAllByRole("row");
    const byTitle = (title: string) => rows.find((row) => row.textContent?.includes(title))!;
    expect(byTitle("On time")).not.toHaveClass("row-flagged");
    expect(byTitle("Late")).toHaveClass("row-flagged");
    expect(byTitle("Late")).toHaveTextContent("Overdue");
    expect(byTitle("Late")).toHaveTextContent("in progress");
    expect(byTitle("Done")).not.toHaveClass("row-flagged");
    expect(byTitle("Done")).toHaveTextContent("implemented");
  });

  it("shows an empty state", async () => {
    vi.mocked(changesApi.list).mockResolvedValue([]);

    renderWithProviders(<ChangeList />);

    expect(await screen.findByText("No planned changes yet.")).toBeInTheDocument();
  });
});

describe("AISystemChanges", () => {
  it("lists the changes affecting one AI system", async () => {
    vi.mocked(changesApi.list).mockResolvedValue([makeChange({ title: "Move the screener" })]);

    renderWithProviders(<AISystemChanges rowId={7} />);

    expect(await screen.findByRole("link", { name: "Move the screener" })).toHaveAttribute(
      "href",
      "/changes/1",
    );
    expect(changesApi.list).toHaveBeenCalledWith(7);
  });
});

describe("ChangesAsOf", () => {
  it("shows each change as it stood on the meeting's date", async () => {
    vi.mocked(changesApi.standingAsOf).mockResolvedValue([
      {
        id: 1,
        title: "Fairness gate",
        change_type: "process",
        owner_id: null,
        planned_date: "2026-08-01",
        standing: { state: "in_progress", overdue: true },
      },
    ]);

    renderWithProviders(<ChangesAsOf asOf="2026-09-13" />);

    expect(await screen.findByText("Fairness gate")).toBeInTheDocument();
    expect(screen.getByText("in progress")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    expect(screen.getByText("A process or control")).toBeInTheDocument();
    expect(changesApi.standingAsOf).toHaveBeenCalledWith("2026-09-13");
  });

  it("says when no change had been raised yet", async () => {
    vi.mocked(changesApi.standingAsOf).mockResolvedValue([]);

    renderWithProviders(<ChangesAsOf asOf="2025-01-01" />);

    expect(await screen.findByText("No changes had been raised by this date.")).toBeInTheDocument();
  });
});
