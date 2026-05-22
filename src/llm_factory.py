from __future__ import annotations

import json
import os
import re
from abc import ABC
from abc import abstractmethod
from typing import Any

import requests
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import StrictInt
from pydantic import StrictStr
from pydantic import ValidationError


class LLMProviderError(Exception):
    """Raised when an LLM provider cannot fulfill a request."""


class MalformedLLMResponse(LLMProviderError):
    """Raised when model output cannot be parsed into the expected schema."""


STRUCTURED_OUTPUT_RULES = (
    "Return only a valid JSON array of objects with exactly these fields: "
    '"file_path" (string), "line_number" (integer), and "comment" '
    "(string). Do not include markdown, prose, or any extra keys. "
    "Example output:\n"
    "[\n"
    "  {\n"
    '    "file_path": "src/auth.py",\n'
    '    "line_number": 42,\n'
    '    "comment": "Ensure you are using a constant-time comparison here..."\n'
    "  }\n"
    "]"
)


class ReviewCommentBlock(BaseModel):
    """Structured review comment emitted by the LLM."""

    file_path: StrictStr
    line_number: StrictInt
    comment: StrictStr

    model_config = ConfigDict(extra="forbid")


def append_structured_output_rules(prompt: str) -> str:
    """Append explicit structured-output instructions to a prompt."""

    return f"{prompt.rstrip()}\n\n{STRUCTURED_OUTPUT_RULES}"


def parse_llm_json_response(raw_text: str) -> list[dict[str, Any]]:
    """Parse and validate the structured JSON response from the LLM."""

    normalized_text = _strip_markdown_code_fences(raw_text)

    try:
        payload = json.loads(normalized_text)
    except json.JSONDecodeError as exc:
        raise MalformedLLMResponse(
            "LLM response did not contain valid JSON."
        ) from exc

    if not isinstance(payload, list):
        raise MalformedLLMResponse(
            "LLM response must be a JSON array."
        )

    parsed_blocks: list[dict[str, Any]] = []
    for item in payload:
        try:
            parsed_blocks.append(
                ReviewCommentBlock.model_validate(item).model_dump()
            )
        except ValidationError as exc:
            raise MalformedLLMResponse(
                "LLM response did not match the expected comment schema."
            ) from exc

    return parsed_blocks


def _strip_markdown_code_fences(raw_text: str) -> str:
    """Remove surrounding markdown code fences from model output."""

    stripped_text = raw_text.strip()
    fence_match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        stripped_text,
        flags=re.DOTALL,
    )
    if fence_match is not None:
        return fence_match.group(1).strip()

    return stripped_text


class BaseLLMProvider(ABC):
    """Abstract interface for review-capable LLM providers."""

    @abstractmethod
    def generate_review(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a review response for the supplied prompts."""


class GeminiProvider(BaseLLMProvider):
    """Gemini implementation that uses raw HTTP requests."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._model = self._get_required_config(config, "model")
        self._api_key = os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise LLMProviderError(
                "GEMINI_API_KEY is required for GeminiProvider."
            )

        self._endpoint = config.get(
            "endpoint",
            (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self._model}:generateContent"
            ),
        )

    def generate_review(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a review response from Gemini."""

        formatted_system_prompt = append_structured_output_rules(
            system_prompt
        )
        formatted_user_prompt = append_structured_output_rules(user_prompt)

        payload = {
            "system_instruction": {
                "parts": [
                    {
                        "text": formatted_system_prompt,
                    }
                ]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "text": formatted_user_prompt,
                        }
                    ]
                }
            ],
        }

        try:
            response = requests.post(
                self._endpoint,
                headers=self._build_headers(),
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise LLMProviderError(
                "Failed to communicate with the Gemini API."
            ) from exc

        if response.status_code != 200:
            raise LLMProviderError(
                "Gemini API returned an unexpected status: "
                f"{response.status_code}"
            )

        return self._parse_response(response.json())

    def _build_headers(self) -> dict[str, str]:
        """Build headers for Gemini API authentication."""

        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _parse_response(self, payload: dict[str, Any]) -> str:
        """Extract the generated review text from the Gemini response."""

        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise LLMProviderError(
                "Gemini API response did not include any candidates."
            )

        content = candidates[0].get("content")
        if not isinstance(content, dict):
            raise LLMProviderError(
                "Gemini API response did not include valid content."
            )

        parts = content.get("parts")
        if not isinstance(parts, list) or not parts:
            raise LLMProviderError(
                "Gemini API response did not include valid content parts."
            )

        text = parts[0].get("text")
        if not isinstance(text, str):
            raise LLMProviderError(
                "Gemini API response did not include generated text."
            )

        return text

    def _get_required_config(
        self,
        config: dict[str, Any],
        key: str,
    ) -> str:
        """Return a required string configuration value."""

        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LLMProviderError(
                f"Gemini configuration requires a non-empty '{key}' value."
            )

        return value


class BedrockProvider(BaseLLMProvider):
    """Amazon Bedrock implementation that uses raw HTTP requests."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._model = self._get_required_config(config, "model")
        self._region = self._get_region(config)
        self._bearer_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
        if not self._bearer_token:
            raise LLMProviderError(
                "AWS_BEARER_TOKEN_BEDROCK is required for BedrockProvider."
            )

        self._endpoint = config.get(
            "endpoint",
            (
                f"https://bedrock-runtime.{self._region}.amazonaws.com/"
                f"model/{self._model}/converse"
            ),
        )

    def generate_review(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a review response from Amazon Bedrock."""

        formatted_system_prompt = append_structured_output_rules(
            system_prompt
        )
        formatted_user_prompt = append_structured_output_rules(user_prompt)

        payload = {
            "system": [
                {
                    "text": formatted_system_prompt,
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": formatted_user_prompt,
                        }
                    ],
                }
            ],
        }

        try:
            response = requests.post(
                self._endpoint,
                headers=self._build_headers(),
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise LLMProviderError(
                "Failed to communicate with the Bedrock API."
            ) from exc

        if response.status_code != 200:
            raise LLMProviderError(
                "Bedrock API returned an unexpected status: "
                f"{response.status_code}"
            )

        return self._parse_response(response.json())

    def _build_headers(self) -> dict[str, str]:
        """Build headers for Bedrock API authentication."""

        return {
            "Authorization": f"Bearer {self._bearer_token}",
            "Content-Type": "application/json",
        }

    def _parse_response(self, payload: dict[str, Any]) -> str:
        """Extract the generated review text from the Bedrock response."""

        output = payload.get("output")
        if not isinstance(output, dict):
            raise LLMProviderError(
                "Bedrock API response did not include valid output."
            )

        message = output.get("message")
        if not isinstance(message, dict):
            raise LLMProviderError(
                "Bedrock API response did not include a valid message."
            )

        content = message.get("content")
        if not isinstance(content, list) or not content:
            raise LLMProviderError(
                "Bedrock API response did not include valid content."
            )

        text = content[0].get("text")
        if not isinstance(text, str):
            raise LLMProviderError(
                "Bedrock API response did not include generated text."
            )

        return text

    def _get_region(self, config: dict[str, Any]) -> str:
        """Return the configured AWS region for Bedrock."""

        region = config.get("region") or os.environ.get("AWS_REGION")
        if not isinstance(region, str) or not region.strip():
            raise LLMProviderError(
                "Bedrock configuration requires a non-empty 'region' "
                "value or AWS_REGION environment variable."
            )

        return region

    def _get_required_config(
        self,
        config: dict[str, Any],
        key: str,
    ) -> str:
        """Return a required string configuration value."""

        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LLMProviderError(
                f"Bedrock configuration requires a non-empty '{key}' value."
            )

        return value


class LLMFactory:
    """Create provider implementations from application config."""

    _PROVIDERS = {
        "bedrock": BedrockProvider,
        "gemini": GeminiProvider,
    }

    @classmethod
    def create_provider(
        cls,
        config: dict[str, Any],
    ) -> BaseLLMProvider:
        """Instantiate the configured LLM provider."""

        llm_config = cls._extract_llm_config(config)
        provider_name = llm_config.get("provider")

        if not isinstance(provider_name, str) or not provider_name.strip():
            raise LLMProviderError(
                "LLM configuration requires a non-empty 'provider' value."
            )

        provider_class = cls._PROVIDERS.get(provider_name.lower())
        if provider_class is None:
            raise LLMProviderError(
                f"Unsupported LLM provider: {provider_name}"
            )

        return provider_class(llm_config)

    @staticmethod
    def _extract_llm_config(config: dict[str, Any]) -> dict[str, Any]:
        """Return the nested LLM configuration block."""

        llm_config = config.get("llm")
        if not isinstance(llm_config, dict):
            raise LLMProviderError(
                "Configuration must include an 'llm' mapping."
            )

        return llm_config