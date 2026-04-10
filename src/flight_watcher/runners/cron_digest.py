from __future__ import annotations

import argparse

from flight_watcher.adapters import FliAdapter
from flight_watcher.services.alert_service import AlertService
from flight_watcher.services.report_service import ReportService
from flight_watcher.services.search_service import SearchService
from flight_watcher.services.watcher_service import WatcherService
from flight_watcher.settings import Settings
from flight_watcher.storage.db import init_db
from flight_watcher.storage.history_repo import HistoryRepository
from flight_watcher.storage.watcher_repo import WatcherRepository


def run_digest(full_digest: bool = False) -> str:
    settings = Settings.load()
    conn = init_db(settings.db_path)

    watcher_repo = WatcherRepository(settings.config_path)
    history_repo = HistoryRepository(conn)
    search_service = SearchService(FliAdapter())
    watcher_service = WatcherService(search_service, history_repo)
    report_service = ReportService()
    alert_service = AlertService(history_repo)

    watchers = watcher_repo.list_enabled()
    if not watchers:
        return "flight-watcher: no enabled watchers"

    digest_lines: list[str] = []
    for watcher in watchers:
        try:
            result = watcher_service.run_watcher(watcher)
            if alert_service.should_emit(result, full_digest=full_digest):
                digest_lines.append(report_service.watcher_report(result))
        except Exception as exc:
            digest_lines.append(f"[{watcher.id}] error: {exc}")

    if not digest_lines:
        return "flight-watcher: nothing materially changed"

    return "\n\n".join(digest_lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flight watcher cron digest runner")
    parser.add_argument("--full-digest", action="store_true", help="Always include every watcher result")
    args = parser.parse_args()
    print(run_digest(full_digest=args.full_digest))


if __name__ == "__main__":
    main()
