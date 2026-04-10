from datetime import UTC, datetime

from flight_watcher.domain.models import DateQuery, FlightOption, FlightQuery
from flight_watcher.domain.normalize import build_fingerprint, normalize_date_results, normalize_flight_results


def test_flight_option_requires_price_and_route():
    option = FlightOption(
        provider="fli",
        origin="MUC",
        destination="LIS",
        departure_date="2026-05-15",
        return_date=None,
        total_price=147.0,
        currency="EUR",
        total_duration_min=765,
        stops=1,
        airlines=["KL"],
        legs=[],
        tags=[],
        fingerprint="abc",
    )
    assert option.total_price == 147.0


def test_normalize_one_way_payload_to_flight_option():
    raw = {
        "results": [
            {
                "price": {"amount": 120, "currency": "EUR"},
                "duration_min": 180,
                "stops": 0,
                "legs": [{"airline": "LH", "departure": "2026-05-15T08:00:00+00:00", "arrival": "2026-05-15T11:00:00+00:00"}],
            }
        ]
    }
    query = FlightQuery(origin="MUC", destination="LIS", departure_date="2026-05-15")
    out = normalize_flight_results(raw, query, searched_at=datetime.now(UTC))
    assert len(out) == 1
    assert out[0].origin == "MUC"
    assert out[0].airlines == ["LH"]
    assert "nonstop" in out[0].tags


def test_normalize_flexible_payload_to_date_option():
    raw = {"date_options": [{"date": "2026-06-07", "total_price": 99, "currency": "EUR", "trip_duration": 3}]}
    query = DateQuery(origin="MUC", destination="LIS", start_date="2026-06-01", end_date="2026-06-30", trip_duration=3)
    out = normalize_date_results(raw, query)
    assert len(out) == 1
    assert out[0].departure_date == "2026-06-07"
    assert out[0].return_date is None
    assert out[0].total_price == 99


def test_flexible_normalize_does_not_invent_return_date_when_missing():
    raw = {
        "date_options": [
            {
                "departure_date": "2026-06-14",
                "total_price": 129,
                "currency": "EUR",
                "trip_duration": 4,
            }
        ]
    }
    query = DateQuery(origin="MUC", destination="LIS", start_date="2026-06-01", end_date="2026-06-30", trip_duration=4)
    out = normalize_date_results(raw, query)
    assert len(out) == 1
    assert out[0].departure_date == "2026-06-14"
    assert out[0].return_date is None


def test_missing_currency_falls_back_to_unknown():
    raw = {"results": [{"total_price": 111, "duration_min": 200, "stops": 1, "legs": []}]}
    query = FlightQuery(origin="MUC", destination="LIS", departure_date="2026-05-15")
    out = normalize_flight_results(raw, query)
    assert out[0].currency == "UNKNOWN"


def test_fingerprint_is_stable_for_identical_input():
    args = {
        "origin": "MUC",
        "destination": "LIS",
        "departure_date": "2026-05-15",
        "return_date": None,
        "total_price": 147,
        "airlines": ["KL"],
        "legs": [{"departure": "2026-05-15T08:00:00+00:00", "arrival": "2026-05-15T12:00:00+00:00"}],
    }
    assert build_fingerprint(**args) == build_fingerprint(**args)
