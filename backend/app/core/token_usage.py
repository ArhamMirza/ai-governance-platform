"""Reading what a model call cost, whichever provider answered.

Every provider reports tokens a little differently, and what a person needs to
know -- how much of the prompt was served from a cache -- is spelled three ways.
LiteLLM normalises some of it; this reads the rest defensively, so a provider
that reports nothing yields zeros rather than an error and a missing field never
fails the call it describes.

    OpenAI, Gemini and most others, through LiteLLM:
        usage.prompt_tokens_details.cached_tokens
    Anthropic, through LiteLLM:
        usage.cache_read_input_tokens, usage.cache_creation_input_tokens
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenCounts:
    prompt: int = 0
    completion: int = 0
    # Prompt tokens served from a cache (cheaper), and prompt tokens written to
    # one (usually dearer than an ordinary prompt token, once).
    cache_read: int = 0
    cache_write: int = 0


def _number(value: object) -> int:
    try:
        return max(int(value), 0)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return 0


def _field(source: object, name: str) -> object:
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(name)
    return getattr(source, name, None)


def read(usage: object) -> TokenCounts:
    """Token counts from a provider's `usage`, as an object or a dict."""
    details = _field(usage, "prompt_tokens_details")
    cache_read = max(
        _number(_field(usage, "cache_read_input_tokens")),
        _number(_field(details, "cached_tokens")),
    )
    return TokenCounts(
        prompt=_number(_field(usage, "prompt_tokens")),
        completion=_number(_field(usage, "completion_tokens")),
        cache_read=cache_read,
        cache_write=_number(_field(usage, "cache_creation_input_tokens")),
    )
