from __future__ import annotations

import hmac
import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.clients.gitlab_client import GitLabClient
from src.config_loader import load_config
from src.env_loader import load_env_file
from src.llm_factory import LLMFactory
from src.llm_factory import parse_llm_json_response
from src.models.lambda_event import LambdaEvent
from src.models.lambda_response import AUTHORIZED_RESPONSE
from src.models.lambda_response import IGNORED_RESPONSE
from src.models.lambda_response import LambdaResponse
from src.models.lambda_response import UNAUTHORIZED_RESPONSE
from src.models.webhook_payload import GitLabWebhookPayload
from src.review_publisher import FAILURE_ALERT
from src.review_publisher import run_review_publishing_workflow


LOGGER = logging.getLogger(__name__)
CONFIG_PATH = Path(__file__).with_name("config.yaml")
DEFAULT_GITLAB_BASE_URL = "https://gitlab.com/api/v4"
REVIEW_IN_PROGRESS_COMMENT = "⏳ Review in progress..."


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
    """Authenticate, filter, and process the incoming webhook request."""

    del context
    load_env_file()

    parsed_event = _parse_event(event)
    if parsed_event is None or not _is_authorized(parsed_event.headers):
        return _to_lambda_dict(UNAUTHORIZED_RESPONSE)

    payload = _parse_body(parsed_event.body)
    if payload is None or not _should_process_event(payload):
        return _to_lambda_dict(IGNORED_RESPONSE)

    review_targets = _extract_review_targets(payload)
    if review_targets is None:
        return _to_lambda_dict(IGNORED_RESPONSE)

    project_id, merge_request_iid, source_branch = review_targets
    gitlab_client = _build_gitlab_client()

    try:
        _orchestrate_review(
            gitlab_client,
            payload,
            project_id,
            merge_request_iid,
            source_branch,
        )
    except Exception:
        LOGGER.exception("Handler review workflow failed.")
        _post_failure_alert(
            gitlab_client,
            project_id,
            merge_request_iid,
        )

    return _to_lambda_dict(AUTHORIZED_RESPONSE)


def _extract_review_targets(
    payload: GitLabWebhookPayload,
) -> tuple[int, int, str] | None:
    """Extract the MR routing fields needed for downstream API calls."""

    project_id = payload.project.id if payload.project is not None else None
    merge_request_iid = payload.merge_request.iid
    source_branch = payload.merge_request.source_branch

    if project_id is None or merge_request_iid is None:
        return None

    if not isinstance(source_branch, str) or not source_branch.strip():
        return None

    return project_id, merge_request_iid, source_branch


def _build_gitlab_client() -> GitLabClient:
    """Create the GitLab API client for the current environment."""

    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        raise RuntimeError("GITLAB_TOKEN is required for review publishing.")

    base_url = os.environ.get("GITLAB_BASE_URL", DEFAULT_GITLAB_BASE_URL)
    return GitLabClient(base_url=base_url, token=token)


def _orchestrate_review(
    gitlab_client: GitLabClient,
    payload: GitLabWebhookPayload,
    project_id: int,
    merge_request_iid: int,
    source_branch: str,
) -> None:
    """Run the end-to-end review pipeline for a valid MR review request."""

    gitlab_client.post_merge_request_comment(
        project_id,
        merge_request_iid,
        REVIEW_IN_PROGRESS_COMMENT,
    )
    config = load_config(CONFIG_PATH)
    provider = LLMFactory.create_provider(config)
    llm_config = config.get("llm", {})
    system_prompt = llm_config.get("system_prompt")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise RuntimeError("LLM configuration requires a system prompt.")

    def publish_operation() -> list[dict[str, Any]]:
        user_prompt = _build_review_prompt(
            gitlab_client,
            payload,
            project_id,
            merge_request_iid,
            source_branch,
        )
        raw_response = provider.generate_review(system_prompt, user_prompt)
        return parse_llm_json_response(raw_response)

    run_review_publishing_workflow(
        publish_operation,
        gitlab_client,
        project_id,
        merge_request_iid,
    )


def _build_review_prompt(
    gitlab_client: GitLabClient,
    payload: GitLabWebhookPayload,
    project_id: int,
    merge_request_iid: int,
    source_branch: str,
) -> str:
    """Assemble MR diff and file content context for the review model."""

    diffs = gitlab_client.get_merge_request_diffs(project_id, merge_request_iid)
    prompt_sections = [
        "Review request note:",
        payload.object_attributes.note,
        "",
        "Merge request code context:",
    ]

    for diff in diffs:
        raw_content = gitlab_client.get_raw_file_content(
            project_id,
            diff.new_path,
            source_branch,
        )
        prompt_sections.extend(
            [
                f"File: {diff.new_path}",
                "Diff:",
                diff.diff,
                "Full file content:",
                raw_content if raw_content is not None else "<unavailable>",
                "",
            ]
        )

    return "\n".join(prompt_sections)


def _post_failure_alert(
    gitlab_client: GitLabClient,
    project_id: int,
    merge_request_iid: int,
) -> None:
    """Post the catastrophic failure alert without masking the original error."""

    try:
        gitlab_client.post_merge_request_comment(
            project_id,
            merge_request_iid,
            FAILURE_ALERT,
        )
    except Exception:
        LOGGER.exception("Failed to post catastrophic failure alert.")


def _to_lambda_dict(response: LambdaResponse) -> dict[str, Any]:
    """Convert a typed response model to the Lambda return shape."""

    return response.model_dump()
