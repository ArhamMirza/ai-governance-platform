import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useUserDirectory } from "../../users/hooks";
import { changesApi } from "../api";
import { ChangeForm } from "../components/ChangeForm";
import { makeChange } from "./fixtures";

vi.mock("../api");
vi.mock("../../users/hooks");

function renderForm(onCreated = vi.fn()) {
  vi.mocked(useUserDirectory).mockReturnValue({ data: [] } as never);
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <ChangeForm onCreated={onCreated} />
    </QueryClientProvider>,
  );
  return onCreated;
}

describe("ChangeForm", () => {
  it("creates a change with its reasons and dates", async () => {
    vi.mocked(changesApi.create).mockResolvedValue(makeChange({ id: 9 }));
    const user = userEvent.setup();
    const onCreated = renderForm();

    await user.type(screen.getByLabelText("Change"), "Move the screener to a new base model");
    await user.selectOptions(screen.getByLabelText("What it concerns"), "ai_system");
    await user.type(screen.getByLabelText("Why"), "The vendor retires the old model");
    await user.type(screen.getByLabelText("Potential consequences"), "Rankings may shift");
    await user.type(screen.getByLabelText("Planned for"), "2099-07-31");
    await user.click(screen.getByRole("button", { name: "Add Change" }));

    expect(changesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Move the screener to a new base model",
        change_type: "ai_system",
        reason: "The vendor retires the old model",
        consequences: "Rankings may shift",
        resources_needed: null,
        owner_id: null,
        planned_date: "2099-07-31",
      }),
    );
    expect(onCreated).toHaveBeenCalledWith(9);
  });

  it("asks for a title and a planned date", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("button", { name: "Add Change" }));

    expect(await screen.findByText("Describe the change in a few words")).toBeInTheDocument();
    expect(screen.getByText("When is it planned for?")).toBeInTheDocument();
    expect(changesApi.create).not.toHaveBeenCalled();
  });

  it("won't plan a change for before it was raised", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Change"), "Backwards");
    await user.clear(screen.getByLabelText("Raised on"));
    await user.type(screen.getByLabelText("Raised on"), "2099-08-01");
    await user.type(screen.getByLabelText("Planned for"), "2099-07-01");
    await user.click(screen.getByRole("button", { name: "Add Change" }));

    expect(
      await screen.findByText("The planned date can't be before the change was raised"),
    ).toBeInTheDocument();
    expect(changesApi.create).not.toHaveBeenCalled();
  });
});
