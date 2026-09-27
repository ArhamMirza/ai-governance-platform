import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { DataGrid } from "../components/DataGrid";
import type { SheetApiAdapter, SheetWithRows } from "../types";

const baseSheet: SheetWithRows = {
  id: 1,
  entity_type: "RiskAssessment",
  title: "Risk Items",
  columns: [
    { key: "category", label: "Category", data_type: "text" },
    { key: "likelihood", label: "Likelihood", data_type: "number" },
    { key: "inherent_risk_score", label: "Inherent Risk Score", data_type: "number" },
  ],
  rows: [
    {
      id: 10,
      sheet_id: 1,
      row_index: 1,
      data: { category: "Bias", likelihood: 3, inherent_risk_score: 12 },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function makeAdapter(overrides: Partial<SheetApiAdapter> = {}): SheetApiAdapter {
  return {
    get: vi.fn().mockResolvedValue(baseSheet),
    setColumns: vi.fn().mockResolvedValue(baseSheet),
    addRow: vi.fn().mockResolvedValue(baseSheet.rows[0]),
    updateRow: vi.fn().mockResolvedValue(baseSheet.rows[0]),
    deleteRow: vi.fn().mockResolvedValue(undefined),
    upload: vi.fn().mockResolvedValue(baseSheet),
    exportUrl: vi.fn().mockReturnValue("http://localhost:8000/api/v1/export"),
    ...overrides,
  };
}

function renderGrid(
  adapter: SheetApiAdapter,
  readOnlyColumnKeys?: string[],
  visibleColumnKeys?: string[],
) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <DataGrid
        queryKey={["test-sheet"]}
        adapter={adapter}
        readOnlyColumnKeys={readOnlyColumnKeys}
        visibleColumnKeys={visibleColumnKeys}
      />
    </QueryClientProvider>,
  );
}

describe("DataGrid", () => {
  it("renders columns and row data", async () => {
    renderGrid(makeAdapter());

    await waitFor(() => {
      expect(screen.getByText("Category")).toBeInTheDocument();
      expect(screen.getByLabelText("Category for row 10")).toHaveValue("Bias");
    });
  });

  it("renders read-only columns as plain text, not editable inputs", async () => {
    renderGrid(makeAdapter(), ["inherent_risk_score"]);

    await waitFor(() => {
      expect(screen.getByText("12")).toBeInTheDocument();
    });
    expect(
      screen.queryByLabelText("Remove Inherent Risk Score"),
    ).not.toBeInTheDocument();
  });

  it("updates a cell on blur", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    renderGrid(adapter);

    const input = await screen.findByLabelText("Category for row 10");
    await user.clear(input);
    await user.type(input, "Privacy");
    await user.tab();

    await waitFor(() => {
      expect(adapter.updateRow).toHaveBeenCalledWith(10, { category: "Privacy" });
    });
  });

  it("adds a new column", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    renderGrid(adapter);

    await screen.findByText("Category");
    await user.type(screen.getByLabelText("New column key"), "impact");
    await user.type(screen.getByLabelText("New column label"), "Impact");
    await user.click(screen.getByRole("button", { name: "Add Column" }));

    await waitFor(() => {
      expect(adapter.setColumns).toHaveBeenCalledWith([
        ...baseSheet.columns,
        { key: "impact", label: "Impact", data_type: "text" },
      ]);
    });
  });

  it("removes a column", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    renderGrid(adapter);

    await user.click(await screen.findByLabelText("Remove Category"));

    await waitFor(() => {
      expect(adapter.setColumns).toHaveBeenCalledWith([
        baseSheet.columns[1],
        baseSheet.columns[2],
      ]);
    });
  });

  it("shows an error when removing a reserved column is rejected", async () => {
    const adapter = makeAdapter({
      setColumns: vi.fn().mockRejectedValue(new ApiError(400, "Cannot remove reserved column")),
    });
    const user = userEvent.setup();
    renderGrid(adapter);

    await user.click(await screen.findByLabelText("Remove Category"));

    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot remove reserved column");
  });

  it("adds a new row from the draft inputs", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    renderGrid(adapter);

    await user.type(await screen.findByLabelText("New row Category"), "Privacy");
    await user.click(screen.getByRole("button", { name: "Add Row" }));

    await waitFor(() => {
      expect(adapter.addRow).toHaveBeenCalledWith({ category: "Privacy" });
    });
  });

  it("never submits a value typed for a column that's no longer visible", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();
    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          visibleColumnKeys={["category", "likelihood"]}
        />
      </QueryClientProvider>,
    );

    // Type into "category" while it's visible (e.g. the "Overview" view),
    // then switch to a view where it's no longer shown -- the same prop
    // change AISystemInventoryGrid makes when someone clicks a different
    // view tab, without ever submitting in between.
    await user.type(await screen.findByLabelText("New row Category"), "Privacy");
    rerender(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          visibleColumnKeys={["likelihood", "inherent_risk_score"]}
        />
      </QueryClientProvider>,
    );

    expect(screen.queryByLabelText("New row Category")).not.toBeInTheDocument();
    await user.type(await screen.findByLabelText("New row Likelihood"), "3");
    await user.click(screen.getByRole("button", { name: "Add Row" }));

    await waitFor(() => {
      expect(adapter.addRow).toHaveBeenCalledWith({ likelihood: "3" });
    });
  });

  it("deletes a row", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    renderGrid(adapter);

    await user.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(adapter.deleteRow).toHaveBeenCalledWith(10);
    });
  });

  it("uploads a file", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    renderGrid(adapter);

    const file = new File(["a,b\n1,2"], "sheet.csv", { type: "text/csv" });
    await user.upload(await screen.findByLabelText("Upload sheet"), file);

    await waitFor(() => {
      expect(adapter.upload).toHaveBeenCalledWith(file);
    });
  });

  it("renders an export link using the adapter's export URL", async () => {
    renderGrid(makeAdapter());

    const link = await screen.findByRole("link", { name: "Export" });
    expect(link).toHaveAttribute("href", "http://localhost:8000/api/v1/export");
  });

  it("shows the flagged label for rows the caller flags", async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={makeAdapter()}
          isRowFlagged={(row) => row.id === 10}
          flaggedLabel="Overdue"
        />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Overdue")).toBeInTheDocument();
  });

  it("does not show a flagged label when isRowFlagged is omitted", async () => {
    renderGrid(makeAdapter());

    await screen.findByLabelText("Category for row 10");
    expect(screen.queryByText("Overdue")).not.toBeInTheDocument();
  });

  it("renders a mapped column as a select and updates on change", async () => {
    const adapter = makeAdapter({
      get: vi.fn().mockResolvedValue({
        ...baseSheet,
        columns: [...baseSheet.columns, { key: "risk_owner", label: "Owner", data_type: "text" }],
        rows: [{ ...baseSheet.rows[0], data: { ...baseSheet.rows[0].data, risk_owner: "2" } }],
      }),
    });
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          selectOptions={{
            risk_owner: [
              { value: "1", label: "Ada" },
              { value: "2", label: "Bob" },
            ],
          }}
        />
      </QueryClientProvider>,
    );

    const select = await screen.findByLabelText("Owner for row 10");
    expect(select).toHaveValue("2");

    await user.selectOptions(select, "1");

    await waitFor(() => {
      expect(adapter.updateRow).toHaveBeenCalledWith(10, { risk_owner: "1" });
    });
  });

  it("shows an unrecognized-value option rather than silently reassigning it", async () => {
    const adapter = makeAdapter({
      get: vi.fn().mockResolvedValue({
        ...baseSheet,
        columns: [...baseSheet.columns, { key: "risk_owner", label: "Owner", data_type: "text" }],
        rows: [{ ...baseSheet.rows[0], data: { ...baseSheet.rows[0].data, risk_owner: "ML Team" } }],
      }),
    });
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          selectOptions={{ risk_owner: [{ value: "1", label: "Ada" }] }}
        />
      </QueryClientProvider>,
    );

    const select = await screen.findByLabelText("Owner for row 10");
    expect(select).toHaveValue("ML Team");
    expect(screen.getByText("ML Team (unrecognized)")).toBeInTheDocument();
  });

  it("renders a long-text column as a wrapping textarea, not a truncating input", async () => {
    const adapter = makeAdapter();
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          longTextColumnKeys={["category"]}
        />
      </QueryClientProvider>,
    );

    const cell = await screen.findByLabelText("Category for row 10");
    expect(cell.tagName).toBe("TEXTAREA");
    expect(cell).toHaveValue("Bias");
  });

  it("saves an edited long-text cell on blur", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          longTextColumnKeys={["category"]}
        />
      </QueryClientProvider>,
    );

    const cell = await screen.findByLabelText("Category for row 10");
    await user.clear(cell);
    await user.type(cell, "A much longer sentence about the risk.");
    await user.tab();

    await waitFor(() => {
      expect(adapter.updateRow).toHaveBeenCalledWith(10, {
        category: "A much longer sentence about the risk.",
      });
    });
  });

  it("keeps columns not listed as long text as plain inputs", async () => {
    const adapter = makeAdapter();
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          longTextColumnKeys={["category"]}
        />
      </QueryClientProvider>,
    );

    const other = await screen.findByLabelText("Likelihood for row 10");
    expect(other.tagName).toBe("INPUT");
  });

  it("renders caller-provided row actions", async () => {
    renderGridWithRowActions(makeAdapter());

    expect(await screen.findByRole("button", { name: "Manage row 10" })).toBeInTheDocument();
  });

  it("renders a group header row spanning the columns in each group", async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={makeAdapter()}
          columnGroups={[
            { label: "Risk Details", keys: ["category", "likelihood"] },
          ]}
        />
      </QueryClientProvider>,
    );

    const groupHeader = await screen.findByText("Risk Details");
    expect(groupHeader.tagName).toBe("TH");
    expect(groupHeader).toHaveAttribute("colspan", "2");
  });

  it("gives an ungrouped column its own blank header cell, not swallowed into a group", async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={makeAdapter()}
          columnGroups={[{ label: "Risk Details", keys: ["category", "likelihood"] }]}
        />
      </QueryClientProvider>,
    );

    await screen.findByText("Risk Details");
    const groupRow = document.querySelector(".data-grid-group-row");
    // 3 columns total, 2 grouped under "Risk Details" (colSpan 2) + 1
    // ungrouped ("inherent_risk_score") + the trailing blank Actions cell.
    expect(groupRow?.querySelectorAll("th")).toHaveLength(3);
  });

  it("deletes immediately when no confirmation is required", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    renderGrid(adapter);

    await user.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() => expect(adapter.deleteRow).toHaveBeenCalledWith(10));
  });

  it("asks for confirmation before deleting when confirmDelete is given", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          confirmDelete={(row) => `Row ${row.id} and everything under it.`}
        />
      </QueryClientProvider>,
    );

    await user.click(await screen.findByRole("button", { name: "Delete" }));

    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(screen.getByText("Row 10 and everything under it.")).toBeInTheDocument();
    expect(adapter.deleteRow).not.toHaveBeenCalled();
  });

  it("deletes once the confirmation is accepted", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          confirmDelete={() => "Are you sure?"}
        />
      </QueryClientProvider>,
    );

    await user.click(await screen.findByRole("button", { name: "Delete" }));
    const dialog = within(screen.getByRole("alertdialog"));
    await user.click(dialog.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(adapter.deleteRow).toHaveBeenCalledWith(10));
  });

  it("does not delete when the confirmation is cancelled", async () => {
    const adapter = makeAdapter();
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataGrid
          queryKey={["test-sheet"]}
          adapter={adapter}
          confirmDelete={() => "Are you sure?"}
        />
      </QueryClientProvider>,
    );

    await user.click(await screen.findByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(adapter.deleteRow).not.toHaveBeenCalled();
  });

  it("renders no group row when columnGroups is not passed", async () => {
    renderGrid(makeAdapter());

    await screen.findByText("Category");
    expect(document.querySelector(".data-grid-group-row")).not.toBeInTheDocument();
  });
});

function renderGridWithRowActions(adapter: SheetApiAdapter) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <DataGrid
        queryKey={["test-sheet"]}
        adapter={adapter}
        rowActions={(row) => <button>Manage row {row.id}</button>}
      />
    </QueryClientProvider>,
  );
}
