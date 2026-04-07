"""Configuration file handling for mmpdfkit."""

from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG = {
    "enable_ocr": True,
}


def load_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """
    Load mmpdfkit configuration from YAML file.

    Looks for ~/.mmpdfkit/config.yaml by default.
    Falls back to defaults if file missing or invalid.

    Args:
        config_path: Optional explicit path to config file (for testing)

    Returns:
        Dict with at least {"enable_ocr": bool}
    """
    if config_path is None:
        config_path = Path.home() / ".mmpdfkit" / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return DEFAULT_CONFIG.copy()

    try:
        import yaml

        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
    except Exception:
        # Invalid YAML, missing PyYAML, etc. — use defaults
        return DEFAULT_CONFIG.copy()

    # Merge user config with defaults (user settings override)
    result = DEFAULT_CONFIG.copy()
    result.update(user_config)
    return result
