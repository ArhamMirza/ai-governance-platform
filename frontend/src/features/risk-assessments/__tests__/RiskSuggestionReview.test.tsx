import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAiAssistStatus } from "../../ai-assist/hooks";
import {
  type RiskSuggestion,
  type RiskSuggestions,
  useApplyRiskSuggestions,
  useDiscardRiskSuggestions,
  useGenerateRiskSuggestions,
  useLatestRiskSuggestions,
} from "../aiRiskSuggestions";
import { RiskSuggestionPanel } from "../components/RiskSuggestionPanel";
import { RiskSuggestionReview } from "../components/RiskSuggestionReview";

vi.mock("../aiRiskSuggestions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../aiRiskSuggestions")>()),
  useApplyRiskSuggestions: vi.fn(),
  useDiscardRiskSuggestions: vi.fn(),
  useGenerateRiskSuggestions: vi.fn(),
  useLatestRiskSuggestions: vi.fn(),
}));
vi.mock("../../ai-assist/hooks", () => ({ useAiAssistStatus: vi.fn() }));

const apply = vi.fn();
const discard = vi.fn();
const generate = vi.fn();

function suggestion(overrides: Partial<RiskSuggestion> = {}): RiskSuggestion {
  return {
    key: "item.0",
    category: "Fairness",
    description: "Ranking may disadvantage older applicants.",
    mitigation: "Audit score distributions by age band.",
    likelihood: 3,
    impact: 4,
    citations: [1],
    gap: null,
    uncited: false,
    withheld: false,
    ...overrides,
  };
}

function draft(proposals: RiskSuggestion[]): RiskSuggestions {
  return {
    id: 9,
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
    suggestion(),
    suggestion({
      key: "item.1",
      category: "Safety",
      description: null,
      mitigation: null,
      likelihood: null,
      impact: null,
      citations: [],
      withheld: true,
      gap: "This suggestion cited sources that were never provided, so it was withheld.",
    }),
    suggestion({
      key: "item.2",
      category: "Privacy",
      description: "Retains applicant data longer than the stated policy allows.",
      citations: [],
      uncited: true,
    }),
  ]);

function renderReview(overrides?: RiskSuggestions) {
  return render(
    <MemoryRouter>
      <RiskSuggestionReview riskAssessmentId={5} draft={overrides ?? standard()} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apply.mockResolvedValue({});
  vi.mocked(useApplyRiskSuggestions).mockReturnValue({
    mutateAsync: apply,
    isPending: false,
  } as never);
  vi.mocked(useDiscardRiskSuggestions).mockReturnValue({
    mutateAsync: discard,
    isPending: false,
  } as never);
  vi.mocked(useGenerateRiskSuggestions).mockReturnValue({
    mutateAsync: generate,
    isPending: false,
  } as never);
});

describe("RiskSuggestionReview", () => {
  it("ticks a cited suggestion and leaves a withheld one with no way to add it", () => {
    renderReview();

    expect(screen.getByRole("checkbox", { name: /Fairness/ })).toBeChecked();
    expect(screen.queryByRole("checkbox", { name: /Safety/ })).not.toBeInTheDocument();
    expect(screen.getByText(/cited sources that were never provided/)).toBeInTheDocument();
  });

  it("flags an uncited suggestion and leaves it unticked", () => {
    renderReview();

    expect(screen.getByText("No source cited")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Privacy/ })).not.toBeChecked();
  });

  it("adds only the ticked items, computing nothing itself", async () => {
    renderReview();

    await userEvent.click(screen.getByRole("button", { name: /^Add \d+ item/ }));

    expect(apply).toHaveBeenCalledWith({
      draftId: 9,
      accepted: [
        {
          key: "item.0",
          category: "Fairness",
          description: "Ranking may disadvantage older applicants.",
          mitigation: "Audit score distributions by age band.",
          likelihood: 3,
          impact: 4,
          risk_owner: null,
        },
      ],
    });
  });

  it("sends an edited description and marks the item as edited by ticking it", async () => {
    renderReview(draft([suggestion({ citations: [], uncited: true })]));

    await userEvent.type(screen.getByLabelText("Description"), " Edited by the assessor.");
    await userEvent.click(screen.getByRole("button", { name: /^Add \d+ item/ }));

    const accepted = apply.mock.calls[0][0].accepted;
    expect(accepted[0].description).toContain("Edited by the assessor.");
  });

  it("never lets the AI supply a risk score", () => {
    renderReview();

    expect(screen.queryByText(/inherent.risk.score/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/always computed from likelihood and impact/).length).toBeGreaterThan(0);
  });

  it("can't add when nothing is selected", () => {
    renderReview(draft([suggestion({ citations: [], uncited: true })]));

    expect(screen.getByRole("button", { name: "Add 0 items" })).toBeDisabled();
  });

  it("links each source back to its record", () => {
    renderReview();

    const sources = screen.getByRole("list", { name: "Sources the suggestions drew on" });
    expect(within(sources).getByRole("link", { name: /Resume Screener/ })).toHaveAttribute(
      "href",
      "/ai-systems/7",
    );
  });

  it("discards the suggestions", async () => {
    renderReview();

    await userEvent.click(screen.getByRole("button", { name: "Discard suggestions" }));

    expect(discard).toHaveBeenCalledWith(9);
  });

  it("redrafts with new guidance", async () => {
    generate.mockResolvedValue(standard());
    renderReview();

    await userEvent.type(
      screen.getByLabelText("Add guidance and redraft"),
      "Focus on data leakage risks.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Redraft with this guidance" }));

    expect(generate).toHaveBeenCalledWith("Focus on data leakage risks.");
  });
});

describe("RiskSuggestionPanel", () => {
  const renderPanel = () =>
    render(
      <MemoryRouter>
        <RiskSuggestionPanel riskAssessmentId={5} />
      </MemoryRouter>,
    );

  it("offers nothing when no provider is configured", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: false } } as never);
    vi.mocked(useLatestRiskSuggestions).mockReturnValue({ data: undefined } as never);

    const { container } = renderPanel();

    expect(container).toBeEmptyDOMElement();
  });

  it("offers to suggest risk items", async () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestRiskSuggestions).mockReturnValue({ data: null, isLoading: false } as never);

    renderPanel();
    await userEvent.type(
      screen.getByLabelText("Guidance (optional)"),
      "Focus on third-party access.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Suggest risk items" }));

    expect(generate).toHaveBeenCalledWith("Focus on third-party access.");
  });

  it("reopens suggestions still waiting for review", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestRiskSuggestions).mockReturnValue({ data: standard() } as never);

    renderPanel();

    expect(
      screen.getByRole("region", { name: "AI risk item suggestions for review" }),
    ).toBeInTheDocument();
  });
});
