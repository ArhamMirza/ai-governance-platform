"""The AI tools the platform watches for out of the box.

A starting list of widely used public AI chat and assistant sites, so a new
installation can flag them straight away. It is a catalogue, not an
approval: every entry starts unapproved. Admins add and edit entries; the
browser extension can only treat a site as an AI site if it is listed.

Single source of truth for the alembic migration that installs it
(real deployments) and for ai_tool_service.install_default_catalog, which
the seed script calls. Deliberately not exhaustive -- new tools appear
constantly, which is what the "add a tool" form and the request workflow
are for.
"""

# (name, vendor, domains)
DEFAULT_CATALOG: list[tuple[str, str, list[str]]] = [
    ("ChatGPT", "OpenAI", ["chatgpt.com", "chat.openai.com"]),
    ("Claude", "Anthropic", ["claude.ai"]),
    ("Gemini", "Google", ["gemini.google.com"]),
    ("Microsoft Copilot", "Microsoft", ["copilot.microsoft.com"]),
    ("Perplexity", "Perplexity AI", ["perplexity.ai"]),
    ("Grok", "xAI", ["grok.com"]),
    ("DeepSeek", "DeepSeek", ["chat.deepseek.com"]),
    ("Mistral Le Chat", "Mistral AI", ["chat.mistral.ai"]),
    ("Meta AI", "Meta", ["meta.ai"]),
    ("Poe", "Quora", ["poe.com"]),
    ("Character.AI", "Character Technologies", ["character.ai"]),
    ("Hugging Face Chat", "Hugging Face", ["huggingface.co"]),
]
