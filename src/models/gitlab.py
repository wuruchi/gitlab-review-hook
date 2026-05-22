from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class MergeRequestDiff(BaseModel):
    """Typed representation of a changed file in a merge request."""

    old_path: str
    new_path: str
    diff: str

    model_config = ConfigDict(extra="ignore")