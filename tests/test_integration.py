from __future__ import annotations

import json

import pytest

from src.handler import REVIEW_IN_PROGRESS_COMMENT
from src.handler import lambda_handler
from src.models.gitlab import MergeRequestDiff


def test_lambda_handler_runs_end_to_end_review_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    mocker: object,
) -> None:
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "expected-secret")
    monkeypatch.setenv("GITLAB_TOKEN", "gitlab-token")
    mocker.patch(
        "src.handler.load_config",
        return_value={
            "llm": {
                "provider": "bedrock",
                "model": "us.anthropic.claude-sonnet-4-6",
                "region": "us-east-1",
                "system_prompt": "Review this diff.",
            }
        },
    )
    provider = mocker.Mock()
    provider.generate_review.return_value = (
        "```json\n"
        "[\n"
        "  {\n"
        "    \"file_path\": \"src/auth.py\",\n"
        "    \"line_number\": 42,\n"
        "    \"comment\": \"Ensure you are using a constant-time comparison here...\"\n"
        "  }\n"
        "]\n"
        "```"
    )
    mocker.patch("src.handler.LLMFactory.create_provider", return_value=provider)
    gitlab_client = mocker.Mock()
    gitlab_client.get_merge_request_diffs.return_value = [
        MergeRequestDiff(
            old_path="src/auth.py",
            new_path="src/auth.py",
            diff="@@ -40,3 +40,3 @@\n-old\n+new\n",
        )
    ]
    gitlab_client.get_raw_file_content.return_value = "def compare():\n    pass\n"
    gitlab_client.post_merge_request_comment.return_value = {
        "id": 1,
        "body": REVIEW_IN_PROGRESS_COMMENT,
    }
    gitlab_client.post_inline_discussion.return_value = {"id": "discussion-1"}
    mocker.patch("src.handler._build_gitlab_client", return_value=gitlab_client)

    event = {
        "headers": {"X-Gitlab-Token": "expected-secret"},
        "body": json.dumps(
            {
                "object_kind": "note",
                "project": {"id": 123},
                "merge_request": {
                    "iid": 456,
                    "source_branch": "feature/review",
                },
                "object_attributes": {
                    "note": "Please /review this merge request.",
                },
            }
        ),
    }

    response = lambda_handler(event, None)

    assert response == {
        "statusCode": 200,
        "body": "Authorized",
    }
    gitlab_client.post_merge_request_comment.assert_called_once_with(
        123,
        456,
        REVIEW_IN_PROGRESS_COMMENT,
    )
    gitlab_client.get_merge_request_diffs.assert_called_once_with(123, 456)
    gitlab_client.get_raw_file_content.assert_called_once_with(
        123,
        "src/auth.py",
        "feature/review",
    )
    provider.generate_review.assert_called_once()
    gitlab_client.post_inline_discussion.assert_called_once_with(
        123,
        456,
        "src/auth.py",
        42,
        "Ensure you are using a constant-time comparison here...",
    )