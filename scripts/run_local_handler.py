from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = REPO_ROOT / ".env"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_env_file = importlib.import_module("src.env_loader").load_env_file
lambda_handler = importlib.import_module("src.handler").lambda_handler


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for local handler execution."""

    parser = argparse.ArgumentParser(
        description="Run the GitLab review hook Lambda handler locally."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help="Path to a .env file to load before invoking the handler.",
    )
    parser.add_argument(
        "--event-file",
        type=Path,
        help="Path to a JSON file containing the full Lambda event.",
    )
    parser.add_argument(
        "--project-id",
        type=int,
        default=123,
        help="GitLab project ID for the generated sample event.",
    )
    parser.add_argument(
        "--merge-request-iid",
        type=int,
        default=456,
        help="Merge request IID for the generated sample event.",
    )
    parser.add_argument(
        "--source-branch",
        default="feature/local-review",
        help="Source branch for the generated sample event.",
    )
    parser.add_argument(
        "--note",
        default="Please /review this merge request.",
        help="Review note text for the generated sample event.",
    )
    parser.add_argument(
        "--webhook-token",
        help=(
            "Webhook token header value. Defaults to GITLAB_WEBHOOK_SECRET "
            "after loading the env file."
        ),
    )
    parser.add_argument(
        "--print-event",
        action="store_true",
        help="Print the generated or loaded Lambda event before invocation.",
    )
    return parser


def build_sample_event(args: argparse.Namespace) -> dict[str, Any]:
    """Build a sample GitLab note webhook Lambda event."""

    webhook_token = args.webhook_token or os.environ.get(
        "GITLAB_WEBHOOK_SECRET",
        "replace-with-your-webhook-secret",
    )
    body = {
        "object_kind": "note",
        "project": {
            "id": args.project_id,
        },
        "merge_request": {
            "iid": args.merge_request_iid,
            "source_branch": args.source_branch,
        },
        "object_attributes": {
            "note": args.note,
        },
    }
    return {
        "headers": {
            "X-Gitlab-Token": webhook_token,
        },
        "body": json.dumps(body),
    }


def load_event(event_file: Path | None, args: argparse.Namespace) -> dict[str, Any]:
    """Load the Lambda event from disk or create a sample event."""

    if event_file is None:
        return build_sample_event(args)

    event = json.loads(event_file.read_text(encoding="utf-8"))
    if not isinstance(event, dict):
        raise ValueError("Event file must contain a top-level JSON object.")

    return event


def main() -> int:
    """Run the Lambda handler locally and print the response."""

    parser = build_parser()
    args = parser.parse_args()
    load_env_file(args.env_file)
    event = load_event(args.event_file, args)

    if args.print_event:
        print("Lambda event:")
        print(json.dumps(event, indent=2))

    response = lambda_handler(event, None)
    print("Lambda response:")
    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())