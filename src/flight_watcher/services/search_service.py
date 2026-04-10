from __future__ import annotations

from flight_watcher.adapters.fli_adapter import FliAdapter, ProviderError
from flight_watcher.domain.models import DateOption, DateQuery, FlightOption, FlightQuery
from flight_watcher.domain.normalize import normalize_date_results, normalize_flight_results
from flight_watcher.domain.scoring import score_flight_options


class SearchService:
    def __init__(self, adapter: FliAdapter) -> None:
        self.adapter = adapter

    def search_flights(self, query: FlightQuery) -> list[FlightOption]:
        raw = self.adapter.search_flights(query)
        options = normalize_flight_results(raw, query)
        return score_flight_options(options)

    def search_dates(self, query: DateQuery) -> list[DateOption]:
        raw = self.adapter.search_dates(query)
        return normalize_date_results(raw, query)
