import pytest

from src.clients.gitlab_client import GitLabAPIError
from src.clients.gitlab_client import GitLabClient


def test_get_merge_request_diffs_parses_changes_and_sends_bearer_token(
    requests_mock: object,
) -> None:
    client = GitLabClient(
        base_url="https://gitlab.example.com/api/v4",
        token="secret-token",
    )
    endpoint = (
        "https://gitlab.example.com/api/v4/projects/123/"
        "merge_requests/456/changes"
    )
    requests_mock.get(
        endpoint,
        json={
            "changes": [
                {
                    "old_path": "src/old.py",
                    "new_path": "src/new.py",
                    "diff": "@@ -1 +1 @@\n-old\n+new\n",
                },
                {
                    "old_path": "README.md",
                    "new_path": "README.md",
                    "diff": "@@ -1 +1 @@\n-old title\n+new title\n",
                },
                {
                    "old_path": "package-lock.json",
                    "new_path": "package-lock.json",
                    "diff": "@@ -1 +1 @@\n-old lock\n+new lock\n",
                },
            ]
        },
    )

    diffs = client.get_merge_request_diffs(123, 456)

    assert len(diffs) == 2
    assert diffs[0].old_path == "src/old.py"
    assert diffs[0].new_path == "src/new.py"
    assert diffs[0].diff == "@@ -1 +1 @@\n-old\n+new\n"
    assert diffs[1].new_path == "README.md"
    assert requests_mock.last_request.headers["Authorization"] == (
        "Bearer secret-token"
    )


def test_get_merge_request_diffs_raises_for_non_200_response(
    requests_mock: object,
) -> None:
    client = GitLabClient(
        base_url="https://gitlab.example.com/api/v4",
        token="secret-token",
    )
    endpoint = (
        "https://gitlab.example.com/api/v4/projects/123/"
        "merge_requests/456/changes"
    )
    requests_mock.get(endpoint, status_code=500)

    with pytest.raises(GitLabAPIError, match="unexpected status: 500"):
        client.get_merge_request_diffs(123, 456)


def test_get_merge_request_diffs_raises_for_invalid_changes_payload(
    requests_mock: object,
) -> None:
    client = GitLabClient(
        base_url="https://gitlab.example.com/api/v4",
        token="secret-token",
    )
    endpoint = (
        "https://gitlab.example.com/api/v4/projects/123/"
        "merge_requests/456/changes"
    )
    requests_mock.get(
        endpoint,
        json={
            "changes": [
                {
                    "old_path": "src/old.py",
                    "diff": "@@ -1 +1 @@\n-old\n+new\n",
                }
            ]
        },
    )

    with pytest.raises(
        GitLabAPIError,
        match="invalid change entry",
    ):
        client.get_merge_request_diffs(123, 456)


def test_get_raw_file_content_returns_file_text(
    requests_mock: object,
) -> None:
    client = GitLabClient(
        base_url="https://gitlab.example.com/api/v4",
        token="secret-token",
    )
    endpoint = (
        "https://gitlab.example.com/api/v4/projects/123/"
        "repository/files/src%2Fmain.py/raw?ref=feature%2Fbranch"
    )
    requests_mock.get(endpoint, text="print('hello')\n")

    content = client.get_raw_file_content(123, "src/main.py", "feature/branch")

    assert content == "print('hello')\n"
    assert requests_mock.last_request.headers["Authorization"] == (
        "Bearer secret-token"
    )


def test_get_raw_file_content_returns_none_for_missing_file(
    requests_mock: object,
) -> None:
    client = GitLabClient(
        base_url="https://gitlab.example.com/api/v4",
        token="secret-token",
    )
    endpoint = (
        "https://gitlab.example.com/api/v4/projects/123/"
        "repository/files/missing.py/raw?ref=main"
    )
    requests_mock.get(endpoint, status_code=404)

    content = client.get_raw_file_content(123, "missing.py", "main")

    assert content is None


def test_post_merge_request_comment_posts_top_level_note(
    requests_mock: object,
) -> None:
    client = GitLabClient(
        base_url="https://gitlab.example.com/api/v4",
        token="secret-token",
    )
    endpoint = (
        "https://gitlab.example.com/api/v4/projects/123/"
        "merge_requests/456/notes"
    )
    requests_mock.post(endpoint, json={"id": 99, "body": "Review started"}, status_code=201)

    payload = client.post_merge_request_comment(123, 456, "Review started")

    assert payload == {"id": 99, "body": "Review started"}
    assert requests_mock.last_request.headers["Authorization"] == (
        "Bearer secret-token"
    )
    assert requests_mock.last_request.json() == {"body": "Review started"}


def test_post_inline_discussion_posts_targeted_line_comment(
    requests_mock: object,
) -> None:
    client = GitLabClient(
        base_url="https://gitlab.example.com/api/v4",
        token="secret-token",
    )
    endpoint = (
        "https://gitlab.example.com/api/v4/projects/123/"
        "merge_requests/456/discussions"
    )
    requests_mock.post(
        endpoint,
        json={"id": "discussion-1"},
        status_code=201,
    )

    payload = client.post_inline_discussion(
        123,
        456,
        "src/auth.py",
        42,
        "Use a constant-time comparison here.",
    )

    assert payload == {"id": "discussion-1"}
    assert requests_mock.last_request.headers["Authorization"] == (
        "Bearer secret-token"
    )
    assert requests_mock.last_request.json() == {
        "body": "Use a constant-time comparison here.",
        "position": {
            "position_type": "text",
            "new_path": "src/auth.py",
            "new_line": 42,
        },
    }


def test_post_merge_request_comment_raises_helpful_404_error(
    requests_mock: object,
) -> None:
    client = GitLabClient(
        base_url="https://gitlab.example.com/api/v4",
        token="secret-token",
    )
    endpoint = (
        "https://gitlab.example.com/api/v4/projects/123/"
        "merge_requests/456/notes"
    )
    requests_mock.post(endpoint, status_code=404)

    with pytest.raises(
        GitLabAPIError,
        match="Check GITLAB_BASE_URL, project ID, merge request IID",
    ):
        client.post_merge_request_comment(123, 456, "Review started")