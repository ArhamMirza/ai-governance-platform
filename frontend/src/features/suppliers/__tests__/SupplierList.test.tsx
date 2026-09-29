import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { suppliersApi } from "../api";
import { AISystemSuppliers } from "../components/AISystemSuppliers";
import { SupplierList } from "../components/SupplierList";
import { makeSupplier } from "./fixtures";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SupplierList", () => {
  it("flags an ended contract and an overdue review", async () => {
    vi.mocked(suppliersApi.list).mockResolvedValue([
      makeSupplier({ id: 3, contract_status: "expired", review_overdue: true }),
      makeSupplier({ id: 4, name: "Cloud Co", supplier_type: "infrastructure" }),
    ]);

    renderWithProviders(<SupplierList />);

    const flagged = (await screen.findByRole("link", { name: "Acme Models" })).closest("tr")!;
    expect(within(flagged).getByText("Contract ended")).toBeInTheDocument();
    expect(within(flagged).getByText("Review overdue")).toBeInTheDocument();
    const fine = screen.getByRole("link", { name: "Cloud Co" }).closest("tr")!;
    expect(within(fine).queryByText("Review overdue")).not.toBeInTheDocument();
    expect(within(fine).getByText("Infrastructure / hosting")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    vi.mocked(suppliersApi.list).mockResolvedValue([]);

    renderWithProviders(<SupplierList />);

    expect(await screen.findByText("No suppliers yet.")).toBeInTheDocument();
  });
});

describe("AISystemSuppliers", () => {
  it("lists the suppliers linked to one AI system", async () => {
    vi.mocked(suppliersApi.list).mockResolvedValue([
      makeSupplier({ id: 5, contract_status: "expiring" }),
    ]);

    renderWithProviders(<AISystemSuppliers rowId={7} />);

    expect(await screen.findByRole("link", { name: "Acme Models" })).toHaveAttribute(
      "href",
      "/suppliers/5",
    );
    expect(screen.getByText("Contract ending soon")).toBeInTheDocument();
    expect(suppliersApi.list).toHaveBeenCalledWith(7);
  });
});
