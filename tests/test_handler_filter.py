import json

import pytest

from src.models.gitlab import MergeRequestDiff
from src.handler import lambda_handler


@pytest.fixture
def authorized_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str]:
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "expected-secret")
    return {"X-Gitlab-Token": "expected-secret"}


def test_lambda_handler_accepts_review_note_on_merge_request(
    authorized_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    mocker: object,
) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "gitlab-token")
    mocker.patch("src.handler.load_config", return_value={
        "llm": {
            "provider": "bedrock",
            "model": "us.anthropic.claude-sonnet-4-6",
            "region": "us-east-1",
            "system_prompt": "Review this diff.",
        }
    })
    provider = mocker.Mock()
    provider.generate_review.return_value = (
        '[{"file_path":"src/main.py","line_number":2,'
        '"comment":"Nice catch."}]'
    )
    mocker.patch("src.handler.LLMFactory.create_provider", return_value=provider)
    gitlab_client = mocker.Mock()
    gitlab_client.get_merge_request_diffs.return_value = [
        MergeRequestDiff(
            old_path="src/main.py",
            new_path="src/main.py",
            diff="@@ -1 +1 @@\n-old\n+new\n",
        )
    ]
    gitlab_client.get_raw_file_content.return_value = "print('hello')\n"
    mocker.patch("src.handler._build_gitlab_client", return_value=gitlab_client)

    event = {
        "headers": authorized_headers,
        "body": json.dumps(
            {
                "object_kind": "note",
                "project": {"id": 100},
                "merge_request": {
                    "iid": 42,
                    "source_branch": "feature/review",
                },
                "object_attributes": {
                    "note": "Please /review this change.",
                },
            }
        ),
    }

    response = lambda_handler(event, None)

    assert response == {
        "statusCode": 200,
        "body": "Authorized",
    }
    gitlab_client.post_merge_request_comment.assert_called()
    gitlab_client.post_inline_discussion.assert_called_once_with(
        100,
        42,
        "src/main.py",
        2,
        "Nice catch.",
    )
    assert response["body"] == "Authorized"


def test_lambda_handler_ignores_comment_without_review_command(
    authorized_headers: dict[str, str],
) -> None:
    event = {
        "headers": authorized_headers,
        "body": json.dumps(
            {
                "object_kind": "note",
                "merge_request": {"iid": 42},
                "object_attributes": {
                    "note": "Looks good to me.",
                },
            }
        ),
    }

    response = lambda_handler(event, None)

    assert response == {
        "statusCode": 200,
        "body": "Event ignored",
    }


def test_lambda_handler_ignores_invalid_payload_shape(
    authorized_headers: dict[str, str],
) -> None:
    event = {
        "headers": authorized_headers,
        "body": json.dumps(
            {
                "object_kind": "note",
                "merge_request": {"iid": 42},
                "object_attributes": {
                    "note": 123,
                },
            }
        ),
    }

    response = lambda_handler(event, None)

    assert response == {
        "statusCode": 200,
        "body": "Event ignored",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {
            "object_kind": "push",
        },
        {
            "object_kind": "note",
            "issue": {"iid": 7},
            "object_attributes": {"note": "/review"},
        },
        {
            "object_kind": "note",
            "object_attributes": {"note": "/review"},
        },
    ],
)
def test_lambda_handler_ignores_unsupported_events(
    authorized_headers: dict[str, str],
    payload: dict[str, object],
) -> None:
    event = {
        "headers": authorized_headers,
        "body": json.dumps(payload),
    }

    response = lambda_handler(event, None)

    assert response == {
        "statusCode": 200,
        "body": "Event ignored",
    }