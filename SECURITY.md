# Security review — remote-exec

Static analysis with SkillSpector v2.12.0 (no LLM).

- Raw scan: **24/100**, MEDIUM, CAUTION, 4 finding(s).
- With the accepted-findings baseline: **0/100, SAFE, 0 open findings**.

Accepted findings live in `.skillspector-baseline.yaml`, so a scan still fails on anything new:

```bash
pip install skillspector
skillspector scan skills/remote-exec --baseline .skillspector-baseline.yaml
```

## Accepted findings

| Rule | Severity | File | Why acceptable |
| --- | --- | --- | --- |
| TT2 | MEDIUM | `rx.py:42` | Writes only the path the user named; nothing is transmitted anywhere. |
| AST4 | MEDIUM | `rx.py:75` | Child process with a fixed argv list: no `shell=True`, no interpolation of user input; stderr is returned as the exit code. |

## What this skill never does

- No `shell=True`, no `eval`, no `exec` of model-supplied strings.
- No credentials in the repo, none echoed.
- No runtime choice of network destination.
- No write outside the path the user named.

## Test evidence

Every command in the SKILL.md was run against a real target. `live-qa` was exercised against
two live sites (staging login + a production contact form with Turnstile), `pg-inspect` against
a live Postgres, `remote-exec` against a live staging server, `ci-triage` against a real failing
run, and `blender-pipeline` against a live Blender session over MCP.
