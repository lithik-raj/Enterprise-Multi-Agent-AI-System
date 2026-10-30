"""
LLM Configuration and Status API.
Allows viewing current LLM readiness and dynamically configuring Azure OpenAI API credentials.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.llm_service import (
    configure_azure_llm,
    get_llm_status,
    get_llm_service_safe,
    ConfigurationError,
    ProviderError,
)

router = APIRouter(prefix="/api/llm", tags=["LLM Configuration"])
logger = logging.getLogger(__name__)


class AzureConfigPayload(BaseModel):
    api_key: str = Field(..., description="Azure OpenAI Service API Key")
    endpoint: str = Field(..., description="Azure OpenAI Endpoint (e.g., https://my-resource.openai.azure.com)")
    deployment_name: Optional[str] = Field("gpt-4o", description="Deployment name in Azure AI Studio (e.g., gpt-4o)")
    api_version: Optional[str] = Field("2024-02-15-preview", description="Azure OpenAI REST API version")
    persist_to_env: Optional[bool] = Field(True, description="Whether to write credentials to local .env file")


class TestPayload(BaseModel):
    prompt: Optional[str] = Field("Ping. Respond with 'PONG' only.", description="Test prompt to verify model response")


@router.get(
    "/status",
    summary="Get current LLM configuration and readiness status",
)
async def get_status():
    """Returns the operational status, current provider, deployment, and masked credentials."""
    try:
        return get_llm_status()
    except Exception as exc:
        logger.exception("Error checking LLM status")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/config",
    summary="Configure Azure OpenAI API key and endpoint",
)
async def update_azure_config(payload: AzureConfigPayload):
    """
    Dynamically configures the Azure OpenAI credentials, tests the connection
    against Azure OpenAI chat completions, and optionally updates .env.
    """
    try:
        result = configure_azure_llm(
            api_key=payload.api_key,
            endpoint=payload.endpoint,
            deployment_name=payload.deployment_name or "gpt-4o",
            api_version=payload.api_version or "2024-02-15-preview",
            persist_to_env=payload.persist_to_env if payload.persist_to_env is not None else True,
        )
        return {
            "success": True,
            "message": "Azure OpenAI credentials successfully verified and activated.",
            "data": result,
        }
    except (ConfigurationError, ProviderError) as exc:
        logger.warning("Azure OpenAI configuration validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Azure OpenAI connection failed: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error configuring Azure OpenAI")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error updating Azure configuration: {str(exc)}",
        )


@router.post(
    "/test",
    summary="Test active LLM connection with a quick completion ping",
)
async def test_llm(payload: TestPayload):
    """Executes a lightweight query against the active LLM provider."""
    llm = get_llm_service_safe()
    if not llm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LLM service is not configured or ready. Please set your Azure OpenAI API key first.",
        )
    try:
        resp = llm.generate(payload.prompt or "Hello", max_tokens=60, temperature=0.1)
        return {
            "success": True,
            "provider": llm.provider_name,
            "reply": resp.text.strip(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM test request failed: {str(exc)}",
        )
