from pathlib import Path


def test_project_scaffold_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "pyproject.toml").exists()
    assert (root / "src/flight_watcher/cli.py").exists()
