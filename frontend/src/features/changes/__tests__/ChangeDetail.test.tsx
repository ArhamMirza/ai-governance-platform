import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { aiSystemInventory } from "../../suppliers/__tests__/fixtures";
import { useUserDirectory } from "../../users/hooks";
import { changesApi } from "../api";
import { ChangeDetail } from "../components/ChangeDetail";
import { makeChange } from "./fixtures";

vi.mock("../api");
vi.mock("../../ai-system-inventory/hooks");
vi.mock("../../users/hooks");
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: () => null,
}));
vi.mock("../../evidence/components/DocumentBrowser", () => ({ DocumentBrowser: () => null }));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));

function renderDetail() {
  vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: aiSystemInventory } as never);
  vi.mocked(useUserDirectory).mockReturnValue({ data: [] } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <ChangeDetail changeId={1} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ChangeDetail", () => {
  it("offers the moves a planned change can make, and starts it", async () => {
    vi.mocked(changesApi.get).mockResolvedValue(makeChange());
    vi.mocked(changesApi.setStatus).mockResolvedValue(makeChange());
    const user = userEvent.setup();
    renderDetail();

    expect(await screen.findByRole("button", { name: "Start" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark Implemented" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel Change" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reopen" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Start" }));
    // Starting isn't a closure, so no note goes with it.
    expect(changesApi.setStatus).toHaveBeenCalledWith(1, { action: "start", note: null });
  });

  it("keeps a note typed for closing out of the move that starts it", async () => {
    vi.mocked(changesApi.get).mockResolvedValue(makeChange());
    vi.mocked(changesApi.setStatus).mockResolvedValue(makeChange());
    const user = userEvent.setup();
    renderDetail();

    await user.type(await screen.findByLabelText("Note (recorded when closing)"), "For later");
    await user.click(screen.getByRole("button", { name: "Start" }));

    expect(changesApi.setStatus).toHaveBeenCalledWith(1, { action: "start", note: null });
  });

  it("can't be started again once it's in progress", async () => {
    vi.mocked(changesApi.get).mockResolvedValue(
      makeChange({ status: "in_progress", standing: { state: "in_progress", overdue: false } }),
    );
    renderDetail();

    expect(await screen.findByRole("button", { name: "Mark Implemented" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start" })).not.toBeInTheDocument();
  });

  it("records the note when closing it", async () => {
    vi.mocked(changesApi.get).mockResolvedValue(makeChange());
    vi.mocked(changesApi.setStatus).mockResolvedValue(makeChange());
    const user = userEvent.setup();
    renderDetail();

    await user.type(await screen.findByLabelText("Note (recorded when closing)"), "Rolled out");
    await user.click(screen.getByRole("button", { name: "Mark Implemented" }));

    expect(changesApi.setStatus).toHaveBeenCalledWith(1, {
      action: "implement",
      note: "Rolled out",
    });
  });

  it("only offers Reopen once closed, with no note field", async () => {
    vi.mocked(changesApi.get).mockResolvedValue(
      makeChange({
        status: "implemented",
        closed_on: "2026-07-20",
        closure_note: "Rolled out",
        standing: { state: "implemented", overdue: false },
      }),
    );
    renderDetail();

    expect(await screen.findByRole("button", { name: "Reopen" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark Implemented" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Note (recorded when closing)")).not.toBeInTheDocument();
    expect(screen.getByText(/closed 2026-07-20: Rolled out/)).toBeInTheDocument();
  });

  it("flags an overdue change", async () => {
    vi.mocked(changesApi.get).mockResolvedValue(
      makeChange({ standing: { state: "planned", overdue: true } }),
    );
    renderDetail();

    expect(await screen.findByText("Overdue")).toBeInTheDocument();
  });

  it("can only be deleted while still planned", async () => {
    vi.mocked(changesApi.get).mockResolvedValue(makeChange());
    const { unmount } = renderDetail();
    expect(await screen.findByRole("button", { name: "Delete Change" })).toBeInTheDocument();
    unmount();

    vi.mocked(changesApi.get).mockResolvedValue(
      makeChange({ status: "in_progress", standing: { state: "in_progress", overdue: false } }),
    );
    renderDetail();
    expect(await screen.findByText(/Cancel it instead of deleting it/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Change" })).not.toBeInTheDocument();
  });

  it("links an AI system and unlinks one by its own Remove button", async () => {
    vi.mocked(changesApi.get).mockResolvedValue(makeChange({ ai_system_row_ids: [7] }));
    vi.mocked(changesApi.setAISystems).mockResolvedValue(makeChange());
    const user = userEvent.setup();
    renderDetail();

    await user.selectOptions(await screen.findByLabelText("Add AI system"), "9");
    await user.click(screen.getByRole("button", { name: "Link" }));
    expect(changesApi.setAISystems).toHaveBeenLastCalledWith(1, [7, 9]);

    await user.click(screen.getByRole("button", { name: "Remove Resume Screener" }));
    expect(changesApi.setAISystems).toHaveBeenLastCalledWith(1, []);
  });
});
