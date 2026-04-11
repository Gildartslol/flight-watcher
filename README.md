# Flight Watcher (v1)

Local-first personal flight watcher. It wraps the `flights` (`fli`) backend behind a local adapter, normalizes results to a stable schema, stores snapshots in SQLite, and emits compact Telegram-friendly digests.

## What v1 does

- One-way + round-trip search
- Flexible date-window scans
- YAML saved watchers
- SQLite price history + alert dedupe
- Scoring + ranking (cheapest, best value, best nonstop)
- CLI + cron-safe digest runner

No dashboard. No booking automation. No cloud dependency.

## Install

```bash
cd /home/jorge/flight-watcher
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Watcher config

Edit `config/watchers.yaml`:

```yaml
watchers:
  - id: muc-lis-weekend
    name: "Munich → Lisbon weekend scout"
    enabled: true
    origin: MUC
    destination: LIS
    search_mode: flexible
    start_date: "2026-05-01"
    end_date: "2026-08-31"
    trip_duration: 3
    weekend_only: true
    cabin_class: economy
    max_stops: any
    max_price: 220
    sort_goal: best_value
    notify_if_below_price: 160
    notify_on_drop_percent: 12
```

## CLI usage

```bash
flight-watcher health
flight-watcher search-flight --origin MUC --destination LIS --departure-date 2026-05-15
flight-watcher search-dates --origin MUC --destination LIS --start-date 2026-05-01 --end-date 2026-06-15 --trip-duration 3
flight-watcher run-watcher muc-lis-weekend
flight-watcher run-all-watchers
```

JSON mode:

```bash
flight-watcher search-flight --origin MUC --destination LIS --departure-date 2026-05-15 --json-output
```

## Cron runner

Digest (alerts-only by default):

```bash
python -m flight_watcher.runners.cron_digest
```

Full digest:

```bash
python -m flight_watcher.runners.cron_digest --full-digest
```

Example cron (Europe/Berlin machine local time):

```cron
30 8 * * 5 cd /home/jorge/flight-watcher && /home/jorge/flight-watcher/.venv/bin/python -m flight_watcher.runners.cron_digest --full-digest
```

## Hermes integration pattern

Hermes skill should map natural language -> CLI args, call local command, and return digest text. Keep it local and deterministic.

## Known limitations / risks

- `flights`/`fli` is reverse-engineered and may break if upstream changes.
- Provider payload shape is not guaranteed stable.
- Rate limiting / temporary blocks can happen.
- Booking-site quality intelligence is intentionally out of scope in v1.

Lab-risk note: this is fine for personal monitoring, but do not treat this backend as production-grade guaranteed infrastructure.
