import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { policiesApi } from "../../policies/api";
import type { Policy } from "../../policies/types";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { proceduresApi } from "../api";
import { ProcedureForm } from "../components/ProcedureForm";
import type { Procedure } from "../types";

vi.mock("../api");
vi.mock("../../policies/api");

const mockPolicy: Policy = {
  id: 5,
  title: "Data Retention Policy",
  description: null,
  status: "approved",
  version: 1,
  owner_id: null,
  effective_date: null,
  next_review_date: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ProcedureForm", () => {
  it("submits the entered values with no policy link by default", async () => {
    vi.mocked(policiesApi.list).mockResolvedValue([mockPolicy]);
    const createdProcedure: Procedure = {
      id: 42,
      title: "New Procedure",
      description: null,
      status: "draft",
      version: 1,
      owner_id: null,
      policy_id: null,
      effective_date: null,
      next_review_date: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(proceduresApi.create).mockResolvedValue(createdProcedure);
    const onCreated = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(<ProcedureForm onCreated={onCreated} />);

    await user.type(screen.getByLabelText("Title"), "New Procedure");
    await user.click(screen.getByRole("button", { name: "Create Procedure" }));

    await vi.waitFor(() => {
      expect(proceduresApi.create).toHaveBeenCalledWith({
        title: "New Procedure",
        description: null,
        owner_id: null,
        policy_id: null,
      });
      expect(onCreated).toHaveBeenCalledWith(42);
    });
  });

  it("submits the selected policy link", async () => {
    vi.mocked(policiesApi.list).mockResolvedValue([mockPolicy]);
    vi.mocked(proceduresApi.create).mockResolvedValue({
      id: 43,
      title: "Linked Procedure",
      description: null,
      status: "draft",
      version: 1,
      owner_id: null,
      policy_id: 5,
      effective_date: null,
      next_review_date: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();

    renderWithProviders(<ProcedureForm />);
    await screen.findByText("Data Retention Policy");

    await user.type(screen.getByLabelText("Title"), "Linked Procedure");
    await user.selectOptions(
      screen.getByLabelText("Implements Policy (optional)"),
      "Data Retention Policy",
    );
    await user.click(screen.getByRole("button", { name: "Create Procedure" }));

    await vi.waitFor(() => {
      expect(proceduresApi.create).toHaveBeenCalledWith({
        title: "Linked Procedure",
        description: null,
        owner_id: null,
        policy_id: 5,
      });
    });
  });

  it("shows a validation error when title is empty", async () => {
    vi.mocked(policiesApi.list).mockResolvedValue([]);
    const user = userEvent.setup();

    renderWithProviders(<ProcedureForm />);

    await user.click(screen.getByRole("button", { name: "Create Procedure" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Title is required");
    expect(proceduresApi.create).not.toHaveBeenCalled();
  });
});
