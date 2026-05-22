from __future__ import annotations

import pytest

from src.llm_factory import MalformedLLMResponse
from src.llm_factory import parse_llm_json_response


def test_parse_llm_json_response_accepts_pristine_json() -> None:
    raw_text = (
        "["
        '{"file_path":"src/auth.py","line_number":42,'
        '"comment":"Use a constant-time comparison here."}'
        "]"
    )

    parsed = parse_llm_json_response(raw_text)

    assert parsed == [
        {
            "file_path": "src/auth.py",
            "line_number": 42,
            "comment": "Use a constant-time comparison here.",
        }
    ]


def test_parse_llm_json_response_accepts_markdown_wrapped_json() -> None:
    raw_text = """```json
[
  {
    "file_path": "src/auth.py",
    "line_number": 42,
    "comment": "Use a constant-time comparison here."
  }
]
```"""

    parsed = parse_llm_json_response(raw_text)

    assert parsed == [
        {
            "file_path": "src/auth.py",
            "line_number": 42,
            "comment": "Use a constant-time comparison here.",
        }
    ]


@pytest.mark.parametrize(
    "raw_text",
    [
        "not json at all",
        '{"file_path":"src/auth.py"}',
        '[{"file_path":"src/auth.py","line_number":"42","comment":"x"}]',
        '[{"file_path":"src/auth.py","line_number":42}]',
    ],
)
def test_parse_llm_json_response_raises_for_invalid_content(
    raw_text: str,
) -> None:
    with pytest.raises(MalformedLLMResponse):
        parse_llm_json_response(raw_text)