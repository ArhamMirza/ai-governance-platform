import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { usePolicies } from "../../policies/hooks";
import { useUserDirectory } from "../../users/hooks";
import { objectivesApi } from "../api";
import { ObjectiveForm } from "../components/ObjectiveForm";
import { makeObjectiveDetail } from "./fixtures";

vi.mock("../api");
vi.mock("../../users/hooks");
vi.mock("../../policies/hooks");

function renderForm(onCreated = vi.fn()) {
  vi.mocked(useUserDirectory).mockReturnValue({ data: [] } as never);
  vi.mocked(usePolicies).mockReturnValue({
    data: [{ id: 3, title: "Vendor AI Risk Policy" }],
  } as never);
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <ObjectiveForm onCreated={onCreated} />
    </QueryClientProvider>,
  );
  return onCreated;
}

describe("ObjectiveForm", () => {
  it("creates a measured objective with its target and schedule", async () => {
    vi.mocked(objectivesApi.create).mockResolvedValue(makeObjectiveDetail({ id: 12 }));
    const user = userEvent.setup();
    const onCreated = renderForm();

    await user.type(screen.getByLabelText("Objective"), "Bias test pass rate");
    await user.selectOptions(screen.getByLabelText("Supports policy"), "3");
    await user.type(screen.getByLabelText("Metric"), "Pass rate");
    await user.type(screen.getByLabelText("Target value"), "95");
    await user.type(screen.getByLabelText("Unit"), "%");
    await user.type(screen.getByLabelText("Measure every (months)"), "3");
    await user.type(screen.getByLabelText("First reading due"), "2026-03-31");
    await user.click(screen.getByRole("button", { name: "Add Objective" }));

    expect(objectivesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Bias test pass rate",
        kind: "measured",
        policy_id: 3,
        metric_name: "Pass rate",
        direction: "at_least",
        target_value: 95,
        unit: "%",
        measurement_interval_months: 3,
        first_measurement_due: "2026-03-31",
      }),
    );
    expect(onCreated).toHaveBeenCalledWith(12);
  });

  it("asks a measured objective for its metric and target", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Objective"), "Pass rate");
    await user.click(screen.getByRole("button", { name: "Add Objective" }));

    expect(await screen.findByText("What's being measured?")).toBeInTheDocument();
    expect(screen.getByText("Enter the target as a number")).toBeInTheDocument();
    expect(objectivesApi.create).not.toHaveBeenCalled();
  });

  it("drops the measurement fields for a milestone, which needs a target date", async () => {
    vi.mocked(objectivesApi.create).mockResolvedValue(makeObjectiveDetail({ id: 4 }));
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Metric"), "Leftover");
    await user.click(screen.getByRole("radio", { name: /Milestone/ }));
    expect(screen.queryByLabelText("Metric")).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Objective"), "Publish a transparency notice");
    await user.click(screen.getByRole("button", { name: "Add Objective" }));
    expect(await screen.findByText("A milestone needs a target date")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Target date"), "2099-09-30");
    await user.click(screen.getByRole("button", { name: "Add Objective" }));

    expect(objectivesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "milestone",
        target_date: "2099-09-30",
        metric_name: null,
        direction: null,
        target_value: null,
      }),
    );
  });
});
