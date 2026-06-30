"""
LLM Provider — interface to language models.

Supports multiple backends:
- OpenCode Zen (MiMo-V2.5 Free, DeepSeek, etc.)
- OpenAI API (GPT-4, GPT-3.5)
- Anthropic API (Claude)
- Mock provider (for testing)
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error


@dataclass
class LLMResponse:
    content: str
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def complete(self, prompt: str, system: str = "",
                 temperature: float = 0.7,
                 max_tokens: int = 4096) -> LLMResponse:
        """Generate a completion."""
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.7,
             max_tokens: int = 4096) -> LLMResponse:
        """Chat completion with message history."""
        pass


class OpenCodeZenProvider(LLMProvider):
    """
    OpenCode Zen provider — MiMo-V2.5 Free and other models.

    Uses OpenAI-compatible API format.
    Endpoint: https://opencode.ai/zen/v1/chat/completions
    """

    ZEN_ENDPOINT = "https://opencode.ai/zen/v1/chat/completions"

    # Available free models
    FREE_MODELS = [
        "mimo-v2.5-free",
        "deepseek-v4-flash-free",
        "north-mini-code-free",
        "nemotron-3-ultra-free",
        "big-pickle",
    ]

    def __init__(self, api_key: Optional[str] = None,
                 model: str = "mimo-v2.5-free"):
        self.api_key = api_key or os.environ.get("ZEN_API_KEY") or os.environ.get("OPENCODE_API_KEY")
        self.model = model

    @property
    def name(self) -> str:
        return f"zen-{self.model}"

    def complete(self, prompt: str, system: str = "",
                 temperature: float = 0.7,
                 max_tokens: int = 4096) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, temperature, max_tokens)

    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.7,
             max_tokens: int = 4096) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                content="Error: No API key. Set ZEN_API_KEY environment variable.",
                finish_reason="error"
            )

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "ReliableAgent/1.0"
        }

        req = urllib.request.Request(
            self.ZEN_ENDPOINT,
            data=payload,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                tokens_used=usage.get("total_tokens", 0),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                metadata={"provider": "opencode-zen"}
            )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.read() else str(e)
            return LLMResponse(
                content=f"API Error {e.code}: {error_body}",
                finish_reason="error"
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                finish_reason="error"
            )


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: Optional[str] = None,
                 model: str = "gpt-4"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    @property
    def name(self) -> str:
        return f"openai-{self.model}"

    def complete(self, prompt: str, system: str = "",
                 temperature: float = 0.7,
                 max_tokens: int = 4096) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, temperature, max_tokens)

    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.7,
             max_tokens: int = 4096) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                content="Error: No API key. Set OPENAI_API_KEY.",
                finish_reason="error"
            )

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                tokens_used=usage.get("total_tokens", 0),
                finish_reason=data["choices"][0].get("finish_reason", "stop")
            )

        except urllib.error.HTTPError as e:
            return LLMResponse(
                content=f"API Error {e.code}",
                finish_reason="error"
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                finish_reason="error"
            )


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: Optional[str] = None,
                 model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model

    @property
    def name(self) -> str:
        return f"anthropic-{self.model}"

    def complete(self, prompt: str, system: str = "",
                 temperature: float = 0.7,
                 max_tokens: int = 4096) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                content="Error: No API key. Set ANTHROPIC_API_KEY.",
                finish_reason="error"
            )

        payload = json.dumps({
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data["content"][0]["text"]
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                finish_reason=data.get("stop_reason", "end_turn")
            )

        except urllib.error.HTTPError as e:
            return LLMResponse(
                content=f"API Error {e.code}",
                finish_reason="error"
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                finish_reason="error"
            )


class MockProvider(LLMProvider):
    """Mock provider for testing — returns predefined responses."""

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or ["This is a mock response."]
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock"

    def complete(self, prompt: str, system: str = "",
                 temperature: float = 0.7,
                 max_tokens: int = 4096) -> LLMResponse:
        content = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return LLMResponse(content=content, model="mock")

    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.7,
             max_tokens: int = 4096) -> LLMResponse:
        return self.complete(messages[-1]["content"] if messages else "")


def create_provider(provider: str = "auto", **kwargs) -> LLMProvider:
    """
    Create an LLM provider.

    Auto-detection order:
    1. OpenCode Zen (ZEN_API_KEY) — MiMo-V2.5 Free
    2. OpenAI (OPENAI_API_KEY)
    3. Anthropic (ANTHROPIC_API_KEY)
    4. Mock (no API key needed)
    """
    if provider == "mock":
        return MockProvider(**kwargs)

    if provider in ("zen", "opencode", "mimo", "auto"):
        api_key = kwargs.get("api_key") or os.environ.get("ZEN_API_KEY") or os.environ.get("OPENCODE_API_KEY")
        if api_key:
            return OpenCodeZenProvider(api_key=api_key, **kwargs)

    if provider in ("openai", "auto"):
        if os.environ.get("OPENAI_API_KEY"):
            return OpenAIProvider(**kwargs)

    if provider in ("anthropic", "auto"):
        if os.environ.get("ANTHROPIC_API_KEY"):
            return AnthropicProvider(**kwargs)

    # Default to mock if no API keys found
    return MockProvider()
