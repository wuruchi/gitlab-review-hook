from __future__ import annotations

import hmac
import os
from typing import Any


UNAUTHORIZED_RESPONSE = {
    "statusCode": 401,
    "body": "Unauthorized",
}


def _get_gitlab_token(headers: dict[str, Any] | None) -> str | None:
    """Extract the GitLab webhook token from request headers."""

    if not headers:
        return None

    normalized_headers = {
        str(key).lower(): value for key, value in headers.items()
    }
    token = normalized_headers.get("x-gitlab-token")

    if token is None:
        return None

    return str(token)


def _is_authorized(headers: dict[str, Any] | None) -> bool:
    """Validate the GitLab webhook token using constant-time compare."""

    provided_token = _get_gitlab_token(headers)
    expected_token = os.environ.get("GITLAB_WEBHOOK_SECRET")

    if provided_token is None or expected_token is None:
        return False

    return hmac.compare_digest(provided_token, expected_token)


def lambda_handler(
    event: dict[str, Any], context: Any
) -> dict[str, Any]:
    """Authenticate the incoming webhook request."""

    del context

    headers = event.get("headers")
    if not _is_authorized(headers):
        return UNAUTHORIZED_RESPONSE

    return {
        "statusCode": 200,
        "body": "Authorized",
    }
