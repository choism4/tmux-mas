# Agent Operator Guide

This guide is written for agents and automation that need to operate
`tmux-mas` without guessing.

`tmux-mas` means **tmux Multi Agents System**. It treats a tmux session as a
small multi-agent runtime: one agent CLI per pane, run-local communication tools,
and a YAML scenario as the source of truth.

## Minimal Operation

List bundled scenarios:

```bash
./tmux-mas list
```

Print version:

```bash
./tmux-mas --version
```

Check the local environment:

```bash
./tmux-mas doctor
./tmux-mas doctor hello-claude
```

Run a scenario by name:

```bash
./tmux-mas run hello-claude
```

Inspect panes:

```bash
./tmux-mas status hello-claude
```

Watch for pane changes and stalls:

```bash
./tmux-mas watch hello-claude --idle-seconds 120
./tmux-mas watch hello-claude --once
```

Attach for visual inspection:

```bash
tmux attach -t hello-claude
```

Stop the session:

```bash
./tmux-mas stop hello-claude
```

Run deterministic tmux smoke scenarios:

```bash
python3 tests/run_mock_scenarios.py
python3 tests/run_public_scenarios_with_mock.py
```

## Scenario Name Resolution

`tmux-mas run <scenario>` resolves scenarios in this order:

1. exact file path passed by the caller
2. `scenarios/<name>`
3. `scenarios/<name>.yml`
4. `scenarios/<name>.yaml`

These are equivalent when run from the project root:

```bash
./tmux-mas run hello-claude
./tmux-mas run scenarios/hello-claude.yml
```

## YAML Schema

Required:

```yaml
name: hello-claude
session: hello-claude
agents:
  - id: HOST
    role: Starts the exchange.
```

Common fields:

```yaml
window: team
runner:
  type: claude
  command: claude --dangerously-skip-permissions
  submit_key: Enter
tools:
  - send
  - broadcast
kickoff:
  agent: HOST
  prompt: Send one greeting.
rules:
  - Keep messages short.
success:
  - The exchange completes.
```

## Runner Contract

`runner.command` is an agent-calling prefix. `tmux-mas` appends the rendered
prompt as the final shell argument.

Effective start command:

```bash
cd "$TMUX_MAS_CWD"
exec <runner.command> "$(cat <prompt-file>)"
```

Examples:

```yaml
runner:
  type: codex
  command: codex --no-alt-screen --dangerously-bypass-approvals-and-sandbox
  submit_key: C-m
```

```yaml
runner:
  type: claude
  command: claude --dangerously-skip-permissions
  submit_key: Enter
```

```yaml
runner:
  type: custom
  command: gemini --yolo
  submit_key: C-m
```

## Injected Tools

Each agent receives a private tool directory at the front of `PATH`.

Use direct send:

```bash
agent_send %214 "HOST: Did this message reach you?"
```

Use broadcast:

```bash
agent_broadcast "LEAD: Everyone give one risk."
```

Do not call `tmux send-keys` directly from an agent prompt unless debugging the
runner itself. The scenario prompt instructs agents to use only the injected
tools for team communication.

## Submit Keys

The injected tools send text literally, wait briefly, then send a tmux key:

```bash
tmux send-keys -t "$pane" -l "$message"
sleep "${TMUX_MAS_SEND_DELAY:-0.3}"
tmux send-keys -t "$pane" "${TMUX_MAS_SUBMIT_KEY:-<submit_key>}"
```

Known values from local testing:

- Codex TUI: `C-m`
- Claude Code v2.1.133 in this environment: `Enter`

Keep `submit_key` explicit in public scenarios.

## Resources

Static site resources create a run-local directory and HTTP server:

```yaml
resources:
  - name: site
    type: static-site
    entry: index.html
    seed: templates/signaldesk.html
```

The rendered prompt includes:

- `site_dir`
- `entry`
- `url`

## Agent Browser

If `agent-browser` is installed and the scenario includes `browser`, each agent
gets an `agent-browser` wrapper bound to a per-agent browser session.

```yaml
tools:
  - send
  - broadcast
  - browser
```

Agent usage:

```bash
agent-browser open http://127.0.0.1:12345
```

`cmux` is not required.

## Environment Overrides

Override runner type:

```bash
TMUX_MAS_RUNNER=claude ./tmux-mas run hello-claude
```

Override runner command:

```bash
TMUX_MAS_RUNNER_COMMAND='claude --dangerously-skip-permissions' ./tmux-mas run hello-claude
```

Override working directory:

```bash
TMUX_MAS_CWD="$PWD" ./tmux-mas run hello-claude
```

Override submit key for generated tools:

```bash
TMUX_MAS_SUBMIT_KEY=Enter ./tmux-mas run hello-claude
```

## Status Output

`tmux-mas status <session>` prints one pane per line:

```text
hello-claude:team.1 %213 HOST node
hello-claude:team.2 %214 GUEST node
```

Fields:

1. `<session>:<window>.<pane-index>`
2. tmux pane id
3. agent id
4. current command

## Watch Output

`tmux-mas watch <session>` polls pane tails and prints one row per pane. When an
agent CLI exits, tmux-mas leaves a `TMUX_MAS_AGENT_EXIT` marker in the pane and
`watch` reports the pane as `exited`.

```text
== 2026-05-08T10:32:00+00:00 ==
   changed hello-claude:team.1       %213   HOST             node         HOST: sent greeting
     quiet hello-claude:team.2       %214   GUEST            node         › Reply to HOST
 idle>120s hello-claude:team.3       %215   QA               node         Worked for 2m 05s
```

Statuses:

- `new`: first time this pane was observed
- `changed`: captured pane tail changed since the previous poll
- `quiet`: unchanged, but below the idle threshold
- `idle>Ns`: unchanged for at least the configured idle threshold
- `exited`: the agent process exited and left a `TMUX_MAS_AGENT_EXIT` marker
- `dead`: tmux reports a closed process without a tmux-mas exit marker; treat this as an abnormal diagnostic state

Use `--once` when another orchestrator process wants to sample state without
holding the terminal.

## Failure Modes

Scenario not found:

```text
Scenario not found: nope
Run './tmux-mas list' to see available scenarios.
```

Session already exists:

```text
tmux session already exists: hello-claude
```

Stop it:

```bash
./tmux-mas stop hello-claude
```

Missing command:

```text
Missing required command: claude
```

Install the agent CLI or change `runner.command`.
