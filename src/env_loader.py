from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = REPO_ROOT / ".env"


def load_env_file(env_path: Path = DEFAULT_ENV_PATH) -> None:
    """Load environment variables from a simple .env file if present."""

    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())