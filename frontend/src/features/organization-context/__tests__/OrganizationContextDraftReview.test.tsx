import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAiAssistStatus } from "../../ai-assist/hooks";
import {
  type ContextProposal,
  type OrganizationContextDraft,
  useApplyOrganizationContextDraft,
  useDiscardOrganizationContextDraft,
  useGenerateOrganizationContextDraft,
  useLatestOrganizationContextDraft,
} from "../aiDraft";
import { OrganizationContextDraftPanel } from "../components/OrganizationContextDraftPanel";
import { OrganizationContextDraftReview } from "../components/OrganizationContextDraftReview";
import type { OrganizationContext } from "../types";

vi.mock("../aiDraft", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../aiDraft")>()),
  useApplyOrganizationContextDraft: vi.fn(),
  useDiscardOrganizationContextDraft: vi.fn(),
  useGenerateOrganizationContextDraft: vi.fn(),
  useLatestOrganizationContextDraft: vi.fn(),
}));
vi.mock("../../ai-assist/hooks", () => ({ useAiAssistStatus: vi.fn() }));

const apply = vi.fn();
const discard = vi.fn();
const generate = vi.fn();

function contextRecord(overrides: Partial<OrganizationContext> = {}): OrganizationContext {
  return {
    id: 1,
    organization_description: null,
    ai_usage_overview: null,
    ai_roles: [],
    aims_scope: null,
    aims_scope_exclusions: null,
    status: "draft",
    approved_by: null,
    approved_at: null,
    next_review_date: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function proposal(overrides: Partial<ContextProposal> = {}): ContextProposal {
  return {
    key: "narrative.organization_description",
    kind: "narrative",
    field: "organization_description",
    label: "Organization description",
    value: "A resume-screening vendor.",
    category: null,
    issue: null,
    planned_response: null,
    party: null,
    needs: null,
    expectations: null,
    requirements: null,
    citations: [1],
    gap: null,
    uncited: false,
    withheld: false,
    ...overrides,
  };
}

function draft(proposals: ContextProposal[]): OrganizationContextDraft {
  return {
    id: 9,
    status: "ready",
    provider: "anthropic",
    model: "claude-sonnet-5",
    requested_by: 1,
    created_at: "2026-01-01T00:00:00Z",
    proposals,
    sources: [
      {
        n: 1,
        title: "AI systems in the inventory",
        section: null,
        kind: "AISystemsSummary",
        href: "/ai-systems",
        download_evidence_id: null,
        read_by_ocr: false,
        excerpt: "Resume Screener: ranks applicants.",
        injection_findings: [],
      },
    ],
    injection_findings: null,
    coverage_gaps: null,
  };
}

const standard = () =>
  draft([
    proposal(),
    proposal({
      key: "narrative.ai_usage_overview",
      field: "ai_usage_overview",
      label: "Overall use of AI",
      value: "Ranks applicants for human review.",
    }),
    proposal({
      key: "issue.0",
      kind: "issue",
      field: null,
      label: null,
      value: null,
      category: "Internal",
      issue: "Staff AI literacy varies by team.",
      planned_response: "Quarterly training.",
    }),
    proposal({
      key: "party.0",
      kind: "party",
      field: null,
      label: null,
      value: null,
      party: "Applicants",
      needs: "A fair, explainable process.",
    }),
  ]);

function renderReview(overrides?: {
  draft?: OrganizationContextDraft;
  context?: OrganizationContext;
}) {
  return render(
    <MemoryRouter>
      <OrganizationContextDraftReview
        draft={overrides?.draft ?? standard()}
        context={overrides?.context ?? contextRecord()}
      />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apply.mockResolvedValue({});
  vi.mocked(useApplyOrganizationContextDraft).mockReturnValue({
    mutateAsync: apply,
    isPending: false,
  } as never);
  vi.mocked(useDiscardOrganizationContextDraft).mockReturnValue({
    mutateAsync: discard,
    isPending: false,
  } as never);
  vi.mocked(useGenerateOrganizationContextDraft).mockReturnValue({
    mutateAsync: generate,
    isPending: false,
  } as never);
});

describe("OrganizationContextDraftReview", () => {
  it("ticks a cited narrative field when the current record is empty", () => {
    renderReview();

    expect(
      screen.getByRole("checkbox", { name: "Apply Organization description" }),
    ).toBeChecked();
  });

  it("does not pre-tick a narrative field the record already has content for", () => {
    renderReview({ context: contextRecord({ organization_description: "Already written." }) });

    expect(
      screen.getByRole("checkbox", { name: "Apply Organization description" }),
    ).not.toBeChecked();
  });

  it("ticks a cited issue and a cited interested party", () => {
    renderReview();

    expect(screen.getByRole("checkbox", { name: "Apply Internal" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Apply Applicants" })).toBeChecked();
  });

  it("offers no way to apply a withheld issue, and shows why", () => {
    renderReview({
      draft: draft([
        proposal({
          key: "issue.0",
          kind: "issue",
          field: null,
          label: null,
          value: null,
          category: null,
          issue: null,
          withheld: true,
          gap: "This cited sources that were never provided, so it was withheld.",
        }),
      ]),
    });

    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByText(/cited sources that were never provided/)).toBeInTheDocument();
  });

  it("applies only the ticked items, with edits included", async () => {
    // Both narrative fields already have content, so they start unticked --
    // only the issue and the interested party, both cited against an empty
    // sheet, are ticked by default.
    renderReview({
      context: contextRecord({
        organization_description: "Already written.",
        ai_usage_overview: "Already written.",
      }),
    });

    await userEvent.click(screen.getByRole("button", { name: /^Apply \d+ item/ }));

    expect(apply).toHaveBeenCalledWith({
      draftId: 9,
      accepted: {
        narrative: [],
        issues: [
          {
            key: "issue.0",
            category: "Internal",
            issue: "Staff AI literacy varies by team.",
            planned_response: "Quarterly training.",
          },
        ],
        interested_parties: [
          {
            key: "party.0",
            party: "Applicants",
            needs: "A fair, explainable process.",
            expectations: null,
            requirements: null,
          },
        ],
      },
    });
  });

  it("can't apply when nothing is selected", () => {
    renderReview({ draft: draft([proposal({ uncited: true, citations: [] })]) });

    expect(screen.getByRole("button", { name: "Apply 0 items" })).toBeDisabled();
  });

  it("links each source back to its record", () => {
    renderReview();

    const sources = screen.getByRole("list", { name: "Sources the draft drew on" });
    expect(
      within(sources).getByRole("link", { name: /AI systems in the inventory/ }),
    ).toHaveAttribute("href", "/ai-systems");
  });

  it("discards the draft", async () => {
    renderReview();

    await userEvent.click(screen.getByRole("button", { name: "Discard draft" }));

    expect(discard).toHaveBeenCalledWith(9);
  });

  it("redrafts with new guidance", async () => {
    generate.mockResolvedValue(standard());
    renderReview();

    await userEvent.type(
      screen.getByLabelText("Add guidance and redraft"),
      "Say more about GDPR.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Redraft with this guidance" }));

    expect(generate).toHaveBeenCalledWith("Say more about GDPR.");
  });
});

describe("OrganizationContextDraftPanel", () => {
  const renderPanel = () =>
    render(
      <MemoryRouter>
        <OrganizationContextDraftPanel context={contextRecord()} />
      </MemoryRouter>,
    );

  it("offers nothing when no provider is configured", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: false } } as never);
    vi.mocked(useLatestOrganizationContextDraft).mockReturnValue({ data: undefined } as never);

    const { container } = renderPanel();

    expect(container).toBeEmptyDOMElement();
  });

  it("offers to draft with AI", async () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestOrganizationContextDraft).mockReturnValue({
      data: null,
      isLoading: false,
    } as never);

    renderPanel();
    await userEvent.type(
      screen.getByLabelText("Guidance (optional)"),
      "Keep it under two sentences.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Draft with AI" }));

    expect(generate).toHaveBeenCalledWith("Keep it under two sentences.");
  });

  it("drafts with no guidance when the field is left empty", async () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestOrganizationContextDraft).mockReturnValue({
      data: null,
      isLoading: false,
    } as never);

    renderPanel();
    await userEvent.click(screen.getByRole("button", { name: "Draft with AI" }));

    expect(generate).toHaveBeenCalledWith(undefined);
  });

  it("reopens a draft that is still waiting for review", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestOrganizationContextDraft).mockReturnValue({ data: standard() } as never);

    renderPanel();

    expect(screen.getByRole("region", { name: "AI draft for review" })).toBeInTheDocument();
  });
});
