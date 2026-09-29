import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useUserDirectory } from "../../users/hooks";
import { suppliersApi } from "../api";
import { SupplierDetail } from "../components/SupplierDetail";
import { aiSystemInventory, makeSupplierDetail } from "./fixtures";

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
        <SupplierDetail supplierId={1} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SupplierDetail", () => {
  it("links an AI system by adding it to the existing set", async () => {
    vi.mocked(suppliersApi.get).mockResolvedValue(makeSupplierDetail({ ai_system_row_ids: [7] }));
    vi.mocked(suppliersApi.setAISystems).mockResolvedValue(makeSupplierDetail());
    const user = userEvent.setup();

    renderDetail();

    expect(await screen.findByRole("checkbox", { name: "Resume Screener" })).toBeChecked();
    await user.click(screen.getByRole("checkbox", { name: "Fraud Model" }));

    expect(suppliersApi.setAISystems).toHaveBeenCalledWith(1, [7, 9]);
  });

  it("records a review with its outcome", async () => {
    vi.mocked(suppliersApi.get).mockResolvedValue(makeSupplierDetail());
    vi.mocked(suppliersApi.recordReview).mockResolvedValue({} as never);
    const user = userEvent.setup();

    renderDetail();

    const date = await screen.findByLabelText("Review date");
    await user.clear(date);
    await user.type(date, "2026-05-01");
    await user.selectOptions(screen.getByLabelText("Outcome"), "concerns");
    await user.type(screen.getByLabelText("Notes"), "No SOC 2 yet");
    await user.click(screen.getByRole("button", { name: "Record Review" }));

    expect(suppliersApi.recordReview).toHaveBeenCalledWith(1, {
      review_date: "2026-05-01",
      outcome: "concerns",
      notes: "No SOC 2 yet",
    });
  });

  it("won't save a review schedule with only one half set", async () => {
    vi.mocked(suppliersApi.get).mockResolvedValue(makeSupplierDetail());
    const user = userEvent.setup();

    renderDetail();

    await user.type(await screen.findByLabelText("Review every (months)"), "12");

    expect(screen.getByRole("button", { name: "Save schedule" })).toBeDisabled();
    expect(screen.getByText("Set both, or clear both for no reviews.")).toBeInTheDocument();
  });
});
