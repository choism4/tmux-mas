#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def check_command(name: str) -> bool:
    path = shutil.which(name)
    if path:
        print(f"ok command {name}: {path}")
        return True
    print(f"missing command {name}")
    return False


def main() -> None:
    ok = True
    ok = check_command("tmux") and ok
    ok = check_command("python3") and ok

    try:
        import yaml  # noqa: F401

        print("ok python package PyYAML")
    except Exception:
        print("missing python package PyYAML")
        ok = False

    if len(sys.argv) > 2:
        raise SystemExit("Usage: doctor.py [scenario.yml]")

    if len(sys.argv) == 2:
        from run_scenario import load_scenario, resolve_runner

        scenario_path = Path(sys.argv[1]).resolve()
        try:
            scenario = load_scenario(scenario_path)
            print(f"ok scenario: {scenario_path}")
            print(f"ok scenario name: {scenario.get('name', '<unnamed>')}")
            runner = resolve_runner(scenario)
            print(f"ok runner type: {runner['type']}")
            print(f"ok runner command: {runner['command']}")
            print(f"ok submit key: {runner['submit_key']}")
        except SystemExit as exc:
            print(str(exc))
            ok = False

    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
