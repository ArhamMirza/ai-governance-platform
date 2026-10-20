import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import type { AiProvider } from "../api";
import { useAiSettings, useUpdateAiSettings } from "../hooks";

const PROVIDERS: { value: AiProvider; label: string; suggested: string }[] = [
  { value: "anthropic", label: "Anthropic (Claude)", suggested: "claude-sonnet-5" },
  { value: "openai", label: "OpenAI", suggested: "gpt-5.1" },
  { value: "gemini", label: "Google Gemini", suggested: "gemini-2.5-pro" },
  { value: "groq", label: "Groq", suggested: "llama-3.3-70b-versatile" },
  { value: "local", label: "Self-hosted (Ollama, vLLM, LM Studio)", suggested: "llama3.3" },
];

/** What an admin needs to know before choosing: whether the records this
 * assistant reads leave the building. In a tool whose job is governing AI,
 * that belongs on the screen, not in a README. */
function egressNote(provider: AiProvider): string {
  return provider === "local"
    ? "Nothing leaves this deployment. Record text is sent only to the model you host at the URL below."
    : "Record text needed to answer a question or draft a field is sent to this provider's API. Uploaded documents are not sent unless you turn on document search.";
}

export function AiSettingsForm() {
  const { data: settings, isLoading } = useAiSettings();
  const update = useUpdateAiSettings();

  const [provider, setProvider] = useState<AiProvider>("anthropic");
  const [model, setModel] = useState("");
  const [fastModel, setFastModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [budget, setBudget] = useState(200000);
  // Empty means "leave whatever is stored alone" -- the server can never
  // send the key back, so a blank box must not read as "delete it".
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Fill the form from the stored settings whenever they (re)load.
  const [loaded, setLoaded] = useState(settings);
  if (settings && settings !== loaded) {
    setLoaded(settings);
    setProvider(settings.provider);
    setModel(settings.model);
    setFastModel(settings.fast_model ?? "");
    setBaseUrl(settings.base_url ?? "");
    setBudget(settings.daily_token_budget);
  }

  if (isLoading) return <p>Loading...</p>;

  const chooseProvider = (next: AiProvider) => {
    setProvider(next);
    // Offer that provider's usual model name, but only when the admin
    // hasn't typed something of their own.
    const current = PROVIDERS.find((p) => p.value === provider);
    if (!model || model === current?.suggested) {
      setModel(PROVIDERS.find((p) => p.value === next)?.suggested ?? "");
    }
  };

  const save = async () => {
    setError(null);
    setSaved(false);
    try {
      await update.mutateAsync({
        provider,
        model,
        fast_model: fastModel || null,
        base_url: baseUrl || null,
        daily_token_budget: budget,
        ...(apiKey ? { api_key: apiKey } : {}),
      });
      setApiKey("");
      setSaved(true);
    } catch (err) {
      setError(readError(err, "Couldn't save these settings"));
    }
  };

  return (
    <article>
      <h3 style={{ marginTop: 0 }}>AI assistance</h3>
      <p>
        Drafting help runs on the provider you choose here. Whatever you pick, the assistant can
        only read records and propose text — it cannot approve, submit, advance or delete
        anything, and nothing it writes is saved until a person keeps it.
      </p>

      {error && <p role="alert">{error}</p>}
      {saved && <p className="ai-settings-saved">Saved.</p>}

      <div>
        <label htmlFor="ai-provider">Provider</label>
        <select
          id="ai-provider"
          value={provider}
          onChange={(e) => chooseProvider(e.target.value as AiProvider)}
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        <p className="ai-settings-egress">{egressNote(provider)}</p>
      </div>

      <div>
        <label htmlFor="ai-model">Model</label>
        <input
          id="ai-model"
          value={model}
          placeholder={PROVIDERS.find((p) => p.value === provider)?.suggested}
          onChange={(e) => setModel(e.target.value)}
        />
        <p className="ai-settings-hint">
          Any model name this provider accepts — so a model released next week works without
          waiting for an update here.
        </p>
      </div>

      {provider === "local" ? (
        <div>
          <label htmlFor="ai-base-url">Model URL</label>
          <input
            id="ai-base-url"
            value={baseUrl}
            placeholder="http://localhost:11434"
            onChange={(e) => setBaseUrl(e.target.value)}
          />
          <p className="ai-settings-hint">
            http:// is accepted for this machine or a private network. A model served from
            anywhere else must use https://, or the record text and any key would cross the
            network in clear text. Put credentials in the API key field, never in this URL.
          </p>
        </div>
      ) : (
        <div>
          <label htmlFor="ai-api-key">
            API key {settings?.has_api_key ? "(configured)" : "(not set)"}
          </label>
          <input
            id="ai-api-key"
            type="password"
            autoComplete="off"
            value={apiKey}
            placeholder={settings?.has_api_key ? "Leave blank to keep the stored key" : ""}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <p className="ai-settings-hint">
            Stored encrypted and never shown again — not even here. Leave blank to keep the key
            you already saved.
          </p>
        </div>
      )}

      <div>
        <label htmlFor="ai-budget">Daily token budget, per person</label>
        <input
          id="ai-budget"
          type="number"
          min={0}
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
        />
        <p className="ai-settings-hint">
          Caps what any one person can spend in a rolling 24 hours. Set it to 0 to switch AI
          assistance off without clearing the key.
        </p>
      </div>

      <button type="submit" onClick={save} disabled={update.isPending}>
        {update.isPending ? "Saving..." : "Save AI settings"}
      </button>
    </article>
  );
}
