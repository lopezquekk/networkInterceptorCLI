# Simulator Certificate Install — Design Spec

**Date:** 2026-06-01  
**Status:** Approved

---

## Goal

Add `ni simulator` subcommands so the CA certificate can be installed into iOS Simulators, enabling HTTPS interception for simulator traffic without browser-style cert errors.

---

## Context

iOS Simulators on macOS automatically inherit the system proxy settings (HTTP_PROXY / HTTPS_PROXY), so no proxy configuration is needed. The only missing piece is trusting the mitmproxy CA cert inside the simulator's keychain.

---

## New CLI Commands

| Command | Description |
|---|---|
| `ni simulator list` | List all currently booted simulators (name, UDID, OS version) |
| `ni simulator install-cert [--udid UDID]` | Install CA cert into all booted simulators, or one specific simulator |

---

## New File: `lib/simulator.py`

Single responsibility: interact with `xcrun simctl` to list simulators and install the cert.

### `list_booted() → list[dict]`

Calls:
```bash
xcrun simctl list devices booted --json
```

Parses the JSON output and returns a flat list of dicts:
```python
[{"name": "iPhone 16e", "udid": "5A74B7E3-...", "os": "iOS 18.6"}]
```

### `install_cert(udid: str) → bool`

Calls:
```bash
xcrun simctl keychain <udid> add-root-cert ~/.networkinterceptor/mitmproxy-ca-cert.pem
```

Returns `True` on success, `False` on failure (logs error to stderr, does not raise).

---

## CLI Changes: `ni`

Add a `simulator` subparser group alongside `mock`:

```
ni simulator list
ni simulator install-cert [--udid UDID]
```

- `install-cert` with no `--udid`: installs into all booted simulators, reports per-simulator success/failure
- `install-cert --udid UDID`: installs into that specific simulator only; fails with clear message if UDID not found among booted devices

---

## Error Handling

| Scenario | Behavior |
|---|---|
| `CERT_PATH` doesn't exist | Print "Run `ni start` first to generate the CA cert." and exit 1 |
| No simulators booted | Print "No simulators currently booted." and exit 0 |
| `xcrun` not found (no Xcode) | Print clear message: "`xcrun` not found — is Xcode installed?" and exit 1 |
| One simulator fails, others succeed | Log per-simulator error, continue with rest, exit 1 at end |
| `--udid` not found among booted | Print "Simulator UDID not found among booted devices." and exit 1 |

---

## File Changes

```
lib/simulator.py     ← new
ni                   ← add simulator subparser + two command functions
```

No changes to `lib/proxy.py`, `lib/db.py`, `lib/mocks.py`, or `addon.py`.

---

## Dependencies

- `xcrun simctl` — bundled with Xcode, pre-installed on macOS dev machines
- `json` — stdlib
- `lib/paths.py` — for `CERT_PATH`
