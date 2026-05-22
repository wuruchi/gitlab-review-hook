from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigLoaderError(Exception):
    """Raised when configuration loading fails."""


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load application configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        ConfigLoaderError: If the file is missing, unreadable, invalid,
            or does not contain a top-level mapping.
    """

    path = Path(config_path)

    if not path.is_file():
        raise ConfigLoaderError(
            f"Configuration file does not exist: {path}"
        )

    try:
        raw_content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigLoaderError(
            f"Unable to read configuration file: {path}"
        ) from exc

    try:
        config = yaml.safe_load(raw_content)
    except yaml.YAMLError as exc:
        raise ConfigLoaderError(
            f"Invalid YAML configuration in file: {path}"
        ) from exc

    if not isinstance(config, dict):
        raise ConfigLoaderError(
            "Configuration must contain a top-level mapping."
        )

    return config
