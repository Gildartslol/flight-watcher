from __future__ import annotations

import json

import typer

from flight_watcher.adapters import FliAdapter, ProviderError
from flight_watcher.domain.models import DateQuery, FlightQuery
from flight_watcher.runners.cron_digest import run_digest
from flight_watcher.services.report_service import ReportService
from flight_watcher.services.search_service import SearchService
from flight_watcher.services.watcher_service import WatcherService
from flight_watcher.settings import Settings
from flight_watcher.storage.db import init_db
from flight_watcher.storage.history_repo import HistoryRepository
from flight_watcher.storage.watcher_repo import WatcherRepository

app = typer.Typer(help="Personal flight watcher for Hermes")


def _build_runtime() -> tuple[SearchService, WatcherRepository, WatcherService, ReportService]:
    settings = Settings.load()
    conn = init_db(settings.db_path)
    history_repo = HistoryRepository(conn)
    watcher_repo = WatcherRepository(settings.config_path)
    search_service = SearchService(FliAdapter())
    watcher_service = WatcherService(search_service, history_repo)
    report_service = ReportService()
    return search_service, watcher_repo, watcher_service, report_service


def _render(data: object, json_output: bool) -> None:
    if json_output:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


@app.command()
def health() -> None:
    print("ok")


@app.command("search-flight")
def search_flight(
    origin: str = typer.Option(...),
    destination: str = typer.Option(...),
    departure_date: str = typer.Option(..., "--departure-date"),
    return_date: str | None = typer.Option(None, "--return-date"),
    cabin_class: str = typer.Option("economy", "--cabin-class"),
    max_stops: str = typer.Option("any", "--max-stops"),
    json_output: bool = typer.Option(False, "--json-output"),
) -> None:
    search_service, _, _, _ = _build_runtime()
    try:
        options = search_service.search_flights(
            FlightQuery(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                cabin_class=cabin_class,
                max_stops=max_stops,
            )
        )
    except ProviderError as exc:
        print(f"provider error: {exc}")
        raise typer.Exit(1)

    if json_output:
        _render([o.model_dump(mode="json") for o in options], True)
    else:
        if not options:
            print("no options")
            return
        for idx, option in enumerate(options[:5], start=1):
            print(
                f"{idx}) {option.total_price:.0f} {option.currency} | {option.departure_date} | "
                f"{option.total_duration_min}m | {option.stops} stop(s) | score={option.score}"
            )


@app.command("search-dates")
def search_dates(
    origin: str = typer.Option(...),
    destination: str = typer.Option(...),
    start_date: str = typer.Option(..., "--start-date"),
    end_date: str = typer.Option(..., "--end-date"),
    trip_duration: int = typer.Option(..., "--trip-duration"),
    weekend_only: bool = typer.Option(False, "--weekend-only"),
    cabin_class: str = typer.Option("economy", "--cabin-class"),
    max_stops: str = typer.Option("any", "--max-stops"),
    json_output: bool = typer.Option(False, "--json-output"),
) -> None:
    search_service, _, _, _ = _build_runtime()
    try:
        options = search_service.search_dates(
            DateQuery(
                origin=origin,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                trip_duration=trip_duration,
                weekend_only=weekend_only,
                cabin_class=cabin_class,
                max_stops=max_stops,
            )
        )
    except ProviderError as exc:
        print(f"provider error: {exc}")
        raise typer.Exit(1)

    if json_output:
        _render([o.model_dump(mode="json") for o in options], True)
    else:
        if not options:
            print("no options")
            return
        for idx, option in enumerate(options[:8], start=1):
            print(f"{idx}) {option.departure_date} | {option.total_price:.0f} {option.currency}")


@app.command("run-watcher")
def run_watcher(watcher_id: str, json_output: bool = typer.Option(False, "--json-output")) -> None:
    _, watcher_repo, watcher_service, report_service = _build_runtime()
    watcher = watcher_repo.get(watcher_id)
    if not watcher:
        print(f"watcher not found: {watcher_id}")
        raise typer.Exit(1)

    try:
        result = watcher_service.run_watcher(watcher)
    except ProviderError as exc:
        print(f"provider error: {exc}")
        raise typer.Exit(1)

    if json_output:
        payload = {
            "watcher_id": watcher.id,
            "material_change": result.material_change,
            "options": [o.model_dump(mode="json") for o in result.options],
        }
        _render(payload, True)
    else:
        print(report_service.watcher_report(result))


@app.command("run-all-watchers")
def run_all_watchers(full_digest: bool = typer.Option(False, "--full-digest")) -> None:
    print(run_digest(full_digest=full_digest))


if __name__ == "__main__":
    app()
