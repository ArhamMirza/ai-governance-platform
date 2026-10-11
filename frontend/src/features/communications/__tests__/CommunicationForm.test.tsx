import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useUserDirectory } from "../../users/hooks";
import { communicationsApi } from "../api";
import { CommunicationForm } from "../components/CommunicationForm";
import { makeCommunicationDetail } from "./fixtures";

vi.mock("../api");
vi.mock("../../users/hooks");

function renderForm(onCreated = vi.fn()) {
  vi.mocked(useUserDirectory).mockReturnValue({ data: [] } as never);
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <CommunicationForm onCreated={onCreated} />
    </QueryClientProvider>,
  );
  return onCreated;
}

describe("CommunicationForm", () => {
  it("creates a scheduled communication", async () => {
    vi.mocked(communicationsApi.create).mockResolvedValue(makeCommunicationDetail({ id: 8 }));
    const user = userEvent.setup();
    const onCreated = renderForm();

    await user.type(screen.getByLabelText("What is communicated"), "Quarterly update");
    await user.type(screen.getByLabelText("To whom"), "Leadership team");
    await user.selectOptions(
      screen.getByLabelText("Inside or outside the organization"),
      "external",
    );
    await user.type(screen.getByLabelText("How"), "Board pack");
    await user.type(screen.getByLabelText("Every (months)"), "3");
    await user.type(screen.getByLabelText("First due"), "2026-09-30");
    await user.click(screen.getByRole("button", { name: "Add Communication" }));

    expect(communicationsApi.create).toHaveBeenCalledWith({
      topic: "Quarterly update",
      audience: "Leadership team",
      direction: "external",
      method: "Board pack",
      responsible_id: null,
      notes: null,
      interval_months: 3,
      first_due: "2026-09-30",
    });
    expect(onCreated).toHaveBeenCalledWith(8);
  });

  it("creates one done only when needed, with no schedule", async () => {
    vi.mocked(communicationsApi.create).mockResolvedValue(makeCommunicationDetail());
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("What is communicated"), "Incident notice");
    await user.type(screen.getByLabelText("To whom"), "Affected customers");
    await user.click(screen.getByRole("button", { name: "Add Communication" }));

    expect(communicationsApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ interval_months: null, first_due: null }),
    );
  });

  it("asks for a topic and an audience", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("button", { name: "Add Communication" }));

    expect(await screen.findByText("What is being communicated?")).toBeInTheDocument();
    expect(screen.getByText("Who is it for?")).toBeInTheDocument();
    expect(communicationsApi.create).not.toHaveBeenCalled();
  });

  it("won't take half a schedule", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("What is communicated"), "Update");
    await user.type(screen.getByLabelText("To whom"), "Staff");
    await user.type(screen.getByLabelText("Every (months)"), "6");
    await user.click(screen.getByRole("button", { name: "Add Communication" }));

    expect(
      await screen.findByText(/Set both how often and when it's first due/),
    ).toBeInTheDocument();
    expect(communicationsApi.create).not.toHaveBeenCalled();
  });
});
