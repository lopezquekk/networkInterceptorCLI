# Network Interceptor — Design Spec

**Date:** 2026-05-31  
**Status:** Approved

---

## Goal

A lightweight CLI tool (`ni`) that intercepts system-wide HTTP/HTTPS traffic using a MITM certificate (exactly like Charles Proxy) and lets you mock endpoint responses by mapping URL patterns to local JSON files. Designed to be used by Claude via the Bash tool for network verification tasks.

---

## Architecture

Two processes, one SQLite database:

```
┌─────────────────────────────────────────────────────┐
│                   System Proxy                       │
│   (HTTP_PROXY / HTTPS_PROXY → localhost:8080)        │
└───────────────────┬─────────────────────────────────┘
                    │
          ┌─────────▼──────────┐
          │   mitmproxy daemon  │  mitmdump -s addon.py -p 8080
          │   + MITM addon      │  (runs in background)
          └─────────┬──────────┘
                    │ writes every req/resp
          ┌─────────▼──────────┐
          │    SQLite DB        │  ~/.networkinterceptor/captures.db
          └─────────┬──────────┘
                    │ reads
          ┌─────────▼──────────┐
          │     ni  CLI         │  ni list / ni get / ni mock / ni clear
          └────────────────────┘
                    ▲
                Claude (Bash tool)
```

---

## Components

### 1. Certificate & System Proxy (`ni start` / `ni stop`)

**On `ni start`:**
- Generate a CA certificate at `~/.networkinterceptor/ca.pem` (once; reused across sessions)
- Install it into the macOS Keychain as a trusted root CA via `security add-trusted-cert`
- Set system HTTP and HTTPS proxy to `localhost:8080` via `networksetup`
- Launch mitmproxy as a background process using the addon

**On `ni stop`:**
- Remove system proxy settings via `networksetup`
- Terminate the mitmproxy background process
- System proxy is always restored, even if mitmproxy crashed

No changes to apps, no localhost routing. All traffic goes through the real network, intercepted transparently via certificate trust — identical to Charles Proxy behavior.

---

### 2. mitmproxy Addon (`addon.py`)

A single Python file loaded by mitmproxy with two responsibilities:

**Capture:** Every request and response is written to SQLite.

**Mock:** Before forwarding a request, the addon checks the URL against enabled mock rules in `~/.networkinterceptor/mocks.json`. If a rule matches, the file content is returned immediately as the response without hitting the real server. The capture is written to SQLite with `is_mocked = true`.

---

### 3. CLI (`ni`)

| Command | Description |
|---|---|
| `ni start` | Start proxy, install cert, set system proxy |
| `ni stop` | Stop proxy, restore system proxy settings |
| `ni status` | Show proxy status and active mock count |
| `ni list [--url <pattern>]` | List captured requests |
| `ni get <id>` | Show full request + response detail |
| `ni clear` | Wipe all captured requests |
| `ni mock add <url-pattern> <file.json>` | Map a URL pattern to a mock response file |
| `ni mock list` | Show all mock rules |
| `ni mock remove <id>` | Delete a mock rule |

---

## Data Model

### SQLite — `captures` table

```sql
CREATE TABLE captures (
    id           TEXT PRIMARY KEY,
    timestamp    TEXT NOT NULL,
    method       TEXT NOT NULL,
    host         TEXT NOT NULL,
    path         TEXT NOT NULL,
    status_code  INTEGER,
    request_headers  TEXT,
    request_body     TEXT,
    response_headers TEXT,
    response_body    TEXT,
    is_mocked    INTEGER DEFAULT 0
);
```

### Mock rules — `~/.networkinterceptor/mocks.json`

```json
[
  {
    "id": "abc123",
    "pattern": "*/api/users*",
    "file": "/path/to/users.json",
    "status": 200,
    "enabled": true
  }
]
```

Pattern matching uses `fnmatch` (shell-style globs), consistent with Charles Proxy URL pattern behavior.

---

## Data Flow

```
App → system proxy → mitmproxy (port 8080)
         └─ addon checks mock rules (fnmatch on full URL)
              ├─ match found → return mock file content
              │                write to SQLite (is_mocked=1)
              └─ no match → forward to real server
                            write req+resp to SQLite (is_mocked=0)
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| CA cert already in Keychain | Skip install silently |
| Port 8080 already in use | Fail fast with clear message |
| Mock file not found at `ni mock add` time | Reject immediately, don't add rule |
| mitmproxy crashes | `ni stop` still restores system proxy |
| SQLite write failure | Log to stderr, skip capture, don't crash proxy |

All SQLite writes use transactions — no partial captures.

---

## File Layout

```
~/.networkinterceptor/
├── ca.pem            # generated CA certificate (reused across sessions)
├── captures.db       # SQLite database
└── mocks.json        # mock rules

networkInterceptor/   # this repo
├── ni                # CLI entry point (Python script)
├── addon.py          # mitmproxy addon
└── requirements.txt  # mitmproxy
```

---

## Dependencies

- `mitmproxy` — proxy engine, certificate generation, HTTPS MITM
- `sqlite3` — stdlib, no extra install
- `fnmatch` — stdlib, pattern matching for mock rules
- macOS `security` and `networksetup` CLI tools (pre-installed)
