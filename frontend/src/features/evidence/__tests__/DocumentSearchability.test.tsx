import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DocumentSearchability } from "../components/DocumentSearchability";
import type { Evidence } from "../types";

function makeDoc(overrides: Partial<Evidence> = {}): Evidence {
  return {
    id: 1,
    entity_type: "Policy",
    entity_id: 1,
    folder_id: null,
    filename: "policy.pdf",
    content_type: "application/pdf",
    size_bytes: 100,
    description: null,
    index_status: "indexed",
    index_detail: "3 passage(s) indexed.",
    injection_findings: null,
    uploaded_by: null,
    uploaded_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("DocumentSearchability", () => {
  it("says nothing about a document that indexed normally", () => {
    // Every row carrying a status badge would be noise, and noise is what
    // stops people reading the rows that matter.
    const { container } = render(<DocumentSearchability doc={makeDoc()} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("says nothing while a freshly uploaded document is still being read", () => {
    const { container } = render(
      <DocumentSearchability doc={makeDoc({ index_status: "pending", index_detail: null })} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("says plainly when the assistant cannot read a document, and why", () => {
    // The failure that matters: this file is in the record but invisible to
    // search, and asking about it would return nothing for the wrong reason.
    render(
      <DocumentSearchability
        doc={makeDoc({
          index_status: "unreadable",
          index_detail: "Word 97-2003 files can't be read. Re-save it in the modern format.",
        })}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/Not searchable/i);
    expect(screen.getByRole("status")).toHaveTextContent(/Word 97-2003/);
  });

  it("reports an image it could find no text in", () => {
    render(
      <DocumentSearchability
        doc={makeDoc({
          filename: "site-photo.jpg",
          index_status: "empty",
          index_detail: "No legible text was found in this image.",
        })}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/No legible text/i);
  });

  it("notes when text was recovered from a scan rather than read", () => {
    render(
      <DocumentSearchability
        doc={makeDoc({
          index_detail: "2 page(s) were read as scans using OCR.",
        })}
      />,
    );

    expect(screen.getByText(/read as scans using OCR/i)).toBeInTheDocument();
  });

  it("surfaces a document written to instruct an AI", () => {
    render(
      <DocumentSearchability
        doc={makeDoc({ injection_findings: ["Ignore all previous instructions"] })}
      />,
    );

    const note = screen.getByRole("status");
    expect(note).toHaveTextContent(/written to instruct an AI/i);
    expect(note).toHaveTextContent(/quoted to the assistant as data, not followed/i);
  });

  it("counts additional findings rather than listing all of them", () => {
    render(
      <DocumentSearchability
        doc={makeDoc({
          injection_findings: ["Ignore all previous instructions", "You are now", "System:"],
        })}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/\+2 more/);
  });
});
