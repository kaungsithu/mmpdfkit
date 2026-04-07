"""Tests for config file loading."""
import tempfile
from pathlib import Path

from mmpdfkit.config import load_config


def test_load_config_default():
    """Default config when file missing."""
    result = load_config()
    assert result["enable_ocr"] is True


def test_load_config_from_file():
    """Load config from ~/.mmpdfkit/config.yaml."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("enable_ocr: false\n")
        f.flush()
        config_path = f.name

    try:
        result = load_config(config_path)
        assert result["enable_ocr"] is False
    finally:
        Path(config_path).unlink()


def test_load_config_malformed():
    """Handle invalid YAML gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: [content\n")
        f.flush()
        config_path = f.name

    try:
        # Should not raise, should use defaults
        result = load_config(config_path)
        assert result["enable_ocr"] is True
    finally:
        Path(config_path).unlink()
