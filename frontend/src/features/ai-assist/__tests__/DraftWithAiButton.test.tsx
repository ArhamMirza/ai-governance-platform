import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { aiAssistApi } from "../api";
import { DraftWithAiButton } from "../components/DraftWithAiButton";

vi.mock("../api", () => ({
  aiAssistApi: { status: vi.fn(), draft: vi.fn() },
}));

const mockApi = vi.mocked(aiAssistApi);

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function renderButton(onDraft = vi.fn()) {
  render(
    <DraftWithAiButton kind="intended_purpose" impactAssessmentId={1} onDraft={onDraft} />,
    { wrapper },
  );
  return onDraft;
}

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.status.mockResolvedValue({
    available: true,
    provider: "anthropic",
    model: "claude-sonnet-5",
    is_local: false,
    reason: null,
  });
});

describe("DraftWithAiButton", () => {
  it("offers nothing at all when no provider is configured", async () => {
    mockApi.status.mockResolvedValue({
      available: false,
      provider: null,
      model: null,
      is_local: false,
      reason: "No model configured yet.",
    });

    renderButton();

    // Not a disabled button with a tooltip -- nothing, so nobody is shown a
    // control that could only fail.
    await waitFor(() => expect(mockApi.status).toHaveBeenCalled());
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("hands the draft to the caller rather than saving it", async () => {
    mockApi.draft.mockResolvedValue({ draft: "A drafted purpose.", injection_findings: [] });
    const onDraft = renderButton();

    await userEvent.click(await screen.findByRole("button", { name: "Draft with AI" }));

    await waitFor(() => expect(onDraft).toHaveBeenCalledWith("A drafted purpose."));
    expect(mockApi.draft).toHaveBeenCalledWith({
      kind: "intended_purpose",
      impact_assessment_id: 1,
      factor: undefined,
    });
  });

  it("surfaces record text that was written to instruct a model", async () => {
    mockApi.draft.mockResolvedValue({
      draft: "A drafted purpose.",
      injection_findings: ["Ignore all previous instructions"],
    });
    renderButton();

    await userEvent.click(await screen.findByRole("button", { name: "Draft with AI" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      /written to instruct an AI/i,
    );
  });

  it("reports a failure in place instead of losing it", async () => {
    mockApi.draft.mockRejectedValue(new Error("boom"));
    const onDraft = renderButton();

    await userEvent.click(await screen.findByRole("button", { name: "Draft with AI" }));

    expect(await screen.findByText(/Couldn't draft this one/i)).toBeInTheDocument();
    expect(onDraft).not.toHaveBeenCalled();
  });
});
