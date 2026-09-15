import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { aiAssistApi } from "../../ai-assist/api";
import { assistantApi } from "../api";
import { AssistantPanel } from "../components/AssistantPanel";

vi.mock("../../ai-assist/api", () => ({ aiAssistApi: { status: vi.fn() } }));
vi.mock("../api", () => ({
  assistantApi: {
    list: vi.fn(),
    start: vi.fn(),
    get: vi.fn(),
    ask: vi.fn(),
    remove: vi.fn(),
    warm: vi.fn(),
  },
}));

const statusApi = vi.mocked(aiAssistApi);
const api = vi.mocked(assistantApi);

function renderAt(path = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AssistantPanel />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const conversation = {
  id: 11,
  title: "New conversation",
  context_entity_type: null,
  context_entity_id: null,
  created_at: "2026-09-15T10:00:00Z",
  updated_at: "2026-09-15T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
  api.warm.mockResolvedValue(undefined);
  statusApi.status.mockResolvedValue({
    available: true,
    provider: "anthropic",
    model: "claude-sonnet-5",
    is_local: false,
    reason: null,
  });
});

describe("AssistantPanel", () => {
  it("offers nothing at all when no provider is configured", async () => {
    statusApi.status.mockResolvedValue({
      available: false,
      provider: null,
      model: null,
      is_local: false,
      reason: "No model configured yet.",
    });

    renderAt();

    await waitFor(() => expect(statusApi.status).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: /assistant/i })).not.toBeInTheDocument();
  });

  it("opens on a record page ready to talk about that record", async () => {
    renderAt("/policies/3");

    await userEvent.click(await screen.findByRole("button", { name: "Ask the assistant" }));

    expect(screen.getByRole("heading", { name: "Ask about this policy" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "What’s missing from this policy?" })).toBeInTheDocument();
  });

  it("starts the conversation on the record on screen, then asks", async () => {
    api.start.mockResolvedValue({ ...conversation, context_entity_type: "Policy", context_entity_id: 3 });
    api.ask.mockResolvedValue({
      id: 2,
      role: "assistant",
      content: "It names no owner.",
      citations: [],
      fabricated_citations: null,
      injection_findings: null,
      coverage_gaps: null,
      retrieval_mode: "hybrid",
      created_at: "2026-09-15T10:00:00Z",
    });
    api.get.mockResolvedValue({ ...conversation, messages: [] });

    renderAt("/policies/3");
    await userEvent.click(await screen.findByRole("button", { name: "Ask the assistant" }));
    await userEvent.type(screen.getByLabelText("Your question"), "Who owns this?{Enter}");

    await waitFor(() =>
      expect(api.start).toHaveBeenCalledWith({ context_entity_type: "Policy", context_entity_id: 3 }),
    );
    expect(api.ask).toHaveBeenCalledWith(11, "Who owns this?");
  });

  it("gives the question back when the answer fails, rather than losing it", async () => {
    api.start.mockResolvedValue(conversation);
    api.ask.mockRejectedValue(new Error("budget exhausted"));

    renderAt("/");
    await userEvent.click(await screen.findByRole("button", { name: "Ask the assistant" }));
    await userEvent.type(screen.getByLabelText("Your question"), "What is our retention period?{Enter}");

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByLabelText("Your question")).toHaveValue("What is our retention period?");
  });

  it("lists your earlier conversations", async () => {
    api.list.mockResolvedValue([{ ...conversation, title: "Resume Screener retention" }]);

    renderAt("/");
    await userEvent.click(await screen.findByRole("button", { name: "Ask the assistant" }));
    await userEvent.click(screen.getByRole("button", { name: "History" }));

    expect(await screen.findByText("Resume Screener retention")).toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    renderAt("/");
    await userEvent.click(await screen.findByRole("button", { name: "Ask the assistant" }));

    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("complementary", { name: "Assistant" })).not.toBeInTheDocument();
  });
});
