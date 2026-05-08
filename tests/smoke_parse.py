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

    artifact_scenarios = 0
    sessions: set[str] = set()
    names: set[str] = set()

    for path in scenarios:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise SystemExit(f"{path}: scenario must be a mapping")
        for key in ("name", "session", "agents"):
            if key not in data:
                raise SystemExit(f"{path}: missing required key: {key}")
        if data["name"] in names:
            raise SystemExit(f"{path}: duplicate scenario name: {data['name']}")
        if data["session"] in sessions:
            raise SystemExit(f"{path}: duplicate tmux session: {data['session']}")
        names.add(data["name"])
        sessions.add(data["session"])
        if not data["agents"]:
            raise SystemExit(f"{path}: agents must not be empty")
        runner = data.get("runner")
        if isinstance(runner, dict):
            if "command" not in runner:
                raise SystemExit(f"{path}: runner.command is required when runner is a mapping")
            if "submit_key" not in runner:
                raise SystemExit(f"{path}: runner.submit_key should be explicit")
        resources = data.get("resources") or []
        if any((resource or {}).get("type") in {"workspace", "static-site"} for resource in resources):
            artifact_scenarios += 1

    if artifact_scenarios < 10:
        raise SystemExit(f"Expected at least 10 artifact-oriented public scenarios, found {artifact_scenarios}")

    print(f"Parsed {len(scenarios)} scenario(s), {artifact_scenarios} artifact-oriented")


if __name__ == "__main__":
    main()
