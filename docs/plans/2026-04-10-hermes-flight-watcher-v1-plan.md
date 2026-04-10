# Hermes Flight Watcher v1 Implementation Plan

> For Hermes: Use subagent-driven-development skill to implement this plan task-by-task.

Goal: Build a local-first personal flight watcher for Boss that uses the `fli` Google Flights reverse-engineered backend, supports ad hoc search plus saved watchers, stores price history, and delivers Telegram-friendly summaries through Hermes.

Architecture: Keep the system boring and isolated. Put `fli` behind a small adapter layer, normalize all results into our own stable schema, store watcher configs and price history locally, and expose two entry modes: manual CLI/Hermes invocation and scheduled cron digests. Do not build a dashboard in v1.

Tech Stack: Python 3.11+, `fli`, SQLite, PyYAML, Typer, pytest, Hermes cron, local files.

---

## Scope and non-goals

In scope:
- one-way and round-trip search
- flexible date search for cheap windows
- saved watcher profiles
- local SQLite history
- scoring + Telegram-friendly summaries
- cron-safe runner for scheduled digests

Out of scope for v1:
- booking automation
- OTA / website ranking
- multi-user auth
- web dashboard
- direct MCP integration inside Hermes core

---

## Project layout

Create this repo-local structure:

```text
/home/jorge/flight-watcher/
  pyproject.toml
  README.md
  config/
    watchers.yaml
  data/
    .gitkeep
  docs/
    plans/
      2026-04-10-hermes-flight-watcher-v1-plan.md
  src/flight_watcher/
    __init__.py
    cli.py
    settings.py
    adapters/
      __init__.py
      fli_adapter.py
    domain/
      __init__.py
      models.py
      normalize.py
      scoring.py
      summary.py
    services/
      __init__.py
      search_service.py
      watcher_service.py
      report_service.py
      alert_service.py
    storage/
      __init__.py
      db.py
      history_repo.py
      watcher_repo.py
    runners/
      __init__.py
      cron_digest.py
  tests/
    test_normalize.py
    test_scoring.py
    test_summary.py
    test_watcher_repo.py
    test_search_service.py
```

---

## Domain model decisions

Use our own normalized schema. Never let the rest of the app depend directly on raw `fli` JSON.

Core models:
- `FlightQuery`
- `DateQuery`
- `FlightOption`
- `DateOption`
- `Watcher`
- `WatcherRun`
- `PriceSnapshot`
- `DigestItem`

Required fields for `FlightOption`:
- `provider: str`
- `searched_at: datetime`
- `origin: str`
- `destination: str`
- `departure_date: str`
- `return_date: str | None`
- `total_price: float`
- `currency: str`
- `total_duration_min: int`
- `stops: int`
- `airlines: list[str]`
- `legs: list[dict]`
- `score: float | None`
- `tags: list[str]`
- `fingerprint: str`

Required fields for `Watcher`:
- `id: str`
- `name: str`
- `enabled: bool`
- `origin: str`
- `destination: str`
- `search_mode: literal["specific","flexible"]`
- `departure_date: str | None`
- `return_date: str | None`
- `start_date: str | None`
- `end_date: str | None`
- `trip_duration: int | None`
- `weekend_only: bool`
- `cabin_class: str`
- `max_stops: str`
- `max_price: float | None`
- `sort_goal: str`
- `notify_if_below_price: float | None`
- `notify_on_drop_percent: float | None`
- `notes: str | None`

Fingerprint rule:
- hash route + dates + price + airline codes + first/last leg timestamps
- use this to dedupe snapshots and repeated alerts

---

## Task 1: Bootstrap the project skeleton

Objective: Create the local project structure and minimal packaging so the app can run as a standalone Python tool.

Files:
- Create: `/home/jorge/flight-watcher/pyproject.toml`
- Create: `/home/jorge/flight-watcher/README.md`
- Create: `/home/jorge/flight-watcher/config/watchers.yaml`
- Create: `/home/jorge/flight-watcher/data/.gitkeep`
- Create: `/home/jorge/flight-watcher/src/flight_watcher/__init__.py`
- Create: `/home/jorge/flight-watcher/src/flight_watcher/settings.py`
- Create: `/home/jorge/flight-watcher/src/flight_watcher/cli.py`

Step 1: Write failing smoke test

```python
from pathlib import Path


def test_project_scaffold_exists():
    root = Path("/home/jorge/flight-watcher")
    assert (root / "pyproject.toml").exists()
    assert (root / "src/flight_watcher/cli.py").exists()
```

Step 2: Run test to verify failure

Run: `pytest -q tests/test_smoke.py`
Expected: FAIL because files do not exist yet.

Step 3: Write minimal files

`pyproject.toml`
```toml
[project]
name = "flight-watcher"
version = "0.1.0"
description = "Local-first Hermes-integrated flight watcher"
requires-python = ">=3.11"
dependencies = [
  "flights",
  "pydantic>=2",
  "PyYAML>=6",
  "typer>=0.12",
]

[project.scripts]
flight-watcher = "flight_watcher.cli:app"
```

`config/watchers.yaml`
```yaml
watchers: []
```

`src/flight_watcher/cli.py`
```python
import typer
app = typer.Typer(help="Personal flight watcher for Hermes")

@app.command()
def health() -> None:
    print("ok")
```

Step 4: Run test to verify pass

Run: `pytest -q tests/test_smoke.py`
Expected: PASS

Step 5: Commit

```bash
git add .
git commit -m "chore: bootstrap flight watcher project"
```

---

## Task 2: Define normalized domain models

Objective: Create stable internal models so upstream `fli` schema changes do not leak through the app.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/domain/models.py`
- Test: `/home/jorge/flight-watcher/tests/test_normalize.py`

Step 1: Write failing test

```python
from flight_watcher.domain.models import FlightOption


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
```

Step 2: Run test to verify failure

Run: `pytest -q tests/test_normalize.py::test_flight_option_requires_price_and_route`
Expected: FAIL with import error

Step 3: Write minimal implementation

Use Pydantic models for `FlightQuery`, `DateQuery`, `FlightOption`, `DateOption`, and `Watcher`.

Step 4: Run test to verify pass

Run: `pytest -q tests/test_normalize.py::test_flight_option_requires_price_and_route`
Expected: PASS

Step 5: Commit

```bash
git add src/flight_watcher/domain/models.py tests/test_normalize.py
git commit -m "feat: add normalized domain models"
```

---

## Task 3: Implement `fli` adapter wrapper

Objective: Wrap `fli` search calls behind a small adapter that returns raw Python dictionaries and handles obvious upstream failures.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/adapters/fli_adapter.py`
- Test: `/home/jorge/flight-watcher/tests/test_search_service.py`

Step 1: Write failing unit test for adapter contract

```python
from flight_watcher.adapters.fli_adapter import FliAdapter


def test_adapter_exposes_search_methods():
    adapter = FliAdapter()
    assert hasattr(adapter, "search_flights")
    assert hasattr(adapter, "search_dates")
```

Step 2: Run test to verify failure

Run: `pytest -q tests/test_search_service.py::test_adapter_exposes_search_methods`
Expected: FAIL

Step 3: Implement adapter

Requirements:
- `search_flights(query: FlightQuery) -> dict`
- `search_dates(query: DateQuery) -> dict`
- catch network/upstream exceptions
- raise local `ProviderError` with compact useful message
- keep raw provider payload out of Telegram responses

Prefer Python API over shelling out to CLI. Only fall back to CLI if the library API proves materially worse.

Step 4: Run test to verify pass

Run: `pytest -q tests/test_search_service.py::test_adapter_exposes_search_methods`
Expected: PASS

Step 5: Commit

```bash
git add src/flight_watcher/adapters/fli_adapter.py tests/test_search_service.py
git commit -m "feat: add fli provider adapter"
```

---

## Task 4: Normalize raw provider results

Objective: Convert raw `fli` responses into our internal `FlightOption` and `DateOption` objects.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/domain/normalize.py`
- Modify: `/home/jorge/flight-watcher/tests/test_normalize.py`

Step 1: Write failing tests for normalization

Add tests for:
- one-way flight payload -> `FlightOption`
- flexible date payload -> `DateOption`
- missing currency falls back to `UNKNOWN`
- fingerprint is stable for identical input

Step 2: Run tests to verify failure

Run: `pytest -q tests/test_normalize.py`
Expected: FAIL

Step 3: Implement normalizers

Normalization rules:
- flatten airline codes from legs
- compute fingerprints deterministically
- attach tags like `nonstop`, `cheap`, `short`, `weekend_candidate`
- keep all timestamps as ISO strings or timezone-aware datetimes, consistently

Step 4: Run tests to verify pass

Run: `pytest -q tests/test_normalize.py`
Expected: PASS

Step 5: Commit

```bash
git add src/flight_watcher/domain/normalize.py tests/test_normalize.py
git commit -m "feat: normalize provider search results"
```

---

## Task 5: Add scoring and ranking logic

Objective: Rank options by usefulness instead of blindly trusting “cheapest”.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/domain/scoring.py`
- Test: `/home/jorge/flight-watcher/tests/test_scoring.py`

Step 1: Write failing tests

Test rules:
- lower price improves score
- fewer stops improves score
- shorter duration improves score
- price should matter most by default

Example expected behavior:
```python
def test_nonstop_can_beat_slightly_cheaper_one_stop():
    ...
```

Step 2: Run test to verify failure

Run: `pytest -q tests/test_scoring.py`
Expected: FAIL

Step 3: Implement scoring

Suggested default weights:
- price: 0.55
- duration: 0.25
- stops: 0.20

Also create helper selectors:
- `pick_cheapest()`
- `pick_best_value()`
- `pick_best_nonstop()`

Step 4: Run test to verify pass

Run: `pytest -q tests/test_scoring.py`
Expected: PASS

Step 5: Commit

```bash
git add src/flight_watcher/domain/scoring.py tests/test_scoring.py
git commit -m "feat: add ranking and scoring logic"
```

---

## Task 6: Create watcher config repository

Objective: Load, validate, and save watcher definitions from YAML.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/storage/watcher_repo.py`
- Modify: `/home/jorge/flight-watcher/config/watchers.yaml`
- Test: `/home/jorge/flight-watcher/tests/test_watcher_repo.py`

Step 1: Write failing tests

Cases:
- load empty watcher file
- load one valid watcher
- reject invalid cabin / stops values
- ignore disabled watchers in active listing

Step 2: Run test to verify failure

Run: `pytest -q tests/test_watcher_repo.py`
Expected: FAIL

Step 3: Implement repository

Provide methods:
- `load_all()`
- `list_enabled()`
- `get(watcher_id)`

Seed `watchers.yaml` with two example watchers commented or disabled by default.

Step 4: Run test to verify pass

Run: `pytest -q tests/test_watcher_repo.py`
Expected: PASS

Step 5: Commit

```bash
git add src/flight_watcher/storage/watcher_repo.py config/watchers.yaml tests/test_watcher_repo.py
git commit -m "feat: add watcher config repository"
```

---

## Task 7: Add SQLite history storage

Objective: Persist snapshots so we can detect price drops and avoid repetitive alerts.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/storage/db.py`
- Create: `/home/jorge/flight-watcher/src/flight_watcher/storage/history_repo.py`
- Modify: `/home/jorge/flight-watcher/src/flight_watcher/settings.py`

Step 1: Write failing tests

Cases:
- database initializes schema
- snapshot insert works
- duplicate fingerprint for same run is ignored or handled safely
- latest price lookup works

Step 2: Run test to verify failure

Run: `pytest -q tests/test_search_service.py -k history`
Expected: FAIL

Step 3: Implement storage

Create tables:
- `watcher_runs`
- `price_snapshots`
- `alerts_sent`

Minimum `price_snapshots` columns:
- `id`
- `watcher_id`
- `checked_at`
- `departure_date`
- `return_date`
- `price`
- `currency`
- `duration_min`
- `stops`
- `airline_summary`
- `fingerprint`

Step 4: Run test to verify pass

Run: `pytest -q tests/test_search_service.py -k history`
Expected: PASS

Step 5: Commit

```bash
git add src/flight_watcher/storage/db.py src/flight_watcher/storage/history_repo.py src/flight_watcher/settings.py tests/test_search_service.py
git commit -m "feat: add sqlite history storage"
```

---

## Task 8: Build search and watcher services

Objective: Orchestrate queries, normalization, scoring, and persistence in one sane service layer.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/services/search_service.py`
- Create: `/home/jorge/flight-watcher/src/flight_watcher/services/watcher_service.py`
- Modify: `/home/jorge/flight-watcher/tests/test_search_service.py`

Step 1: Write failing tests

Cases:
- manual search returns ranked normalized options
- flexible search returns ranked date options
- watcher run stores snapshots
- provider failure returns clean local error

Step 2: Run test to verify failure

Run: `pytest -q tests/test_search_service.py`
Expected: FAIL

Step 3: Implement services

Responsibilities:
- `SearchService`: adapter call + normalize + score
- `WatcherService`: load watcher + run query + save history + compare previous price

Step 4: Run test to verify pass

Run: `pytest -q tests/test_search_service.py`
Expected: PASS

Step 5: Commit

```bash
git add src/flight_watcher/services/search_service.py src/flight_watcher/services/watcher_service.py tests/test_search_service.py
git commit -m "feat: add search and watcher services"
```

---

## Task 9: Build summary/report generation

Objective: Produce Telegram-safe concise outputs that are actually useful.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/domain/summary.py`
- Create: `/home/jorge/flight-watcher/src/flight_watcher/services/report_service.py`
- Test: `/home/jorge/flight-watcher/tests/test_summary.py`

Step 1: Write failing tests

Cases:
- summary includes cheapest option
- summary includes best-value option if different
- summary mentions threshold hit when applicable
- summary stays under a sensible message length for Telegram digests

Step 2: Run test to verify failure

Run: `pytest -q tests/test_summary.py`
Expected: FAIL

Step 3: Implement summary generation

Output shape for a watcher digest:
- watcher name
- top 3 options
- cheapest found
- best value found
- notable change vs last seen
- plain-English recommendation

Step 4: Run test to verify pass

Run: `pytest -q tests/test_summary.py`
Expected: PASS

Step 5: Commit

```bash
git add src/flight_watcher/domain/summary.py src/flight_watcher/services/report_service.py tests/test_summary.py
git commit -m "feat: add telegram-friendly summaries"
```

---

## Task 10: Add CLI entry points

Objective: Provide a simple local interface before wiring into Hermes.

Files:
- Modify: `/home/jorge/flight-watcher/src/flight_watcher/cli.py`

Step 1: Write failing tests or manual CLI acceptance notes

Commands to support:
- `flight-watcher health`
- `flight-watcher search-flight ...`
- `flight-watcher search-dates ...`
- `flight-watcher run-watcher <id>`
- `flight-watcher run-all-watchers`

Step 2: Run command to verify failure

Run: `flight-watcher --help`
Expected: missing commands beyond `health`

Step 3: Implement commands

Requirements:
- JSON output option for machine use
- text output option for humans
- exit non-zero on provider failure

Step 4: Run command to verify pass

Run:
- `flight-watcher health`
- `flight-watcher search-flight --origin MUC --destination LIS --departure-date 2026-05-15`
- `flight-watcher search-dates --origin MUC --destination LIS --start-date 2026-05-01 --end-date 2026-06-15 --trip-duration 3`

Expected: usable output, no stack-trace nonsense

Step 5: Commit

```bash
git add src/flight_watcher/cli.py
git commit -m "feat: add local CLI commands"
```

---

## Task 11: Add cron-safe digest runner

Objective: Create a runner that Hermes cron can call without interactive context.

Files:
- Create: `/home/jorge/flight-watcher/src/flight_watcher/runners/cron_digest.py`
- Create: `/home/jorge/flight-watcher/src/flight_watcher/services/alert_service.py`

Step 1: Write failing test or acceptance criteria

Acceptance criteria:
- run all enabled watchers
- only emit alert items for threshold hits or material changes unless `--full-digest` is set
- return one compact digest string

Step 2: Run verification before implementation

Run: module import / dry run
Expected: missing module

Step 3: Implement runner

Rules:
- suppress duplicate alerts using `alerts_sent`
- material change = price below threshold or drop percent reached
- allow `--full-digest` for weekly summary mode

Step 4: Run verification after implementation

Run:
- `python -m flight_watcher.runners.cron_digest --full-digest`
- `python -m flight_watcher.runners.cron_digest`

Expected: compact digest text, even when nothing interesting happened

Step 5: Commit

```bash
git add src/flight_watcher/runners/cron_digest.py src/flight_watcher/services/alert_service.py
git commit -m "feat: add cron digest runner"
```

---

## Task 12: Document Hermes integration

Objective: Make manual use and scheduled use obvious.

Files:
- Modify: `/home/jorge/flight-watcher/README.md`
- Optionally create later: Hermes skill file outside the project after v1 works

Step 1: Write docs covering:
- install steps
- example watcher YAML
- example CLI usage
- how Hermes cron should call the tool
- known limitations of `fli`
- lab-risk disclaimer about reverse-engineered backend

Step 2: Verify docs are accurate

Run the documented commands exactly.
Expected: they work without “oh right except for this part” nonsense.

Step 3: Commit

```bash
git add README.md
git commit -m "docs: add usage and Hermes integration notes"
```

---

## Verification checklist

Before calling v1 complete, run:

```bash
cd /home/jorge/flight-watcher
python -m pytest -q
flight-watcher health
flight-watcher search-flight --origin MUC --destination LIS --departure-date 2026-05-15
flight-watcher search-dates --origin MUC --destination LIS --start-date 2026-05-01 --end-date 2026-06-15 --trip-duration 3
flight-watcher run-all-watchers
python -m flight_watcher.runners.cron_digest --full-digest
```

Expected outcomes:
- tests pass
- manual search works
- flexible search works
- watcher config loads
- DB is created automatically
- digest output is readable and compact

---

## Hermes integration after code is stable

Do this after the project works locally:

1. Create a Hermes skill named something like `flight-watcher`
2. The skill should:
   - translate Boss requests into CLI arguments
   - call the local tool
   - return concise summaries
3. Add one or two cron jobs:
   - Friday morning full digest
   - optional daily alerts-only digest

Suggested cron command path:
- use the project venv Python or a dedicated venv
- avoid relying on random shell state

---

## Known risks and guardrails

Risks:
- `fli` is reverse engineered and can break
- upstream may rate limit or return schema shifts
- booking-site intelligence is weak in current data

Guardrails:
- adapter layer isolates provider changes
- normalization stabilizes internal contracts
- history + dedupe prevents spam
- no dashboard in v1
- no booking automation in v1

---

## Recommended implementation order

1. bootstrap
2. models
3. adapter
4. normalization
5. scoring
6. watcher YAML repo
7. SQLite history
8. services
9. summaries
10. CLI
11. cron runner
12. docs

This order keeps the ugly parts boxed in early and gets you to something usable before you waste time polishing furniture.

---

Plan complete. Ready to execute using subagent-driven-development task-by-task.