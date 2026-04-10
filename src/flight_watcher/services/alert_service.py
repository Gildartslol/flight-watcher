from __future__ import annotations

from flight_watcher.services.watcher_service import WatcherRunResult
from flight_watcher.storage.history_repo import HistoryRepository


class AlertService:
    def __init__(self, history_repo: HistoryRepository) -> None:
        self.history_repo = history_repo

    def should_emit(self, result: WatcherRunResult, full_digest: bool = False) -> bool:
        if full_digest:
            return True
        if not result.options:
            return False

        changed = result.material_change
        if not changed:
            return False

        cheapest = result.cheapest
        if cheapest is None:
            return False

        alert_type = "threshold" if result.threshold_hit else "drop_percent"
        if self.history_repo.alert_sent(result.watcher.id, cheapest.fingerprint, alert_type):
            return False

        self.history_repo.mark_alert_sent(
            watcher_id=result.watcher.id,
            fingerprint=cheapest.fingerprint,
            alert_type=alert_type,
            details={"run_id": result.run_id},
        )
        return True
