import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { aiAssistApi } from "../../ai-assist/api";
import { assistantApi } from "../api";
import { AssistantPanel } from "../components/AssistantPanel";

vi.mock("../../ai-assist/api", () => ({ aiAssistApi: { status: vi.fn() } }));
vi.mock("../api", () => ({ assistantApi: { warm: vi.fn() } }));

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AssistantPanel />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// Its own file, so the once-per-page-load flag starts fresh.
describe("warming the assistant's models", () => {
  it("asks the server to load them once the assistant is usable, and only once", async () => {
    vi.mocked(aiAssistApi.status).mockResolvedValue({
      available: true,
      provider: "local",
      model: "llama3.3",
      is_local: true,
      reason: null,
    });
    vi.mocked(assistantApi.warm).mockResolvedValue(undefined);

    renderPanel();
    await screen.findByRole("button", { name: "Ask the assistant" });
    renderPanel();

    await waitFor(() => expect(assistantApi.warm).toHaveBeenCalledTimes(1));
  });
});
