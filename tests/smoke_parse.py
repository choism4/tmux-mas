#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit("VERSION must not be empty")

    scenarios = sorted((ROOT / "scenarios").glob("*.yml")) + sorted((ROOT / "scenarios").glob("*.yaml"))
    if not scenarios:
        raise SystemExit("No scenarios found")
    if len(scenarios) < 10:
        raise SystemExit("Expected at least 10 bundled scenarios")

    for path in scenarios:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise SystemExit(f"{path}: scenario must be a mapping")
        for key in ("name", "session", "agents"):
            if key not in data:
                raise SystemExit(f"{path}: missing required key: {key}")
        if not data["agents"]:
            raise SystemExit(f"{path}: agents must not be empty")
        runner = data.get("runner")
        if isinstance(runner, dict):
            if "command" not in runner:
                raise SystemExit(f"{path}: runner.command is required when runner is a mapping")
            if "submit_key" not in runner:
                raise SystemExit(f"{path}: runner.submit_key should be explicit")

    print(f"Parsed {len(scenarios)} scenario(s)")


if __name__ == "__main__":
    main()
