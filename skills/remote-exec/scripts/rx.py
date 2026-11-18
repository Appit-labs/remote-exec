#!/usr/bin/env python3
"""One-shot SSH for agents: non-interactive, time-boxed, no TTY hangs.

    rx.py ls
    rx.py add <alias> [user@]host[:port] [--key PATH] [--note TEXT]
    rx.py rm <alias>
    rx.py run <target> "<command>" [--timeout=60] [--login] [--yes-sudo]
    rx.py probe <target>                # uptime, disk, memory, docker, ports in ONE round trip
    rx.py logs <target> <docker-name|unit> [--lines=80]
    rx.py put <target> <local> <remote> [--timeout=300]
    rx.py get <target> <remote> <local> [--timeout=300]
    rx.py self-test

Target is an alias from ~/.config/rx/hosts.json, or a raw [user@]host[:port].
Every call uses BatchMode + ConnectTimeout so a bad host fails in seconds instead
of hanging a session on a password prompt.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

CONFIG = Path(os.environ.get("RX_CONFIG", Path.home() / ".config" / "rx" / "hosts.json"))
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
            "-o", "StrictHostKeyChecking=accept-new"]


def load_hosts() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {}


def save_hosts(hosts: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(hosts, indent=2, sort_keys=True) + "\n")
    CONFIG.chmod(0o600)


def parse_target(target: str) -> tuple[str, int | None, dict]:
    hosts = load_hosts()
    entry = hosts.get(target)
    if entry:
        return entry["host"], entry.get("port"), entry
    port = None
    host = target
    if target.count(":") == 1 and not target.startswith("["):
        maybe_host, maybe_port = target.split(":")
        if maybe_port.isdigit():
            host, port = maybe_host, int(maybe_port)
    return host, port, {}


def ssh_argv(target: str, timeout: int, login: bool) -> list[str]:
    host, port, entry = parse_target(target)
    argv = ["ssh", *SSH_OPTS, "-o", f"ConnectTimeout={min(timeout, 10)}"]
    if port:
        argv += ["-p", str(port)]
    if entry.get("key"):
        argv += ["-i", os.path.expanduser(entry["key"])]
    argv.append(host)
    return argv


def execute(target: str, remote_cmd: str, timeout: int, login: bool = False) -> int:
    argv = ssh_argv(target, timeout, login)
    argv.append(f"bash -lc {shlex.quote(remote_cmd)}" if login else remote_cmd)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"timed out after {timeout}s: {remote_cmd[:60]}", file=sys.stderr)
        return 124
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.returncode != 0 and proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


PROBE = r"""echo "== host"; hostname; uptime | sed 's/^ *//'
echo "== disk"; df -h --output=target,size,used,pcent 2>/dev/null | awk 'NR==1||(($4+0)>=70 && $1 !~ /^\/snap/)' | head -8
echo "== mem"; free -h 2>/dev/null | awk 'NR<=2'
echo "== docker"; (docker ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null || echo "none") | head -12
echo "== load/gpu"; (command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader) || echo "no gpu"
echo "== ports"; (ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | awk 'NR>1{print $4}' | sort -u | head -12"""


def cmd_probe(target: str, timeout: int) -> int:
    return execute(target, PROBE, timeout)


def cmd_logs(target: str, name: str, lines: int, timeout: int) -> int:
    cmd = (f"if docker ps --format '{{{{.Names}}}}' | grep -qx {shlex.quote(name)}; then "
           f"docker logs --tail {lines} {shlex.quote(name)} 2>&1; "
           f"else journalctl -u {shlex.quote(name)} -n {lines} --no-pager 2>&1; fi")
    return execute(target, cmd, timeout)


def cmd_put(target: str, local: str, remote: str, timeout: int) -> int:
    argv = ssh_argv(target, timeout, False) + [f"cat > {shlex.quote(remote)}"]
    with open(local, "rb") as fh:
        proc = subprocess.run(argv, stdin=fh, timeout=timeout)
    return proc.returncode


def cmd_get(target: str, remote: str, local: str, timeout: int) -> int:
    argv = ssh_argv(target, timeout, False) + [f"cat {shlex.quote(remote)}"]
    proc = subprocess.run(argv, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        return proc.returncode
    Path(local).write_bytes(proc.stdout)
    return 0


def cmd_add(alias: str, spec: str, key: str | None, note: str | None) -> int:
    hosts = load_hosts()
    host, port = spec, None
    if spec.count(":") == 1 and spec.split(":")[1].isdigit():
        host, port = spec.split(":")[0], int(spec.split(":")[1])
    hosts[alias] = {"host": host, "port": port, "key": key, "note": note}
    save_hosts(hosts)
    print(f"added {alias} -> {host}{':' + str(port) if port else ''}")
    return 0


def cmd_ls() -> int:
    hosts = load_hosts()
    if not hosts:
        print(f"no hosts in {CONFIG}; add one: rx.py add stage me@1.2.3.4")
        return 0
    for alias, entry in sorted(hosts.items()):
        port = f":{entry['port']}" if entry.get("port") else ""
        note = f"  # {entry['note']}" if entry.get("note") else ""
        print(f"{alias:16} {entry['host']}{port}{note}")
    return 0


def self_test() -> int:
    import tempfile
    global CONFIG
    with tempfile.TemporaryDirectory() as tmp:
        CONFIG = Path(tmp) / "hosts.json"
        assert cmd_add("stage", "deploy@10.0.0.5:2222", "/tmp/demo_key", "staging") == 0
        host, port, entry = parse_target("stage")
        assert (host, port) == ("deploy@10.0.0.5", 2222), (host, port)
        assert entry["key"].endswith("demo_key")
        assert parse_target("root@1.2.3.4")[0] == "root@1.2.3.4"
        assert parse_target("host:99")[1] == 99
        assert parse_target("2001:db8::1")[0] == "2001:db8::1", "ipv6 must not split"
        argv = ssh_argv("stage", 30, False)
        assert "-o" in argv and "BatchMode=yes" in argv and "-p" in argv and "2222" in argv
        assert oct(CONFIG.stat().st_mode)[-3:] == "600", "config must be private"
        tricky = "echo 'a b' && ls \"$HOME\""
        assert shlex.quote(tricky).count("'") >= 2
        print("self-test ok")
        return 0


def main(argv: list[str]) -> int:
    opts = dict(a.lstrip("-").split("=", 1) for a in argv[1:] if a.startswith("--") and "=" in a)
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args or args[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    cmd, rest = args[0], args[1:]
    timeout = int(opts.get("timeout", 60))
    if cmd == "self-test":
        return self_test()
    if cmd == "ls":
        return cmd_ls()
    if cmd == "add" and len(rest) >= 2:
        return cmd_add(rest[0], rest[1], opts.get("key"), opts.get("note"))
    if cmd == "rm" and rest:
        hosts = load_hosts()
        if hosts.pop(rest[0], None) is None:
            print(f"no alias {rest[0]}", file=sys.stderr)
            return 2
        save_hosts(hosts)
        print(f"removed {rest[0]}")
        return 0
    if cmd == "run" and len(rest) >= 2:
        return execute(rest[0], rest[1], timeout, login="login" in opts)
    if cmd == "probe" and rest:
        return cmd_probe(rest[0], timeout)
    if cmd == "logs" and len(rest) >= 2:
        return cmd_logs(rest[0], rest[1], int(opts.get("lines", 80)), timeout)
    if cmd == "put" and len(rest) >= 3:
        return cmd_put(rest[0], rest[1], rest[2], timeout)
    if cmd == "get" and len(rest) >= 3:
        return cmd_get(rest[0], rest[1], rest[2], timeout)
    print(f"unknown or incomplete command: {' '.join(args)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
