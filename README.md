# tmux-mas

[![CI](https://github.com/choism4/tmux-mas/actions/workflows/ci.yml/badge.svg)](https://github.com/choism4/tmux-mas/actions/workflows/ci.yml)

`tmux-mas` means **tmux Multi Agents System**.

It runs small multi-agent teams inside tmux.

It launches one agent CLI per tmux pane, injects run-local communication tools,
and lets agents talk to each other with `agent_send` and `agent_broadcast`.

The launcher starts the team. It does not facilitate the conversation.

## Requirements

Required system package:

- `tmux`

Runtime commands:

- `python3`
- the command named by `runner.command` in your scenario

Optional:

- `agent-browser` for browser/UI scenarios

## Install

From a clone:

```bash
git clone https://github.com/choism4/tmux-mas.git
cd tmux-mas
./install.sh
```

Default install target:

```text
~/.local/bin/tmux-mas
```

Custom install prefix:

```bash
PREFIX=/usr/local ./install.sh
```

Or use it directly without installing:

```bash
./tmux-mas list
```

## Quick Start

```bash
./tmux-mas --help
./tmux-mas doctor
./tmux-mas list
./tmux-mas run hello-claude
tmux attach -t hello-claude
```

Or:

```bash
./tmux-mas attach hello-claude
./tmux-mas stop hello-claude
```

For the full agent-facing operator contract, read
[`docs/agent-operator-guide.md`](docs/agent-operator-guide.md).

## Scenario Files

Scenarios are YAML files:

```yaml
name: landing-page-team
session: landing-page-team-yml
window: landing
runner:
  type: codex
  command: codex --no-alt-screen --dangerously-bypass-approvals-and-sandbox
  submit_key: C-m

agents:
  - id: LEAD
    role: Project owner.
  - id: DESIGNER
    role: Landing page designer.
  - id: DEVELOPER
    role: Frontend developer.
  - id: QA
    role: Browser QA reviewer.

tools:
  - send
  - broadcast
  - browser

resources:
  - name: site
    type: static-site
    entry: index.html
    seed: templates/signaldesk.html
```

## Runtime Model

For each run, `tmux-mas` creates:

- a tmux session
- one pane per agent
- pane titles from agent IDs
- run-local tools in `runs/<run-id>/tools/<agent>/`
- prompts in `runs/<run-id>/prompts/`
- static-site resources when requested

Agents receive tools through `PATH`:

```bash
agent_send <target-pane> "LEAD: message"
agent_broadcast "LEAD: message"
agent-browser open http://127.0.0.1:12345
```

Runner presets:

```yaml
runner: codex
```

```yaml
runner: claude
```

```yaml
runner: gemini
```

For public scenarios, prefer the explicit form:

```yaml
runner:
  type: custom
  command: my-agent --some-flag
  submit_key: C-m
```

`command` is an agent-calling prefix. `tmux-mas` appends the rendered prompt as
the final shell argument. `submit_key` defaults to `C-m`; override it only when
your agent TUI needs a different tmux key name. In current Claude Code TUI
builds, `Enter` may be required.

You can also override a scenario runner command for one launch:

```bash
TMUX_MAS_RUNNER=claude ./tmux-mas run scenarios/hello-claude.yml
TMUX_MAS_RUNNER_COMMAND='claude --dangerously-skip-permissions' ./tmux-mas run scenarios/hello-claude.yml
```

The message submit primitive is:

```bash
tmux send-keys -t "$pane" -l "$message"
sleep 0.3
tmux send-keys -t "$pane" C-m
```

## Commands

```bash
./tmux-mas --help
./tmux-mas --version
./tmux-mas doctor [scenario-name]
./tmux-mas run <scenario.yml>
./tmux-mas run <scenario-name>
./tmux-mas list
./tmux-mas status [session]
./tmux-mas attach <session>
./tmux-mas stop <session>
```

## Release Checklist

```bash
python3 -m pip install -r requirements.txt
bash -n tmux-mas install.sh
./tmux-mas doctor
python3 -m py_compile runtime/run_scenario.py runtime/doctor.py tests/smoke_parse.py
python3 tests/smoke_parse.py
git tag v0.1.1
git push origin main --tags
```

## Notes

- `tmux` is the core required package.
- `cmux` is not required.
- `agent-browser` is optional, but browser scenarios use it when available.
- Run artifacts are ignored by git under `runs/`.
- This project is experimental. Treat agent output as untrusted.
