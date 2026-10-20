import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

// The route table as text (Vite's raw import; this project has no Node types), so the
// links in the handbook can be checked against the pages that actually exist.
import routes from "../../app/routes.tsx?raw";
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
      "The rest of the management system",
      "Governing staff use of AI",
      "The assistant",
      "Reading the dashboard",
      "Your account & signing in",
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

  it("has a section for every entry in the table of contents, and no entry without one", () => {
    const { container } = render(<HandbookPage />);

    const toc = within(screen.getByRole("navigation", { name: "Handbook sections" }));
    const targets = toc.getAllByRole("link").map((a) => a.getAttribute("href")?.slice(1) ?? "");

    expect(targets.length).toBeGreaterThanOrEqual(14);
    for (const id of targets) {
      expect(container.querySelector(`section[id="${id}"]`), `section #${id}`).not.toBeNull();
    }
    // ...and every top-level section is reachable from the table of contents.
    const sections = [...container.querySelectorAll("section.handbook > section[id]")].map((e) => e.id);
    expect(sections.sort()).toEqual([...targets].sort());
  });

  it("only links to pages that exist", () => {
    const { container } = render(<HandbookPage />);

    const known = [...routes.matchAll(/path="([^"]+)"/g)].map((m) => m[1]);
    const internal = [...container.querySelectorAll("a[href^='/']")].map((a) => a.getAttribute("href") ?? "");

    expect(known.length).toBeGreaterThan(30);
    expect(internal.length).toBeGreaterThan(20);
    for (const href of internal) {
      expect(known, `link ${href}`).toContain(href);
    }
  });

  it("describes the employee login, which holds no permissions", () => {
    render(<HandbookPage />);

    const row = screen.getByRole("cell", { name: "Employee" }).closest("tr") as HTMLElement;
    expect(within(row).getByText(/staff home/)).toBeInTheDocument();
  });

  it("explains how staff use of AI is governed", () => {
    render(<HandbookPage />);

    const section = document.getElementById("ai-use") as HTMLElement;
    const terms = [...section.querySelectorAll("dt")].map((dt) => dt.textContent);
    expect(terms).toEqual(["The register", "Requests", "Data rules", "The browser extension"]);
    expect(within(section).getByText(/blocked by default/)).toBeInTheDocument();
  });

  it("says the assistant never changes anything", () => {
    render(<HandbookPage />);

    const section = within(document.getElementById("assistant") as HTMLElement);
    expect(section.getByText("It never changes anything")).toBeInTheDocument();
  });

  it("covers passwords, two-step sign-in and what administrators can do", () => {
    render(<HandbookPage />);

    const section = within(document.getElementById("account") as HTMLElement);
    expect(section.getByText(/At least 12 characters/)).toBeInTheDocument();
    expect(section.getByText(/ten recovery codes/)).toBeInTheDocument();
    expect(section.getByText("Reset two-step")).toBeInTheDocument();
    expect(section.getByText(/require two-step sign-in for administrators/)).toBeInTheDocument();
  });
});
