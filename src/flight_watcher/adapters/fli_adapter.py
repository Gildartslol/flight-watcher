from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from flight_watcher.domain.models import DateQuery, FlightQuery


class ProviderError(RuntimeError):
    pass


class FliAdapter:
    """Thin wrapper around the fli backend.

    Strategy:
    1) Use injected client in tests.
    2) Try Python module-level API if present.
    3) Fall back to fli CLI JSON output.
    """

    def __init__(self, client: Any | None = None) -> None:
        self.client = client

    def search_flights(self, query: FlightQuery) -> dict[str, Any]:
        payload = query.model_dump()
        return self._dispatch("search_flights", payload)

    def search_dates(self, query: DateQuery) -> dict[str, Any]:
        payload = query.model_dump()
        return self._dispatch("search_dates", payload)

    def _dispatch(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.client is not None:
                fn = getattr(self.client, method, None)
                if callable(fn):
                    data = fn(**payload)
                    return data if isinstance(data, dict) else {"results": data}

            # Prefer Python API if package exposes one.
            try:
                fli = __import__("fli")
                direct = getattr(fli, method, None)
                if callable(direct):
                    data = direct(**payload)
                    return data if isinstance(data, dict) else {"results": data}
            except Exception:
                pass

            # Fallback: CLI contract from fli package.
            if method == "search_flights":
                return self._cli_search_flights(payload)
            return self._cli_search_dates(payload)

        except ProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise ProviderError(f"provider request failed: {exc}") from exc

    def _cli_search_flights(self, payload: dict[str, Any]) -> dict[str, Any]:
        cmd = [
            sys.executable,
            "-m",
            "fli.cli.main",
            "flights",
            payload["origin"],
            payload["destination"],
            payload["departure_date"],
            "--format",
            "json",
            "--currency",
            "EUR",
            "--class",
            str(payload.get("cabin_class", "economy")).upper(),
            "--stops",
            str(payload.get("max_stops", "any")).upper(),
        ]
        if payload.get("return_date"):
            cmd.extend(["--return", payload["return_date"]])
        out = self._run_cli(cmd)
        flights = out.get("flights") or out.get("results") or []
        return {"results": flights}

    def _cli_search_dates(self, payload: dict[str, Any]) -> dict[str, Any]:
        cmd = [
            sys.executable,
            "-m",
            "fli.cli.main",
            "dates",
            payload["origin"],
            payload["destination"],
            "--round",
            "--from",
            payload["start_date"],
            "--to",
            payload["end_date"],
            "--duration",
            str(payload["trip_duration"]),
            "--format",
            "json",
            "--currency",
            "EUR",
            "--class",
            str(payload.get("cabin_class", "economy")).upper(),
            "--stops",
            str(payload.get("max_stops", "any")).upper(),
        ]
        if payload.get("weekend_only"):
            cmd.extend(["--friday", "--saturday", "--sunday"])

        out = self._run_cli(cmd)
        date_prices = out.get("dates") or out.get("date_prices") or out.get("results") or []
        normalized = []
        for item in date_prices:
            if not isinstance(item, dict):
                continue
            dep = item.get("departure_date") or item.get("date")
            ret = item.get("return_date")
            if isinstance(dep, list) and dep:
                dep, ret = (dep + [None])[:2]
            normalized.append(
                {
                    "departure_date": dep,
                    "return_date": ret,
                    "total_price": item.get("price") or item.get("total_price"),
                    "currency": item.get("currency", "EUR"),
                    "trip_duration": payload["trip_duration"],
                }
            )
        return {"date_options": normalized}

    def _run_cli(self, cmd: list[str]) -> dict[str, Any]:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            msg = (result.stderr or result.stdout).strip().splitlines()[-1]
            raise ProviderError(f"fli command failed: {msg}")

        text = result.stdout.strip()
        start = text.find("{")
        if start == -1:
            raise ProviderError("fli command returned non-JSON output")

        try:
            return json.loads(text[start:])
        except json.JSONDecodeError as exc:
            raise ProviderError("fli command returned invalid JSON payload") from exc
