import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ImpactAssessmentList } from "../components/ImpactAssessmentList";
import { useImpactAssessments } from "../hooks";
import type { ImpactAssessment } from "../types";

vi.mock("../hooks");
vi.mock("../components/ImpactAssessmentForm", () => ({
  ImpactAssessmentForm: ({
    assessment,
    allowDelete,
  }: {
    assessment: ImpactAssessment;
    allowDelete?: boolean;
  }) => (
    <div>
      Form for assessment {assessment.id} (delete: {String(allowDelete)})
    </div>
  ),
}));

function makeAssessment(overrides: Partial<ImpactAssessment> = {}): ImpactAssessment {
  return {
    id: 1,
    ai_system_row_id: 7,
    status: "completed",
    assessor_id: null,
    assessment_date: "2026-01-01",
    next_review_date: "2027-01-01",
    review_overdue: false,
    system_description: null,
    intended_purpose: null,
    foreseeable_misuse: null,
    data_and_model_info: null,
    deployment_environment: null,
    affected_interested_parties: null,
    human_oversight_role: null,
    conclusion: null,
    owner_approved_by: null,
    owner_approved_at: null,
    caigo_approved_by: null,
    caigo_approved_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    framework_tags: [],
    factors: [],
    ...overrides,
  };
}

function mockHook(assessments: ImpactAssessment[]) {
  vi.mocked(useImpactAssessments).mockReturnValue({
    data: assessments,
    isLoading: false,
    isError: false,
  } as never);
}

function renderList() {
  return render(
    <MemoryRouter>
      <ImpactAssessmentList riskAssessmentId={1} />
    </MemoryRouter>,
  );
}

describe("ImpactAssessmentList", () => {
  it("shows the AI system's single impact assessment", () => {
    mockHook([makeAssessment({ id: 3 })]);

    renderList();

    expect(screen.getByText(/Impact Assessment #3/)).toBeInTheDocument();
    expect(screen.getByText(/Form for assessment 3/)).toBeInTheDocument();
  });

  it("shows the review due date", () => {
    mockHook([makeAssessment()]);

    renderList();

    expect(screen.getByText(/Review due/)).toBeInTheDocument();
    expect(screen.getByText(/2027-01-01/)).toBeInTheDocument();
  });

  it("flags an overdue review", () => {
    mockHook([makeAssessment({ review_overdue: true })]);

    renderList();

    expect(screen.getByText(/Review overdue/)).toBeInTheDocument();
  });

  it("does not offer deletion here, since a risk assessment depends on it", () => {
    mockHook([makeAssessment({ id: 3 })]);

    renderList();

    expect(screen.getByText(/delete: false/)).toBeInTheDocument();
  });

  it("handles a system with no impact assessment", () => {
    mockHook([]);

    renderList();

    expect(screen.getByText("No impact assessment for this AI system.")).toBeInTheDocument();
  });
});
