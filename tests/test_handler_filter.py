import json

import pytest

from src.handler import lambda_handler


@pytest.fixture
def authorized_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str]:
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "expected-secret")
    return {"X-Gitlab-Token": "expected-secret"}


def test_lambda_handler_accepts_review_note_on_merge_request(
    authorized_headers: dict[str, str],
) -> None:
    event = {
        "headers": authorized_headers,
        "body": json.dumps(
            {
                "object_kind": "note",
                "merge_request": {"iid": 42},
                "object_attributes": {
                    "note": "Please /review this change.",
                },
            }
        ),
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] != 401
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