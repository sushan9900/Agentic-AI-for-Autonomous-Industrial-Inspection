"""Ollama local LLM provider implementation."""

import json
import time
import urllib.error
import urllib.request
from typing import Optional
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.schemas import LLMGenerationRequest, LLMGenerationResponse, LLMHealthStatus

logger = get_logger(__name__)


class OllamaProviderError(Exception):
    """Exception raised when local Ollama API fails or is unreachable."""
    pass


class OllamaProvider(BaseLLMProvider):
    """Local Ollama HTTP client implementing BaseLLMProvider."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.LLM_REQUEST_TIMEOUT_SECONDS

    def model_name(self) -> str:
        return self.model

    def health_check(self) -> LLMHealthStatus:
        """Verifies local Ollama server connectivity and model availability."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=4.0) as response:
                if response.status != 200:
                    return LLMHealthStatus(
                        provider="ollama",
                        model=self.model,
                        available=False,
                        details=f"Ollama returned HTTP status {response.status}"
                    )
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                
                # Check exact name or tag match
                model_base = self.model.split(":")[0]
                model_present = any(self.model in m or m.startswith(model_base) for m in models)
                
                if model_present:
                    return LLMHealthStatus(
                        provider="ollama",
                        model=self.model,
                        available=True,
                        details=f"Ollama server online. Model '{self.model}' is loaded and ready."
                    )
                else:
                    return LLMHealthStatus(
                        provider="ollama",
                        model=self.model,
                        available=False,
                        details=f"Ollama server online, but model '{self.model}' was not found in: {models}"
                    )
        except urllib.error.URLError as e:
            return LLMHealthStatus(
                provider="ollama",
                model=self.model,
                available=False,
                details=f"Cannot connect to Ollama at '{self.base_url}': {e.reason}"
            )
        except Exception as e:
            return LLMHealthStatus(
                provider="ollama",
                model=self.model,
                available=False,
                details=f"Ollama health check failed: {str(e)}"
            )

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        """Executes generation against local Ollama API."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            }
        }
        if request.system:
            payload["system"] = request.system
        if request.format:
            payload["format"] = request.format

        headers = {"Content-Type": "application/json"}
        req_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_bytes, headers=headers, method="POST")

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise OllamaProviderError(f"Ollama API returned HTTP status {response.status}")
                raw_data = response.read().decode("utf-8")
                res_json = json.loads(raw_data)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
            logger.error(f"Ollama HTTP error ({e.code}): {err_body}")
            raise OllamaProviderError(f"Ollama HTTP error ({e.code}): {err_body}") from e
        except urllib.error.URLError as e:
            logger.error(f"Ollama connection error: {e.reason}")
            raise OllamaProviderError(f"Failed to connect to local Ollama server at '{self.base_url}': {e.reason}") from e
        except TimeoutError as e:
            logger.error(f"Ollama request timed out after {self.timeout_seconds}s")
            raise OllamaProviderError(f"Ollama request timed out after {self.timeout_seconds} seconds") from e
        except Exception as e:
            logger.error(f"Ollama unexpected error: {e}")
            raise OllamaProviderError(f"Ollama execution error: {str(e)}") from e

        duration_ms = (time.perf_counter() - t0) * 1000.0

        return LLMGenerationResponse(
            text=res_json.get("response", ""),
            model=res_json.get("model", self.model),
            duration_ms=round(duration_ms, 2),
            prompt_tokens=res_json.get("prompt_eval_count"),
            completion_tokens=res_json.get("eval_count"),
            metadata={
                "total_duration_ns": res_json.get("total_duration"),
                "load_duration_ns": res_json.get("load_duration"),
                "eval_duration_ns": res_json.get("eval_duration"),
            }
        )
