from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    project_root: Path
    config_path: Path
    data_dir: Path
    db_path: Path

    @classmethod
    def load(cls) -> "Settings":
        root_env = os.getenv("FLIGHT_WATCHER_ROOT")
        root = Path(root_env).expanduser().resolve() if root_env else Path(__file__).resolve().parents[2]
        config_path = Path(os.getenv("FLIGHT_WATCHER_CONFIG", root / "config" / "watchers.yaml"))
        data_dir = Path(os.getenv("FLIGHT_WATCHER_DATA_DIR", root / "data"))
        db_path = Path(os.getenv("FLIGHT_WATCHER_DB", data_dir / "flight_watcher.sqlite3"))
        settings = cls(
            project_root=root,
            config_path=config_path,
            data_dir=data_dir,
            db_path=db_path,
        )
        settings.ensure_dirs()
        return settings

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
