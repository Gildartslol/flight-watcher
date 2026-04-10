from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from flight_watcher.domain.models import DateOption, DateQuery, FlightOption, FlightQuery


def normalize_flight_results(
    raw: dict[str, Any],
    query: FlightQuery,
    *,
    provider: str = "fli",
    searched_at: datetime | None = None,
) -> list[FlightOption]:
    searched_at = searched_at or datetime.now(UTC)
    options: list[FlightOption] = []
    for item in _iter_items(raw):
        price, currency = _extract_price_and_currency(item)
        duration = int(item.get("total_duration_min") or item.get("duration_min") or item.get("duration") or 0)
        legs = _extract_legs(item)
        stops = int(item.get("stops") if item.get("stops") is not None else max(len(legs) - 1, 0))
        airlines = _extract_airlines(item, legs)

        dep_date = str(item.get("departure_date") or query.departure_date)
        ret_date = item.get("return_date") if item.get("return_date") is not None else query.return_date

        fingerprint = build_fingerprint(
            origin=query.origin,
            destination=query.destination,
            departure_date=dep_date,
            return_date=ret_date,
            total_price=price,
            airlines=airlines,
            legs=legs,
        )

        options.append(
            FlightOption(
                provider=provider,
                searched_at=searched_at,
                origin=query.origin,
                destination=query.destination,
                departure_date=dep_date,
                return_date=ret_date,
                total_price=price,
                currency=currency,
                total_duration_min=duration,
                stops=stops,
                airlines=airlines,
                legs=legs,
                tags=[],
                fingerprint=fingerprint,
            )
        )

    _tag_flight_options(options)
    return options


def normalize_date_results(
    raw: dict[str, Any],
    query: DateQuery,
    *,
    provider: str = "fli",
    searched_at: datetime | None = None,
) -> list[DateOption]:
    searched_at = searched_at or datetime.now(UTC)
    options: list[DateOption] = []
    for item in _iter_items(raw):
        price, currency = _extract_price_and_currency(item)
        dep_date = str(item.get("departure_date") or item.get("date") or "")
        ret_date = item.get("return_date")
        if ret_date is None and dep_date:
            try:
                dep_dt = datetime.fromisoformat(dep_date)
                ret_date = dep_dt.replace(day=dep_dt.day).date().isoformat()
            except Exception:
                ret_date = None

        trip_duration = int(item.get("trip_duration") or query.trip_duration)
        fingerprint = build_fingerprint(
            origin=query.origin,
            destination=query.destination,
            departure_date=dep_date,
            return_date=ret_date,
            total_price=price,
            airlines=item.get("airlines") or [],
            legs=item.get("legs") or [],
        )
        tags: list[str] = []
        if query.weekend_only:
            tags.append("weekend_candidate")
        options.append(
            DateOption(
                provider=provider,
                searched_at=searched_at,
                origin=query.origin,
                destination=query.destination,
                departure_date=dep_date,
                return_date=ret_date,
                trip_duration=trip_duration,
                total_price=price,
                currency=currency,
                tags=tags,
                fingerprint=fingerprint,
            )
        )

    return sorted(options, key=lambda o: o.total_price)


def build_fingerprint(
    *,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None,
    total_price: float,
    airlines: list[str],
    legs: list[dict[str, Any]],
) -> str:
    first_dep = legs[0].get("departure") if legs else ""
    last_arr = legs[-1].get("arrival") if legs else ""
    basis = {
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "total_price": round(float(total_price), 2),
        "airlines": sorted(airlines),
        "first_departure": first_dep,
        "last_arrival": last_arr,
    }
    payload = json.dumps(basis, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _iter_items(raw: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("results", "flights", "itineraries", "data", "date_options"):
        value = raw.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    if isinstance(raw.get("result"), list):
        return [x for x in raw["result"] if isinstance(x, dict)]
    return []


def _extract_price_and_currency(item: dict[str, Any]) -> tuple[float, str]:
    price_obj = item.get("price")
    if isinstance(price_obj, dict):
        value = float(price_obj.get("amount") or price_obj.get("value") or 0)
        currency = str(price_obj.get("currency") or item.get("currency") or "UNKNOWN")
        return value, currency
    if isinstance(price_obj, (int, float)):
        return float(price_obj), str(item.get("currency") or "UNKNOWN")
    if isinstance(item.get("total_price"), (int, float)):
        return float(item["total_price"]), str(item.get("currency") or "UNKNOWN")
    return 0.0, str(item.get("currency") or "UNKNOWN")


def _extract_legs(item: dict[str, Any]) -> list[dict[str, Any]]:
    legs = item.get("legs")
    if isinstance(legs, list):
        return [leg for leg in legs if isinstance(leg, dict)]
    segments = item.get("segments")
    if isinstance(segments, list):
        return [seg for seg in segments if isinstance(seg, dict)]
    return []


def _extract_airlines(item: dict[str, Any], legs: list[dict[str, Any]]) -> list[str]:
    airlines = item.get("airlines")
    if isinstance(airlines, list) and airlines:
        return [str(a) for a in airlines]

    found: list[str] = []
    for leg in legs:
        code = leg.get("airline") or leg.get("airline_code") or leg.get("carrier")
        if code:
            found.append(str(code))
    # keep order but dedupe
    return list(dict.fromkeys(found))


def _tag_flight_options(options: list[FlightOption]) -> None:
    if not options:
        return
    min_price = min(o.total_price for o in options)
    min_duration = min(o.total_duration_min for o in options) if options else 0
    for option in options:
        tags: list[str] = []
        if option.stops == 0:
            tags.append("nonstop")
        if option.total_price <= (min_price * 1.05):
            tags.append("cheap")
        if min_duration and option.total_duration_min <= (min_duration * 1.1):
            tags.append("short")
        try:
            dep_weekday = datetime.fromisoformat(option.departure_date).weekday()
            if dep_weekday in (4, 5):
                tags.append("weekend_candidate")
        except Exception:
            pass
        option.tags = tags
