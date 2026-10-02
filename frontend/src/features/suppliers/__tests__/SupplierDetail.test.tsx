import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useUserDirectory } from "../../users/hooks";
import { suppliersApi } from "../api";
import { SupplierDetail } from "../components/SupplierDetail";
import type { SupplierAISystemLink } from "../types";
import { aiSystemInventory, makeSupplierDetail } from "./fixtures";

function link(rowId: number, overrides: Partial<SupplierAISystemLink> = {}): SupplierAISystemLink {
  return {
    ai_system_row_id: rowId,
    supplier_role: null,
    rebranded: false,
    substantially_modified: false,
    repurposed_to_high_risk: false,
    art25_triggered: false,
    ...overrides,
  };
}

vi.mock("../api");
vi.mock("../../ai-system-inventory/hooks");
vi.mock("../../users/hooks");
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: () => null,
}));
vi.mock("../../evidence/components/DocumentBrowser", () => ({ DocumentBrowser: () => null }));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));

function renderDetail() {
  if (!vi.mocked(suppliersApi.listRiskItems).getMockImplementation()) {
    vi.mocked(suppliersApi.listRiskItems).mockResolvedValue([]);
  }
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
  it("links another AI system by adding it to the existing set", async () => {
    vi.mocked(suppliersApi.get).mockResolvedValue(
      makeSupplierDetail({ ai_system_row_ids: [7], ai_system_links: [link(7)] }),
    );
    vi.mocked(suppliersApi.setAISystems).mockResolvedValue(makeSupplierDetail());
    const user = userEvent.setup();

    renderDetail();

    // Already-linked systems aren't offered again.
    const add = await screen.findByLabelText("Add AI system");
    expect(within(add).queryByRole("option", { name: "Resume Screener" })).not.toBeInTheDocument();
    await user.selectOptions(add, "9");
    await user.click(screen.getByRole("button", { name: "Link" }));

    expect(suppliersApi.setAISystems).toHaveBeenCalledWith(1, [7, 9]);
  });

  it("records the supplier's role and an Art. 25 trigger for a system", async () => {
    vi.mocked(suppliersApi.get).mockResolvedValue(
      makeSupplierDetail({ ai_system_row_ids: [7], ai_system_links: [link(7)] }),
    );
    vi.mocked(suppliersApi.updateAISystemLink).mockResolvedValue(makeSupplierDetail());
    const user = userEvent.setup();

    renderDetail();

    await user.selectOptions(
      await screen.findByLabelText("Supplier's role for Resume Screener"),
      "provider",
    );
    expect(suppliersApi.updateAISystemLink).toHaveBeenLastCalledWith(1, 7, {
      supplier_role: "provider",
      rebranded: false,
      substantially_modified: false,
      repurposed_to_high_risk: false,
    });

    await user.click(screen.getByRole("checkbox", { name: "We substantially modified it" }));
    expect(suppliersApi.updateAISystemLink).toHaveBeenLastCalledWith(1, 7, {
      supplier_role: null,
      rebranded: false,
      substantially_modified: true,
      repurposed_to_high_risk: false,
    });
  });

  it("warns when the organization may have become the provider", async () => {
    vi.mocked(suppliersApi.get).mockResolvedValue(
      makeSupplierDetail({
        ai_system_row_ids: [7],
        ai_system_links: [link(7, { rebranded: true, art25_triggered: true })],
      }),
    );

    renderDetail();

    expect(await screen.findByText(/may be this system's provider/)).toBeInTheDocument();
  });

  it("lists the risk items naming the supplier", async () => {
    vi.mocked(suppliersApi.get).mockResolvedValue(makeSupplierDetail());
    vi.mocked(suppliersApi.listRiskItems).mockResolvedValue([
      {
        risk_assessment_id: 3,
        row_id: 41,
        ai_system_row_id: 7,
        category: "Third party",
        description: "Model swapped without notice",
        status: "open",
      },
    ]);

    renderDetail();

    expect(await screen.findByRole("link", { name: "Third party" })).toHaveAttribute(
      "href",
      "/risk-assessments/3",
    );
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
