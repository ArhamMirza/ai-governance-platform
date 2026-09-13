import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HandbookPage } from "../HandbookPage";

describe("HandbookPage", () => {
  it("renders every section named in the table of contents", () => {
    render(<HandbookPage />);

    expect(screen.getByRole("heading", { name: "Governance Handbook", level: 1 })).toBeInTheDocument();
    [
      "Who does what",
      "The AI system life cycle",
      "The Data Inventory",
      "Impact & risk assessments",
      "Policies & procedures",
      "Retiring a system",
      "Evidence & documents",
      "Frameworks & the Statement of Applicability",
      "Reading the dashboard",
      "Editing in bulk, safely",
      "Quick reference",
    ].forEach((heading) => {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    });
  });

  it("shows all seven life cycle stages plus Archive", () => {
    render(<HandbookPage />);

    const stages = screen.getByLabelText("Life cycle stages");
    expect(stages.querySelectorAll("li")).toHaveLength(8);
  });

  it("shows one gate card per life cycle stage", () => {
    render(<HandbookPage />);

    expect(document.querySelectorAll(".stage-gate")).toHaveLength(7);
  });
});
