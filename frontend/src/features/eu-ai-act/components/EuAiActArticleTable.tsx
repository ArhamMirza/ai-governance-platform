import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useClearArticleOverride, useEuAiActArticles, useSetArticleOverride } from "../hooks";
import type { Applicability, EuAiActArticle } from "../types";

type OverrideChoice = "automatic" | Applicability;

function ArticleRow({ article }: { article: EuAiActArticle }) {
  const setOverride = useSetArticleOverride();
  const clearOverride = useClearArticleOverride();
  const [choice, setChoice] = useState<OverrideChoice>(article.override_applicability ?? "automatic");
  const [justification, setJustification] = useState(article.override_justification ?? "");
  const error = setOverride.error ?? clearOverride.error;

  const changeChoice = (next: OverrideChoice) => {
    setChoice(next);
    // Back to automatic saves at once; an override waits for its
    // justification.
    if (next === "automatic" && article.override_applicability !== null) {
      clearOverride.mutate(article.id);
    }
  };

  const overrideDirty =
    choice !== "automatic" &&
    (choice !== article.override_applicability ||
      justification !== (article.override_justification ?? ""));

  return (
    <tr>
      <td data-type="code">{article.code}</td>
      <td>{article.title}</td>
      <td>
        <StatusBadge status={article.applicable ? "applicable" : "not_applicable"} />
      </td>
      <td>{article.reason}</td>
      <td>
        <select
          aria-label={`Override for ${article.code}`}
          value={choice}
          onChange={(e) => changeChoice(e.target.value as OverrideChoice)}
        >
          <option value="automatic">
            Automatic ({article.automatic_applicable ? "applies" : "doesn't apply"})
          </option>
          <option value="applicable">Applies</option>
          <option value="not_applicable">Doesn't apply</option>
        </select>
        {choice !== "automatic" && (
          <>
            <textarea
              aria-label={`Override justification for ${article.code}`}
              placeholder="Why this differs from the assessment"
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
            />
            <button
              onClick={() =>
                setOverride.mutate({ controlId: article.id, applicability: choice, justification })
              }
              disabled={!overrideDirty || !justification.trim() || setOverride.isPending}
            >
              Save Override
            </button>
          </>
        )}
        {error && (
          <p role="alert">{error instanceof ApiError ? error.message : "Failed to save."}</p>
        )}
      </td>
    </tr>
  );
}

export function EuAiActArticleTable() {
  const { data: articles, isLoading, isError } = useEuAiActArticles();

  if (isLoading) return <p>Loading articles...</p>;
  if (isError || !articles) return <p>Failed to load articles.</p>;

  return (
    <table>
      <thead>
        <tr>
          <th>Article</th>
          <th>Title</th>
          <th>Applies?</th>
          <th>Why</th>
          <th>Override</th>
        </tr>
      </thead>
      <tbody>
        {articles.map((article) => (
          <ArticleRow
            key={`${article.id}-${article.override_applicability ?? "auto"}`}
            article={article}
          />
        ))}
      </tbody>
    </table>
  );
}
