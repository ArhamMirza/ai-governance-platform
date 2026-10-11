import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { communicationsApi } from "../api";
import { CommunicationList } from "../components/CommunicationList";
import { makeCommunication } from "./fixtures";

vi.mock("../api");

function renderList() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <CommunicationList />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CommunicationList", () => {
  it("shows cadence, last done and next due, and flags only the overdue ones", async () => {
    vi.mocked(communicationsApi.list).mockResolvedValue([
      makeCommunication({
        id: 1,
        topic: "Up to date",
        last_communicated_on: "2026-06-01",
        next_due: "2026-09-01",
      }),
      makeCommunication({ id: 2, topic: "Lapsed", overdue: true, interval_months: 12 }),
      makeCommunication({
        id: 3,
        topic: "On an incident",
        interval_months: null,
        first_due: null,
        next_due: null,
        direction: "external",
      }),
      makeCommunication({ id: 4, topic: "Digest", interval_months: 1 }),
    ]);

    renderList();

    const rows = await screen.findAllByRole("row");
    const byTopic = (topic: string) => rows.find((row) => row.textContent?.includes(topic))!;
    expect(byTopic("Up to date")).not.toHaveClass("row-flagged");
    expect(byTopic("Up to date")).toHaveTextContent("Every 3 months");
    expect(byTopic("Up to date")).toHaveTextContent("2026-06-01");
    expect(byTopic("Lapsed")).toHaveClass("row-flagged");
    expect(byTopic("Lapsed")).toHaveTextContent("Overdue");
    expect(byTopic("Lapsed")).toHaveTextContent("Every 12 months");
    expect(byTopic("On an incident")).not.toHaveClass("row-flagged");
    expect(byTopic("On an incident")).toHaveTextContent("When needed");
    expect(byTopic("On an incident")).toHaveTextContent("External");
    expect(byTopic("Digest")).toHaveTextContent("Monthly");
    expect(byTopic("Digest")).not.toHaveTextContent("Every 1 months");
  });

  it("marks a retired communication", async () => {
    vi.mocked(communicationsApi.list).mockResolvedValue([
      makeCommunication({ topic: "Old briefing", status: "retired" }),
    ]);

    renderList();

    expect(await screen.findByText("retired")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    vi.mocked(communicationsApi.list).mockResolvedValue([]);

    renderList();

    expect(await screen.findByText("Nothing planned yet.")).toBeInTheDocument();
  });
});
