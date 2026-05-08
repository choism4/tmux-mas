#!/usr/bin/env python3
from __future__ import annotations

import re
import select
import subprocess
import sys
import time


def parse_agent_id(prompt: str) -> str:
    match = re.search(r"^You are ([A-Za-z0-9_-]+) in the tmux-mas scenario", prompt, re.MULTILINE)
    if not match:
        raise SystemExit("mock_agent: could not parse agent id")
    return match.group(1)


def parse_participants(prompt: str) -> dict[str, str]:
    participants: dict[str, str] = {}
    for match in re.finditer(r"^([A-Za-z0-9_-]+)=(%\d+)$", prompt, re.MULTILINE):
        participants[match.group(1)] = match.group(2)
    if not participants:
        raise SystemExit("mock_agent: could not parse participants")
    return participants


def parse_starter(prompt: str) -> str | None:
    match = re.search(r"^- Starter: ([A-Za-z0-9_-]+)$", prompt, re.MULTILINE)
    return match.group(1) if match else None


def send(pane: str, message: str) -> None:
    subprocess.run(["agent_send", pane, message], check=True)


def first_other(agent_id: str, participants: dict[str, str]) -> tuple[str, str] | None:
    for name, pane in participants.items():
        if name != agent_id:
            return name, pane
    return None


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: mock_agent.py <rendered-prompt>")

    prompt = sys.argv[1]
    agent_id = parse_agent_id(prompt)
    participants = parse_participants(prompt)
    starter = parse_starter(prompt)
    replied = False

    print(f"MOCK_AGENT_READY {agent_id}", flush=True)

    if starter == agent_id:
        target = first_other(agent_id, participants)
        if target:
            target_name, target_pane = target
            time.sleep(1.0)
            send(target_pane, f"{agent_id}: hello {target_name}, mock message from {agent_id}")
            print(f"MOCK_AGENT_SENT {agent_id} {target_name}", flush=True)

    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        readable, _, _ = select.select([sys.stdin], [], [], 0.5)
        if not readable:
            continue

        line = sys.stdin.readline()
        if not line:
            continue
        line = line.strip()
        print(f"MOCK_AGENT_RECEIVED {agent_id} {line}", flush=True)

        if replied or ":" not in line:
            continue

        sender, _ = line.split(":", 1)
        sender = sender.strip()
        if sender == agent_id or sender not in participants:
            continue

        send(participants[sender], f"{agent_id}: ack from {agent_id}")
        print(f"MOCK_AGENT_REPLIED {agent_id} {sender}", flush=True)
        replied = True

    print(f"MOCK_AGENT_DONE {agent_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
