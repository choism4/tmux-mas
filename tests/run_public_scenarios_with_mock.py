#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def run(
    args: list[str],
    *,
    check: bool = True,
    timeout: int = 40,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(args, cwd=ROOT, check=check, text=True, capture_output=True, timeout=timeout, env=full_env)


def scenario_files() -> list[Path]:
    return sorted((ROOT / "scenarios").glob("*.yml")) + sorted((ROOT / "scenarios").glob("*.yaml"))


def scenario_session(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return str(data["session"])


def kill_session(session: str) -> None:
    run(["tmux", "kill-session", "-t", session], check=False, timeout=5)


def capture_session(session: str) -> str:
    panes = run(["tmux", "list-panes", "-t", session, "-F", "#{pane_id}"], timeout=10).stdout.splitlines()
    captures: list[str] = []
    for pane in panes:
        captures.append(run(["tmux", "capture-pane", "-t", pane, "-p", "-S", "-120"], timeout=10).stdout)
    return "\n".join(captures)


def check_scenario(path: Path) -> None:
    session = scenario_session(path)
    kill_session(session)
    env = {
        "TMUX_MAS_RUNNER_COMMAND": 'python3 "$TMUX_MAS_ROOT/examples/mock_agent.py"',
        "TMUX_MAS_CWD": str(ROOT),
    }
    try:
        started = run(["./tmux-mas", "run", str(path)], timeout=25, env=env)
        if f"Started tmux session: {session}" not in started.stdout:
            raise AssertionError(f"{path.name}: start output missing session name\n{started.stdout}")

        time.sleep(6.0)
        status = run(["./tmux-mas", "status", session], timeout=10).stdout
        if session not in status:
            raise AssertionError(f"{path.name}: status output missing session\n{status}")

        watch = run(["./tmux-mas", "watch", session, "--once", "--lines", "80"], timeout=10).stdout
        if "exited" not in watch:
            raise AssertionError(f"{path.name}: watch did not report exited agents\n{watch}")

        capture = capture_session(session)
        if "MOCK_AGENT_READY" not in capture:
            raise AssertionError(f"{path.name}: mock runner did not start\n{capture}")
        if "MOCK_AGENT_SENT" not in capture:
            raise AssertionError(f"{path.name}: scenario starter did not send\n{capture}")
        if "TMUX_MAS_AGENT_EXIT" not in capture:
            raise AssertionError(f"{path.name}: agent exit marker missing\n{capture}")
        print(f"ok {path.name}")
    finally:
        kill_session(session)


def main() -> int:
    files = scenario_files()
    if len(files) < 10:
        raise SystemExit(f"Expected at least 10 public scenarios, found {len(files)}")
    for path in files:
        check_scenario(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
