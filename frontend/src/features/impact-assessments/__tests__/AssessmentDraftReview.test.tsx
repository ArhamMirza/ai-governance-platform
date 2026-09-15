import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAiAssistStatus } from "../../ai-assist/hooks";
import {
  type AssessmentDraft,
  type DraftProposal,
  useApplyAssessmentDraft,
  useDiscardAssessmentDraft,
  useGenerateAssessmentDraft,
  useLatestAssessmentDraft,
} from "../aiDraft";
import { AssessmentDraftPanel } from "../components/AssessmentDraftPanel";
import { AssessmentDraftReview } from "../components/AssessmentDraftReview";
import type { ImpactAssessment } from "../types";

vi.mock("../aiDraft", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../aiDraft")>()),
  useApplyAssessmentDraft: vi.fn(),
  useDiscardAssessmentDraft: vi.fn(),
  useGenerateAssessmentDraft: vi.fn(),
  useLatestAssessmentDraft: vi.fn(),
}));
vi.mock("../../ai-assist/hooks", () => ({ useAiAssistStatus: vi.fn() }));

const apply = vi.fn();
const discard = vi.fn();
const generate = vi.fn();

function assessment(overrides: Partial<ImpactAssessment> = {}): ImpactAssessment {
  return {
    id: 4,
    ai_system_row_id: 7,
    status: "draft",
    assessor_id: null,
    assessment_date: null,
    next_review_date: null,
    review_overdue: false,
    owner_approved_by: null,
    owner_approved_at: null,
    caigo_approved_by: null,
    caigo_approved_at: null,
    system_description: "Written by the assessor.",
    intended_purpose: null,
    foreseeable_misuse: null,
    data_and_model_info: null,
    deployment_environment: null,
    affected_interested_parties: null,
    human_oversight_role: null,
    conclusion: null,
    created_at: "2026-09-15T10:00:00Z",
    updated_at: "2026-09-15T10:00:00Z",
    framework_tags: [],
    factors: [
      { id: 1, factor: "Fairness", benefits: null, harms: null, criteria: null, score: null },
    ],
    ...overrides,
  } as ImpactAssessment;
}

function narrative(field: string, label: string, overrides: Partial<DraftProposal> = {}) {
  return {
    key: `narrative.${field}`,
    section: "narrative",
    field,
    factor: null,
    label,
    value: `Drafted ${label.toLowerCase()}.`,
    rationale: null,
    citations: [1],
    gap: null,
    uncited: false,
    withheld: false,
    ...overrides,
  } as DraftProposal;
}

function draft(proposals: DraftProposal[]): AssessmentDraft {
  return {
    id: 21,
    status: "ready",
    provider: "anthropic",
    model: "claude-sonnet-5",
    requested_by: 1,
    created_at: "2026-09-15T10:00:00Z",
    proposals,
    sources: [
      {
        n: 1,
        title: "AI system: Resume Screener",
        section: "AI system record",
        kind: "AISystem",
        href: "/ai-systems/7",
        download_evidence_id: null,
        read_by_ocr: false,
        excerpt: "Ranks applicants.",
        injection_findings: [],
      },
    ],
    injection_findings: null,
    coverage_gaps: null,
  };
}

const standard = () =>
  draft([
    narrative("system_description", "System Description"),
    narrative("intended_purpose", "Intended Purpose"),
    narrative("foreseeable_misuse", "Foreseeable Misuse", {
      value: null,
      withheld: true,
      gap: "The draft for this field cited sources that were never provided, so it was withheld.",
    }),
    narrative("deployment_environment", "Deployment Environment", { citations: [], uncited: true }),
    {
      key: "factor.Fairness.score",
      section: "factor",
      field: "score",
      factor: "Fairness",
      label: "Score",
      value: 4,
      rationale: "Shortlisting may disadvantage career-break applicants.",
      citations: [1],
      gap: null,
      uncited: false,
      withheld: false,
    },
  ]);

function renderReview(props: { assessment?: ImpactAssessment; draft?: AssessmentDraft } = {}) {
  return render(
    <MemoryRouter>
      <AssessmentDraftReview
        riskAssessmentId={null}
        assessment={props.assessment ?? assessment()}
        draft={props.draft ?? standard()}
      />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apply.mockResolvedValue({});
  vi.mocked(useApplyAssessmentDraft).mockReturnValue({ mutateAsync: apply, isPending: false } as never);
  vi.mocked(useDiscardAssessmentDraft).mockReturnValue({ mutateAsync: discard, isPending: false } as never);
  vi.mocked(useGenerateAssessmentDraft).mockReturnValue({ mutateAsync: generate, isPending: false } as never);
});

describe("AssessmentDraftReview", () => {
  it("never pre-selects a field someone already wrote", () => {
    // A draft must not overwrite a person's work because they clicked through.
    renderReview();

    expect(screen.getByRole("checkbox", { name: "Apply System Description" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Apply Intended Purpose" })).toBeChecked();
  });

  it("offers no way to apply a withheld field, and says why", () => {
    renderReview();

    expect(screen.queryByRole("checkbox", { name: "Apply Foreseeable Misuse" })).not.toBeInTheDocument();
    expect(screen.getByText(/cited sources that were never provided/)).toBeInTheDocument();
  });

  it("flags proposed text that cites nothing, and waits for it to be chosen", () => {
    // Unsupported text must not ride along in a bulk apply.
    renderReview();

    expect(screen.getByText("No source cited")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Apply Deployment Environment" })).not.toBeChecked();
  });

  it("applies only the ticked fields, with any edits the reviewer made", async () => {
    renderReview();

    await userEvent.clear(screen.getByLabelText(/^Proposed.*$/, { selector: "#draft-21-narrative\\.intended_purpose" }));
    await userEvent.type(
      screen.getByLabelText(/^Proposed/, { selector: "#draft-21-narrative\\.intended_purpose" }),
      "Shortlists applicants for human review.",
    );
    await userEvent.click(screen.getByRole("button", { name: /^Apply \d+ field/ }));

    expect(apply).toHaveBeenCalledWith({
      draftId: 21,
      accepted: [
        { key: "narrative.intended_purpose", value: "Shortlists applicants for human review." },
        { key: "factor.Fairness.score", value: 4 },
      ],
    });
  });

  it("sends a changed score as a number", async () => {
    renderReview();

    await userEvent.selectOptions(
      screen.getByLabelText(/^Proposed/, { selector: "#draft-21-factor\\.Fairness\\.score" }),
      "2",
    );
    await userEvent.click(screen.getByRole("button", { name: /^Apply \d+ field/ }));

    const accepted = apply.mock.calls[0][0].accepted;
    expect(accepted).toContainEqual({ key: "factor.Fairness.score", value: 2 });
  });

  it("shows the reason behind a proposed score", () => {
    renderReview();

    expect(screen.getByText(/career-break applicants/)).toBeInTheDocument();
  });

  it("warns that applying returns an approved assessment to draft", () => {
    renderReview({ assessment: assessment({ status: "completed" }) });

    expect(screen.getByText(/returns it to draft and withdraws its approvals/)).toBeInTheDocument();
  });

  it("can't apply when nothing is selected", async () => {
    renderReview({
      draft: draft([narrative("system_description", "System Description")]),
    });

    expect(screen.getByRole("button", { name: "Apply 0 fields" })).toBeDisabled();
  });

  it("links each source back to its record", () => {
    renderReview();

    const sources = screen.getByRole("list", { name: "Sources the draft drew on" });
    expect(within(sources).getByRole("link", { name: /Resume Screener/ })).toHaveAttribute(
      "href",
      "/ai-systems/7",
    );
  });

  it("discards the draft", async () => {
    renderReview();

    await userEvent.click(screen.getByRole("button", { name: "Discard draft" }));

    expect(discard).toHaveBeenCalledWith(21);
  });
});

describe("AssessmentDraftPanel", () => {
  const renderPanel = () =>
    render(
      <MemoryRouter>
        <AssessmentDraftPanel riskAssessmentId={null} assessment={assessment()} />
      </MemoryRouter>,
    );

  it("offers nothing when no provider is configured", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: false } } as never);
    vi.mocked(useLatestAssessmentDraft).mockReturnValue({ data: undefined } as never);

    const { container } = renderPanel();

    expect(container).toBeEmptyDOMElement();
  });

  it("offers to draft the whole assessment", async () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestAssessmentDraft).mockReturnValue({ data: null, isLoading: false } as never);

    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: "Draft with AI" }));

    expect(generate).toHaveBeenCalled();
  });

  it("reopens a draft that is still waiting for review", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestAssessmentDraft).mockReturnValue({ data: standard() } as never);

    renderPanel();

    expect(screen.getByRole("region", { name: "AI draft for review" })).toBeInTheDocument();
  });
});
