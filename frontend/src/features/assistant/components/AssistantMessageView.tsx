import { Fragment, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { API_BASE_URL } from "../../../shared/api/httpClient";
import type { AssistantMessage, Citation } from "../api";

const CITATION = /\[S(\d+)\]/g;

/**
 * Answer text with its [S#] markers turned into links to the sources below.
 *
 * Rendered as text and nothing else -- never as HTML or markdown-to-HTML. A
 * model's output is untrusted in the same way a document is: an injected
 * instruction that got a model to emit a <script> or an <img onerror> would
 * otherwise become cross-site scripting in the reader's own session.
 */
function withCitations(text: string, messageId: number, citations: Citation[]): ReactNode[] {
  const known = new Set(citations.map((c) => c.n));
  const nodes: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(CITATION)) {
    const n = Number(match[1]);
    nodes.push(text.slice(last, match.index));
    if (known.has(n)) {
      nodes.push(
        <a
          key={`${match.index}-${n}`}
          className="assistant-cite"
          href={`#cite-${messageId}-${n}`}
          aria-label={`Source ${n}`}
        >
          {n}
        </a>,
      );
    }
    last = (match.index ?? 0) + match[0].length;
  }
  nodes.push(text.slice(last));
  return nodes;
}

function Paragraphs({ message }: { message: AssistantMessage }) {
  const citations = message.citations ?? [];
  const blocks = message.content.split(/\n{2,}/).filter((b) => b.trim());
  return (
    <>
      {blocks.map((block, index) => {
        const lines = block.split("\n");
        const isList = lines.every((line) => /^\s*([-*•]|\d+\.)\s+/.test(line));
        if (isList) {
          return (
            <ul key={index} className="assistant-list">
              {lines.map((line, i) => (
                <li key={i}>
                  {withCitations(line.replace(/^\s*([-*•]|\d+\.)\s+/, ""), message.id, citations)}
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={index}>
            {lines.map((line, i) => (
              <Fragment key={i}>
                {i > 0 && <br />}
                {withCitations(line, message.id, citations)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}

function SourceLink({ citation }: { citation: Citation }) {
  const label = (
    <>
      <span className="assistant-source-title">{citation.title}</span>
      {citation.section && <span className="assistant-source-section">{citation.section}</span>}
    </>
  );
  if (citation.download_evidence_id !== null) {
    return (
      <a
        className="assistant-source-link"
        href={`${API_BASE_URL}/evidence/${citation.download_evidence_id}/download`}
        target="_blank"
        rel="noreferrer"
      >
        {label}
      </a>
    );
  }
  if (citation.href) {
    return (
      <Link className="assistant-source-link" to={citation.href}>
        {label}
      </Link>
    );
  }
  return <span className="assistant-source-link">{label}</span>;
}

export function AssistantMessageView({ message }: { message: AssistantMessage }) {
  if (message.role === "user") {
    return <div className="assistant-question">{message.content}</div>;
  }

  const citations = message.citations ?? [];
  const gaps = message.coverage_gaps ?? [];
  const findings = message.injection_findings ?? [];

  return (
    <div className="assistant-answer">
      <div className="assistant-answer-body">
        <Paragraphs message={message} />
      </div>

      {(message.fabricated_citations?.length ?? 0) > 0 && (
        <p className="assistant-flag assistant-flag-danger" role="status">
          The model cited sources it was never given. Claims resting only on those were removed
          before this was shown — treat anything uncited here as unsupported.
        </p>
      )}

      {findings.length > 0 && (
        <p className="assistant-flag assistant-flag-warning" role="status">
          A source or question contained text written to instruct an AI (“{findings[0]}”
          {findings.length > 1 ? `, +${findings.length - 1} more` : ""}). It was treated as data
          and not followed.
        </p>
      )}

      {gaps.length > 0 && (
        <p className="assistant-flag assistant-flag-neutral">
          {gaps.length === 1 ? "One document" : `${gaps.length} documents`} on record couldn’t be
          read, so {gaps.length === 1 ? "it wasn’t" : "they weren’t"} searched:{" "}
          {gaps.map((g) => g.filename).join(", ")}.
        </p>
      )}

      {citations.length > 0 && (
        <ol className="assistant-sources" aria-label="Sources">
          {citations.map((citation) => (
            <li key={citation.n} id={`cite-${message.id}-${citation.n}`}>
              <span className="assistant-source-number">{citation.n}</span>
              <div className="assistant-source-detail">
                <SourceLink citation={citation} />
                {citation.read_by_ocr && (
                  <span className="assistant-source-badge">Read from a scan — may be imperfect</span>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}

      {message.retrieval_mode === "keyword" && (
        <p className="assistant-mode-note">
          Searched by keyword only on this deployment, so differently-worded matches may be missed.
        </p>
      )}
    </div>
  );
}
