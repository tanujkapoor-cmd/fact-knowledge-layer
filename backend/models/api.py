"""Schemas used at the HTTP boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Health information returned by the service."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    database: Literal["ok"]
    version: str
