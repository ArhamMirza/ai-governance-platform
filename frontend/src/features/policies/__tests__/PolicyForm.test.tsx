import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useUserDirectory } from "../../users/hooks";
import { policiesApi } from "../api";
import { PolicyForm } from "../components/PolicyForm";
import type { Policy } from "../types";

vi.mock("../api");
vi.mock("../../users/hooks");

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("PolicyForm", () => {
  beforeEach(() => {
    vi.mocked(useUserDirectory).mockReturnValue({
      data: [{ id: 9, name: "Priya Shah", governance_roles: ["Risk Owner"] }],
    } as never);
  });

  it("labels a directory user with their governance role and submits the chosen owner", async () => {
    const createdPolicy: Policy = {
      id: 1,
      title: "New Policy",
      description: null,
      status: "draft",
      version: 1,
      owner_id: 9,
      effective_date: null,
      next_review_date: null,
      shared_with_employees: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(policiesApi.create).mockResolvedValue(createdPolicy);
    const user = userEvent.setup();

    renderWithProviders(<PolicyForm />);

    expect(screen.getByRole("option", { name: "Priya Shah (Risk Owner)" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Title"), "New Policy");
    await user.selectOptions(screen.getByLabelText("Owner"), "9");
    await user.click(screen.getByRole("button", { name: "Create Policy" }));

    await vi.waitFor(() => {
      expect(policiesApi.create).toHaveBeenCalledWith({
        title: "New Policy",
        description: null,
        owner_id: 9,
      });
    });
  });

  it("submits the entered values and calls onCreated with the new policy id", async () => {
    const createdPolicy: Policy = {
      id: 42,
      title: "New Policy",
      description: null,
      status: "draft",
      version: 1,
      owner_id: null,
      effective_date: null,
      next_review_date: null,
      shared_with_employees: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(policiesApi.create).mockResolvedValue(createdPolicy);
    const onCreated = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(<PolicyForm onCreated={onCreated} />);

    await user.type(screen.getByLabelText("Title"), "New Policy");
    await user.click(screen.getByRole("button", { name: "Create Policy" }));

    await vi.waitFor(() => {
      expect(policiesApi.create).toHaveBeenCalledWith({
        title: "New Policy",
        description: null,
        owner_id: null,
      });
      expect(onCreated).toHaveBeenCalledWith(42);
    });
  });

  it("shows a validation error when title is empty", async () => {
    const user = userEvent.setup();

    renderWithProviders(<PolicyForm />);

    await user.click(screen.getByRole("button", { name: "Create Policy" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Title is required");
    expect(policiesApi.create).not.toHaveBeenCalled();
  });
});
