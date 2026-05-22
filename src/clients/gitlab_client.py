from __future__ import annotations

from typing import Any

import requests
from pydantic import ValidationError

from src.file_filter import should_review_file
from src.models.gitlab import MergeRequestDiff


class GitLabAPIError(Exception):
    """Raised when the GitLab API returns an unexpected response."""


class GitLabClient:
    """Minimal GitLab REST client for merge request context retrieval."""

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    def get_merge_request_diffs(
        self,
        project_id: int | str,
        merge_request_iid: int | str,
    ) -> list[MergeRequestDiff]:
        """Return structured changed-file diffs for a merge request."""

        endpoint = (
            f"{self._base_url}/projects/{project_id}/merge_requests/"
            f"{merge_request_iid}/changes"
        )

        try:
            response = requests.get(
                endpoint,
                headers=self._build_headers(),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise GitLabAPIError(
                "Failed to communicate with GitLab API."
            ) from exc

        if response.status_code != 200:
            raise GitLabAPIError(
                "GitLab API returned an unexpected status: "
                f"{response.status_code}"
            )

        payload = response.json()
        changes = payload.get("changes")
        if not isinstance(changes, list):
            raise GitLabAPIError(
                "GitLab API response did not include a valid changes list."
            )

        return self._parse_changes(changes)

    def _build_headers(self) -> dict[str, str]:
        """Build headers for GitLab API authentication."""

        return {
            "Authorization": f"Bearer {self._token}",
        }

    def _parse_changes(
        self,
        changes: list[Any],
    ) -> list[MergeRequestDiff]:
        """Validate and normalize the GitLab changes payload."""

        parsed_changes: list[MergeRequestDiff] = []

        for change in changes:
            try:
                parsed_change = MergeRequestDiff.model_validate(change)
            except ValidationError as exc:
                raise GitLabAPIError(
                    "GitLab API response contained an invalid change entry."
                ) from exc

            if should_review_file(parsed_change.new_path):
                parsed_changes.append(parsed_change)

        return parsed_changes