import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { usePolicies } from "../../policies/hooks";
import { aiSystemInventory } from "../../suppliers/__tests__/fixtures";
import { useUserDirectory } from "../../users/hooks";
import { objectivesApi } from "../api";
import { ObjectiveDetail } from "../components/ObjectiveDetail";
import { makeMeasurement, makeObjectiveDetail, makeStanding } from "./fixtures";

vi.mock("../api");
vi.mock("../../ai-system-inventory/hooks");
vi.mock("../../users/hooks");
vi.mock("../../policies/hooks");
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: () => null,
}));
vi.mock("../../evidence/components/DocumentBrowser", () => ({ DocumentBrowser: () => null }));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));

function renderDetail() {
  vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: aiSystemInventory } as never);
  vi.mocked(useUserDirectory).mockReturnValue({ data: [] } as never);
  vi.mocked(usePolicies).mockReturnValue({ data: [] } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <ObjectiveDetail objectiveId={1} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ObjectiveDetail", () => {
  it("shows where it stands and charts the readings against the target", async () => {
    vi.mocked(objectivesApi.get).mockResolvedValue(
      makeObjectiveDetail({
        standing: makeStanding({
          state: "on_track",
          latest_value: 96.5,
          latest_on: "2026-06-01",
          next_measurement_due: "2026-09-01",
        }),
        measurements: [
          makeMeasurement({ id: 3, measured_on: "2026-06-01", value: 96.5 }),
          makeMeasurement({ id: 2, measured_on: "2026-04-15", value: 95 }),
          makeMeasurement({ id: 1, measured_on: "2026-03-01", value: 90 }),
        ],
      }),
    );

    const { container } = renderDetail();

    expect(
      await screen.findByText(
        "Latest 96.5% on 2026-06-01 · target ≥ 95% by 2026-12-31 · next reading due 2026-09-01",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Readings against the target of ≥ 95%" })).toBeVisible();
    const dots = container.querySelectorAll(".objective-chart-dot");
    // Oldest first: 90 missed the target, exactly 95 met it, 96.5 met it.
    expect([...dots].map((dot) => dot.getAttribute("data-meets"))).toEqual([
      "false",
      "true",
      "true",
    ]);
  });

  it("records a reading", async () => {
    vi.mocked(objectivesApi.get).mockResolvedValue(makeObjectiveDetail());
    vi.mocked(objectivesApi.recordMeasurement).mockResolvedValue(makeMeasurement());
    const user = userEvent.setup();

    renderDetail();

    const date = await screen.findByLabelText("Measured on");
    await user.clear(date);
    await user.type(date, "2026-03-01");
    await user.type(screen.getByLabelText("Value"), "91.5");
    await user.type(screen.getByLabelText("Note"), "First run");
    await user.click(screen.getByRole("button", { name: "Record Reading" }));

    expect(objectivesApi.recordMeasurement).toHaveBeenCalledWith(1, {
      measured_on: "2026-03-01",
      value: 91.5,
      note: "First run",
    });
  });

  it("closes an objective with the reason", async () => {
    vi.mocked(objectivesApi.get).mockResolvedValue(makeObjectiveDetail());
    vi.mocked(objectivesApi.close).mockResolvedValue(makeObjectiveDetail());
    const user = userEvent.setup();

    renderDetail();

    await user.selectOptions(await screen.findByLabelText("Close as"), "withdrawn");
    await user.type(screen.getByLabelText("Why"), "Replaced by a broader objective");
    await user.click(screen.getByRole("button", { name: "Close Objective" }));

    expect(objectivesApi.close).toHaveBeenCalledWith(1, {
      status: "withdrawn",
      closure_note: "Replaced by a broader objective",
    });
  });

  it("takes no readings once closed, and can be reopened", async () => {
    vi.mocked(objectivesApi.get).mockResolvedValue(
      makeObjectiveDetail({
        status: "achieved",
        closed_on: "2026-06-30",
        closure_note: "Target held for two quarters",
        standing: makeStanding({ state: "achieved" }),
      }),
    );
    vi.mocked(objectivesApi.reopen).mockResolvedValue(makeObjectiveDetail());
    const user = userEvent.setup();

    renderDetail();

    expect(
      await screen.findByText("Closed as achieved on 2026-06-30: Target held for two quarters"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record Reading" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reopen Objective" }));
    expect(objectivesApi.reopen).toHaveBeenCalledWith(1);
  });

  it("can't be deleted once it has readings", async () => {
    vi.mocked(objectivesApi.get).mockResolvedValue(
      makeObjectiveDetail({ measurements: [makeMeasurement()] }),
    );

    renderDetail();

    expect(await screen.findByText(/close it as withdrawn instead/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Objective" })).not.toBeInTheDocument();
  });

  it("has no measurement section for a milestone", async () => {
    vi.mocked(objectivesApi.get).mockResolvedValue(
      makeObjectiveDetail({
        kind: "milestone",
        metric_name: null,
        unit: null,
        direction: null,
        target_value: null,
        standing: makeStanding({ state: "in_progress" }),
      }),
    );

    renderDetail();

    expect(await screen.findByText("Due by 2026-12-31.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record Reading" })).not.toBeInTheDocument();
  });

  it("links an AI system and unlinks one by its own Remove button", async () => {
    vi.mocked(objectivesApi.get).mockResolvedValue(
      makeObjectiveDetail({ ai_system_row_ids: [7] }),
    );
    vi.mocked(objectivesApi.setAISystems).mockResolvedValue(makeObjectiveDetail());
    const user = userEvent.setup();

    renderDetail();

    await user.selectOptions(await screen.findByLabelText("Add AI system"), "9");
    await user.click(screen.getByRole("button", { name: "Link" }));
    expect(objectivesApi.setAISystems).toHaveBeenLastCalledWith(1, [7, 9]);

    await user.click(screen.getByRole("button", { name: "Remove Resume Screener" }));
    expect(objectivesApi.setAISystems).toHaveBeenLastCalledWith(1, []);
  });
});
