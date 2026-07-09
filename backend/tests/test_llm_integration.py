"""LLM integration + provider-fallback verification.

Exercises the "LLM as final analyst" contract with mock providers (no network):
provider attribution, the fallback chain across every configuration, refusal /
error-as-text handling, and the grounding-guard fallback — all with honest
``fallback_reason`` so the UI never shows "Fallback Active" for a provider that
truly answered.
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.clients.llm import (
    ChainedLLMClient,
    LLMUnavailableError,
    _build_factories,
    _looks_like_provider_noise,
)
from app.schemas.investigation_executor import (
    InvestigationAwardResult,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationTenderResult,
)
from app.schemas.investigation_planner import InvestigationPlan
from app.services import investigation_reasoning
from app.services.investigation_executor import _build_entities, _build_evidence
from app.services.investigation_indicators import build_indicators
from app.services.investigation_reasoning import build_reasoning


class _FakeClient:
    def __init__(self, *, text: str | None = None, raise_: bool = False, provider="anthropic", model="claude-opus-4-8"):
        self.provider = provider
        self.model = model
        self._text = text
        self._raise = raise_

    def complete(self, *, system: str, prompt: str, max_tokens=None) -> str:
        if self._raise:
            raise LLMUnavailableError(f"{self.provider}: simulated failure")
        assert self._text is not None
        return self._text


# --------------------------------------------------------------------------- noise

class ProviderNoiseTest(unittest.TestCase):
    def test_access_denied_is_noise(self) -> None:
        self.assertTrue(_looks_like_provider_noise(
            "Access Denied: This service is restricted to authorized use through the official client."
        ))

    def test_auth_and_quota_are_noise(self) -> None:
        self.assertTrue(_looks_like_provider_noise("invalid api key provided"))
        self.assertTrue(_looks_like_provider_noise("You exceeded your current quota, please check your plan"))

    def test_genuine_summary_is_not_noise(self) -> None:
        self.assertFalse(_looks_like_provider_noise(
            "Investigation of Acme Infra shows elevated procurement risk driven by single-bidder awards."
        ))


# --------------------------------------------------------------------------- chain fallback

class ChainedFallbackTest(unittest.TestCase):
    def _chain(self, *clients):
        return ChainedLLMClient([(c.provider, (lambda c=c: c)) for c in clients])

    def test_single_provider_answers_and_is_attributed(self) -> None:
        chain = self._chain(_FakeClient(text="clean summary", provider="anthropic", model="claude-opus-4-8"))
        self.assertEqual(chain.complete(system="s", prompt="p"), "clean summary")
        self.assertEqual(chain.provider, "anthropic")
        self.assertEqual(chain.model, "claude-opus-4-8")

    def test_first_unavailable_falls_to_second(self) -> None:
        chain = self._chain(
            _FakeClient(raise_=True, provider="anthropic"),
            _FakeClient(text="from openrouter", provider="openrouter", model="claude-3.5"),
        )
        self.assertEqual(chain.complete(system="s", prompt="p"), "from openrouter")
        self.assertEqual(chain.provider, "openrouter")

    def test_refusal_text_falls_to_next_provider(self) -> None:
        chain = self._chain(
            _FakeClient(text="Access Denied: this service is restricted to authorized use", provider="anthropic"),
            _FakeClient(text="from gemini", provider="gemini", model="gemini-1.5"),
        )
        self.assertEqual(chain.complete(system="s", prompt="p"), "from gemini")
        self.assertEqual(chain.provider, "gemini")

    def test_all_fail_raises(self) -> None:
        chain = self._chain(
            _FakeClient(raise_=True, provider="anthropic"),
            _FakeClient(text="invalid api key", provider="openai"),
        )
        with self.assertRaises(LLMUnavailableError):
            chain.complete(system="s", prompt="p")


# --------------------------------------------------------------------------- config scenarios

def _settings(**keys):
    base = dict(
        llm_provider_order="anthropic,openrouter,openai,gemini",
        llm_timeout_seconds=30.0,
        llm_max_tokens=512,
        anthropic_api_key=None, anthropic_model="claude-opus-4-8", anthropic_base_url=None,
        openrouter_api_key=None, openrouter_model="or/model", openrouter_base_url="http://or",
        openai_api_key=None, openai_model="gpt", openai_base_url="http://oai",
        gemini_api_key=None, gemini_model="gemini-1.5-flash",
    )
    base.update(keys)
    return SimpleNamespace(**base)


class AnthropicBaseUrlTest(unittest.TestCase):
    def test_custom_base_url_passed_to_sdk(self) -> None:
        from app.clients.llm import AnthropicLLMClient
        c = AnthropicLLMClient(api_key="sk-x", model="m", max_tokens=16, timeout=5, base_url="https://cc.freemodel.dev")
        self.assertEqual(str(c._client.base_url).rstrip("/"), "https://cc.freemodel.dev")

    def test_default_base_url_is_official(self) -> None:
        import os
        from app.clients.llm import AnthropicLLMClient
        prev = os.environ.pop("ANTHROPIC_BASE_URL", None)
        try:
            c = AnthropicLLMClient(api_key="sk-x", model="m", max_tokens=16, timeout=5)
            self.assertEqual(str(c._client.base_url).rstrip("/"), "https://api.anthropic.com")
        finally:
            if prev is not None:
                os.environ["ANTHROPIC_BASE_URL"] = prev

    def test_factory_wires_base_url_from_settings(self) -> None:
        s = _settings(anthropic_api_key="sk-x", anthropic_base_url="https://cc.freemodel.dev")
        client = dict(_build_factories(s))["anthropic"]()
        self.assertEqual(str(client._client.base_url).rstrip("/"), "https://cc.freemodel.dev")


class ProviderConfigTest(unittest.TestCase):
    def _names(self, settings):
        return [name for name, _ in _build_factories(settings)]

    def test_no_providers_configured(self) -> None:
        self.assertEqual(self._names(_settings()), [])

    def test_anthropic_configured(self) -> None:
        self.assertEqual(self._names(_settings(anthropic_api_key="sk-x")), ["anthropic"])

    def test_openrouter_configured(self) -> None:
        self.assertEqual(self._names(_settings(openrouter_api_key="or-x")), ["openrouter"])

    def test_gemini_configured(self) -> None:
        self.assertEqual(self._names(_settings(gemini_api_key="g-x")), ["gemini"])

    def test_order_is_respected_across_multiple(self) -> None:
        names = self._names(_settings(anthropic_api_key="a", openrouter_api_key="o", gemini_api_key="g"))
        self.assertEqual(names, ["anthropic", "openrouter", "gemini"])

    def test_custom_order(self) -> None:
        s = _settings(anthropic_api_key="a", gemini_api_key="g", llm_provider_order="gemini,anthropic")
        self.assertEqual(self._names(s), ["gemini", "anthropic"])


# --------------------------------------------------------------------------- reasoning attribution

def _meta(rid: str) -> InvestigationSourceMetadata:
    return InvestigationSourceMetadata(source_name="cppp", source_record_id=rid, source_url="https://x/" + rid, retrieved_at=None)


def _package() -> InvestigationPackage:
    recs = [
        InvestigationProcurementRecord(
            tender=InvestigationTenderResult(
                reference_number=f"T-{i}", title=f"Road {i}", description=None, procuring_entity="PWD",
                published_date=date(2026, 1, i + 1), closing_date=None, estimated_value=Decimal("50000000"),
                currency="INR", metadata=_meta(f"T-{i}"),
            ),
            awards=[InvestigationAwardResult(
                tender_reference_number=f"T-{i}", company_name="Acme", company_registration_number=None,
                award_date=date(2026, 1, i + 2), award_value=Decimal("50000000"), currency="INR", metadata=_meta(f"T-{i}:a"),
            )],
        )
        for i in range(1, 4)
    ]
    plan = InvestigationPlan(query="Acme", investigation_type="supplier", confidence=0.8, connectors=["cppp"], modules=[], steps=[])
    pkg = InvestigationPackage(plan=plan, records=recs)
    pkg.evidence = _build_evidence(pkg)
    pkg.entities = _build_entities(pkg)
    pkg.indicators = build_indicators(pkg)
    return pkg


class ReasoningAttributionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._orig = investigation_reasoning.get_llm_client

    def tearDown(self) -> None:
        investigation_reasoning.get_llm_client = self._orig

    def _patch(self, client) -> None:
        investigation_reasoning.get_llm_client = lambda: client

    def test_no_provider_is_deterministic_with_reason(self) -> None:
        self._patch(None)
        r = build_reasoning(_package(), "Acme")
        self.assertEqual(r.generated_by, "deterministic")
        self.assertEqual(r.fallback_reason, "no_provider")
        self.assertIsNone(r.provider)

    def test_llm_grounded_answer_is_attributed(self) -> None:
        # No numbers => passes the grounding guard.
        self._patch(_FakeClient(text="Acme shows elevated procurement risk from repeated single-bidder awards."))
        r = build_reasoning(_package(), "Acme")
        self.assertEqual(r.generated_by, "llm")
        self.assertEqual(r.provider, "anthropic")
        self.assertEqual(r.model, "claude-opus-4-8")
        self.assertIsNone(r.fallback_reason)
        self.assertNotIn("Access Denied", r.executive_summary)

    def test_ungrounded_answer_falls_back_but_keeps_provider(self) -> None:
        # A fabricated figure (99999) not in context trips the grounding guard.
        self._patch(_FakeClient(text="Acme won contracts worth 99999 crore across the market."))
        r = build_reasoning(_package(), "Acme")
        self.assertEqual(r.generated_by, "deterministic")
        self.assertEqual(r.fallback_reason, "grounding_guard")
        self.assertEqual(r.provider, "anthropic")  # provider preserved for transparency
        self.assertNotIn("99999", r.executive_summary)

    def test_provider_error_falls_back_with_reason(self) -> None:
        self._patch(_FakeClient(raise_=True))
        r = build_reasoning(_package(), "Acme")
        self.assertEqual(r.generated_by, "deterministic")
        self.assertEqual(r.fallback_reason, "provider_error")


if __name__ == "__main__":
    unittest.main()
