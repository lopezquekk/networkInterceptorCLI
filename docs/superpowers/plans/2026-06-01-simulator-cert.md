# Simulator Certificate Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ni simulator list` and `ni simulator install-cert` commands that install the mitmproxy CA cert into booted iOS Simulators.

**Architecture:** A new `lib/simulator.py` module wraps `xcrun simctl` for listing and cert installation. The `ni` CLI gets a `simulator` subparser group mirroring the existing `mock` pattern. Simulators inherit system proxy automatically — only the cert needs installing.

**Tech Stack:** Python stdlib (`json`, `subprocess`, `sys`), `xcrun simctl` (bundled with Xcode), existing `lib/paths.CERT_PATH`.

---

## File Layout

```
lib/simulator.py          ← new: list_booted() + install_cert(udid)
tests/test_simulator.py   ← new: 7 unit tests (monkeypatched subprocess)
ni                        ← modify: add simulator subparser + 2 command functions
```

---

## Task 1: lib/simulator.py (TDD)

**Files:**
- Create: `lib/simulator.py`
- Create: `tests/test_simulator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_simulator.py`:

```python
import json
import pytest
from lib import simulator
from lib.paths import CERT_PATH


BOOTED_JSON = {
    "devices": {
        "com.apple.CoreSimulator.SimRuntime.iOS-18-6": [
            {"name": "iPhone 16e", "udid": "5A74B7E3-AAAA", "state": "Booted"},
            {"name": "iPhone 15", "udid": "BBBB-CCCC", "state": "Shutdown"},
        ],
        "com.apple.CoreSimulator.SimRuntime.iOS-17-0": [
            {"name": "iPhone 14", "udid": "DDDD-EEEE", "state": "Booted"},
        ],
    }
}


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_list_booted_returns_only_booted(monkeypatch):
    monkeypatch.setattr(
        simulator.subprocess, "run",
        lambda *a, **kw: FakeResult(stdout=json.dumps(BOOTED_JSON))
    )
    devices = simulator.list_booted()
    assert len(devices) == 2
    udids = {d["udid"] for d in devices}
    assert "5A74B7E3-AAAA" in udids
    assert "DDDD-EEEE" in udids
    assert "BBBB-CCCC" not in udids  # Shutdown — must be excluded


def test_list_booted_returns_correct_fields(monkeypatch):
    monkeypatch.setattr(
        simulator.subprocess, "run",
        lambda *a, **kw: FakeResult(stdout=json.dumps(BOOTED_JSON))
    )
    devices = simulator.list_booted()
    iphone = next(d for d in devices if d["udid"] == "5A74B7E3-AAAA")
    assert iphone["name"] == "iPhone 16e"
    assert "iOS" in iphone["os"] or "com.apple" in iphone["os"]


def test_list_booted_empty_when_none_booted(monkeypatch):
    data = {"devices": {"com.apple.CoreSimulator.SimRuntime.iOS-18-6": [
        {"name": "iPhone 16e", "udid": "AAA", "state": "Shutdown"}
    ]}}
    monkeypatch.setattr(
        simulator.subprocess, "run",
        lambda *a, **kw: FakeResult(stdout=json.dumps(data))
    )
    assert simulator.list_booted() == []


def test_list_booted_handles_xcrun_not_found(monkeypatch):
    def raise_fnf(*a, **kw):
        raise FileNotFoundError
    monkeypatch.setattr(simulator.subprocess, "run", raise_fnf)
    assert simulator.list_booted() == []


def test_install_cert_returns_true_on_success(monkeypatch):
    monkeypatch.setattr(
        simulator.subprocess, "run",
        lambda *a, **kw: FakeResult(returncode=0)
    )
    assert simulator.install_cert("SOME-UDID") is True


def test_install_cert_returns_false_on_failure(monkeypatch):
    monkeypatch.setattr(
        simulator.subprocess, "run",
        lambda *a, **kw: FakeResult(returncode=1, stderr="error: device not found")
    )
    assert simulator.install_cert("BAD-UDID") is False


def test_install_cert_uses_cert_path_and_udid(monkeypatch):
    captured = []
    def capture(*a, **kw):
        captured.append(a[0])
        return FakeResult(returncode=0)
    monkeypatch.setattr(simulator.subprocess, "run", capture)
    simulator.install_cert("MY-UDID")
    cmd = captured[0]
    assert "MY-UDID" in cmd
    assert str(CERT_PATH) in cmd
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/camilolopez/networkInterceptor && python3 -m pytest tests/test_simulator.py -v
```

Expected: `ImportError: cannot import name 'simulator' from 'lib'`

- [ ] **Step 3: Implement lib/simulator.py**

```python
import json
import subprocess
import sys

from .paths import CERT_PATH


def list_booted() -> list:
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted", "--json"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("`xcrun` not found — is Xcode installed?", file=sys.stderr)
        return []
    if result.returncode != 0:
        print(f"[ni] simctl error: {result.stderr.strip()}", file=sys.stderr)
        return []
    data = json.loads(result.stdout)
    devices = []
    for os_name, sims in data.get("devices", {}).items():
        for sim in sims:
            if sim.get("state") == "Booted":
                devices.append({
                    "name": sim["name"],
                    "udid": sim["udid"],
                    "os": os_name,
                })
    return devices


def install_cert(udid: str) -> bool:
    result = subprocess.run(
        ["xcrun", "simctl", "keychain", udid, "add-root-cert", str(CERT_PATH)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[ni] Failed to install cert in {udid}: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python3 -m pytest tests/test_simulator.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
python3 -m pytest tests/ -v
```

Expected: all 26 tests PASS (19 existing + 7 new).

- [ ] **Step 6: Commit**

```bash
git add lib/simulator.py tests/test_simulator.py
git commit -m "feat: simulator module — list booted devices and install CA cert"
```

---

## Task 2: CLI Simulator Subcommands

**Files:**
- Modify: `ni` (add 2 command functions + simulator subparser + dispatch branch)

No new tests — behaviour is exercised via the simulator module tests. A smoke test validates the CLI wiring.

- [ ] **Step 1: Add the two command functions to `ni`**

Insert after `cmd_mock_remove` (after line 82), before `def main()`:

```python
def cmd_simulator_list(args):
    from lib.simulator import list_booted
    devices = list_booted()
    if not devices:
        print("No simulators currently booted.")
        return
    for d in devices:
        print(f"{d['udid']}  {d['name']}  ({d['os']})")


def cmd_simulator_install_cert(args):
    from lib.paths import CERT_PATH
    from lib.simulator import install_cert, list_booted
    if not CERT_PATH.exists():
        print("Error: CA cert not found. Run `ni start` first.", file=sys.stderr)
        sys.exit(1)
    devices = list_booted()
    if not devices:
        print("No simulators currently booted.")
        return
    if args.udid:
        devices = [d for d in devices if d["udid"] == args.udid]
        if not devices:
            print(f"Error: Simulator {args.udid} not found among booted devices.", file=sys.stderr)
            sys.exit(1)
    any_failed = False
    for d in devices:
        ok = install_cert(d["udid"])
        if ok:
            print(f"✓ {d['name']} ({d['udid']})")
        else:
            print(f"✗ {d['name']} ({d['udid']}) — failed", file=sys.stderr)
            any_failed = True
    if any_failed:
        sys.exit(1)
```

- [ ] **Step 2: Add the simulator subparser inside `main()`**

Insert after the `mock` subparser block (after the `p_rm.add_argument("id" ...)` line, before `args = parser.parse_args()`):

```python
    sim_p = sub.add_parser("simulator", help="Manage simulator certificates")
    sim_sub = sim_p.add_subparsers(dest="sim_command")
    sim_sub.required = True

    sim_sub.add_parser("list", help="List booted simulators")

    p_sim_cert = sim_sub.add_parser("install-cert", help="Install CA cert in booted simulators")
    p_sim_cert.add_argument("--udid", help="Target a specific simulator by UDID")
```

- [ ] **Step 3: Update the dispatch at the bottom of `main()`**

Replace the existing dispatch block:

```python
    if args.command == "mock":
        {"add": cmd_mock_add, "list": cmd_mock_list, "remove": cmd_mock_remove}[args.mock_command](args)
    else:
        {"start": cmd_start, "stop": cmd_stop, "status": cmd_status,
         "list": cmd_list, "get": cmd_get, "clear": cmd_clear}[args.command](args)
```

With:

```python
    if args.command == "mock":
        {"add": cmd_mock_add, "list": cmd_mock_list, "remove": cmd_mock_remove}[args.mock_command](args)
    elif args.command == "simulator":
        {"list": cmd_simulator_list, "install-cert": cmd_simulator_install_cert}[args.sim_command](args)
    else:
        {"start": cmd_start, "stop": cmd_stop, "status": cmd_status,
         "list": cmd_list, "get": cmd_get, "clear": cmd_clear}[args.command](args)
```

- [ ] **Step 4: Verify help works**

```bash
./ni simulator --help
```

Expected:
```
usage: ni simulator [-h] {list,install-cert} ...

positional arguments:
  {list,install-cert}
    list               List booted simulators
    install-cert       Install CA cert in booted simulators
```

```bash
./ni simulator install-cert --help
```

Expected:
```
usage: ni simulator install-cert [-h] [--udid UDID]

optional arguments:
  --udid UDID  Target a specific simulator by UDID
```

- [ ] **Step 5: Smoke test against real simulator**

```bash
./ni simulator list
```

Expected: prints one line per booted simulator, e.g.:
```
5A74B7E3-C2C0-444A-81B9-4348AC4A399A  iPhone 16e  (com.apple.CoreSimulator.SimRuntime.iOS-18-6)
```

```bash
./ni simulator install-cert
```

Expected: prints `✓ iPhone 16e (5A74B7E3-...)` for each booted simulator.

- [ ] **Step 6: Commit**

```bash
git add ni
git commit -m "feat: ni simulator list + install-cert subcommands"
```
