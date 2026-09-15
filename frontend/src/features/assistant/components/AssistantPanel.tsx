import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { useAiAssistStatus } from "../../ai-assist/hooks";
import { assistantApi } from "../api";
import {
  conversationKey,
  useAsk,
  useConversation,
  useConversations,
  useDeleteConversation,
  useStartConversation,
} from "../hooks";
import { pageContextFor } from "../pageContext";
import { AssistantMessageView } from "./AssistantMessageView";

let warmRequested = false;

function suggestionsFor(noun: string | null): string[] {
  if (noun) {
    return [`Summarise ${noun}`, `What’s missing from ${noun}?`, `What evidence supports ${noun}?`];
  }
  return [
    "What do our policies say about data retention?",
    "Summarise the risks recorded so far",
    "How does impact assessment approval work?",
  ];
}

function whenLabel(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  return date.toDateString() === today.toDateString()
    ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString([], { day: "numeric", month: "short" });
}

/**
 * The assistant, docked to the right of every page.
 *
 * Renders nothing when no provider is configured -- the same rule every AI
 * surface follows, so nobody is offered a control that can only fail.
 *
 * A conversation started while a record is on screen is opened on that
 * record: the server reads it directly, and "this" means what the person is
 * looking at. Moving to another page does not re-point an existing
 * conversation; starting a new one does.
 */
export function AssistantPanel() {
  const { data: status } = useAiAssistStatus();
  const location = useLocation();
  const queryClient = useQueryClient();
  const context = pageContextFor(location.pathname);

  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"thread" | "history">("thread");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const history = useConversations(open && view === "history");
  const conversation = useConversation(conversationId);
  const start = useStartConversation();
  const ask = useAsk();
  const remove = useDeleteConversation();

  const composer = useRef<HTMLTextAreaElement>(null);
  const threadEnd = useRef<HTMLDivElement>(null);

  const messages = conversation.data?.messages ?? [];

  useEffect(() => {
    // Once per page load, the moment the assistant is known to be usable. A
    // freshly started server otherwise loads its models on the first question
    // anyone asks, which costs that person several seconds of an apparently
    // hung assistant. The models are loaded once per server, so this is cheap
    // for every browser after the first.
    if (status?.available && !warmRequested) {
      warmRequested = true;
      assistantApi.warm().catch(() => {
        // Warming is an optimisation; a failure just means the first
        // question pays the loading cost instead.
      });
    }
  }, [status?.available]);

  useEffect(() => {
    if (open && view === "thread") composer.current?.focus();
  }, [open, view, conversationId]);

  useEffect(() => {
    threadEnd.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length, pendingQuestion]);

  if (!status?.available) return null;

  const busy = pendingQuestion !== null;

  const send = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    setError(null);
    setPendingQuestion(trimmed);
    setDraft("");
    try {
      let id = conversationId;
      if (id === null) {
        const created = await start.mutateAsync(
          context
            ? { context_entity_type: context.entityType, context_entity_id: context.entityId }
            : {},
        );
        id = created.id;
        setConversationId(id);
      }
      await ask.mutateAsync({ id, question: trimmed });
      // Wait for the stored answer before dropping the pending question, so
      // the thread never flickers empty between the two.
      await queryClient.fetchQuery({
        queryKey: conversationKey(id),
        queryFn: () => assistantApi.get(id as number),
      });
    } catch (err) {
      setError(readError(err, "The assistant couldn’t answer that"));
      // Nothing was stored, so give the question back rather than lose it.
      setDraft(trimmed);
    } finally {
      setPendingQuestion(null);
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void send(draft);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(draft);
    }
  };

  const newConversation = () => {
    setConversationId(null);
    setError(null);
    setView("thread");
  };

  const heading =
    conversationId !== null && conversation.data
      ? conversation.data.title
      : context
        ? `Ask about ${context.noun}`
        : "Ask the assistant";

  if (!open) {
    return (
      <button
        type="button"
        className="assistant-launcher"
        onClick={() => setOpen(true)}
        aria-expanded={false}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        Ask the assistant
      </button>
    );
  }

  return (
    <aside
      className="assistant-panel"
      aria-label="Assistant"
      onKeyDown={(event) => event.key === "Escape" && setOpen(false)}
    >
      <header className="assistant-header">
        <div className="assistant-heading">
          <span className="assistant-eyebrow">Assistant</span>
          <h2 className="assistant-title">{view === "history" ? "Your conversations" : heading}</h2>
        </div>
        <div className="assistant-header-actions">
          <button type="button" className="assistant-icon-button" onClick={newConversation}>
            New
          </button>
          <button
            type="button"
            className="assistant-icon-button"
            onClick={() => setView(view === "history" ? "thread" : "history")}
            aria-pressed={view === "history"}
          >
            History
          </button>
          <button
            type="button"
            className="assistant-icon-button"
            onClick={() => setOpen(false)}
            aria-label="Close assistant"
          >
            ✕
          </button>
        </div>
      </header>

      {view === "history" ? (
        <div className="assistant-body">
          {history.isLoading && <p className="assistant-muted">Loading…</p>}
          {history.data?.length === 0 && (
            <p className="assistant-muted">No conversations yet. They’re private to you.</p>
          )}
          <ul className="assistant-history">
            {history.data?.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="assistant-history-item"
                  onClick={() => {
                    setConversationId(item.id);
                    setView("thread");
                  }}
                >
                  <span className="assistant-history-title">{item.title}</span>
                  <span className="assistant-history-when">{whenLabel(item.updated_at)}</span>
                </button>
                <button
                  type="button"
                  className="assistant-history-delete"
                  aria-label={`Delete “${item.title}”`}
                  onClick={() => {
                    remove.mutate(item.id);
                    if (item.id === conversationId) setConversationId(null);
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <>
          <div className="assistant-body" aria-live="polite">
            {messages.length === 0 && !busy && (
              <div className="assistant-empty">
                <p>
                  Answers come from your governance records and the documents filed against them,
                  and every claim cites its source.
                </p>
                <div className="assistant-suggestions">
                  {suggestionsFor(context?.noun ?? null).map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      className="assistant-suggestion"
                      onClick={() => void send(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <AssistantMessageView key={message.id} message={message} />
            ))}

            {busy && (
              <>
                <div className="assistant-question">{pendingQuestion}</div>
                <div className="assistant-working" role="status">
                  <span className="assistant-working-dot" aria-hidden="true" />
                  Searching the record and checking citations…
                </div>
              </>
            )}

            {error && (
              <p className="assistant-flag assistant-flag-danger" role="alert">
                {error}
              </p>
            )}
            <div ref={threadEnd} />
          </div>

          <form className="assistant-composer" onSubmit={onSubmit}>
            <label htmlFor="assistant-question" className="assistant-visually-hidden">
              Your question
            </label>
            <textarea
              id="assistant-question"
              ref={composer}
              value={draft}
              rows={2}
              placeholder="Ask about a system, assessment, policy or document…"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={onKeyDown}
              disabled={busy}
              maxLength={4000}
            />
            <button type="submit" disabled={busy || !draft.trim()}>
              {busy ? "Working…" : "Ask"}
            </button>
          </form>
          <p className="assistant-footnote">
            Cited answers, checked before you see them. The assistant can’t change any record.
          </p>
        </>
      )}
    </aside>
  );
}
