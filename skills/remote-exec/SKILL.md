---
name: remote-exec
description: Run commands on a remote server over SSH without hanging — aliased hosts, hard timeouts, non-interactive auth, plus one-shot probes (disk, memory, docker, GPU, ports) and file put/get. Use when a task needs to check or fix something on a remote box, a stage/prod host, a GPU worker, or any machine that is not this one.
allowed-tools:
  - Bash
  - Read
  - Write
permissions:
  - shell
  - env
  - file_read
  - file_write
license: MIT
---

# Remote exec

SSH from an agent fails in three predictable ways: it prompts for a password and
blocks forever, quoting mangles the remote command, or the command starts
something long-lived and the call never returns. This wrapper removes all three.

```
python3 "$SKILL_DIR/scripts/rx.py" <command>
```

**Not for:** provisioning a box, managing users or installing agents — it assumes the host exists and you already have an alias. Anything that must survive your session belongs in systemd, not in this wrapper.

## Portability

Works in any agent that can run shell commands (pi, Claude Code, Codex, Cursor,
Gemini CLI, …): the instructions are plain Markdown and the helper is a stdlib
script. Commands use `$SKILL_DIR` for this skill's own directory — the folder that
holds this `SKILL.md`. Set it once per session, for example:

```bash
SKILL_DIR=~/.claude/skills/remote-exec     # or ~/.codex/skills/…, ~/.pi/agent/skills/…, .cursor/skills/…
```

## Hosts

```
rx.py add stage deploy@10.0.0.5:2222 --key /path/to/your/key --note staging
rx.py ls
rx.py rm stage
```

Stored in `~/.config/rx/hosts.json` (mode 600), never in the repo and never in a
skill file. A raw `[user@]host[:port]` works without registering, so one-off
boxes need no setup.

## Commands

| Need | Command |
| --- | --- |
| is the box healthy, in one round trip | `probe stage` |
| run something | `run stage "systemctl is-active api"` |
| run with the user's login shell (`~/.bashrc` env) | `run stage "source ~/.nvm/nvm.sh && node -v" --login` |
| tail a container or unit | `logs stage api --lines=120` |
| copy up / down | `put stage ./x.tar /tmp/x.tar` / `get stage /var/log/app.log ./app.log` |
| bound the wait | `--timeout=120` on any command (default 60s) |

`probe` replaces the four or five separate calls usually spent finding out
whether a box is out of disk: it returns hostname, uptime, only filesystems over
70%, memory, running containers, GPU memory/util, and listening ports.

## Rules

- **One round trip beats five.** Anything you would run as three commands to build
  context belongs in a single `run "a; b; c"`, because each call costs latency and
  context.
- **Quote for the remote shell, not yours.** The command is one string; single
  quotes inside it survive. If it needs `$VAR` expanded remotely, use double
  quotes deliberately, or `--login` with an explicit `bash -lc`.
- **Never start an interactive process** (`vim`, `top`, `psql` with no `-c`,
  `docker exec -it`). Prefer `psql -c "..."`, `docker logs --tail`, `journalctl -n`.
- **Long jobs go to a log, not the call**: detach the job, redirect it to a file
  under `/tmp`, then poll that file. A 60s timeout on a 20-minute run returns
  nothing useful.
- **Destructive remote commands** (rm, migrations, service restarts, anything on
  prod) need the user's explicit go-ahead first, and you show the exact command
  before running it.
- Reported failures are real failures: a non-zero exit is printed to stderr and
  returned as the exit code. Do not re-run blindly; read the error.

## Keys and auth

Password auth cannot work here by design (BatchMode). If the user has only a
password, ask them to add a key (`ssh-copy-id`) or run the password-requiring step
themselves. `StrictHostKeyChecking=accept-new` trusts a new host once, then pins
it; it does not weaken an existing known_hosts entry.

## Self-check

`python3 "$SKILL_DIR/scripts/rx.py" self-test` verifies alias parsing
(including IPv6 and `host:port`), the 600 config mode, the BatchMode flags, and
quoting of a hostile command. Run it after editing the script.
