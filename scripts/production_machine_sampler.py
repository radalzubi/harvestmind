"""Sample the production machine from outside while a solve runs: CPU counters (user / system / idle
/ steal from /proc/stat), load average, available memory, and every Python process's RSS, high-water
RSS, thread count and CPU ticks, through `fly machine exec`. The image carries no ps / free / top, so
/proc is read directly. Nothing on the machine is changed; each sample is one short exec.

Writes one JSON line per sample. Stop with --stop-file (created by the caller) or --duration.

Usage: python3 -m scripts.production_machine_sampler --app zaad-api --machine 0804e0dfd1e948 \
           --interval 10 --stop-file /tmp/stop --out samples.jsonl
"""
from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404 - fly CLI, fixed argv
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = (
    'head -1 /proc/stat; cat /proc/loadavg; grep -E "MemTotal|MemAvailable" /proc/meminfo; '
    'for p in /proc/[0-9]*; do n=$(grep -E "^Name" $p/status 2>/dev/null | cut -f2); '
    'case "$n" in python*|uvicorn*) echo "PROC $p $n"; grep -E "^(VmRSS|VmHWM|Threads)" $p/status; '
    'echo "TICKS $(cut -d" " -f14,15 $p/stat)";; esac; done'
)


def sample(app: str, machine: str) -> dict:
    t = time.perf_counter()
    proc = subprocess.run(["fly", "machine", "exec", machine, "-a", app, f'sh -c \'{SCRIPT}\''],  # nosec B603 B607
                          capture_output=True, text=True, timeout=60)
    out = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "exec_seconds": round(time.perf_counter() - t, 2),
           "returncode": proc.returncode, "processes": []}
    if proc.returncode != 0:
        out["error"] = (proc.stderr or proc.stdout)[-300:]
        return out
    current: dict | None = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("cpu "):
            f = [int(x) for x in line.split()[1:]]
            out["cpu_ticks"] = {"user": f[0], "nice": f[1], "system": f[2], "idle": f[3], "iowait": f[4], "irq": f[5], "softirq": f[6], "steal": f[7]}
        elif line.startswith("MemTotal"):
            out["mem_total_kb"] = int(line.split()[1])
        elif line.startswith("MemAvailable"):
            out["mem_available_kb"] = int(line.split()[1])
        elif line.startswith("PROC "):
            _, path, name = line.split(" ", 2)
            current = {"pid": int(path.rsplit("/", 1)[1]), "name": name}
            out["processes"].append(current)
        elif current is not None and line.startswith("VmRSS"):
            current["rss_kb"] = int(line.split()[1])
        elif current is not None and line.startswith("VmHWM"):
            current["hwm_kb"] = int(line.split()[1])
        elif current is not None and line.startswith("Threads"):
            current["threads"] = int(line.split()[1])
        elif current is not None and line.startswith("TICKS"):
            parts = line.split()
            if len(parts) == 3:
                current["utime_ticks"], current["stime_ticks"] = int(parts[1]), int(parts[2])
        elif len(line.split()) == 5 and "/" in line.split()[3]:
            la = line.split()
            out["loadavg"] = [float(la[0]), float(la[1]), float(la[2])]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default="zaad-api")
    ap.add_argument("--machine", required=True)
    ap.add_argument("--interval", type=float, default=10.)
    ap.add_argument("--duration", type=float, default=3600.)
    ap.add_argument("--stop-file", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    started = time.perf_counter()
    with open(args.out, "a") as fh:
        while time.perf_counter() - started < args.duration:
            if args.stop_file and Path(args.stop_file).exists():
                break
            row = sample(args.app, args.machine)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            procs = ", ".join(f"{p['name']}[{p['pid']}] rss {p.get('rss_kb', 0) // 1024} MB thr {p.get('threads')}" for p in row["processes"])
            cpu = row.get("cpu_ticks", {})
            print(f"{row['at']} steal {cpu.get('steal')} user {cpu.get('user')} load {row.get('loadavg')} avail {row.get('mem_available_kb', 0) // 1024} MB | {procs}", flush=True)
            time.sleep(max(0., args.interval - row["exec_seconds"]))


if __name__ == "__main__":
    main()
