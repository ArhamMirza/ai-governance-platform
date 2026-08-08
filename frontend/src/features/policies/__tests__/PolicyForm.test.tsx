import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { policiesApi } from "../api";
import { PolicyForm } from "../components/PolicyForm";
import type { Policy } from "../types";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("PolicyForm", () => {
  it("submits the entered values and calls onCreated with the new policy id", async () => {
    const createdPolicy: Policy = {
      id: 42,
      title: "New Policy",
      description: null,
      status: "draft",
      version: 1,
      owner_id: null,
      content: "",
      effective_date: null,
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
        content: "",
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
