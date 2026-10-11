import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useUserDirectory } from "../../users/hooks";
import { communicationsApi } from "../api";
import { CommunicationDetail } from "../components/CommunicationDetail";
import { makeCommunicationDetail, makeRecord } from "./fixtures";

vi.mock("../api");
vi.mock("../../users/hooks");
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: () => null,
}));
vi.mock("../../evidence/components/DocumentBrowser", () => ({ DocumentBrowser: () => null }));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));

function renderDetail() {
  vi.mocked(useUserDirectory).mockReturnValue({ data: [] } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <CommunicationDetail communicationId={1} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CommunicationDetail", () => {
  it("shows how often, when it was last done and when it's next due", async () => {
    vi.mocked(communicationsApi.get).mockResolvedValue(
      makeCommunicationDetail({
        last_communicated_on: "2026-06-01",
        next_due: "2026-09-01",
        records: [makeRecord({ summary: "Presented the incidents" })],
      }),
    );

    renderDetail();

    expect(
      await screen.findByText("Every 3 months · last done 2026-06-01 · next due 2026-09-01"),
    ).toBeInTheDocument();
    expect(screen.getByText("2026-06-01: Presented the incidents")).toBeInTheDocument();
  });

  it("records that it was done", async () => {
    vi.mocked(communicationsApi.get).mockResolvedValue(makeCommunicationDetail());
    vi.mocked(communicationsApi.record).mockResolvedValue(makeRecord());
    const user = userEvent.setup();
    renderDetail();

    const date = await screen.findByLabelText("Done on");
    await user.clear(date);
    await user.type(date, "2026-06-01");
    await user.type(screen.getByLabelText("What was communicated"), "Board briefing");
    await user.click(screen.getByRole("button", { name: "Record Communication" }));

    expect(communicationsApi.record).toHaveBeenCalledWith(1, {
      communicated_on: "2026-06-01",
      summary: "Board briefing",
    });
  });

  it("deletes one record by its own dated button", async () => {
    vi.mocked(communicationsApi.get).mockResolvedValue(
      makeCommunicationDetail({
        records: [
          makeRecord({ id: 12, communicated_on: "2026-06-01" }),
          makeRecord({ id: 7, communicated_on: "2026-03-01" }),
        ],
      }),
    );
    vi.mocked(communicationsApi.removeRecord).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderDetail();

    await user.click(
      await screen.findByRole("button", { name: "Delete the record from 2026-03-01" }),
    );

    // The record's id, not the communication's.
    expect(communicationsApi.removeRecord).toHaveBeenCalledWith(7);
  });

  it("records it with no summary as null, not an empty string", async () => {
    vi.mocked(communicationsApi.get).mockResolvedValue(makeCommunicationDetail());
    vi.mocked(communicationsApi.record).mockResolvedValue(makeRecord());
    const user = userEvent.setup();
    renderDetail();

    const date = await screen.findByLabelText("Done on");
    await user.clear(date);
    await user.type(date, "2026-06-01");
    await user.click(screen.getByRole("button", { name: "Record Communication" }));

    expect(communicationsApi.record).toHaveBeenCalledWith(1, {
      communicated_on: "2026-06-01",
      summary: null,
    });
  });

  it("won't blank the topic or audience, but clears optional fields to null", async () => {
    vi.mocked(communicationsApi.get).mockResolvedValue(makeCommunicationDetail());
    vi.mocked(communicationsApi.update).mockResolvedValue(makeCommunicationDetail());
    const user = userEvent.setup();
    renderDetail();

    await user.clear(await screen.findByLabelText("What is communicated"));
    await user.tab();
    await user.clear(screen.getByLabelText("To whom"));
    await user.tab();
    expect(communicationsApi.update).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("How"));
    await user.tab();
    expect(communicationsApi.update).toHaveBeenCalledWith(1, { method: null });
  });

  it("flags an overdue communication", async () => {
    vi.mocked(communicationsApi.get).mockResolvedValue(
      makeCommunicationDetail({ overdue: true }),
    );

    renderDetail();

    expect(await screen.findByText("Overdue")).toBeInTheDocument();
  });

  it("saves the schedule only as a pair", async () => {
    vi.mocked(communicationsApi.get).mockResolvedValue(makeCommunicationDetail());
    vi.mocked(communicationsApi.update).mockResolvedValue(makeCommunicationDetail());
    const user = userEvent.setup();
    renderDetail();

    const interval = await screen.findByLabelText("Every (months)");
    await user.clear(interval);
    await user.type(interval, "6");
    expect(screen.getByRole("button", { name: "Save schedule" })).toBeEnabled();

    await user.clear(screen.getByLabelText("First due"));
    expect(screen.getByRole("button", { name: "Save schedule" })).toBeDisabled();
    expect(screen.getByText(/Set both, or clear both/)).toBeInTheDocument();

    await user.clear(interval);
    await user.click(screen.getByRole("button", { name: "Save schedule" }));
    expect(communicationsApi.update).toHaveBeenCalledWith(1, {
      interval_months: null,
      first_due: null,
    });
  });

  it("can be retired", async () => {
    vi.mocked(communicationsApi.get).mockResolvedValue(makeCommunicationDetail());
    vi.mocked(communicationsApi.update).mockResolvedValue(makeCommunicationDetail());
    const user = userEvent.setup();
    renderDetail();

    await user.selectOptions(await screen.findByLabelText("Status"), "retired");

    expect(communicationsApi.update).toHaveBeenCalledWith(1, { status: "retired" });
  });
});
