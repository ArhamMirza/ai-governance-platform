import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ImpactAssessmentList } from "../components/ImpactAssessmentList";
import { useCreateImpactAssessment, useImpactAssessments } from "../hooks";
import type { ImpactAssessment } from "../types";

vi.mock("../hooks");
vi.mock("../components/ImpactAssessmentForm", () => ({
  ImpactAssessmentForm: ({ assessment }: { assessment: ImpactAssessment }) => (
    <div>Form for assessment {assessment.id}</div>
  ),
}));

function makeAssessment(overrides: Partial<ImpactAssessment> = {}): ImpactAssessment {
  return {
    id: 1,
    ai_system_row_id: 7,
    status: "draft",
    assessor_id: null,
    assessment_date: null,
    system_description: null,
    intended_purpose: null,
    foreseeable_misuse: null,
    data_and_model_info: null,
    deployment_environment: null,
    affected_interested_parties: null,
    human_oversight_role: null,
    conclusion: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    framework_tags: [],
    factors: [],
    ...overrides,
  };
}

function mockHooks({
  assessments = [],
  mutateAsync = vi.fn(),
}: { assessments?: ImpactAssessment[]; mutateAsync?: ReturnType<typeof vi.fn> } = {}) {
  vi.mocked(useImpactAssessments).mockReturnValue({
    data: assessments,
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useCreateImpactAssessment).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as never);
  return mutateAsync;
}

describe("ImpactAssessmentList", () => {
  it("shows a placeholder when there are no impact assessments yet", () => {
    mockHooks({ assessments: [] });

    render(<ImpactAssessmentList riskAssessmentId={1} />);

    expect(screen.getByText("No impact assessments yet for this AI system.")).toBeInTheDocument();
  });

  it("lists assessments, most recent first, with the newest expanded", () => {
    mockHooks({ assessments: [makeAssessment({ id: 1 }), makeAssessment({ id: 2 })] });

    render(<ImpactAssessmentList riskAssessmentId={1} />);

    expect(screen.getByText(/Impact Assessment #2/)).toBeInTheDocument();
    expect(screen.getByText("Form for assessment 2")).toBeInTheDocument();
    expect(screen.queryByText("Form for assessment 1")).not.toBeInTheDocument();
  });

  it("creates a new impact assessment and expands it", async () => {
    const mutateAsync = vi.fn().mockResolvedValue(makeAssessment({ id: 3 }));
    mockHooks({ assessments: [makeAssessment({ id: 1 })], mutateAsync });
    const user = userEvent.setup();

    render(<ImpactAssessmentList riskAssessmentId={1} />);
    await user.click(screen.getByRole("button", { name: "New Impact Assessment" }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({});
    });
  });
});
