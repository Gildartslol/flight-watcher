from flight_watcher.domain.models import FlightOption, Watcher
from flight_watcher.domain.summary import build_watcher_summary


def _watcher() -> Watcher:
    return Watcher(
        id="w1",
        name="MUC-LIS",
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
        max_price=130,
        sort_goal="best_value",
        notify_if_below_price=120,
        notify_on_drop_percent=10,
        notes=None,
    )


def _option(price: float, duration: int, stops: int, fp: str) -> FlightOption:
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
        airlines=["LH"],
        legs=[],
        tags=[],
        fingerprint=fp,
    )


def test_summary_includes_cheapest_option():
    txt = build_watcher_summary(_watcher(), [_option(120, 200, 0, "a"), _option(140, 180, 0, "b")])
    assert "Cheapest:" in txt


def test_summary_includes_best_value_if_different():
    txt = build_watcher_summary(_watcher(), [_option(115, 500, 2, "a"), _option(130, 180, 0, "b")])
    assert "Best value:" in txt


def test_summary_mentions_threshold_hit_when_applicable():
    txt = build_watcher_summary(_watcher(), [_option(110, 200, 0, "a")], threshold_hit=True)
    assert "threshold" in txt.lower()


def test_summary_stays_under_reasonable_length():
    options = [_option(100 + i, 200 + i * 5, i % 2, f"f{i}") for i in range(20)]
    txt = build_watcher_summary(_watcher(), options, max_chars=700)
    assert len(txt) <= 700
