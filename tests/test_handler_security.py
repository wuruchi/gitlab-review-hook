import pytest

from src.handler import lambda_handler


@pytest.fixture
def base_event() -> dict[str, dict[str, str]]:
    return {
        "headers": {
            "X-Gitlab-Token": "expected-secret",
        }
    }


def test_lambda_handler_accepts_correct_token(
    monkeypatch: pytest.MonkeyPatch,
    base_event: dict[str, dict[str, str]],
) -> None:
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "expected-secret")

    response = lambda_handler(base_event, None)

    assert response["statusCode"] != 401


def test_lambda_handler_rejects_incorrect_token(
    monkeypatch: pytest.MonkeyPatch,
    base_event: dict[str, dict[str, str]],
) -> None:
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "expected-secret")

    event = {
        "headers": {
            "X-Gitlab-Token": "wrong-secret",
        }
    }

    response = lambda_handler(event, None)

    assert response == {
        "statusCode": 401,
        "body": "Unauthorized",
    }


def test_lambda_handler_rejects_missing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "expected-secret")

    response = lambda_handler({"headers": {}}, None)

    assert response == {
        "statusCode": 401,
        "body": "Unauthorized",
    }