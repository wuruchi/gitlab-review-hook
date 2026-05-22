import pytest

from src.file_filter import should_review_file


@pytest.mark.parametrize(
    ("file_path", "expected"),
    [
        ("src/main.py", True),
        ("src/styles.css", True),
        ("README.md", True),
        ("package-lock.json", False),
        ("frontend/yarn.lock", False),
        ("pnpm-lock.yaml", False),
        ("poetry.lock", False),
        ("rust/Cargo.lock", False),
        ("assets/app.min.js", False),
        ("assets/site.min.css", False),
        ("assets/logo.png", False),
        ("assets/photo.jpg", False),
        ("assets/photo.jpeg", False),
        ("assets/animation.gif", False),
        ("assets/favicon.ico", False),
        ("docs/report.pdf", False),
        ("downloads/archive.zip", False),
        ("assets/LOGO.PNG", False),
        ("src/minified.js", True),
    ],
)
def test_should_review_file(
    file_path: str,
    expected: bool,
) -> None:
    assert should_review_file(file_path) is expected