"""
LLM Service — provider-agnostic abstraction layer.

Design decisions:
- Abstract base class isolates provider-specific logic.
- Provider is selected from LLM_PROVIDER env var (default: google).
- Missing API key raises a clear ConfigurationError instead of crashing silently.
- The factory `get_llm_service()` is cached so the model client is instantiated once.
- To add a new provider, subclass BaseLLMProvider and register it in _PROVIDER_MAP.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────────────

class LLMError(Exception):
    """Base exception for all LLM-related failures."""


class ConfigurationError(LLMError):
    """Raised when required config (e.g. API key) is missing."""


class ProviderError(LLMError):
    """Raised when the upstream provider returns an error."""


# ── Response model ────────────────────────────────────────────────────────────

class LLMResponse:
    """Lightweight wrapper around an LLM response."""

    def __init__(self, text: str, model: str, provider: str, metadata: dict | None = None):
        self.text = text
        self.model = model
        self.provider = provider
        self.metadata: dict = metadata or {}

    @property
    def content(self) -> str:
        """Alias for .text for LangChain / OpenAI style property access."""
        return self.text

    def __repr__(self) -> str:  # noqa: D105
        return f"<LLMResponse provider={self.provider} model={self.model} chars={len(self.text)}>"


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseLLMProvider(ABC):
    """All LLM providers must implement this interface."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a completion for the given prompt."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is correctly configured."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""


# ── Google Gemini implementation ──────────────────────────────────────────────

class GoogleGeminiProvider(BaseLLMProvider):
    """
    Uses the google-generativeai SDK.
    Supports Gemini 1.5 Flash / Pro.
    """

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        if not api_key:
            raise ConfigurationError(
                "LLM_API_KEY is not set. "
                "Copy .env.example → .env and add your Google Gemini API key."
            )
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as exc:
            raise LLMError(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=api_key)
        self._model_name = model
        self._client = genai.GenerativeModel(model)
        logger.info("GoogleGeminiProvider initialised with model=%s", model)

    @property
    def provider_name(self) -> str:
        return "google"

    def is_available(self) -> bool:
        return True  # key already validated in __init__

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        try:
            response = self._client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
            text = response.text
            logger.debug("Gemini response: %d chars", len(text))
            return LLMResponse(text=text, model=self._model_name, provider=self.provider_name)
        except Exception as exc:
            logger.exception("Gemini API call failed")
            raise ProviderError(f"Gemini error: {exc}") from exc


# ── OpenAI stub ───────────────────────────────────────────────────────────────

class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI ChatCompletion provider.
    Uncomment openai in requirements.txt to activate.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ConfigurationError(
                "LLM_API_KEY is not set. Add your OpenAI API key to .env."
            )
        try:
            from openai import OpenAI  # type: ignore
            self._client = OpenAI(api_key=api_key)
        except ImportError as exc:
            raise LLMError("openai package not installed. Run: pip install openai") from exc
        self._model_name = model
        logger.info("OpenAIProvider initialised with model=%s", model)

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message.content or ""
            return LLMResponse(text=text, model=self._model_name, provider=self.provider_name)
        except Exception as exc:
            logger.exception("OpenAI API call failed")
            raise ProviderError(f"OpenAI error: {exc}") from exc


# ── Azure OpenAI implementation ───────────────────────────────────────────────

class AzureOpenAIProvider(BaseLLMProvider):
    """
    Azure OpenAI Chat Completions provider.
    Connects to Azure OpenAI Service endpoints using direct HTTPX REST calls,
    ensuring zero external dependency issues while fully supporting GPT-4o,
    GPT-4, and GPT-3.5 deployments.
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment_name: str | None = None,
        api_version: str | None = None,
        model: str | None = None,
    ):
        settings = get_settings()
        raw_key = api_key if api_key is not None else (settings.AZURE_OPENAI_API_KEY or settings.LLM_API_KEY)
        raw_endpoint = endpoint if endpoint is not None else settings.AZURE_OPENAI_ENDPOINT

        self._api_key = (raw_key or "").strip()
        self._endpoint = (raw_endpoint or "").strip().rstrip("/")
        self._deployment = (
            deployment_name
            or settings.AZURE_OPENAI_DEPLOYMENT_NAME
            or model
            or settings.LLM_MODEL
            or "gpt-4o"
        ).strip()
        self._api_version = (
            api_version
            or settings.AZURE_OPENAI_API_VERSION
            or "2024-02-15-preview"
        ).strip()

        if not self._api_key:
            raise ConfigurationError(
                "AZURE_OPENAI_API_KEY (or LLM_API_KEY) is not set. "
                "Add your Azure OpenAI API key to .env or configure via the UI modal."
            )
        if not self._endpoint or "your-resource-name" in self._endpoint:
            raise ConfigurationError(
                "AZURE_OPENAI_ENDPOINT is not set. "
                "Set AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com in .env or configure via UI."
            )

        logger.info(
            "AzureOpenAIProvider initialised: endpoint=%s deployment=%s api_version=%s",
            self._endpoint,
            self._deployment,
            self._api_version,
        )

    @property
    def provider_name(self) -> str:
        return "azure"

    @property
    def deployment(self) -> str:
        return self._deployment

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def is_available(self) -> bool:
        return bool(self._api_key and self._endpoint and self._deployment)

    def _get_request_url(self) -> str:
        if "/chat/completions" in self._endpoint:
            url = self._endpoint
            if "api-version=" not in url:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}api-version={self._api_version}"
            return url
        return f"{self._endpoint}/openai/deployments/{self._deployment}/chat/completions?api-version={self._api_version}"

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        import httpx

        url = self._get_request_url()
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url, headers=headers, json=payload)

            if resp.status_code >= 400:
                err_text = resp.text
                try:
                    err_json = resp.json()
                    if isinstance(err_json, dict) and "error" in err_json:
                        err_info = err_json["error"]
                        err_text = err_info.get("message", err_text) if isinstance(err_info, dict) else str(err_info)
                except Exception:
                    pass
                raise ProviderError(f"Azure OpenAI API error (status {resp.status_code}): {err_text}")

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise ProviderError("Azure OpenAI returned empty response choices.")

            message_obj = choices[0].get("message", {})
            text = message_obj.get("content", "")
            metadata = {
                "usage": data.get("usage", {}),
                "id": data.get("id"),
                "deployment": self._deployment,
                "provider": "azure",
            }
            logger.info("Azure OpenAI generated response (%d chars, deployment=%s)", len(text), self._deployment)
            return LLMResponse(text=text, model=self._deployment, provider=self.provider_name, metadata=metadata)

        except httpx.RequestError as exc:
            logger.exception("Azure OpenAI connection error")
            raise ProviderError(f"Azure OpenAI connection failed: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, (ConfigurationError, ProviderError)):
                raise
            logger.exception("Azure OpenAI unexpected failure")
            raise ProviderError(f"Azure OpenAI request failed: {exc}") from exc

    def test_connection(self) -> dict[str, Any]:
        """Test the connection by issuing a minimal query."""
        res = self.generate("Ping. Respond with 'PONG' only.", max_tokens=10, temperature=0.0)
        return {
            "success": True,
            "message": f"Connected to Azure OpenAI deployment '{self._deployment}'",
            "reply": res.text.strip(),
        }


# ── Provider registry & factory ───────────────────────────────────────────────

_PROVIDER_MAP: dict[str, type[BaseLLMProvider]] = {
    "google": GoogleGeminiProvider,
    "openai": OpenAIProvider,
    "azure": AzureOpenAIProvider,
    "azure_openai": AzureOpenAIProvider,
    "azure-openai": AzureOpenAIProvider,
}


class LLMService:
    """
    High-level LLM service used throughout the platform.
    Wraps the underlying provider and exposes a clean API.
    """

    def __init__(self, provider: BaseLLMProvider):
        self._provider = provider

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a completion. Raises LLMError on failure."""
        logger.info(
            "LLMService.generate via %s (prompt_len=%d)",
            self._provider.provider_name,
            len(prompt),
        )
        return self._provider.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def is_ready(self) -> bool:
        """Return True if the underlying provider is configured and ready."""
        return self._provider.is_available()

    @property
    def provider(self) -> BaseLLMProvider:
        return self._provider

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """
    Return a cached LLMService instance.
    Called once at startup; subsequent calls return the same object.
    Raises ConfigurationError if the required env vars are missing.
    """
    settings = get_settings()
    provider_key = settings.LLM_PROVIDER.lower()

    if provider_key not in _PROVIDER_MAP:
        raise ConfigurationError(
            f"Unknown LLM_PROVIDER '{provider_key}'. "
            f"Choose one of: {list(_PROVIDER_MAP.keys())}"
        )

    provider_cls = _PROVIDER_MAP[provider_key]
    if provider_key in ("azure", "azure_openai", "azure-openai"):
        provider = provider_cls(
            api_key=settings.AZURE_OPENAI_API_KEY or settings.LLM_API_KEY,
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME or settings.LLM_MODEL or "gpt-4o",
            api_version=settings.AZURE_OPENAI_API_VERSION or "2024-02-15-preview",
        )
    else:
        provider = provider_cls(api_key=settings.LLM_API_KEY, model=settings.LLM_MODEL)
    return LLMService(provider=provider)


def get_llm_service_safe() -> LLMService | None:
    """
    Safely retrieve the active LLMService, returning None if unconfigured.
    Prevents runtime crashes when user has not yet entered their API credentials.
    """
    try:
        svc = get_llm_service()
        if svc.is_ready():
            return svc
        return None
    except Exception as exc:
        logger.debug("LLM service not configured or unavailable: %s", exc)
        return None


def get_llm_status() -> dict[str, Any]:
    """Return diagnostic status of the LLM configuration."""
    settings = get_settings()
    provider_name = (settings.LLM_PROVIDER or "azure").lower()

    api_key = settings.AZURE_OPENAI_API_KEY or settings.LLM_API_KEY or ""
    endpoint = settings.AZURE_OPENAI_ENDPOINT or ""
    deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME or settings.LLM_MODEL or "gpt-4o"
    api_version = settings.AZURE_OPENAI_API_VERSION or "2024-02-15-preview"

    masked_key = ""
    if api_key:
        masked_key = (api_key[:4] + "..." + api_key[-4:]) if len(api_key) > 8 else "***"

    is_configured = bool(
        api_key
        and (endpoint if provider_name in ("azure", "azure_openai") else True)
        and "your-resource-name" not in endpoint
    )

    return {
        "provider": provider_name,
        "configured": is_configured,
        "deployment": deployment,
        "endpoint": endpoint,
        "api_version": api_version,
        "api_key_masked": masked_key,
        "model": deployment if provider_name in ("azure", "azure_openai") else settings.LLM_MODEL,
    }


def configure_azure_llm(
    api_key: str,
    endpoint: str,
    deployment_name: str = "gpt-4o",
    api_version: str = "2024-02-15-preview",
    persist_to_env: bool = True,
) -> dict[str, Any]:
    """
    Dynamically configure or update the Azure OpenAI provider at runtime.
    Optionally persists the new credentials to the local .env file.
    """
    import os
    from pathlib import Path

    clean_key = (api_key or "").strip()
    clean_endpoint = (endpoint or "").strip().rstrip("/")
    clean_deployment = (deployment_name or "gpt-4o").strip()
    clean_version = (api_version or "2024-02-15-preview").strip()

    if not clean_key:
        raise ConfigurationError("Azure OpenAI API key cannot be empty.")
    if not clean_endpoint:
        raise ConfigurationError("Azure OpenAI Endpoint cannot be empty (e.g. https://<resource>.openai.azure.com).")

    # Update runtime environment
    os.environ["LLM_PROVIDER"] = "azure"
    os.environ["AZURE_OPENAI_API_KEY"] = clean_key
    os.environ["AZURE_OPENAI_ENDPOINT"] = clean_endpoint
    os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = clean_deployment
    os.environ["AZURE_OPENAI_API_VERSION"] = clean_version

    # Invalidate settings cache and LLM service cache
    get_settings.cache_clear()
    get_llm_service.cache_clear()

    # Create temporary provider to verify connection
    test_provider = AzureOpenAIProvider(
        api_key=clean_key,
        endpoint=clean_endpoint,
        deployment_name=clean_deployment,
        api_version=clean_version,
    )
    test_result = test_provider.test_connection()

    if persist_to_env:
        try:
            env_path = Path(".env")
            lines: list[str] = []
            if env_path.exists():
                lines = env_path.read_text(encoding="utf-8").splitlines()

            var_map = {
                "LLM_PROVIDER": "azure",
                "AZURE_OPENAI_API_KEY": clean_key,
                "AZURE_OPENAI_ENDPOINT": clean_endpoint,
                "AZURE_OPENAI_DEPLOYMENT_NAME": clean_deployment,
                "AZURE_OPENAI_API_VERSION": clean_version,
            }

            written_keys = set()
            new_lines = []
            for line in lines:
                stripped = line.strip()
                matched_key = None
                for k in var_map:
                    if stripped.startswith(f"{k}=") or stripped == k:
                        matched_key = k
                        break
                if matched_key:
                    new_lines.append(f"{matched_key}={var_map[matched_key]}")
                    written_keys.add(matched_key)
                else:
                    new_lines.append(line)

            for k, v in var_map.items():
                if k not in written_keys:
                    new_lines.append(f"{k}={v}")

            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            logger.info("Persisted Azure OpenAI settings to .env")
        except Exception as exc:
            logger.warning("Could not persist to .env file: %s", exc)

    return {
        "status": "connected",
        "provider": "azure",
        "deployment": clean_deployment,
        "endpoint": clean_endpoint,
        "test": test_result,
    }

