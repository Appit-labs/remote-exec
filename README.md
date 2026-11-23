# remote-exec

<h3 align="center">Run one command on a remote server without hanging on a prompt.</h3>

<p align="center">
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-MIT-3DA639?style=flat-square"></a>
  <img alt="agents" src="https://img.shields.io/badge/works%20in-pi%20%7C%20Claude%20Code%20%7C%20Codex%20%7C%20Cursor-4B5563?style=flat-square">
  <img alt="skillspector" src="https://img.shields.io/badge/SkillSpector-0%2F100%20SAFE-2EA043?style=flat-square">
  <img alt="cost" src="https://img.shields.io/badge/session%20cost-~80%20tok-6E7681?style=flat-square">
</p>

<p align="center">
  <img alt="remote-exec demo — real run, regenerable from demos/remote-exec.json" src="skills/remote-exec/assets/demo.gif" width="900">
</p>

## What it is

`remote-exec` is **one-shot SSH with guard rails**: registered hosts, hard timeouts, no
interactive prompts, a single-call health probe (uptime, disks over 70%, memory, containers, GPU,
listening ports) and file put/get. Every call either returns an answer or fails inside the timeout you
set.

## The problem it removes

SSH from an agent fails in three predictable ways: it blocks forever on a password prompt, it
mangles the remote quoting, or it starts something long-lived and never returns. That is why sessions end
up hand-writing `ssh -o BatchMode=yes -o ConnectTimeout=… 'bash -lc …'` **825 times**. Here the flags are
fixed, hosts are aliases, and the timeout is a parameter.

## Install

```bash
# any agent, via the skills CLI — this one, or all twelve at once
npx skills add Appit-labs/remote-exec -g -y
npx skills add Appit-labs/appit-skills -g -y

# Claude Code — the whole collection as one marketplace
claude plugin marketplace add Appit-labs/appit-skills
claude plugin install remote-exec@appit-skills

# pi
pi install git:github.com/Appit-labs/remote-exec

# any agent that reads a skills directory
git clone git@github.com:Appit-labs/remote-exec.git
cp -r remote-exec/skills/remote-exec ~/.claude/skills/      # or ~/.codex/skills/, .cursor/skills/, …
```

## Use

- **Register a host** — `scripts/rx.py add staging deploy@10.0.0.5 --key /path/to/key`
- **Health in one call** — `scripts/rx.py probe staging`
- **Run / logs / copy** — `run` · `logs` · `put` · `get`, each with `--timeout`
- **See what is registered** — `scripts/rx.py ls`

## What it does not do

- Password authentication is not supported, on purpose — use a key (`ssh-copy-id`).
- It does not run interactive programs (`vim`, `top`, `psql` without `-c`); long jobs go to a log you poll.

## Requires

- `ssh` client and key-based auth to the target.
- Optional hosts file at `~/.config/rx/hosts.json` (mode 600, outside any repo).
- Python 3.9+ (stdlib only).

## Cost

| | tokens |
| --- | --- |
| always-on — the description, paid every session | ~80 |
| on invoke | ~0.9k |

The demo above is not a mockup: `demos/remote-exec.json` holds the captured run and
`tools/make_demo.py` renders it, so it can be regenerated and audited.

## Provenance

Every command in this skill was run against a real target before it was written down: a live
database, a staging host, a failing CI run, a browser session. The repository was created and
published on 2026-11-18; where the workflow itself is older, `CHANGELOG.md` carries the dates.

## Security

SkillSpector: **0/100, SAFE, 0 open findings** against the committed baseline. Every accepted
finding is listed with its reason in [SECURITY.md](SECURITY.md). No `shell=True`, no credential
storage, no network destination chosen at runtime.

## Part of the Appit collection

All twelve, one install: `npx skills add Appit-labs/appit-skills -g -y`.

- [`live-qa`](https://github.com/Appit-labs/live-qa) — live QA in a real browser
- [`ci-triage`](https://github.com/Appit-labs/ci-triage) — red CI to the failing line
- [`pg-inspect`](https://github.com/Appit-labs/pg-inspect) — read-only Postgres inspection
- [`repo-runbook`](https://github.com/Appit-labs/repo-runbook) — the verified runbook in AGENTS.md
- [`remote-exec`](https://github.com/Appit-labs/remote-exec) — SSH that cannot hang ← this skill
- [`trello-tickets`](https://github.com/Appit-labs/trello-tickets) — seven ticket types, one card
- [`cloud-browser`](https://github.com/Appit-labs/cloud-browser) — hosted browsers that stop billing
- [`open-design`](https://github.com/Appit-labs/open-design) — the OpenDesign monorepo
- [`blender-pipeline`](https://github.com/Appit-labs/blender-pipeline) — Blender via MCP
- [`code-scan`](https://github.com/Appit-labs/code-scan) — Skylos + Fallow, one gate
- [`release`](https://github.com/Appit-labs/release) — conventional commits to a tag
- [`hermes-setup`](https://github.com/Appit-labs/hermes-setup) — least-privilege agent wiring


## License

MIT, copyright Appit Labs. See [LICENSE](LICENSE).
