import pytest

from flight_watcher.storage.watcher_repo import WatcherRepository


def test_load_empty_watcher_file(tmp_path):
    path = tmp_path / "watchers.yaml"
    path.write_text("watchers: []\n")
    repo = WatcherRepository(path)
    assert repo.load_all() == []


def test_load_one_valid_watcher(tmp_path):
    path = tmp_path / "watchers.yaml"
    path.write_text(
        """
watchers:
  - id: w1
    name: test
    enabled: true
    origin: MUC
    destination: LIS
    search_mode: specific
    departure_date: "2026-05-01"
    return_date: null
    weekend_only: false
    cabin_class: economy
    max_stops: any
    max_price: null
    sort_goal: best_value
    notify_if_below_price: null
    notify_on_drop_percent: null
    notes: null
""".strip()
    )
    repo = WatcherRepository(path)
    all_watchers = repo.load_all()
    assert len(all_watchers) == 1
    assert all_watchers[0].id == "w1"


def test_reject_invalid_cabin_or_stops(tmp_path):
    path = tmp_path / "watchers.yaml"
    path.write_text(
        """
watchers:
  - id: bad
    name: bad
    enabled: true
    origin: MUC
    destination: LIS
    search_mode: specific
    departure_date: "2026-05-01"
    return_date: null
    weekend_only: false
    cabin_class: spaceship
    max_stops: ten
    max_price: null
    sort_goal: best_value
    notify_if_below_price: null
    notify_on_drop_percent: null
    notes: null
""".strip()
    )
    repo = WatcherRepository(path)
    with pytest.raises(Exception):
        repo.load_all()


def test_ignore_disabled_watchers(tmp_path):
    path = tmp_path / "watchers.yaml"
    path.write_text(
        """
watchers:
  - id: off
    name: off
    enabled: false
    origin: MUC
    destination: LIS
    search_mode: specific
    departure_date: "2026-05-01"
    return_date: null
    weekend_only: false
    cabin_class: economy
    max_stops: any
    max_price: null
    sort_goal: best_value
    notify_if_below_price: null
    notify_on_drop_percent: null
    notes: null
  - id: on
    name: on
    enabled: true
    origin: MUC
    destination: LIS
    search_mode: specific
    departure_date: "2026-05-01"
    return_date: null
    weekend_only: false
    cabin_class: economy
    max_stops: any
    max_price: null
    sort_goal: best_value
    notify_if_below_price: null
    notify_on_drop_percent: null
    notes: null
""".strip()
    )
    repo = WatcherRepository(path)
    enabled = repo.list_enabled()
    assert len(enabled) == 1
    assert enabled[0].id == "on"
