from __future__ import annotations

import hmac
import json
import os
from typing import Any

from pydantic import ValidationError

from src.models.lambda_event import LambdaEvent
from src.models.lambda_response import AUTHORIZED_RESPONSE
from src.models.lambda_response import IGNORED_RESPONSE
from src.models.lambda_response import LambdaResponse
from src.models.lambda_response import UNAUTHORIZED_RESPONSE
from src.models.webhook_payload import GitLabWebhookPayload


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


def _parse_body(body: Any) -> GitLabWebhookPayload | None:
    """Parse the incoming JSON body into a typed webhook payload."""

    if not isinstance(body, str):
        return None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return GitLabWebhookPayload.model_validate(payload)
    except ValidationError:
        return None


def _parse_event(event: Any) -> LambdaEvent | None:
    """Parse the incoming Lambda event into a typed wrapper."""

    try:
        return LambdaEvent.model_validate(event)
    except ValidationError:
        return None


def _should_process_event(payload: GitLabWebhookPayload) -> bool:
    """Return whether the webhook payload is a supported review request."""

    if payload.object_kind != "note":
        return False

    return "/review" in payload.object_attributes.note


def lambda_handler(
    event: dict[str, Any], context: Any
) -> dict[str, Any]:
    """Authenticate and filter the incoming webhook request."""

    del context

    parsed_event = _parse_event(event)
    if parsed_event is None or not _is_authorized(parsed_event.headers):
        return _to_lambda_dict(UNAUTHORIZED_RESPONSE)

    payload = _parse_body(parsed_event.body)
    if payload is None or not _should_process_event(payload):
        return _to_lambda_dict(IGNORED_RESPONSE)

    return _to_lambda_dict(AUTHORIZED_RESPONSE)


def _to_lambda_dict(response: LambdaResponse) -> dict[str, Any]:
    """Convert a typed response model to the Lambda return shape."""

    return response.model_dump()
