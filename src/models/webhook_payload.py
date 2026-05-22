from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class ProjectPayload(BaseModel):
    """Typed subset of the GitLab project block."""

    id: int | None = None

    model_config = ConfigDict(extra="ignore")


class MergeRequestPayload(BaseModel):
    """Typed subset of the GitLab merge request webhook block."""

    iid: int | None = None
    source_branch: str | None = None

    model_config = ConfigDict(extra="ignore")


class ObjectAttributesPayload(BaseModel):
    """Typed subset of GitLab webhook object attributes."""

    note: str

    model_config = ConfigDict(extra="ignore")


class GitLabWebhookPayload(BaseModel):
    """Typed representation of the GitLab webhook payload used by the app."""

    object_kind: str
    merge_request: MergeRequestPayload
    object_attributes: ObjectAttributesPayload
    project: ProjectPayload | None = None

    model_config = ConfigDict(extra="ignore")