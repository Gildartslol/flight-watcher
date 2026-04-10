from __future__ import annotations

from flight_watcher.domain.summary import build_watcher_summary
from flight_watcher.services.watcher_service import WatcherRunResult


class ReportService:
    def watcher_report(self, result: WatcherRunResult) -> str:
        return build_watcher_summary(
            result.watcher,
            result.options,
            previous_best_price=result.previous_best_price,
            threshold_hit=result.threshold_hit,
        )
