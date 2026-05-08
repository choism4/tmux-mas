#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "scenarios"
MOCK_SCENARIOS = [
    "mock-handshake",
    "mock-standup",
    "mock-incident-response",
    "mock-design-review",
    "mock-product-trio",
    "mock-security-review",
    "mock-writing-room",
    "mock-quiet-room",
]


def run(args: list[str], *, check: bool = True, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True, capture_output=True, timeout=timeout)


def scenario_session(name: str) -> str:
    with (FIXTURE_DIR / f"{name}.yml").open("r", encoding="utf-8") as f:
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


def check_scenario(name: str) -> None:
    session = scenario_session(name)
    kill_session(session)
    try:
        started = run(["./tmux-mas", "run", str(FIXTURE_DIR / f"{name}.yml")], timeout=20)
        if f"Started tmux session: {session}" not in started.stdout:
            raise AssertionError(f"{name}: start output missing session name\n{started.stdout}")

        time.sleep(6.0)
        status = run(["./tmux-mas", "status", session], timeout=10).stdout
        if session not in status:
            raise AssertionError(f"{name}: status output missing session\n{status}")

        watch = run(["./tmux-mas", "watch", session, "--once", "--lines", "40"], timeout=10).stdout
        if session not in watch:
            raise AssertionError(f"{name}: watch output missing session\n{watch}")

        capture = capture_session(session)
        if "MOCK_AGENT_READY" not in capture:
            raise AssertionError(f"{name}: mock agents did not start\n{capture}")
        if "MOCK_AGENT_SENT" not in capture:
            raise AssertionError(f"{name}: starter did not send\n{capture}")
        if "TMUX_MAS_AGENT_EXIT" not in capture:
            raise AssertionError(f"{name}: agent exit marker missing\n{capture}")
        if "exited" not in watch:
            raise AssertionError(f"{name}: watch did not report exited panes\n{watch}")
        print(f"ok {name}")
    finally:
        kill_session(session)


def main() -> int:
    for name in MOCK_SCENARIOS:
        check_scenario(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
