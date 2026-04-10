from __future__ import annotations

from typing import Iterable

from flight_watcher.domain.models import FlightOption

DEFAULT_WEIGHTS = {
    "price": 0.55,
    "duration": 0.25,
    "stops": 0.20,
}


def score_flight_options(options: list[FlightOption]) -> list[FlightOption]:
    if not options:
        return options

    prices = [o.total_price for o in options]
    durations = [o.total_duration_min for o in options]
    stops = [o.stops for o in options]

    pmin, pmax = min(prices), max(prices)
    dmin, dmax = min(durations), max(durations)
    smin, smax = min(stops), max(stops)

    for option in options:
        p = _benefit(option.total_price, pmin, pmax)
        d = _benefit(option.total_duration_min, dmin, dmax)
        s = _benefit(option.stops, smin, smax)
        nonstop_bonus = 0.12 if option.stops == 0 else 0.0
        option.score = round(
            (p * DEFAULT_WEIGHTS["price"] + d * DEFAULT_WEIGHTS["duration"] + s * DEFAULT_WEIGHTS["stops"] + nonstop_bonus) * 100,
            2,
        )

    return sorted(options, key=lambda o: (o.score or 0), reverse=True)


def pick_cheapest(options: Iterable[FlightOption]) -> FlightOption | None:
    options = list(options)
    return min(options, key=lambda o: o.total_price) if options else None


def pick_best_value(options: Iterable[FlightOption]) -> FlightOption | None:
    options = list(options)
    if not options:
        return None
    scored = score_flight_options(options)
    return scored[0] if scored else None


def pick_best_nonstop(options: Iterable[FlightOption]) -> FlightOption | None:
    nonstop = [o for o in options if o.stops == 0]
    if not nonstop:
        return None
    return pick_best_value(nonstop)


def _benefit(value: float, lower: float, upper: float) -> float:
    if upper == lower:
        return 1.0
    ratio = (value - lower) / (upper - lower)
    return max(0.0, min(1.0, 1 - ratio))
