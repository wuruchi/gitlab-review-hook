from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests
from pydantic import ValidationError

from src.file_filter import should_review_file
from src.models.gitlab import MergeRequestDiff


class GitLabAPIError(Exception):
    """Raised when the GitLab API returns an unexpected response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


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
                f"{response.status_code}",
                status_code=response.status_code,
            )

        payload = response.json()
        changes = payload.get("changes")
        if not isinstance(changes, list):
            raise GitLabAPIError(
                "GitLab API response did not include a valid changes list."
            )

        return self._parse_changes(changes)

    def get_raw_file_content(
        self,
        project_id: int | str,
        file_path: str,
        ref: str,
    ) -> str | None:
        """Return raw file content for a repository path at a given ref."""

        encoded_file_path = quote(file_path, safe="")
        encoded_ref = quote(ref, safe="")
        endpoint = (
            f"{self._base_url}/projects/{project_id}/repository/files/"
            f"{encoded_file_path}/raw?ref={encoded_ref}"
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

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise GitLabAPIError(
                "GitLab API returned an unexpected status: "
                f"{response.status_code}",
                status_code=response.status_code,
            )

        return response.text

    def post_merge_request_comment(
        self,
        project_id: int | str,
        merge_request_iid: int | str,
        body: str,
    ) -> dict[str, Any]:
        """Post a top-level note to a merge request."""

        endpoint = (
            f"{self._base_url}/projects/{project_id}/merge_requests/"
            f"{merge_request_iid}/notes"
        )
        payload = {"body": body}

        return self._post_json(endpoint, payload)

    def post_inline_discussion(
        self,
        project_id: int | str,
        merge_request_iid: int | str,
        file_path: str,
        line_number: int,
        comment_text: str,
    ) -> dict[str, Any]:
        """Post a targeted inline discussion comment for a merge request."""

        endpoint = (
            f"{self._base_url}/projects/{project_id}/merge_requests/"
            f"{merge_request_iid}/discussions"
        )
        payload = {
            "body": comment_text,
            "position": {
                "position_type": "text",
                "new_path": file_path,
                "new_line": line_number,
            },
        }

        return self._post_json(endpoint, payload)

    def _build_headers(self) -> dict[str, str]:
        """Build headers for GitLab API authentication."""

        return {
            "Authorization": f"Bearer {self._token}",
        }

    def _post_json(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send an authenticated JSON POST request to GitLab."""

        try:
            response = requests.post(
                endpoint,
                headers=self._build_headers(),
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise GitLabAPIError(
                "Failed to communicate with GitLab API."
            ) from exc

        if response.status_code not in {200, 201}:
            raise GitLabAPIError(
                "GitLab API returned an unexpected status: "
                f"{response.status_code}",
                status_code=response.status_code,
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise GitLabAPIError(
                "GitLab API response did not include a valid object payload."
            )

        return payload

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