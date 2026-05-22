from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config_loader import ConfigLoaderError, load_config


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description="Load and inspect the GitLab review bot configuration."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the YAML configuration file.",
    )
    return parser


def main() -> int:
    """Load configuration and print a minimal summary."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except ConfigLoaderError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(config, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())