from pathlib import Path

import pytest

from src.config_loader import ConfigLoaderError, load_config


def test_load_config_parses_valid_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
llm:
  provider: "gemini"
  model: "gemini-1.5-pro"
  system_prompt: "Review this diff."
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config["llm"]["provider"] == "gemini"
    assert config["llm"]["model"] == "gemini-1.5-pro"
    assert config["llm"]["system_prompt"] == "Review this diff."


def test_load_config_raises_for_missing_file(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.yaml"

    with pytest.raises(ConfigLoaderError, match="does not exist"):
        load_config(missing_file)


def test_load_config_raises_for_invalid_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("llm: [invalid", encoding="utf-8")

    with pytest.raises(ConfigLoaderError, match="Invalid YAML"):
        load_config(config_file)


def test_load_config_raises_for_non_mapping_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("- item1\n- item2\n", encoding="utf-8")

    with pytest.raises(ConfigLoaderError, match="top-level mapping"):
        load_config(config_file)