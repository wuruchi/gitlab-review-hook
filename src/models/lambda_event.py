from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict


class LambdaEvent(BaseModel):
    """Typed subset of the AWS Lambda event used by this handler."""

    headers: dict[str, Any] | None = None
    body: str | None = None

    model_config = ConfigDict(extra="ignore")