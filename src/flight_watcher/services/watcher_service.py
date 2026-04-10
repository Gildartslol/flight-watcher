from __future__ import annotations

from dataclasses import dataclass

from flight_watcher.domain.models import DateQuery, FlightOption, FlightQuery, Watcher
from flight_watcher.domain.scoring import pick_best_value, pick_cheapest
from flight_watcher.services.search_service import SearchService
from flight_watcher.storage.history_repo import HistoryRepository


@dataclass(slots=True)
class WatcherRunResult:
    watcher: Watcher
    options: list[FlightOption]
    run_id: int
    previous_best_price: float | None
    cheapest: FlightOption | None
    best_value: FlightOption | None
    threshold_hit: bool
    drop_percent_hit: bool

    @property
    def material_change(self) -> bool:
        return self.threshold_hit or self.drop_percent_hit


class WatcherService:
    def __init__(self, search_service: SearchService, history_repo: HistoryRepository) -> None:
        self.search_service = search_service
        self.history_repo = history_repo

    def run_watcher(self, watcher: Watcher) -> WatcherRunResult:
        run_id = self.history_repo.start_run(watcher.id)
        previous_best = self.history_repo.previous_best_price(watcher.id, before_run_id=run_id)
        try:
            if watcher.search_mode == "specific":
                options = self.search_service.search_flights(
                    FlightQuery(
                        origin=watcher.origin,
                        destination=watcher.destination,
                        departure_date=watcher.departure_date or "",
                        return_date=watcher.return_date,
                        cabin_class=watcher.cabin_class,
                        max_stops=watcher.max_stops,
                    )
                )
            else:
                date_options = self.search_service.search_dates(
                    DateQuery(
                        origin=watcher.origin,
                        destination=watcher.destination,
                        start_date=watcher.start_date or "",
                        end_date=watcher.end_date or "",
                        trip_duration=watcher.trip_duration or 3,
                        weekend_only=watcher.weekend_only,
                        cabin_class=watcher.cabin_class,
                        max_stops=watcher.max_stops,
                    )
                )
                options = [
                    FlightOption(
                        provider=d.provider,
                        searched_at=d.searched_at,
                        origin=d.origin,
                        destination=d.destination,
                        departure_date=d.departure_date,
                        return_date=d.return_date,
                        total_price=d.total_price,
                        currency=d.currency,
                        total_duration_min=(watcher.trip_duration or d.trip_duration) * 24 * 60,
                        stops=0,
                        airlines=[],
                        legs=[],
                        score=d.score,
                        tags=d.tags,
                        fingerprint=d.fingerprint,
                    )
                    for d in date_options
                ]

            self.history_repo.insert_snapshots(run_id, watcher.id, options)
            cheapest = pick_cheapest(options)
            best_value = pick_best_value(options)
            threshold_hit = bool(
                watcher.notify_if_below_price is not None
                and cheapest is not None
                and cheapest.total_price <= watcher.notify_if_below_price
            )
            drop_percent_hit = False
            if watcher.notify_on_drop_percent and cheapest and previous_best:
                drop_pct = ((previous_best - cheapest.total_price) / previous_best) * 100
                drop_percent_hit = drop_pct >= watcher.notify_on_drop_percent

            self.history_repo.finish_run(run_id, status="ok")
            return WatcherRunResult(
                watcher=watcher,
                options=options,
                run_id=run_id,
                previous_best_price=previous_best,
                cheapest=cheapest,
                best_value=best_value,
                threshold_hit=threshold_hit,
                drop_percent_hit=drop_percent_hit,
            )
        except Exception as exc:
            self.history_repo.finish_run(run_id, status="error", message=str(exc))
            raise
