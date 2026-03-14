"""Config store service — skeleton (Plan 02 implements save_config)."""

from __future__ import annotations

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
    config_file = _config_path()
    if config_file.exists():
        import json

        with config_file.open("r", encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]
    return {"version": 1, "projects": [], "active_project": None}


def save_config(cfg: dict) -> None:
    """Persist config to disk."""
    raise NotImplementedError("save_config implemented in Plan 02")
