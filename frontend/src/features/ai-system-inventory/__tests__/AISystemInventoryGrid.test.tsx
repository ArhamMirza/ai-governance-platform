import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { httpClient } from "../../../shared/api/httpClient";
import { createTestQueryClient } from "../../../test/testQueryClient";
import type { SheetWithRows } from "../../sheets/types";
import { AISystemInventoryGrid } from "../components/AISystemInventoryGrid";

vi.mock("../../../shared/api/httpClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../shared/api/httpClient")>();
  return {
    ...actual,
    httpClient: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      postForm: vi.fn(),
    },
  };
});

const inventorySheet: SheetWithRows = {
  id: 1,
  entity_type: "AISystemInventory",
  title: "AI System Inventory",
  columns: [
    { key: "name", label: "Name", data_type: "text" },
    { key: "risk_tier", label: "Risk Tier", data_type: "text" },
    { key: "resource_documentation", label: "Resource Documentation", data_type: "text" },
    { key: "data_resources", label: "Data Resources", data_type: "text" },
  ],
  rows: [
    {
      id: 1,
      sheet_id: 1,
      row_index: 1,
      data: { name: "Resume Screener", risk_tier: "high" },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("AISystemInventoryGrid", () => {
  it("fetches and renders the inventory sheet via DataGrid", async () => {
    vi.mocked(httpClient.get).mockResolvedValue(inventorySheet);
    const queryClient = createTestQueryClient();

    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <AISystemInventoryGrid />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(httpClient.get).toHaveBeenCalledWith("/ai-system-inventory");
      expect(screen.getByLabelText("Name for row 1")).toHaveValue("Resume Screener");
    });
  });

  it("doesn't label the pinned name column with another view's group heading", async () => {
    vi.mocked(httpClient.get).mockResolvedValue(inventorySheet);
    const queryClient = createTestQueryClient();

    render(
      <MemoryRouter initialEntries={["/?view=resources"]}>
        <QueryClientProvider client={queryClient}>
          <AISystemInventoryGrid />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Name for row 1")).toBeInTheDocument();
    });

    // "name" is pinned into every view rather than belonging to any one of
    // them -- it must never carry "System Overview" (the "overview" view's
    // own group label) into a view that isn't Overview.
    expect(screen.queryByRole("columnheader", { name: "System Overview" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Resource Documentation (A.4.2 / A.4.3)" }),
    ).toBeInTheDocument();
  });
});
