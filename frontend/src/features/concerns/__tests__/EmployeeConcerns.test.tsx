import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { staffConcernsApi } from "../api";
import { ConcernSubmittedNotice } from "../components/ConcernSubmittedNotice";
import { MyConcerns } from "../components/MyConcerns";
import { ReportConcernForm } from "../components/ReportConcernForm";
import { makeReporterConcern } from "./fixtures";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubStaffData() {
  vi.mocked(staffConcernsApi.aiSystems).mockResolvedValue([
    { id: 7, name: "Resume Screener" },
    { id: 9, name: "Support Chatbot" },
  ]);
  vi.mocked(staffConcernsApi.process).mockResolvedValue({
    process_description: "Tell us here. We acknowledge every concern within 7 days.",
    acknowledge_within_days: 7,
  });
}

const DESCRIPTION = "The screener keeps ranking candidates from one university first.";

describe("ReportConcernForm", () => {
  it("sends a named concern about a chosen system", async () => {
    stubStaffData();
    vi.mocked(staffConcernsApi.submit).mockResolvedValue({
      tracking_code: "ABCD-EFGH-JKMN",
      concern: makeReporterConcern(),
    });
    const onSubmitted = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<ReportConcernForm onSubmitted={onSubmitted} />);

    await screen.findByRole("option", { name: "Resume Screener" });
    await user.selectOptions(screen.getByLabelText("What is it about?"), "bias_or_fairness");
    await user.selectOptions(screen.getByLabelText("Which AI system?"), "7");
    await user.type(screen.getByLabelText("What's your concern?"), DESCRIPTION);
    await user.click(screen.getByRole("button", { name: "Send concern" }));

    expect(staffConcernsApi.submit).toHaveBeenCalledWith({
      category: "bias_or_fairness",
      description: DESCRIPTION,
      ai_system_row_id: 7,
      system_note: null,
      anonymous: false,
    });
    expect(onSubmitted).toHaveBeenCalledWith(expect.objectContaining({ tracking_code: "ABCD-EFGH-JKMN" }));
  });

  it("asks where they came across it when they aren't sure which system", async () => {
    stubStaffData();
    vi.mocked(staffConcernsApi.submit).mockResolvedValue({
      tracking_code: "ABCD-EFGH-JKMN",
      concern: makeReporterConcern(),
    });
    const user = userEvent.setup();
    renderWithProviders(<ReportConcernForm onSubmitted={vi.fn()} />);

    await user.type(await screen.findByLabelText("Where did you come across it?"), "The HR portal");
    await user.type(screen.getByLabelText("What's your concern?"), DESCRIPTION);
    await user.click(screen.getByRole("button", { name: "Send concern" }));

    expect(staffConcernsApi.submit).toHaveBeenCalledWith(
      expect.objectContaining({ ai_system_row_id: null, system_note: "The HR portal" }),
    );
  });

  it("drops the note when a system is chosen", async () => {
    stubStaffData();
    vi.mocked(staffConcernsApi.submit).mockResolvedValue({
      tracking_code: "ABCD-EFGH-JKMN",
      concern: makeReporterConcern(),
    });
    const user = userEvent.setup();
    renderWithProviders(<ReportConcernForm onSubmitted={vi.fn()} />);

    await user.type(await screen.findByLabelText("Where did you come across it?"), "Somewhere");
    await screen.findByRole("option", { name: "Support Chatbot" });
    await user.selectOptions(screen.getByLabelText("Which AI system?"), "9");
    expect(screen.queryByLabelText("Where did you come across it?")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("What's your concern?"), DESCRIPTION);
    await user.click(screen.getByRole("button", { name: "Send concern" }));

    expect(staffConcernsApi.submit).toHaveBeenCalledWith(
      expect.objectContaining({ ai_system_row_id: 9, system_note: null }),
    );
  });

  it("says plainly what anonymous means, and sends it when chosen", async () => {
    stubStaffData();
    vi.mocked(staffConcernsApi.submit).mockResolvedValue({
      tracking_code: "ABCD-EFGH-JKMN",
      concern: makeReporterConcern({ is_anonymous: true }),
    });
    const user = userEvent.setup();
    renderWithProviders(<ReportConcernForm onSubmitted={vi.fn()} />);

    expect(await screen.findByText(/Your name goes with this concern/)).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: "Report anonymously" }));
    expect(screen.queryByText(/Your name goes with this concern/)).not.toBeInTheDocument();
    expect(screen.getByText(/We won't store your name or account/)).toBeInTheDocument();
    expect(screen.getByText(/what you write can still point to you/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("What's your concern?"), DESCRIPTION);
    await user.click(screen.getByRole("button", { name: "Send concern" }));

    expect(staffConcernsApi.submit).toHaveBeenCalledWith(
      expect.objectContaining({ anonymous: true }),
    );
  });

  it("shows what staff have been told about the process", async () => {
    stubStaffData();
    renderWithProviders(<ReportConcernForm onSubmitted={vi.fn()} />);

    expect(await screen.findByText(/We acknowledge every concern within 7 days/)).toBeInTheDocument();
  });

  it("asks for more than a few words", async () => {
    stubStaffData();
    const user = userEvent.setup();
    renderWithProviders(<ReportConcernForm onSubmitted={vi.fn()} />);

    await user.type(await screen.findByLabelText("What's your concern?"), "too short");
    await user.click(screen.getByRole("button", { name: "Send concern" }));

    expect(await screen.findByText(/Tell us a little more/)).toBeInTheDocument();
    expect(staffConcernsApi.submit).not.toHaveBeenCalled();
  });

  it("says so when it couldn't be sent", async () => {
    stubStaffData();
    vi.mocked(staffConcernsApi.submit).mockRejectedValue(new ApiError(500, "boom"));
    const user = userEvent.setup();
    renderWithProviders(<ReportConcernForm onSubmitted={vi.fn()} />);

    await user.type(await screen.findByLabelText("What's your concern?"), DESCRIPTION);
    await user.click(screen.getByRole("button", { name: "Send concern" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});

describe("ConcernSubmittedNotice", () => {
  it("shows the code once, with a warning that an anonymous one can't be shown again", () => {
    renderWithProviders(
      <ConcernSubmittedNotice
        result={{
          tracking_code: "ABCD-EFGH-JKMN",
          concern: makeReporterConcern({ is_anonymous: true }),
        }}
      />,
    );

    expect(screen.getByText("ABCD-EFGH-JKMN")).toBeInTheDocument();
    expect(screen.getByText(/It was sent anonymously/)).toBeInTheDocument();
    expect(screen.getByText(/it can't be shown again/)).toBeInTheDocument();
  });

  it("tells someone who gave their name where to follow it", () => {
    renderWithProviders(
      <ConcernSubmittedNotice
        result={{ tracking_code: "ABCD-EFGH-JKMN", concern: makeReporterConcern() }}
      />,
    );

    expect(screen.getByText("It was sent under your name.")).toBeInTheDocument();
    expect(screen.getByText(/You'll find this concern under My concerns/)).toBeInTheDocument();
    expect(screen.queryByText(/can't be shown again/)).not.toBeInTheDocument();
  });
});

describe("MyConcerns", () => {
  it("lists the concerns raised under the person's name, with the reply", async () => {
    vi.mocked(staffConcernsApi.mine).mockResolvedValue([
      makeReporterConcern({
        status: "resolved",
        outcome: "substantiated",
        closed_on: "2026-06-20",
        reply_to_reporter: "You were right; we've fixed the ranking.",
      }),
      makeReporterConcern({ id: 2, category: "privacy_or_data", description: "Data worry here." }),
    ]);

    renderWithProviders(<MyConcerns />);

    expect(await screen.findByText("You were right; we've fixed the ranking.")).toBeInTheDocument();
    expect(screen.getByText("Outcome: Substantiated")).toBeInTheDocument();
    expect(screen.getByText("Data worry here.")).toBeInTheDocument();
    expect(screen.getByText("No reply yet.")).toBeInTheDocument();
  });

  it("says when nothing has been raised under a name", async () => {
    vi.mocked(staffConcernsApi.mine).mockResolvedValue([]);

    renderWithProviders(<MyConcerns />);

    expect(await screen.findByText("You haven't raised any concerns under your name.")).toBeInTheDocument();
  });

  it("looks up an anonymous concern by its tracking code", async () => {
    vi.mocked(staffConcernsApi.mine).mockResolvedValue([]);
    vi.mocked(staffConcernsApi.lookup).mockResolvedValue(
      makeReporterConcern({
        is_anonymous: true,
        status: "under_review",
        reply_to_reporter: "We're re-testing it.",
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<MyConcerns />);

    await user.type(await screen.findByLabelText("Tracking code"), "abcd efgh jkmn");
    await user.click(screen.getByRole("button", { name: "Look up" }));

    expect(staffConcernsApi.lookup).toHaveBeenCalledWith("abcd efgh jkmn");
    expect(await screen.findByText("We're re-testing it.")).toBeInTheDocument();
    expect(screen.getByText("Being looked into")).toBeInTheDocument();
    expect(screen.getByText(/Raised 2026-06-01 · anonymously/)).toBeInTheDocument();
  });

  it("only looks up when there's a code", async () => {
    vi.mocked(staffConcernsApi.mine).mockResolvedValue([]);
    renderWithProviders(<MyConcerns />);

    expect(await screen.findByRole("button", { name: "Look up" })).toBeDisabled();
  });

  it("says when a code matched nothing, and when too many were tried", async () => {
    vi.mocked(staffConcernsApi.mine).mockResolvedValue([]);
    vi.mocked(staffConcernsApi.lookup)
      .mockRejectedValueOnce(new ApiError(404, JSON.stringify({ detail: "Concern 0 not found" })))
      .mockRejectedValueOnce(
        new ApiError(429, JSON.stringify({ detail: "Too many tracking codes tried. Wait fifteen minutes and try again." })),
      );
    const user = userEvent.setup();
    renderWithProviders(<MyConcerns />);

    await user.type(await screen.findByLabelText("Tracking code"), "WRONG");
    await user.click(screen.getByRole("button", { name: "Look up" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Concern 0 not found");

    await user.click(screen.getByRole("button", { name: "Look up" }));
    expect(await screen.findByText(/Wait fifteen minutes/)).toBeInTheDocument();
    // Each miss counts against them, so a failed lookup is never retried by itself.
    expect(staffConcernsApi.lookup).toHaveBeenCalledTimes(2);
  });
});
