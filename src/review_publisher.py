from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from src.clients.gitlab_client import GitLabAPIError
from src.clients.gitlab_client import GitLabClient


LOGGER = logging.getLogger(__name__)
FAILURE_ALERT = "⚠️ Sorry, I encountered an error while processing this review."


def publish_review_comments(
    gitlab_client: GitLabClient,
    project_id: int | str,
    merge_request_iid: int | str,
    review_comments: list[dict[str, Any]],
) -> None:
    """Publish parsed review comments with inline-to-global fallback."""

    for review_comment in review_comments:
        try:
            gitlab_client.post_inline_discussion(
                project_id,
                merge_request_iid,
                review_comment["file_path"],
                review_comment["line_number"],
                review_comment["comment"],
            )
        except GitLabAPIError as exc:
            if exc.status_code != 400:
                raise

            LOGGER.warning(
                "Falling back to merge request note for %s:%s because "
                "inline discussion posting failed with status 400.",
                review_comment["file_path"],
                review_comment["line_number"],
            )
            gitlab_client.post_merge_request_comment(
                project_id,
                merge_request_iid,
                _format_global_fallback_comment(review_comment),
            )


def run_review_publishing_workflow(
    publish_operation: Callable[[], list[dict[str, Any]]],
    gitlab_client: GitLabClient,
    project_id: int | str,
    merge_request_iid: int | str,
) -> None:
    """Run the end-to-end publish workflow with a catastrophic fallback."""

    try:
        review_comments = publish_operation()
        publish_review_comments(
            gitlab_client,
            project_id,
            merge_request_iid,
            review_comments,
        )
    except Exception:
        LOGGER.exception("Review publishing workflow failed.")
        gitlab_client.post_merge_request_comment(
            project_id,
            merge_request_iid,
            FAILURE_ALERT,
        )


def _format_global_fallback_comment(
    review_comment: dict[str, Any],
) -> str:
    """Format a fallback top-level comment for an inline review item."""

    return (
        f"{review_comment['file_path']}:{review_comment['line_number']} - "
        f"{review_comment['comment']}"
    )