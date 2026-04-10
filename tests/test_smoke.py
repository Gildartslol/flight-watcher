from pathlib import Path


def test_project_scaffold_exists():
    root = Path("/home/jorge/flight-watcher")
    assert (root / "pyproject.toml").exists()
    assert (root / "src/flight_watcher/cli.py").exists()
