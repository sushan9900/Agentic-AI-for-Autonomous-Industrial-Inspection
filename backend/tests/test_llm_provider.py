"""Unit tests for LLM provider abstraction and Ollama HTTP client with mocking."""

import json
import pytest
from unittest.mock import MagicMock, patch
from backend.app.llm.ollama import OllamaProvider, OllamaProviderError
from backend.app.llm.schemas import LLMGenerationRequest, LLMGenerationResponse, LLMHealthStatus


def test_ollama_provider_health_check_success():
    provider = OllamaProvider(base_url="http://localhost:11434", model="gemma3:latest")
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({
        "models": [{"name": "gemma3:latest"}, {"name": "nomic-embed-text:latest"}]
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        health = provider.health_check()
        assert health.available is True
        assert health.provider == "ollama"
        assert health.model == "gemma3:latest"
        assert "loaded and ready" in health.details


def test_ollama_provider_health_check_model_missing():
    provider = OllamaProvider(base_url="http://localhost:11434", model="nonexistent:model")
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({
        "models": [{"name": "other-model:latest"}]
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        health = provider.health_check()
        assert health.available is False
        assert "was not found" in health.details


def test_ollama_provider_generate_success():
    provider = OllamaProvider(base_url="http://localhost:11434", model="gemma3:latest")
    req = LLMGenerationRequest(prompt="Test prompt", format="json", temperature=0.1)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({
        "response": '{"summary": "Test OK"}',
        "model": "gemma3:latest",
        "prompt_eval_count": 10,
        "eval_count": 5
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        res = provider.generate(req)
        assert isinstance(res, LLMGenerationResponse)
        assert res.text == '{"summary": "Test OK"}'
        assert res.model == "gemma3:latest"
        assert res.duration_ms >= 0.0


def test_ollama_provider_connection_error_raises_ollama_error():
    import urllib.error
    provider = OllamaProvider(base_url="http://localhost:11434", model="gemma3:latest")
    req = LLMGenerationRequest(prompt="Test prompt")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(OllamaProviderError) as exc:
            provider.generate(req)
        assert "Failed to connect" in str(exc.value)
