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