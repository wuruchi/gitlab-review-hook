from __future__ import annotations

from typing import Any

import pytest

from src.llm_factory import BedrockProvider
from src.llm_factory import GeminiProvider
from src.llm_factory import LLMFactory
from src.llm_factory import LLMProviderError
from src.llm_factory import STRUCTURED_OUTPUT_RULES


def test_factory_builds_gemini_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    config = {
        "llm": {
            "provider": "gemini",
            "model": "gemini-1.5-pro",
        }
    }

    provider = LLMFactory.create_provider(config)

    assert isinstance(provider, GeminiProvider)


def test_factory_raises_for_unsupported_provider() -> None:
    config = {
        "llm": {
            "provider": "unsupported",
            "model": "whatever",
        }
    }

    with pytest.raises(LLMProviderError, match="Unsupported LLM provider"):
        LLMFactory.create_provider(config)


def test_factory_builds_bedrock_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-bedrock-token")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    config = {
        "llm": {
            "provider": "bedrock",
            "model": "us.anthropic.claude-sonnet-4-6",
        }
    }

    provider = LLMFactory.create_provider(config)

    assert isinstance(provider, BedrockProvider)


def test_gemini_provider_generate_review_posts_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
    mocker: Any,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    provider = GeminiProvider(
        {
            "model": "gemini-1.5-pro",
            "endpoint": "https://llm.example.com/generate",
        }
    )
    response = mocker.Mock()
    response.status_code = 200
    response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "Generated review text.",
                        }
                    ]
                }
            }
        ]
    }
    post_mock = mocker.patch("src.llm_factory.requests.post", return_value=response)

    result = provider.generate_review(
        system_prompt="You are a reviewer.",
        user_prompt="Review this diff.",
    )

    assert result == "Generated review text."
    post_mock.assert_called_once_with(
        "https://llm.example.com/generate",
        headers={
            "Authorization": "Bearer test-api-key",
            "Content-Type": "application/json",
        },
        json={
            "system_instruction": {
                "parts": [
                    {
                        "text": (
                            "You are a reviewer.\n\n"
                            f"{STRUCTURED_OUTPUT_RULES}"
                        ),
                    }
                ]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Review this diff.\n\n"
                                f"{STRUCTURED_OUTPUT_RULES}"
                            ),
                        }
                    ]
                }
            ],
        },
        timeout=30,
    )


def test_gemini_provider_raises_for_non_200_response(
    monkeypatch: pytest.MonkeyPatch,
    mocker: Any,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    provider = GeminiProvider(
        {
            "model": "gemini-1.5-pro",
            "endpoint": "https://llm.example.com/generate",
        }
    )
    response = mocker.Mock()
    response.status_code = 503
    response.json.return_value = {}
    mocker.patch("src.llm_factory.requests.post", return_value=response)

    with pytest.raises(LLMProviderError, match="unexpected status: 503"):
        provider.generate_review(
            system_prompt="You are a reviewer.",
            user_prompt="Review this diff.",
        )


def test_bedrock_provider_generate_review_posts_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
    mocker: Any,
) -> None:
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-bedrock-token")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    provider = BedrockProvider(
        {
            "model": "us.anthropic.claude-sonnet-4-6",
            "endpoint": "https://bedrock.example.com/model/test/converse",
        }
    )
    response = mocker.Mock()
    response.status_code = 200
    response.json.return_value = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": "Bedrock review text.",
                    }
                ]
            }
        }
    }
    post_mock = mocker.patch("src.llm_factory.requests.post", return_value=response)

    result = provider.generate_review(
        system_prompt="You are a reviewer.",
        user_prompt="Review this diff.",
    )

    assert result == "Bedrock review text."
    post_mock.assert_called_once_with(
        "https://bedrock.example.com/model/test/converse",
        headers={
            "Authorization": "Bearer test-bedrock-token",
            "Content-Type": "application/json",
        },
        json={
            "system": [
                {
                    "text": (
                        "You are a reviewer.\n\n"
                        f"{STRUCTURED_OUTPUT_RULES}"
                    ),
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": (
                                "Review this diff.\n\n"
                                f"{STRUCTURED_OUTPUT_RULES}"
                            ),
                        }
                    ],
                }
            ],
        },
        timeout=30,
    )


def test_bedrock_provider_raises_for_non_200_response(
    monkeypatch: pytest.MonkeyPatch,
    mocker: Any,
) -> None:
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-bedrock-token")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    provider = BedrockProvider(
        {
            "model": "us.anthropic.claude-sonnet-4-6",
            "endpoint": "https://bedrock.example.com/model/test/converse",
        }
    )
    response = mocker.Mock()
    response.status_code = 403
    response.json.return_value = {}
    mocker.patch("src.llm_factory.requests.post", return_value=response)

    with pytest.raises(LLMProviderError, match="unexpected status: 403"):
        provider.generate_review(
            system_prompt="You are a reviewer.",
            user_prompt="Review this diff.",
        )