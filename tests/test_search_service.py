import sqlite3

import pytest

from flight_watcher.adapters.fli_adapter import FliAdapter, ProviderError
from flight_watcher.domain.models import DateQuery, FlightQuery, Watcher
from flight_watcher.services.search_service import SearchService
from flight_watcher.services.watcher_service import WatcherService
from flight_watcher.storage.db import init_db
from flight_watcher.storage.history_repo import HistoryRepository


class FakeAdapter:
    def search_flights(self, **kwargs):
        return {
            "results": [
                {
                    "price": {"amount": 120, "currency": "EUR"},
                    "duration_min": 180,
                    "stops": 0,
                    "legs": [{"airline": "LH", "departure": "2026-05-15T08:00:00+00:00", "arrival": "2026-05-15T11:00:00+00:00"}],
                },
                {
                    "price": {"amount": 110, "currency": "EUR"},
                    "duration_min": 350,
                    "stops": 1,
                    "legs": [{"airline": "KL", "departure": "2026-05-15T06:00:00+00:00", "arrival": "2026-05-15T12:00:00+00:00"}],
                },
            ]
        }

    def search_dates(self, **kwargs):
        return {
            "date_options": [
                {"date": "2026-05-10", "total_price": 150, "currency": "EUR", "trip_duration": 3},
                {"date": "2026-05-11", "total_price": 130, "currency": "EUR", "trip_duration": 3},
            ]
        }


class FailingAdapter:
    def search_flights(self, **kwargs):
        raise RuntimeError("boom")

    def search_dates(self, **kwargs):
        raise RuntimeError("boom")


def test_adapter_exposes_search_methods():
    adapter = FliAdapter(client=FakeAdapter())
    assert hasattr(adapter, "search_flights")
    assert hasattr(adapter, "search_dates")


def test_dates_cli_requests_round_trip_mode_and_preserves_return_date(monkeypatch):
    adapter = FliAdapter()
    captured_cmd = []

    def fake_run_cli(cmd):
        captured_cmd.extend(cmd)
        return {
            "dates": [
                {
                    "date": ["2026-06-07", "2026-06-10"],
                    "price": 199,
                    "currency": "EUR",
                }
            ]
        }

    monkeypatch.setattr(adapter, "_run_cli", fake_run_cli)

    out = adapter.search_dates(
        DateQuery(
            origin="MUC",
            destination="LIS",
            start_date="2026-06-01",
            end_date="2026-06-30",
            trip_duration=3,
        )
    )

    assert "--round" in captured_cmd
    assert out["date_options"][0]["return_date"] == "2026-06-10"


def test_database_initializes_schema(tmp_path):
    db_path = tmp_path / "x.sqlite3"
    conn = init_db(db_path)
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_snapshots'").fetchone()
    assert row is not None


def test_snapshot_insert_and_duplicate_handling(tmp_path):
    db_path = tmp_path / "x.sqlite3"
    conn = init_db(db_path)
    history = HistoryRepository(conn)

    run_id = history.start_run("w1")
    search = SearchService(FliAdapter(client=FakeAdapter()))
    options = search.search_flights(FlightQuery(origin="MUC", destination="LIS", departure_date="2026-05-15"))

    inserted_first = history.insert_snapshots(run_id, "w1", options)
    inserted_second = history.insert_snapshots(run_id, "w1", options)

    assert inserted_first > 0
    assert inserted_second == 0


def test_latest_price_lookup(tmp_path):
    db_path = tmp_path / "x.sqlite3"
    conn = init_db(db_path)
    history = HistoryRepository(conn)
    search = SearchService(FliAdapter(client=FakeAdapter()))
    options = search.search_flights(FlightQuery(origin="MUC", destination="LIS", departure_date="2026-05-15"))
    run_id = history.start_run("w1")
    history.insert_snapshots(run_id, "w1", options)

    assert history.latest_price("w1") is not None


def test_manual_search_returns_ranked_normalized_options():
    service = SearchService(FliAdapter(client=FakeAdapter()))
    options = service.search_flights(FlightQuery(origin="MUC", destination="LIS", departure_date="2026-05-15"))
    assert len(options) == 2
    assert options[0].score is not None
    assert options[0].origin == "MUC"


def test_flexible_search_returns_ranked_date_options():
    service = SearchService(FliAdapter(client=FakeAdapter()))
    options = service.search_dates(
        DateQuery(origin="MUC", destination="LIS", start_date="2026-05-01", end_date="2026-05-31", trip_duration=3)
    )
    assert len(options) == 2
    assert options[0].total_price <= options[1].total_price


def test_watcher_run_stores_snapshots(tmp_path):
    conn = init_db(tmp_path / "x.sqlite3")
    history = HistoryRepository(conn)
    search = SearchService(FliAdapter(client=FakeAdapter()))
    watcher_service = WatcherService(search, history)
    watcher = Watcher(
        id="w1",
        name="test",
        enabled=True,
        origin="MUC",
        destination="LIS",
        search_mode="specific",
        departure_date="2026-05-15",
        return_date=None,
        start_date=None,
        end_date=None,
        trip_duration=None,
        weekend_only=False,
        cabin_class="economy",
        max_stops="any",
        max_price=None,
        sort_goal="best_value",
        notify_if_below_price=None,
        notify_on_drop_percent=None,
        notes=None,
    )
    result = watcher_service.run_watcher(watcher)
    count = conn.execute("SELECT COUNT(*) c FROM price_snapshots WHERE watcher_id='w1'").fetchone()[0]
    assert result.run_id > 0
    assert count > 0


def test_provider_failure_returns_clean_local_error():
    service = SearchService(FliAdapter(client=FailingAdapter()))
    with pytest.raises(ProviderError):
        service.search_flights(FlightQuery(origin="MUC", destination="LIS", departure_date="2026-05-15"))
