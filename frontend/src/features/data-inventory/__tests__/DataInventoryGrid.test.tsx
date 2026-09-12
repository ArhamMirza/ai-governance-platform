import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import type { SheetWithRows } from "../../sheets/types";
import { dataInventoryAdapter } from "../api";
import { DataInventoryGrid } from "../components/DataInventoryGrid";

vi.mock("../api");
vi.mock("../../ai-system-inventory/hooks");

const dataInventorySheet: SheetWithRows = {
  id: 1,
  entity_type: "DataInventory",
  title: "Data Inventory",
  columns: [
    { key: "dataset_name", label: "Dataset Name", data_type: "text" },
    { key: "ai_system_row_id", label: "AI System", data_type: "text" },
    { key: "approval_status", label: "Approval Status", data_type: "text" },
  ],
  rows: [
    {
      id: 5,
      sheet_id: 1,
      row_index: 1,
      data: {
        dataset_name: "Resume corpus",
        ai_system_row_id: "7",
        approval_status: "draft",
      },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const aiSystemInventory: SheetWithRows = {
  id: 2,
  entity_type: "AISystemInventory",
  title: "AI System Inventory",
  columns: [{ key: "name", label: "Name", data_type: "text" }],
  rows: [
    {
      id: 7,
      sheet_id: 2,
      row_index: 1,
      data: { name: "Resume Screener" },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderGrid() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <DataInventoryGrid />
    </QueryClientProvider>,
  );
}

describe("DataInventoryGrid", () => {
  it("shows the linked AI system's name as a select option", async () => {
    vi.mocked(dataInventoryAdapter.get).mockResolvedValue(dataInventorySheet);
    vi.mocked(useAISystemInventoryRows).mockReturnValue({
      data: aiSystemInventory,
    } as never);

    renderGrid();

    const select = await screen.findByLabelText("AI System for row 5");
    await waitFor(() => expect(select).toHaveValue("7"));
    expect(screen.getByText("Resume Screener")).toBeInTheDocument();
  });

  it("shows the review status without letting it be edited in the grid", async () => {
    vi.mocked(dataInventoryAdapter.get).mockResolvedValue(dataInventorySheet);
    vi.mocked(useAISystemInventoryRows).mockReturnValue({
      data: aiSystemInventory,
    } as never);

    renderGrid();

    expect(await screen.findByText("draft")).toBeInTheDocument();
    expect(screen.queryByLabelText("Approval Status for row 5")).not.toBeInTheDocument();
  });
});
