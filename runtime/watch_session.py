#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone


PANE_FORMAT = "\t".join(
    [
        "#{session_name}:#{window_name}.#{pane_index}",
        "#{pane_id}",
        "#{@agent_name}",
        "#{pane_current_command}",
        "#{pane_dead}",
    ],
)


@dataclass
class PaneSnapshot:
    target: str
    pane_id: str
    agent: str
    command: str
    dead: bool
    digest: str
    tail: str


@dataclass
class PaneState:
    digest: str
    changed_at: float


def run_tmux(args: list[str]) -> str:
    completed = subprocess.run(
        ["tmux", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout


def list_panes(session: str) -> list[tuple[str, str, str, str, bool]]:
    output = run_tmux(["list-panes", "-a", "-F", PANE_FORMAT])
    panes: list[tuple[str, str, str, str, bool]] = []
    for line in output.splitlines():
        target, pane_id, agent, command, dead = line.split("\t", 4)
        if not target.startswith(f"{session}:"):
            continue
        panes.append((target, pane_id, agent or "-", command or "-", dead == "1"))
    return panes


def capture_tail(pane_id: str, lines: int) -> str:
    start = f"-{max(lines, 1)}"
    return run_tmux(["capture-pane", "-t", pane_id, "-p", "-S", start])


def snapshot_panes(session: str, lines: int) -> list[PaneSnapshot]:
    snapshots: list[PaneSnapshot] = []
    for target, pane_id, agent, command, dead in list_panes(session):
        tail = "" if dead else capture_tail(pane_id, lines)
        digest = hashlib.sha256(tail.encode("utf-8", errors="replace")).hexdigest()
        snapshots.append(
            PaneSnapshot(
                target=target,
                pane_id=pane_id,
                agent=agent,
                command=command,
                dead=dead,
                digest=digest,
                tail=last_non_empty_line(tail),
            ),
        )
    return snapshots


def last_non_empty_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def print_snapshot(
    snapshots: list[PaneSnapshot],
    states: dict[str, PaneState],
    now: float,
    idle_seconds: float,
) -> None:
    print(f"== {datetime.now(timezone.utc).isoformat(timespec='seconds')} ==")
    for snapshot in snapshots:
        state = states.get(snapshot.pane_id)
        if snapshot.dead:
            status = "dead"
        elif state is None:
            status = "new"
        elif state.digest != snapshot.digest:
            status = "changed"
        elif now - state.changed_at >= idle_seconds:
            status = f"idle>{int(idle_seconds)}s"
        else:
            status = "quiet"

        tail = snapshot.tail.replace("\t", " ")
        if len(tail) > 140:
            tail = f"{tail[:137]}..."
        print(
            f"{status:>10} {snapshot.target:<28} {snapshot.pane_id:<6} "
            f"{snapshot.agent:<16} {snapshot.command:<12} {tail}"
        )
    print("", flush=True)


def update_states(
    snapshots: list[PaneSnapshot],
    states: dict[str, PaneState],
    now: float,
) -> None:
    live_ids = {snapshot.pane_id for snapshot in snapshots}
    for pane_id in list(states):
        if pane_id not in live_ids:
            del states[pane_id]

    for snapshot in snapshots:
        state = states.get(snapshot.pane_id)
        if state is None or state.digest != snapshot.digest:
            states[snapshot.pane_id] = PaneState(snapshot.digest, now)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch a tmux-mas session for pane output changes, idle panes, and dead panes.",
    )
    parser.add_argument("session", help="tmux session to watch")
    parser.add_argument("--interval", type=float, default=5.0, help="poll interval in seconds")
    parser.add_argument("--idle-seconds", type=float, default=120.0, help="mark panes idle after this many unchanged seconds")
    parser.add_argument("--lines", type=int, default=80, help="capture this many recent lines per pane")
    parser.add_argument("--once", action="store_true", help="print one snapshot and exit")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    states: dict[str, PaneState] = {}

    while True:
        now = time.monotonic()
        try:
            snapshots = snapshot_panes(args.session, args.lines)
        except subprocess.CalledProcessError as error:
            sys.stderr.write(error.stderr or str(error))
            return 1

        print_snapshot(snapshots, states, now, args.idle_seconds)
        update_states(snapshots, states, now)

        if args.once:
            return 0
        try:
            time.sleep(max(args.interval, 0.5))
        except KeyboardInterrupt:
            return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
