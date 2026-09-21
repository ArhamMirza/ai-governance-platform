import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAiAssistStatus } from "../../ai-assist/hooks";
import {
  type ProcedureDraft,
  type ProcedureDraftProposal,
  useApplyProcedureDraft,
  useDiscardProcedureDraft,
  useGenerateProcedureDraft,
  useLatestProcedureDraft,
} from "../aiDraft";
import { ProcedureDraftPanel } from "../components/ProcedureDraftPanel";
import { ProcedureDraftReview } from "../components/ProcedureDraftReview";
import type { Procedure } from "../types";

vi.mock("../aiDraft", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../aiDraft")>()),
  useApplyProcedureDraft: vi.fn(),
  useDiscardProcedureDraft: vi.fn(),
  useGenerateProcedureDraft: vi.fn(),
  useLatestProcedureDraft: vi.fn(),
}));
vi.mock("../../ai-assist/hooks", () => ({ useAiAssistStatus: vi.fn() }));

const apply = vi.fn();
const discard = vi.fn();
const generate = vi.fn();

function procedure(overrides: Partial<Procedure> = {}): Procedure {
  return {
    id: 4,
    title: "Draft Procedure",
    description: null,
    status: "draft",
    version: 1,
    owner_id: null,
    policy_id: null,
    effective_date: null,
    next_review_date: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function proposal(overrides: Partial<ProcedureDraftProposal> = {}): ProcedureDraftProposal {
  return {
    key: "procedure.title",
    section: "narrative",
    field: "title",
    label: "Title",
    value: "Model Review Procedure",
    citations: [1],
    gap: null,
    uncited: false,
    withheld: false,
    ...overrides,
  };
}

function draft(proposals: ProcedureDraftProposal[]): ProcedureDraft {
  return {
    id: 8,
    status: "ready",
    provider: "anthropic",
    model: "claude-sonnet-5",
    requested_by: 1,
    created_at: "2026-01-01T00:00:00Z",
    proposals,
    sources: [
      {
        n: 1,
        title: "The policy this procedure implements",
        section: null,
        kind: "ParentPolicy",
        href: "/policies/1",
        download_evidence_id: null,
        read_by_ocr: false,
        excerpt: "Title: Model Review Policy",
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
      key: "procedure.description",
      field: "description",
      label: "Description",
      value: "How models get reviewed before deployment.",
    }),
  ]);

function renderReview(overrides?: { draft?: ProcedureDraft; procedure?: Procedure }) {
  return render(
    <MemoryRouter>
      <ProcedureDraftReview
        draft={overrides?.draft ?? standard()}
        procedure={overrides?.procedure ?? procedure()}
      />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apply.mockResolvedValue({});
  vi.mocked(useApplyProcedureDraft).mockReturnValue({
    mutateAsync: apply,
    isPending: false,
  } as never);
  vi.mocked(useDiscardProcedureDraft).mockReturnValue({
    mutateAsync: discard,
    isPending: false,
  } as never);
  vi.mocked(useGenerateProcedureDraft).mockReturnValue({
    mutateAsync: generate,
    isPending: false,
  } as never);
});

describe("ProcedureDraftReview", () => {
  it("ticks a cited field when the current record is empty", () => {
    // description is null by default -- title, required at creation, is
    // never genuinely empty, so it starts unticked (covered below).
    renderReview();

    expect(screen.getByRole("checkbox", { name: "Apply Description" })).toBeChecked();
  });

  it("does not pre-tick a field the record already has content for", () => {
    renderReview({ procedure: procedure({ description: "Already described." }) });

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
      procedure: procedure({ title: "Already Titled", description: "Already described." }),
    });

    await userEvent.click(screen.getByRole("checkbox", { name: "Apply Description" }));
    await userEvent.click(screen.getByRole("button", { name: /^Apply \d+ field/ }));

    expect(apply).toHaveBeenCalledWith({
      draftId: 8,
      accepted: [
        { key: "procedure.description", value: "How models get reviewed before deployment." },
      ],
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
      within(sources).getByRole("link", { name: /The policy this procedure implements/ }),
    ).toHaveAttribute("href", "/policies/1");
  });

  it("discards the draft", async () => {
    renderReview();

    await userEvent.click(screen.getByRole("button", { name: "Discard draft" }));

    expect(discard).toHaveBeenCalledWith(8);
  });

  it("redrafts with new guidance", async () => {
    generate.mockResolvedValue(standard());
    renderReview();

    await userEvent.type(
      screen.getByLabelText("Add guidance and redraft"),
      "Say more about sign-off.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Redraft with this guidance" }));

    expect(generate).toHaveBeenCalledWith("Say more about sign-off.");
  });
});

describe("ProcedureDraftPanel", () => {
  const renderPanel = (overrides: Partial<Procedure> = {}) =>
    render(
      <MemoryRouter>
        <ProcedureDraftPanel procedure={procedure(overrides)} />
      </MemoryRouter>,
    );

  it("offers nothing when no provider is configured", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: false } } as never);
    vi.mocked(useLatestProcedureDraft).mockReturnValue({ data: undefined } as never);

    const { container } = renderPanel();

    expect(container).toBeEmptyDOMElement();
  });

  it("offers nothing once the procedure has left draft status", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestProcedureDraft).mockReturnValue({ data: undefined } as never);

    const { container } = renderPanel({ status: "in_review" });

    expect(container).toBeEmptyDOMElement();
  });

  it("offers to draft with AI", async () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestProcedureDraft).mockReturnValue({ data: null, isLoading: false } as never);

    renderPanel();
    await userEvent.type(screen.getByLabelText("Guidance (optional)"), "Keep it concise.");
    await userEvent.click(screen.getByRole("button", { name: "Draft with AI" }));

    expect(generate).toHaveBeenCalledWith("Keep it concise.");
  });

  it("reopens a draft that is still waiting for review", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({ data: { available: true } } as never);
    vi.mocked(useLatestProcedureDraft).mockReturnValue({ data: standard() } as never);

    renderPanel();

    expect(screen.getByRole("region", { name: "AI draft for review" })).toBeInTheDocument();
  });
});
