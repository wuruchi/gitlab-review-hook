# GitLab Review Hook

Minimal Python 3.11 scaffold for a GitLab LLM code review bot.

## Requirements

- Python 3.11
- `pip`

## Install

Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you want to install the package with its development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Run The CLI

Load the default configuration file:

```bash
python -m src.cli
```

Or use the installed console script:

```bash
gitlab-review-hook
```

## Run Tests

Run the full test suite with pytest:

```bash
python -m pytest
```

Run only the configuration tests:

```bash
python -m pytest tests/test_config.py
```
