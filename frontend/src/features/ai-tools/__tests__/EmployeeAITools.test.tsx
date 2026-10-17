import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { staffAiToolsApi } from "../api";
import { MyAIToolRequests } from "../components/MyAIToolRequests";
import { RequestAIToolForm } from "../components/RequestAIToolForm";
import { StaffAITools } from "../components/StaffAITools";
import { makeStaffTool } from "./fixtures";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

const PURPOSE = "Checking public sources quickly while researching suppliers.";

describe("StaffAITools", () => {
  it("shows each approved tool with its address, what data it may take and its conditions", async () => {
    vi.mocked(staffAiToolsApi.approved).mockResolvedValue([
      makeStaffTool({ conditions_of_use: "Sign in with your work account." }),
      makeStaffTool({
        id: 2,
        name: "Perplexity",
        vendor: null,
        domains: ["perplexity.ai"],
        status: "restricted",
        max_data_classification: "public",
      }),
    ]);

    renderWithProviders(<StaffAITools />);

    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Microsoft Copilot");
    expect(items[0]).toHaveTextContent("copilot.microsoft.com · up to internal data");
    expect(items[0]).toHaveTextContent("Sign in with your work account.");
    expect(items[0]).not.toHaveTextContent("limited use");
    expect(items[1]).toHaveTextContent("up to public data · limited use");
  });

  it("says when nothing has been approved, and points to asking", async () => {
    vi.mocked(staffAiToolsApi.approved).mockResolvedValue([]);

    renderWithProviders(<StaffAITools />);

    expect(
      await screen.findByText("No AI tools have been approved yet. You can ask for one below."),
    ).toBeInTheDocument();
  });
});

describe("RequestAIToolForm", () => {
  it("asks for a new tool by name and website", async () => {
    vi.mocked(staffAiToolsApi.requestable).mockResolvedValue([]);
    vi.mocked(staffAiToolsApi.request).mockResolvedValue({} as never);
    const onRequested = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<RequestAIToolForm onRequested={onRequested} />);

    await user.type(screen.getByLabelText("Name of the tool"), "  Mystery AI ");
    await user.type(screen.getByLabelText("Its website, if you know it"), "mystery.ai");
    await user.type(screen.getByLabelText("What would you use it for?"), PURPOSE);
    await user.type(screen.getByLabelText(/What kind of information/), "Public web pages");
    await user.click(screen.getByRole("button", { name: "Send request" }));

    expect(staffAiToolsApi.request).toHaveBeenCalledWith({
      tool_id: null,
      tool_name: "Mystery AI",
      domain: "mystery.ai",
      purpose: PURPOSE,
      data_involved: "Public web pages",
    });
    expect(onRequested).toHaveBeenCalledWith("Mystery AI");
  });

  it("asks for a known tool from the list, without typing its name or address", async () => {
    vi.mocked(staffAiToolsApi.requestable).mockResolvedValue([
      { id: 7, name: "Claude", vendor: "Anthropic" },
    ]);
    vi.mocked(staffAiToolsApi.request).mockResolvedValue({} as never);
    const user = userEvent.setup();
    renderWithProviders(<RequestAIToolForm />);

    await screen.findByRole("option", { name: "Claude (Anthropic)" });
    await user.type(screen.getByLabelText("Name of the tool"), "ignored");
    await user.type(screen.getByLabelText("Its website, if you know it"), "ignored.example");
    await user.selectOptions(screen.getByLabelText("Which tool?"), "7");
    expect(screen.queryByLabelText("Name of the tool")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("What would you use it for?"), PURPOSE);
    await user.click(screen.getByRole("button", { name: "Send request" }));

    expect(staffAiToolsApi.request).toHaveBeenCalledWith({
      tool_id: 7,
      tool_name: "Claude",
      domain: null,
      purpose: PURPOSE,
      data_involved: null,
    });
  });

  it("needs a name for a tool that isn't listed, and a real reason", async () => {
    vi.mocked(staffAiToolsApi.requestable).mockResolvedValue([]);
    const user = userEvent.setup();
    renderWithProviders(<RequestAIToolForm />);

    await user.type(screen.getByLabelText("What would you use it for?"), "too short");
    await user.click(screen.getByRole("button", { name: "Send request" }));

    expect(await screen.findByText("What is the tool called?")).toBeInTheDocument();
    expect(screen.getByText("Tell us a little more about what you'd use it for")).toBeInTheDocument();
    expect(staffAiToolsApi.request).not.toHaveBeenCalled();
  });

  it("says why when the request couldn't be sent", async () => {
    vi.mocked(staffAiToolsApi.requestable).mockResolvedValue([]);
    vi.mocked(staffAiToolsApi.request).mockRejectedValue(
      new ApiError(409, JSON.stringify({ detail: "You have already asked for this tool." })),
    );
    const user = userEvent.setup();
    renderWithProviders(<RequestAIToolForm />);

    await user.type(screen.getByLabelText("Name of the tool"), "Mystery AI");
    await user.type(screen.getByLabelText("What would you use it for?"), PURPOSE);
    await user.click(screen.getByRole("button", { name: "Send request" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("You have already asked for this tool.");
  });
});

describe("MyAIToolRequests", () => {
  it("shows each request and how it was answered", async () => {
    vi.mocked(staffAiToolsApi.mine).mockResolvedValue([
      {
        id: 1,
        tool_name: "Character.AI",
        domain: null,
        purpose: "Practising difficult conversations.",
        requested_on: "2026-05-01",
        status: "rejected",
        decided_on: "2026-05-03",
        decision_note: "No business data-protection terms.",
      },
      {
        id: 2,
        tool_name: "Claude",
        domain: null,
        purpose: "Drafting policies.",
        requested_on: "2026-06-01",
        status: "requested",
        decided_on: null,
        decision_note: null,
      },
    ]);

    renderWithProviders(<MyAIToolRequests />);

    const items = await screen.findAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Character.AI");
    expect(items[0]).toHaveTextContent("Not approved");
    expect(items[0]).toHaveTextContent("Answered 2026-05-03: No business data-protection terms.");
    expect(items[1]).toHaveTextContent("Waiting for a decision");
    expect(items[1]).not.toHaveTextContent("Answered");
  });

  it("says when nothing has been asked for", async () => {
    vi.mocked(staffAiToolsApi.mine).mockResolvedValue([]);

    renderWithProviders(<MyAIToolRequests />);

    expect(await screen.findByText("You haven't asked for any tools.")).toBeInTheDocument();
  });
});
