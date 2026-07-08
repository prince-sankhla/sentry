"""Multi-provider LLM client for the investigation reasoning layer.

The AI Investigation Engine runs with OR without a live model. When one or more
providers are configured, :func:`get_llm_client` returns a **chained** client
that tries providers in a resilient fallback order:

    Anthropic  →  OpenRouter  →  OpenAI  →  Gemini  →  (deterministic composer)

The first provider that answers wins; any provider that is unconfigured, missing
its dependency, or failing at call-time is skipped and the next is tried. If no
provider is usable, :func:`get_llm_client` returns ``None`` and the reasoning
service falls back to its deterministic, template-based composer — so the
platform is always fully functional.

Grounding contract
------------------
Whatever provider answers, the model is only ever used to *phrase* conclusions
that were already derived from an :class:`InvestigationPackage`. The caller hands
it a grounded evidence context and instructs it to answer strictly from that
context. The model explains; the backend proves. The model is never given
authority to invent procurement facts.

Transport
---------
Anthropic uses its official (optional) SDK. OpenRouter / OpenAI / Gemini are
called over their HTTP REST APIs via ``httpx`` (already a core dependency), so no
extra SDKs are required to enable them.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import get_settings


class LLMUnavailableError(RuntimeError):
    """Raised when a live model call is attempted but the provider is not usable."""


class LLMClient(Protocol):
    """Structural type every provider client satisfies."""

    provider: str
    model: str

    def complete(self, *, system: str, prompt: str, max_tokens: int | None = None) -> str: ...


# --------------------------------------------------------------------------- Anthropic


class AnthropicLLMClient:
    """Thin, dependency-optional wrapper around the Anthropic Messages API."""

    provider = "anthropic"

    def __init__(self, api_key: str, model: str, max_tokens: int, timeout: float) -> None:
        self.model = model
        self._max_tokens = max_tokens
        self._timeout = timeout
        try:
            import anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dep
            raise LLMUnavailableError(
                "anthropic package is not installed; install it to enable the Anthropic provider"
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    def complete(self, *, system: str, prompt: str, max_tokens: int | None = None) -> str:
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # pragma: no cover - network/SDK errors
            raise LLMUnavailableError(f"anthropic: {exc}") from exc

        parts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
        text = "".join(parts).strip()
        if not text:
            raise LLMUnavailableError("anthropic returned an empty response")
        return text


# --------------------------------------------------------------------------- OpenAI-compatible


class OpenAICompatLLMClient:
    """OpenAI Chat Completions client — powers both OpenAI and OpenRouter.

    Both expose the identical ``POST {base_url}/chat/completions`` contract; only
    the base URL, auth key, and (for OpenRouter) a couple of attribution headers
    differ. Implemented over ``httpx`` so no OpenAI SDK is required.
    """

    def __init__(
        self,
        *,
        provider: str,
        api_key: str,
        model: str,
        base_url: str,
        max_tokens: int,
        timeout: float,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._extra_headers = extra_headers or {}

    def complete(self, *, system: str, prompt: str, max_tokens: int | None = None) -> str:
        headers = {"Authorization": f"Bearer {self._api_key}", **self._extra_headers}
        payload = {
            "model": self.model,
            "max_tokens": max_tokens or self._max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            resp = httpx.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
        except Exception as exc:  # pragma: no cover - network errors
            raise LLMUnavailableError(f"{self.provider}: {exc}") from exc
        if not text:
            raise LLMUnavailableError(f"{self.provider} returned an empty response")
        return text


# --------------------------------------------------------------------------- Gemini


class GeminiLLMClient:
    """Google Gemini client over the Generative Language REST API (httpx)."""

    provider = "gemini"

    def __init__(self, *, api_key: str, model: str, max_tokens: int, timeout: float) -> None:
        self.model = model
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._timeout = timeout

    def complete(self, *, system: str, prompt: str, max_tokens: int | None = None) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens or self._max_tokens},
        }
        try:
            resp = httpx.post(
                url,
                params={"key": self._api_key},
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
        except Exception as exc:  # pragma: no cover - network errors
            raise LLMUnavailableError(f"gemini: {exc}") from exc
        if not text:
            raise LLMUnavailableError("gemini returned an empty response")
        return text


# --------------------------------------------------------------------------- Chain


class ChainedLLMClient:
    """Tries each configured provider in order until one answers.

    ``model`` / ``provider`` reflect whichever provider produced the most recent
    successful completion, so the reasoning layer can attribute the narrative
    accurately. Providers are constructed lazily and memoised.
    """

    def __init__(self, factories: list[tuple[str, callable]]) -> None:
        # factories: ordered [(provider_name, () -> LLMClient)]
        self._factories = factories
        self._clients: dict[str, LLMClient | None] = {}
        self.provider = factories[0][0]
        self.model = ""  # resolved after first successful complete()

    @property
    def configured_providers(self) -> list[str]:
        return [name for name, _ in self._factories]

    def _client_for(self, name: str, factory) -> LLMClient | None:
        if name not in self._clients:
            try:
                self._clients[name] = factory()
            except LLMUnavailableError:
                self._clients[name] = None
        return self._clients[name]

    def complete(self, *, system: str, prompt: str, max_tokens: int | None = None) -> str:
        errors: list[str] = []
        for name, factory in self._factories:
            client = self._client_for(name, factory)
            if client is None:
                errors.append(f"{name}: unavailable")
                continue
            try:
                text = client.complete(system=system, prompt=prompt, max_tokens=max_tokens)
            except LLMUnavailableError as exc:
                errors.append(str(exc))
                continue
            # success — record attribution
            self.provider = client.provider
            self.model = client.model
            return text
        raise LLMUnavailableError("all providers failed: " + "; ".join(errors))


# --------------------------------------------------------------------------- factory


def _build_factories(settings) -> list[tuple[str, callable]]:
    """Build the ordered provider factory list from settings.

    Order follows ``settings.llm_provider_order`` (default Anthropic → OpenRouter
    → OpenAI → Gemini); only providers with an API key are included.
    """
    timeout = settings.llm_timeout_seconds
    max_tokens = settings.llm_max_tokens

    builders: dict[str, callable] = {
        "anthropic": lambda: (
            AnthropicLLMClient(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            if settings.anthropic_api_key
            else None
        ),
        "openrouter": lambda: (
            OpenAICompatLLMClient(
                provider="openrouter",
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                base_url=settings.openrouter_base_url,
                max_tokens=max_tokens,
                timeout=timeout,
                extra_headers={
                    "HTTP-Referer": "https://sentry.intelligence",
                    "X-Title": "SENTRY Procurement Intelligence",
                },
            )
            if settings.openrouter_api_key
            else None
        ),
        "openai": lambda: (
            OpenAICompatLLMClient(
                provider="openai",
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                base_url=settings.openai_base_url,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            if settings.openai_api_key
            else None
        ),
        "gemini": lambda: (
            GeminiLLMClient(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            if settings.gemini_api_key
            else None
        ),
    }

    key_present = {
        "anthropic": bool(settings.anthropic_api_key),
        "openrouter": bool(settings.openrouter_api_key),
        "openai": bool(settings.openai_api_key),
        "gemini": bool(settings.gemini_api_key),
    }

    order = [p.strip() for p in settings.llm_provider_order.split(",") if p.strip()]
    factories: list[tuple[str, callable]] = []
    for name in order:
        if name in builders and key_present.get(name):
            factories.append((name, builders[name]))
    return factories


def available_providers() -> list[str]:
    """Provider names that have an API key configured, in fallback order."""
    return [name for name, _ in _build_factories(get_settings())]


@lru_cache
def get_llm_client() -> ChainedLLMClient | None:
    """Return a usable chained LLM client, or ``None`` when no provider is configured.

    Cached so provider probing happens once per process.
    """
    settings = get_settings()
    factories = _build_factories(settings)
    if not factories:
        return None
    return ChainedLLMClient(factories)
