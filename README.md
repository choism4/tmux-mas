<p align="center">
  <img src="assets/tmux-mas-hero.png" alt="tmux-mas hero" width="860">
</p>

<h1 align="center">tmux-mas</h1>

<p align="center">
  <strong>tmux Multi Agents System</strong>
  <br>
  Spin up agent CLI teams as tmux panes. Let them talk with injected tools.
</p>

<p align="center">
  <a href="https://github.com/choism4/tmux-mas/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/choism4/tmux-mas/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-0ea5e9"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-0.1.4-f43f5e">
  <img alt="Requires tmux" src="https://img.shields.io/badge/requires-tmux-22c55e">
  <img alt="cmux not required" src="https://img.shields.io/badge/cmux-not_required-64748b">
</p>

---

`tmux-mas` means **tmux Multi Agents System**.

`tmux-mas` starts a tmux session from a YAML scenario. Each agent gets its own
pane, prompt, role, and run-local tools such as `agent_send` and
`agent_broadcast`. The launcher starts the team; it does not sit in the middle
of the conversation.

## Why

Most multi-agent demos hide the actual coordination surface. `tmux-mas` makes it
boringly visible:

| What you get | Why it matters |
| --- | --- |
| One agent CLI per tmux pane | Every participant is inspectable and interruptible. |
| YAML scenarios | Teams are reproducible, reviewable, and shareable. |
| Run-local tools | Agents communicate through a stable contract, not global shell hacks. |
| Runner command prefixes | Use `codex`, `claude`, `gemini`, or any custom agent CLI. |
| No `cmux` dependency | The required system package is `tmux`. |

## Install

```bash
git clone https://github.com/choism4/tmux-mas.git
cd tmux-mas
./install.sh
```

Default install target:

```text
~/.local/bin/tmux-mas
```

Custom prefix:

```bash
PREFIX=/usr/local ./install.sh
```

You can also run it directly from the repo:

```bash
./tmux-mas --help
```

## Quick Start

Run the smallest Claude scenario:

```bash
./tmux-mas doctor hello-claude
./tmux-mas run hello-claude
tmux attach -t hello-claude
```

If Claude asks to trust the workspace, select `1. Yes`.

Stop it:

```bash
./tmux-mas stop hello-claude
```

Run the landing page team:

```bash
./tmux-mas doctor landing-page
./tmux-mas run landing-page
tmux attach -t landing-page-team-yml
```

Run the deterministic mock test suite:

```bash
python3 tests/run_mock_scenarios.py
python3 tests/run_public_scenarios_with_mock.py
```

## The Core Idea

An agent receives a prompt that includes:

- its role
- the participant pane map
- shared resources
- available tools
- scenario rules
- success criteria

Agents then communicate with injected run-local commands:

```bash
agent_send %214 "HOST: Did this tmux message reach you?"
agent_broadcast "LEAD: Everyone give one concrete risk."
```

The submit primitive is intentionally small:

```bash
tmux send-keys -t "$pane" -l "$message"
sleep 0.3
tmux send-keys -t "$pane" "$submit_key"
```

## Scenario Example

```yaml
name: hello-claude
session: hello-claude
window: team

runner:
  type: claude
  command: claude --dangerously-skip-permissions
  submit_key: Enter

agents:
  - id: HOST
    role: Starts the exchange, asks one concise question, and closes after one reply.
  - id: GUEST
    role: Replies once with a concise answer, then stops.

tools:
  - send
  - broadcast

kickoff:
  agent: HOST
  prompt: Send GUEST one short greeting and ask whether the tmux message reached them.

rules:
  - Keep messages short.
  - Receiving a message does not require a response unless your role has useful input.
  - Stop after the first complete exchange.

success:
  - HOST sends one message to GUEST.
  - GUEST sends one reply to HOST.
  - Both agents stop naturally.
```

## Runners

Presets:

```yaml
runner: codex
runner: claude
runner: gemini
```

Public scenarios should prefer explicit runner objects:

```yaml
runner:
  type: custom
  command: my-agent --some-flag
  submit_key: C-m
```

`runner.command` is an agent-calling prefix. `tmux-mas` appends the rendered
prompt as the final shell argument:

```bash
exec <runner.command> "$(cat <prompt-file>)"
```

Known local submit keys:

| Agent TUI | `submit_key` |
| --- | --- |
| Codex | `C-m` |
| Claude Code v2.1.133 | `Enter` |

## Commands

```bash
tmux-mas --help
tmux-mas --version
tmux-mas doctor [scenario-name]
tmux-mas list
tmux-mas run <scenario.yml|scenario-name>
tmux-mas status [session]
tmux-mas watch <session>
tmux-mas attach <session>
tmux-mas stop <session>
```

`watch` is the operator awareness loop. It polls pane output and reports
`changed`, `quiet`, `idle`, and `agent-exited` states:

```bash
tmux-mas watch hello-claude --idle-seconds 120
tmux-mas watch hello-claude --once
```

## Requirements

Required:

- `tmux`
- `python3`
- `PyYAML`
- the command named by `runner.command`

Optional:

- `agent-browser` for browser/UI scenarios

Not required:

- `cmux`

## Docs

- [Agent Operator Guide](docs/agent-operator-guide.md)
- [Example: Claude hello](scenarios/hello-claude.yml)
- [Example: Codex hello](scenarios/hello-codex.yml)
- [Example: Gemini hello](scenarios/hello-gemini.yml)
- [Example: landing page team](scenarios/landing-page.yml)
- Artifact-oriented examples:
  - [generative-art-studio-codex](scenarios/generative-art-studio-codex.yml)
  - [travel-itinerary-pdf-claude](scenarios/travel-itinerary-pdf-claude.yml)
  - [tabletop-game-jam-gemini](scenarios/tabletop-game-jam-gemini.yml)
  - [podcast-production-room-claude](scenarios/podcast-production-room-claude.yml)
  - [newsletter-briefing-codex](scenarios/newsletter-briefing-codex.yml)
  - [api-spec-design-codex](scenarios/api-spec-design-codex.yml)
  - [workshop-curriculum-claude](scenarios/workshop-curriculum-claude.yml)
  - [ops-runbook-codex](scenarios/ops-runbook-codex.yml)
  - [brand-system-studio-gemini](scenarios/brand-system-studio-gemini.yml)
  - [ux-research-synthesis-claude](scenarios/ux-research-synthesis-claude.yml)
- Mock scenarios live under `tests/fixtures/scenarios/` and are used only for deterministic CI.

## Release Checklist

```bash
bash -n tmux-mas install.sh
./tmux-mas --help
./tmux-mas --version
./tmux-mas doctor
python3 -m py_compile runtime/run_scenario.py runtime/doctor.py runtime/watch_session.py examples/mock_agent.py tests/smoke_parse.py tests/run_mock_scenarios.py tests/run_public_scenarios_with_mock.py
python3 tests/smoke_parse.py
python3 tests/run_public_scenarios_with_mock.py
python3 tests/run_mock_scenarios.py
git tag v0.1.4
git push origin main --tags
```

## Status

Experimental, but intentionally small. Treat agent output as untrusted, keep
scenario files explicit, and inspect the tmux panes when behavior matters.
