"""
Tests for LLM API configuration and diagnostic endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_service import LLMResponse


@pytest.fixture
def client():
    return TestClient(app)


def test_get_llm_status_endpoint(client):
    response = client.get("/api/llm/status")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "configured" in data
    assert "deployment" in data


def test_update_azure_config_invalid_data(client):
    response = client.post("/api/llm/config", json={
        "api_key": "",
        "endpoint": "",
    })
    assert response.status_code in (400, 422)


def test_update_azure_config_mocked_success(client, monkeypatch):
    class MockProvider:
        def test_connection(self):
            return {"success": True, "message": "Connected", "reply": "PONG"}

    with patch("app.services.llm_service.AzureOpenAIProvider", return_value=MockProvider()):
        response = client.post("/api/llm/config", json={
            "api_key": "dummy-azure-key",
            "endpoint": "https://custom-resource.openai.azure.com",
            "deployment_name": "gpt-4o",
            "persist_to_env": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deployment"] == "gpt-4o"


def test_test_llm_endpoint_unconfigured(client, monkeypatch):
    with patch("app.api.llm.get_llm_service_safe", return_value=None):
        response = client.post("/api/llm/test", json={"prompt": "Ping"})
        assert response.status_code == 400
        assert "not configured" in response.json()["detail"].lower()


def test_test_llm_endpoint_success(client):
    mock_llm = MagicMock()
    mock_llm.provider_name = "azure"
    mock_llm.generate.return_value = LLMResponse(text="PONG", model="gpt-4o", provider="azure")

    with patch("app.api.llm.get_llm_service_safe", return_value=mock_llm):
        response = client.post("/api/llm/test", json={"prompt": "Ping"})
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["reply"] == "PONG"
