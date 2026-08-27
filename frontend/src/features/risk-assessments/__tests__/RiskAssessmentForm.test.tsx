import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RiskAssessmentForm } from "../components/RiskAssessmentForm";
import { useAISystemInventoryRows, useCreateRiskAssessment } from "../hooks";
import type { RiskAssessment } from "../types";

vi.mock("../hooks");

const mockInventory = {
  id: 1,
  entity_type: "AISystemInventory",
  title: "AI System Inventory",
  columns: [],
  rows: [
    {
      id: 5,
      sheet_id: 1,
      row_index: 1,
      data: { name: "Resume Screener" },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const createdRiskAssessment: RiskAssessment = {
  id: 42,
  ai_system_row_id: 5,
  sheet_id: 2,
  framework_tags: [],
  status: "draft",
  assessor_id: null,
  assessment_date: null,
  overall_risk_rating: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("RiskAssessmentForm", () => {
  it("submits the selected AI system", async () => {
    vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: mockInventory } as never);
    const mutateAsync = vi.fn().mockResolvedValue(createdRiskAssessment);
    vi.mocked(useCreateRiskAssessment).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as never);
    const onCreated = vi.fn();
    const user = userEvent.setup();

    render(<RiskAssessmentForm onCreated={onCreated} />);

    await user.selectOptions(screen.getByLabelText("AI System"), "Resume Screener");
    await user.click(screen.getByRole("button", { name: "Create Risk Assessment" }));

    expect(mutateAsync).toHaveBeenCalledWith({ ai_system_row_id: 5 });
    expect(onCreated).toHaveBeenCalledWith(42);
  });

  it("shows a validation error when no AI System is selected", async () => {
    vi.mocked(useAISystemInventoryRows).mockReturnValue({ data: mockInventory } as never);
    const mutateAsync = vi.fn();
    vi.mocked(useCreateRiskAssessment).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as never);
    const user = userEvent.setup();

    render(<RiskAssessmentForm />);
    await user.click(screen.getByRole("button", { name: "Create Risk Assessment" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Select an AI System");
    expect(mutateAsync).not.toHaveBeenCalled();
  });
});
