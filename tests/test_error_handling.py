from __future__ import annotations

import logging

import pytest

from src.clients.gitlab_client import GitLabAPIError
from src.review_publisher import FAILURE_ALERT
from src.review_publisher import publish_review_comments
from src.review_publisher import run_review_publishing_workflow


def test_publish_review_comments_falls_back_to_global_comment_on_bad_request(
    mocker: pytest.MockFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    gitlab_client = mocker.Mock()
    gitlab_client.post_inline_discussion.side_effect = GitLabAPIError(
        "GitLab API returned an unexpected status: 400",
        status_code=400,
    )

    review_comments = [
        {
            "file_path": "src/auth.py",
            "line_number": 42,
            "comment": "Use a constant-time comparison here.",
        }
    ]

    with caplog.at_level(logging.WARNING):
        publish_review_comments(gitlab_client, 123, 456, review_comments)

    gitlab_client.post_merge_request_comment.assert_called_once_with(
        123,
        456,
        "src/auth.py:42 - Use a constant-time comparison here.",
    )
    assert "Falling back to merge request note" in caplog.text


def test_run_review_publishing_workflow_posts_failure_alert_on_total_collapse(
    mocker: pytest.MockFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    gitlab_client = mocker.Mock()

    def publish_operation() -> list[dict[str, object]]:
        raise RuntimeError("LLM unavailable")

    with caplog.at_level(logging.ERROR):
        run_review_publishing_workflow(
            publish_operation,
            gitlab_client,
            123,
            456,
        )

    gitlab_client.post_merge_request_comment.assert_called_once_with(
        123,
        456,
        FAILURE_ALERT,
    )
    assert "Review publishing workflow failed." in caplog.text
    assert "Traceback" in caplog.text