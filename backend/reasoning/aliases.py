"""Validated, user-configurable aliases for deterministic canonicalization."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class AliasConfig(BaseModel):
    """Explicit aliases; an empty file preserves conservative exact matching."""

    model_config = ConfigDict(extra="forbid")

    entity_aliases: dict[str, str] = Field(default_factory=dict)
    predicate_aliases: dict[str, str] = Field(default_factory=dict)


def load_alias_config(path: str | Path | None) -> AliasConfig:
    """Load aliases from JSON, or return an empty configuration when unset."""

    if path is None:
        return AliasConfig()
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"alias configuration does not exist: {config_path}")
    return AliasConfig.model_validate(json.loads(config_path.read_text(encoding="utf-8")))
