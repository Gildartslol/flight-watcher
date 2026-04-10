from flight_watcher.domain.models import FlightOption
from flight_watcher.domain.scoring import pick_best_nonstop, pick_best_value, pick_cheapest, score_flight_options


def _opt(price: float, duration: int, stops: int, fingerprint: str) -> FlightOption:
    return FlightOption(
        provider="fli",
        origin="MUC",
        destination="LIS",
        departure_date="2026-05-15",
        return_date=None,
        total_price=price,
        currency="EUR",
        total_duration_min=duration,
        stops=stops,
        airlines=["XX"],
        legs=[],
        tags=[],
        fingerprint=fingerprint,
    )


def test_lower_price_improves_score():
    a = _opt(100, 200, 0, "a")
    b = _opt(140, 200, 0, "b")
    scored = score_flight_options([a, b])
    assert scored[0].fingerprint == "a"


def test_fewer_stops_improves_score():
    a = _opt(120, 240, 0, "a")
    b = _opt(120, 240, 1, "b")
    scored = score_flight_options([a, b])
    assert scored[0].fingerprint == "a"


def test_shorter_duration_improves_score():
    a = _opt(120, 180, 1, "a")
    b = _opt(120, 260, 1, "b")
    scored = score_flight_options([a, b])
    assert scored[0].fingerprint == "a"


def test_nonstop_can_beat_slightly_cheaper_one_stop():
    nonstop = _opt(125, 190, 0, "n")
    one_stop = _opt(120, 220, 1, "s")
    assert pick_best_value([nonstop, one_stop]).fingerprint == "n"


def test_selectors():
    a = _opt(99, 220, 1, "a")
    b = _opt(120, 190, 0, "b")
    assert pick_cheapest([a, b]).fingerprint == "a"
    assert pick_best_nonstop([a, b]).fingerprint == "b"
