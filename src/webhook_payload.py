from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class MergeRequestPayload(BaseModel):
    """Typed subset of the GitLab merge request webhook block."""

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

    model_config = ConfigDict(extra="ignore")