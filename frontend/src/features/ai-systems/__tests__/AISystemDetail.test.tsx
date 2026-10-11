import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useAllImpactAssessments } from "../../impact-assessments/hooks";
import { useRiskAssessments } from "../../risk-assessments/hooks";
import { AISystemDetail } from "../components/AISystemDetail";
import { useLifecycle } from "../hooks";

vi.mock("../hooks");
vi.mock("../../ai-system-inventory/hooks");
vi.mock("../../impact-assessments/hooks");
vi.mock("../../risk-assessments/hooks");
// Everything below the header is its own feature with its own tests.
vi.mock("../components/LifecycleStageTracker", () => ({ LifecycleStageTracker: () => null }));
vi.mock("../components/StageFields", () => ({
  OwnerField: () => null,
  DeploymentRecordFields: () => null,
  MonitoringFields: () => null,
  RetirementFields: () => null,
}));
vi.mock("../components/StageGateChecklist", () => ({ StageGateChecklist: () => null }));
vi.mock("../../ai-roles/components/AISystemAIRoles", () => ({ AISystemAIRoles: () => null }));
vi.mock("../../changes/components/AISystemChanges", () => ({ AISystemChanges: () => null }));
vi.mock("../../objectives/components/AISystemObjectives", () => ({
  AISystemObjectives: () => null,
}));
vi.mock("../../suppliers/components/AISystemSuppliers", () => ({ AISystemSuppliers: () => null }));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));
vi.mock("../../evidence/components/DocumentBrowser", () => ({ DocumentBrowser: () => null }));
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: ({ entityType, entityId }: { entityType: string; entityId: number }) => (
    <p>{`Tags for ${entityType} ${entityId}`}</p>
  ),
}));

function renderDetail(rowId: number) {
  vi.mocked(useLifecycle).mockReturnValue({
    data: {
      current_stage: "inception",
      current_stage_label: "Inception",
      entered_stage_at: "2026-01-01T00:00:00Z",
      requirements: [],
      can_advance: false,
      can_archive: false,
    },
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useAISystemInventoryRows).mockReturnValue({
    data: { rows: [{ id: rowId, data: { name: "Resume Screener" } }] },
  } as never);
  vi.mocked(useAllImpactAssessments).mockReturnValue({ data: [] } as never);
  vi.mocked(useRiskAssessments).mockReturnValue({ data: [] } as never);
  return render(
    <MemoryRouter>
      <AISystemDetail rowId={rowId} />
    </MemoryRouter>,
  );
}

describe("AISystemDetail", () => {
  it("lets the system be tagged to the controls its record evidences", () => {
    renderDetail(7);

    expect(screen.getByText("Resume Screener")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Framework Tags" })).toBeInTheDocument();
    // The system's own row id, under the entity type the compliance view reads.
    expect(screen.getByText("Tags for AISystem 7")).toBeInTheDocument();
    expect(screen.getByText(/only counts once the matching inventory columns are filled in/)).toBeInTheDocument();
  });
});
