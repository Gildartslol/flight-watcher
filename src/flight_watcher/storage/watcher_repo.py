from __future__ import annotations

from pathlib import Path

import yaml

from flight_watcher.domain.models import Watcher


def _clean_null_scalars(value):
    if isinstance(value, dict):
        return {k: _clean_null_scalars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_null_scalars(v) for v in value]
    if isinstance(value, str) and value.lower() in {"null", "~", "none", ""}:
        return None
    return value


class WatcherRepository:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def load_all(self) -> list[Watcher]:
        if not self.config_path.exists():
            return []
        raw = yaml.load(self.config_path.read_text(), Loader=yaml.BaseLoader) or {}
        data = _clean_null_scalars(raw)
        raw_watchers = data.get("watchers", [])
        return [Watcher.model_validate(item) for item in raw_watchers]

    def list_enabled(self) -> list[Watcher]:
        return [w for w in self.load_all() if w.enabled]

    def get(self, watcher_id: str) -> Watcher | None:
        for watcher in self.load_all():
            if watcher.id == watcher_id:
                return watcher
        return None
