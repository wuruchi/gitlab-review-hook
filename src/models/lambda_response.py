from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class LambdaResponse(BaseModel):
    """Typed representation of an AWS Lambda proxy response."""

    statusCode: int
    body: str

    model_config = ConfigDict(frozen=True)


UNAUTHORIZED_RESPONSE = LambdaResponse(
    statusCode=401,
    body="Unauthorized",
)

IGNORED_RESPONSE = LambdaResponse(
    statusCode=200,
    body="Event ignored",
)

AUTHORIZED_RESPONSE = LambdaResponse(
    statusCode=200,
    body="Authorized",
)