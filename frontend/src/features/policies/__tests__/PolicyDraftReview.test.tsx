import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAiAssistStatus } from "../../ai-assist/hooks";
import {
  type PolicyDraft,
  type PolicyDraftProposal,
  useApplyPolicyDraft,
  useDiscardPolicyDraft,
  useGeneratePolicyDraft,
  useLatestPolicyDraft,
} from "../aiDraft";
import { PolicyDraftPanel } from "../components/PolicyDraftPanel";
import { PolicyDraftReview } from "../components/PolicyDraftReview";
import type { Policy } from "../types";

vi.mock("../aiDraft", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../aiDraft")>()),
  useApplyPolicyDraft: vi.fn(),
  useDiscardPolicyDraft: vi.fn(),
  useGeneratePolicyDraft: vi.fn(),
  useLatestPolicyDraft: vi.fn(),
}));
vi.mock("../../ai-assist/hooks", () => ({ useAiAssistStatus: vi.fn() }));

const apply = vi.fn();
const discard = vi.fn();
const generate = vi.fn();

function policy(overrides: Partial<Policy> = {}): Policy {
  return {
    id: 3,
    title: "Draft Policy",
    description: null,
    status: "draft",
    version: 1,
    owner_id: null,
    effective_date: null,
    next_review_date: null,
    shared_with_employees: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function proposal(overrides: Partial<PolicyDraftProposal> = {}): PolicyDraftProposal {
  return {
    key: "policy.title",
    section: "narrative",
    field: "title",
    label: "Title",
    value: "AI Acceptable Use Policy",
    citations: [1],
    gap: null,
    uncited: false,
    withheld: false,
    ...overrides,
  };
}

function draft(proposals: PolicyDraftProposal[]): PolicyDraft {
  return {
    id: 7,
    status: "ready",
    provider: "anthropic",
    model: "claude-sonnet-5",
    requested_by: 1,
    created_at: "2026-01-01T00:00:00Z",
    proposals,
    sources: [
      {
        n: 1,
        title: "Controls tagged to this policy",
        section: null,
        kind: "TaggedControls",
        href: "/frameworks",
        download_evidence_id: null,
        read_by_ocr: false,
        excerpt: "ISO 42001 6.1.2: Risk assessment.",
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
      key: "policy.description",
      field: "description",
      label: "Description",
      value: "Sets the rules for using AI systems.",
    }),
  ]);

function renderReview(overrides?: { draft?: PolicyDraft; policy?: Policy }) {
  return render(
    <MemoryRouter>
      <PolicyDraftReview
        draft={overrides?.draft ?? standard()}
        policy={overrides?.policy ?? policy()}
      />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apply.mockResolvedValue({});
  vi.mocked(useApplyPolicyDraft).mockReturnValue({
    mutateAsync: apply,
    isPending: false,
  } as never);
  vi.mocked(useDiscardPolicyDraft).mockReturnValue({
    mutateAsync: discard,
    isPending: false,
  } as never);
  vi.mocked(useGeneratePolicyDraft).mockReturnValue({
    mutateAsync: generate,
    isPending: false,
  } as never);
});

describe("PolicyDraftReview", () => {
  it("ticks a cited field when the current record is empty", () => {
    // description is null by default -- title, required at creation, is
    // never genuinely empty, so it starts unticked (covered below).
    renderReview();

    expect(screen.getByRole("checkbox", { name: "Apply Description" })).toBeChecked();
  });

  it("does not pre-tick a field the record already has content for", () => {
    renderReview({ policy: policy({ description: "Already described." }) });

    expect(screen.getByRole("checkbox", { name: "Apply Description" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Apply Title" })).not.toBeChecked();
  });

  it("offers no way to apply a withheld field, and shows why", () => {
    renderReview({
      draft: draft([
        proposal({
          value: null,
          withheld: true,
          gap: "This cited sources that were never provided, so it was withheld.",
        }),
      ]),
    });

    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByText(/cited sources that were never provided/)).toBeInTheDocument();
  });

  it("applies only the ticked fields, with edits included", async () => {
    // Both fields already have content, so they start unticked.
    renderReview({
      policy: policy({ title: "Already Titled", description: "Already described." }),
    });

    await userEvent.click(
      screen.getByRole("checkbox", { name: "Apply Description" }),
    );
    await userEvent.click(screen.getByRole("button", { name: /^Apply \d+ field/ }));

    expect(apply).toHaveBeenCalledWith({
      draftId: 7,
      accepted: [{ key: "policy.description", value: "Sets the rules for using AI systems." }],
    });
  });

  it("can't apply when nothing is selected", () => {
    renderReview({ draft: draft([proposal({ uncited: true, citations: [] })]) });

    expect(screen.getByRole("button", { name: "Apply 0 fields" })).toBeDisabled();
  });

  it("links each source back to its page", () => {
    renderReview();

    const sources = screen.getByRole("list", { name: "Sources the draft drew on" });
    expect(
      within(sources).getByRole("link", { name: /Controls tagged to this policy/ }),
    ).toHaveAttribute("href", "/frameworks");
  });

  it("discards the draft", async () => {
    renderReview();

    await userEvent.click(screen.getByRole("button", { name: "Discard draft" }));

    expect(discard).toHaveBeenCalledWith(7);
  });

  it("redrafts with new guidance", async () => {
    generate.mockResolvedValue(standard());
    renderReview();

    await userEvent.type(
      screen.getByLabelText("Add guidance and redraft"),
      "Say more about exceptions.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Redraft with this guidance" }));

    expect(generate).toHaveBeenCalledWith("Say more about exceptions.");
  });
});

describe("PolicyDraftPanel", () => {
  const renderPanel = (overrides: Partial<Policy> = {}) =>
    render(
      <MemoryRouter>
        <PolicyDraftPanel policy={policy(overrides)} />
      </MemoryRouter>,
    );

  it("offers nothing when no provider is configured", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: false } } as never);
    vi.mocked(useLatestPolicyDraft).mockReturnValue({ data: undefined } as never);

    const { container } = renderPanel();

    expect(container).toBeEmptyDOMElement();
  });

  it("offers nothing once the policy has left draft status", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestPolicyDraft).mockReturnValue({ data: undefined } as never);

    const { container } = renderPanel({ status: "in_review" });

    expect(container).toBeEmptyDOMElement();
  });

  it("offers to draft with AI", async () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestPolicyDraft).mockReturnValue({ data: null, isLoading: false } as never);

    renderPanel();
    await userEvent.type(
      screen.getByLabelText("Guidance (optional)"),
      "Keep it concise.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Draft with AI" }));

    expect(generate).toHaveBeenCalledWith("Keep it concise.");
  });

  it("reopens a draft that is still waiting for review", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestPolicyDraft).mockReturnValue({ data: standard() } as never);

    renderPanel();

    expect(screen.getByRole("region", { name: "AI draft for review" })).toBeInTheDocument();
  });
});
