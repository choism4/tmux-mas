#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import shutil
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=capture)


def require(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Missing required command: {name}")
    return path


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return int(port)


def load_scenario(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Scenario not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Scenario must be a mapping: {path}")
    return data


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_agent_tools(agent_bin: Path, others: list[str], browser_session: str | None, submit_key: str) -> None:
    agent_bin.mkdir(parents=True, exist_ok=True)
    write(
        agent_bin / "agent_send",
        f"""#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: agent_send <pane> <message...>" >&2
  exit 1
fi

pane="$1"
shift
message="$*"

tmux send-keys -t "$pane" -l "$message"
sleep "${{TMUX_MAS_SEND_DELAY:-0.3}}"
tmux send-keys -t "$pane" "${{TMUX_MAS_SUBMIT_KEY:-{submit_key}}}"
""",
    )
    write(
        agent_bin / "agent_broadcast",
        f"""#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: agent_broadcast <message...>" >&2
  exit 1
fi

message="$*"
panes={shell_quote(" ".join(others))}

for pane in $panes; do
  tmux send-keys -t "$pane" -l "$message"
  sleep "${{TMUX_MAS_SEND_DELAY:-0.3}}"
  tmux send-keys -t "$pane" "${{TMUX_MAS_SUBMIT_KEY:-{submit_key}}}"
  sleep "${{TMUX_MAS_BROADCAST_DELAY:-0.8}}"
done
""",
    )

    if browser_session:
        agent_browser = shutil.which("agent-browser")
        if agent_browser:
            write(
                agent_bin / "agent-browser",
                f"""#!/usr/bin/env bash
set -euo pipefail
exec {shell_quote(agent_browser)} --session {shell_quote(browser_session)} "$@"
""",
            )

    for tool in agent_bin.iterdir():
        tool.chmod(0o755)


def render_prompt(
    *,
    scenario: dict,
    agent: dict,
    participants: str,
    resources_text: str,
    tools_text: str,
) -> str:
    rules = scenario.get("rules") or []
    success = scenario.get("success") or []
    kickoff = scenario.get("kickoff") or {}
    kickoff_text = ""
    if kickoff:
        kickoff_text = "\nKickoff:\n"
        if kickoff.get("agent"):
            kickoff_text += f"- Starter: {kickoff['agent']}\n"
        if kickoff.get("prompt"):
            kickoff_text += textwrap.indent(str(kickoff["prompt"]).strip(), "- ") + "\n"

    rules_text = "\n".join(f"- {rule}" for rule in rules)
    success_text = "\n".join(f"- {item}" for item in success)

    return f"""You are {agent['id']} in the tmux-mas scenario "{scenario['name']}".

Your role:
{agent.get('role', '')}

Scenario:
{scenario.get('description', '')}

Participants and tmux panes:
{participants}

Shared resources:
{resources_text}

Available tools:
{tools_text}

Team rules:
- Use the language requested by the scenario. If none is requested, use concise natural English.
- Every team message you send must start with "{agent['id']}: ".
- Use only agent_send or agent_broadcast for team communication.
- Do not run tmux commands directly. Do not inspect other panes with capture-pane.
- Treat messages that arrive in your own input as the conversation transcript.
- Stay within your role.
{rules_text}
{kickoff_text}
Success criteria:
{success_text}
"""


def prepare_static_site(resource: dict, run_dir: Path) -> tuple[str, str]:
    site_dir = run_dir / resource.get("name", "site")
    site_dir.mkdir(parents=True, exist_ok=True)
    seed = resource.get("seed")
    entry = resource.get("entry", "index.html")
    if seed:
        seed_path = (ROOT / seed).resolve() if not Path(seed).is_absolute() else Path(seed)
        shutil.copyfile(seed_path, site_dir / entry)
    elif not (site_dir / entry).exists():
        write(site_dir / entry, "<!doctype html><title>tmux-mas</title><h1>Hello</h1>\n")

    port = free_port()
    url = f"http://127.0.0.1:{port}"
    return str(site_dir), url


def prepare_workspace(resource: dict, run_dir: Path) -> str:
    workspace_dir = run_dir / resource.get("name", "workspace")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    for relative_path, content in (resource.get("files") or {}).items():
        write(workspace_dir / str(relative_path), str(content))
    return str(workspace_dir)


def wait_url(url: str, attempts: int = 30) -> bool:
    import urllib.request

    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return response.status < 500
        except Exception:
            time.sleep(0.2)
    return False


def resolve_runner(scenario: dict) -> dict[str, str]:
    raw_runner = scenario.get("runner") or "codex"
    if os.environ.get("TMUX_MAS_RUNNER"):
        raw_runner = os.environ["TMUX_MAS_RUNNER"]

    if isinstance(raw_runner, str):
        runner = {"type": raw_runner}
    elif isinstance(raw_runner, dict):
        runner = {str(key): str(value) for key, value in raw_runner.items()}
    else:
        raise SystemExit("runner must be a string or mapping")

    runner_type = runner.get("type", "custom")
    presets = {
        "codex": {
            "command": "codex --no-alt-screen --dangerously-bypass-approvals-and-sandbox",
            "submit_key": "C-m",
        },
        "claude": {
            "command": "claude --dangerously-skip-permissions",
            "submit_key": "Enter",
        },
        "gemini": {
            "command": "gemini --yolo",
            "submit_key": "C-m",
        },
    }

    if runner_type in presets:
        preset = presets[runner_type]
        runner.setdefault("command", preset["command"])
        runner.setdefault("submit_key", preset["submit_key"])
    elif runner_type != "custom":
        raise SystemExit(f"Unsupported runner type: {runner_type}")

    if os.environ.get("TMUX_MAS_RUNNER_COMMAND"):
        runner["command"] = os.environ["TMUX_MAS_RUNNER_COMMAND"]

    command = runner.get("command")
    if not command:
        raise SystemExit("runner.command is required for custom runners")

    command_parts = shlex.split(command)
    if not command_parts:
        raise SystemExit("runner.command cannot be empty")
    require(command_parts[0])

    runner["type"] = runner_type
    runner["cwd"] = os.environ.get("TMUX_MAS_CWD") or runner.get("cwd") or str(Path.home())
    runner["command"] = command
    runner["submit_key"] = runner.get("submit_key") or "C-m"
    return runner


def render_start_script(
    *,
    runner: dict[str, str],
    agent_id: str,
    agent_bin: Path,
    prompt_file: Path,
    screenshot_dir: Path,
) -> str:
    cwd = shell_quote(runner["cwd"])
    prompt = shell_quote(str(prompt_file))
    command = runner["command"]

    return f"""#!/usr/bin/env bash
set -euo pipefail
export PATH={shell_quote(str(agent_bin))}:"$PATH"
export TMUX_MAS_ROOT={shell_quote(str(ROOT))}
export TMUX_MAS_AGENT_ID={shell_quote(agent_id)}
export AGENT_BROWSER_SCREENSHOT_DIR={shell_quote(str(screenshot_dir))}
mkdir -p "$AGENT_BROWSER_SCREENSHOT_DIR"
cd {cwd}
set +e
{command} "$(cat {prompt})"
status=$?
printf '\\nTMUX_MAS_AGENT_EXIT agent=%s status=%s\\n' "$TMUX_MAS_AGENT_ID" "$status"
exit "$status"
"""


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: run_scenario.py <scenario.yml>")

    require("tmux")

    scenario_path = Path(sys.argv[1]).resolve()
    scenario = load_scenario(scenario_path)
    runner = resolve_runner(scenario)
    session = scenario.get("session") or scenario["name"]
    window = scenario.get("window", "team")
    agents = scenario.get("agents") or []
    if not agents:
        raise SystemExit("Scenario must define at least one agent")

    run_id = f"{session}-{time.strftime('%Y%m%d-%H%M%S')}"
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if run(["tmux", "has-session", "-t", session], check=False).returncode == 0:
        raise SystemExit(f"tmux session already exists: {session}")

    resources: dict[str, dict[str, str]] = {}
    for resource in scenario.get("resources", []):
        if resource.get("type") == "static-site":
            site_dir, url = prepare_static_site(resource, run_dir)
            resources[resource.get("name", "site")] = {
                "type": "static-site",
                "site_dir": site_dir,
                "entry": resource.get("entry", "index.html"),
                "url": url,
            }
        elif resource.get("type") == "workspace":
            workspace_dir = prepare_workspace(resource, run_dir)
            resources[resource.get("name", "workspace")] = {
                "type": "workspace",
                "workspace_dir": workspace_dir,
            }

    run(["tmux", "new-session", "-d", "-s", session, "-n", window, "bash --noprofile --norc"])

    for name, resource in resources.items():
        if resource["type"] == "static-site":
            command = f"cd {shell_quote(resource['site_dir'])} && python3 -m http.server {resource['url'].rsplit(':', 1)[1]} --bind 127.0.0.1"
            run(["tmux", "new-window", "-t", session, "-n", f"{name}-server", command])
            if not wait_url(resource["url"]):
                raise SystemExit(f"HTTP server failed to start: {resource['url']}")

    run(["tmux", "select-window", "-t", f"{session}:{window}"])
    run(["tmux", "set-option", "-t", f"{session}:{window}", "remain-on-exit", "on"])
    run(["tmux", "set-option", "-t", f"{session}:{window}", "pane-border-status", "top"])
    run(["tmux", "set-option", "-t", f"{session}:{window}", "pane-border-format", " #{pane_index} #{@agent_name} #{pane_id} "])

    for _ in range(2, len(agents) + 1):
        run(["tmux", "split-window", "-t", f"{session}:{window}", "bash --noprofile --norc"])
        run(["tmux", "select-layout", "-t", f"{session}:{window}", "tiled"], check=False)

    pane_lines = run(
        ["tmux", "list-panes", "-t", f"{session}:{window}", "-F", "#{pane_index} #{pane_id}"],
        capture=True,
    ).stdout.splitlines()
    panes = [line.split()[1] for line in sorted(pane_lines, key=lambda item: int(item.split()[0]))]
    participants = "\n".join(f"{agent['id']}={panes[i]}" for i, agent in enumerate(agents))

    resources_text_lines: list[str] = []
    for name, resource in resources.items():
        resources_text_lines.append(f"- {name}:")
        for key, value in resource.items():
            resources_text_lines.append(f"  - {key}: {value}")
    resources_text = "\n".join(resources_text_lines) if resources_text_lines else "- none"

    for i, agent in enumerate(agents):
        pane = panes[i]
        agent_id = agent["id"]
        others = [panes[j] for j in range(len(agents)) if j != i]
        run(["tmux", "select-pane", "-t", pane, "-T", agent_id])
        run(["tmux", "set-option", "-pt", pane, "@agent_name", agent_id])

        tools = scenario.get("tools", ["send", "broadcast"])
        browser_session = f"{session}-{agent_id}" if "browser" in tools else None
        agent_bin = run_dir / "tools" / agent_id
        create_agent_tools(agent_bin, others, browser_session, runner["submit_key"])

        tools_text = [
            f'- agent_send <target-pane> "{agent_id}: <message>"',
            f'- agent_broadcast "{agent_id}: <message>"',
        ]
        if "browser" in tools and shutil.which("agent-browser"):
            tools_text.append("- agent-browser ...")
        elif "browser" in tools:
            tools_text.append("- agent-browser requested but command is not installed")

        prompt = render_prompt(
            scenario=scenario,
            agent=agent,
            participants=participants,
            resources_text=resources_text,
            tools_text="\n".join(tools_text),
        )
        prompt_file = run_dir / "prompts" / f"{agent_id}.prompt"
        write(prompt_file, prompt)

        start_file = run_dir / "start" / agent_id
        write(
            start_file,
            render_start_script(
                runner=runner,
                agent_id=agent_id,
                agent_bin=agent_bin,
                prompt_file=prompt_file,
                screenshot_dir=run_dir / "screenshots" / agent_id,
            ),
        )
        start_file.chmod(0o755)
        run(["tmux", "respawn-pane", "-k", "-t", pane, str(start_file)])

    write(run_dir / "metadata.txt", f"session={session}\nwindow={window}\n{participants}\n")

    print(f"Started tmux session: {session}")
    print(f"Runner: {runner['type']}")
    print(f"Run dir: {run_dir}")
    if resources:
        print("\nResources:")
        for name, resource in resources.items():
            print(f"- {name}: {resource}")
    print("\nParticipants:")
    print(participants)
    print("\nAttach with:")
    print(f"  tmux attach -t {session}")


if __name__ == "__main__":
    main()
