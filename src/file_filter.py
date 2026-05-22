from __future__ import annotations

import re


EXCLUDED_FILE_PATTERNS = [
    re.compile(
        r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|"
        r"poetry\.lock|Cargo\.lock)$"
    ),
    re.compile(r"\.min\.(js|css)$"),
    re.compile(r"\.(png|jpg|jpeg|gif|ico|pdf|zip)$", re.IGNORECASE),
]


def should_review_file(file_path: str) -> bool:
    """Return whether a changed file should be kept for review."""

    normalized_path = file_path.strip()
    if not normalized_path:
        return True

    for pattern in EXCLUDED_FILE_PATTERNS:
        if pattern.search(normalized_path):
            return False

    return True