"""
Phase 2 — LLM service tests (all providers mocked).

Run with:   pytest tests/test_llm_service.py -v

External API calls are NEVER made in tests — we patch the provider's
`generate` method or the underlying SDK to keep tests fast and offline.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.llm_service import (
    BaseLLMProvider,
    ConfigurationError,
    LLMResponse,
    LLMService,
    ProviderError,
    get_llm_service,
)
from app.services.prompt_templates import get_template


# ── Fixtures ──────────────────────────────────────────────────────────────────

class MockProvider(BaseLLMProvider):
    """In-memory provider used across unit tests — no network calls."""

    def __init__(self, response_text: str = "mock response", available: bool = True):
        self._text = response_text
        self._available = available

    @property
    def provider_name(self) -> str:
        return "mock"

    def is_available(self) -> bool:
        return self._available

    def generate(self, prompt, *, system_prompt=None, temperature=0.2, max_tokens=4096):
        if not self._available:
            raise ProviderError("Mock provider unavailable")
        return LLMResponse(text=self._text, model="mock-model", provider="mock")


@pytest.fixture
def llm_service():
    return LLMService(provider=MockProvider("Hello from mock LLM"))


# ── LLMResponse tests ─────────────────────────────────────────────────────────

def test_llm_response_fields():
    r = LLMResponse(text="Hello", model="my-model", provider="test")
    assert r.text == "Hello"
    assert r.model == "my-model"
    assert r.provider == "test"
    assert r.metadata == {}


def test_llm_response_repr():
    r = LLMResponse(text="abc", model="m", provider="p")
    assert "provider=p" in repr(r)


# ── LLMService tests ──────────────────────────────────────────────────────────

def test_llm_service_generate_returns_response(llm_service):
    resp = llm_service.generate("Tell me something")
    assert isinstance(resp, LLMResponse)
    assert resp.text == "Hello from mock LLM"


def test_llm_service_is_ready(llm_service):
    assert llm_service.is_ready() is True


def test_llm_service_not_ready_when_provider_unavailable():
    svc = LLMService(provider=MockProvider(available=False))
    assert svc.is_ready() is False


def test_llm_service_provider_name(llm_service):
    assert llm_service.provider_name == "mock"


def test_llm_service_provider_error_propagates():
    svc = LLMService(provider=MockProvider(available=False))
    with pytest.raises(ProviderError):
        svc.generate("crash")


# ── ConfigurationError tests ──────────────────────────────────────────────────

def test_gemini_raises_configuration_error_when_key_missing():
    """GoogleGeminiProvider must raise ConfigurationError, not crash, when key is empty."""
    from app.services.llm_service import GoogleGeminiProvider
    with pytest.raises(ConfigurationError, match="LLM_API_KEY"):
        GoogleGeminiProvider(api_key="")


def test_openai_raises_configuration_error_when_key_missing():
    from app.services.llm_service import OpenAIProvider
    with pytest.raises(ConfigurationError, match="LLM_API_KEY"):
        OpenAIProvider(api_key="")


def test_azure_raises_configuration_error_when_key_missing():
    from app.services.llm_service import AzureOpenAIProvider
    with pytest.raises(ConfigurationError, match="AZURE_OPENAI_API_KEY"):
        AzureOpenAIProvider(api_key="", endpoint="https://myresource.openai.azure.com")


def test_azure_raises_configuration_error_when_endpoint_missing():
    from app.services.llm_service import AzureOpenAIProvider
    with pytest.raises(ConfigurationError, match="AZURE_OPENAI_ENDPOINT"):
        AzureOpenAIProvider(api_key="dummy-key", endpoint="")


def test_azure_provider_generate_with_mocked_httpx(monkeypatch):
    from app.services.llm_service import AzureOpenAIProvider
    provider = AzureOpenAIProvider(
        api_key="test-azure-key",
        endpoint="https://myresource.openai.azure.com",
        deployment_name="gpt-4o",
    )

    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "choices": [
                    {"message": {"role": "assistant", "content": "Azure GPT-4o response for job search"}}
                ],
                "usage": {"total_tokens": 42},
            }

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def post(self, url, headers=None, json=None):
            assert "api-key" in headers
            assert "messages" in json
            return MockResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", MockClient)

    resp = provider.generate("Recommend top AI internships", system_prompt="You are a career mentor")
    assert resp.provider == "azure"
    assert resp.model == "gpt-4o"
    assert "Azure GPT-4o response" in resp.text


def test_azure_provider_handles_api_error(monkeypatch):
    from app.services.llm_service import AzureOpenAIProvider
    provider = AzureOpenAIProvider(
        api_key="invalid-key",
        endpoint="https://myresource.openai.azure.com",
        deployment_name="gpt-4o",
    )

    class MockErrorResponse:
        status_code = 401
        text = "Access denied due to invalid subscription key"
        def json(self):
            return {"error": {"message": "Access denied due to invalid subscription key"}}

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def post(self, url, headers=None, json=None):
            return MockErrorResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", MockClient)

    with pytest.raises(ProviderError, match="Access denied"):
        provider.generate("Hello")


def test_get_llm_status():
    from app.services.llm_service import get_llm_status
    status = get_llm_status()
    assert "provider" in status
    assert "deployment" in status
    assert "configured" in status



# ── Factory tests ─────────────────────────────────────────────────────────────

def test_get_llm_service_raises_on_unknown_provider(monkeypatch):
    """Factory must raise ConfigurationError for unrecognised provider names."""
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "LLM_PROVIDER", "unknown_llm")

    from app.services import llm_service as svc_module
    svc_module.get_llm_service.cache_clear()

    with patch("app.services.llm_service.get_settings", return_value=settings):
        with pytest.raises(ConfigurationError, match="unknown_llm"):
            svc_module.get_llm_service()

    svc_module.get_llm_service.cache_clear()


# ── Prompt template tests ─────────────────────────────────────────────────────

def test_all_agent_templates_exist():
    agents = [
        "orchestrator", "nlp_agent", "ml_agent", "rag_agent",
        "research_agent", "recommendation_agent", "evaluation_agent",
    ]
    for agent in agents:
        tmpl = get_template(agent)
        assert isinstance(tmpl, str)
        assert len(tmpl) > 50, f"Template for {agent} is suspiciously short"


def test_unknown_template_raises_key_error():
    with pytest.raises(KeyError):
        get_template("nonexistent_agent")


def test_rag_template_contains_hallucination_guard():
    tmpl = get_template("rag_agent")
    assert "hallucinate" in tmpl.lower() or "not present" in tmpl.lower()


def test_evaluation_template_contains_json_schema():
    tmpl = get_template("evaluation_agent")
    assert "groundedness" in tmpl
    assert "relevance" in tmpl
