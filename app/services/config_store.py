"""Config store service — load/save app configuration using platformdirs + JSON."""

from __future__ import annotations

import json
from pathlib import Path

import platformdirs

APP_NAME = "AlteryxGitCompanion"


def _config_path() -> Path:
    """Return the path to the config JSON file, creating parent dirs as needed."""
    data_dir = Path(platformdirs.user_data_dir(APP_NAME))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "config.json"


def load_config() -> dict:
    """Load config from disk. Returns defaults if file doesn't exist yet."""
    p = _config_path()
    if not p.exists():
        return {"version": 1, "projects": [], "active_project": None}
    return json.loads(p.read_text(encoding="utf-8"))


def save_config(cfg: dict) -> None:
    """Persist config to disk."""
    _config_path().write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
