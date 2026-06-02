import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from .paths import CERT_PATH, DATA_DIR, PID_PATH

PORT = 8080
ADDON_PATH = Path(__file__).parent.parent / "addon.py"

def _find_mitmdump() -> str:
    # 1. Same bin dir as the running Python interpreter
    candidate = Path(sys.executable).parent / "mitmdump"
    if candidate.exists():
        return str(candidate)
    # 2. macOS user-local install: ~/Library/Python/X.Y/bin/ (pip install --user)
    ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    candidate = Path.home() / f"Library/Python/{ver}/bin/mitmdump"
    if candidate.exists():
        return str(candidate)
    # 3. PATH
    import shutil as _shutil
    found = _shutil.which("mitmdump")
    if found:
        return found
    return "mitmdump"  # let Popen raise a clear FileNotFoundError

MITMDUMP = _find_mitmdump()


def _network_services():
    result = subprocess.run(
        ["networksetup", "-listallnetworkservices"],
        capture_output=True, text=True,
    )
    lines = result.stdout.strip().splitlines()[1:]  # skip header line
    return [l for l in lines if not l.startswith("*")]


def _set_system_proxy(enable):
    for svc in _network_services():
        if enable:
            subprocess.run(["networksetup", "-setwebproxy", svc, "127.0.0.1", str(PORT)], check=False)
            subprocess.run(["networksetup", "-setsecurewebproxy", svc, "127.0.0.1", str(PORT)], check=False)
            subprocess.run(["networksetup", "-setwebproxystate", svc, "on"], check=False)
            subprocess.run(["networksetup", "-setsecurewebproxystate", svc, "on"], check=False)
        else:
            subprocess.run(["networksetup", "-setwebproxystate", svc, "off"], check=False)
            subprocess.run(["networksetup", "-setsecurewebproxystate", svc, "off"], check=False)


def _install_cert():
    if not CERT_PATH.exists():
        print("[ni] Warning: cert not found yet, run `ni start` again after first boot.", file=sys.stderr)
        return
    result = subprocess.run(
        [
            "security", "add-trusted-cert",
            "-d", "-r", "trustRoot",
            "-k", str(Path.home() / "Library/Keychains/login.keychain-db"),
            str(CERT_PATH),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"[ni] Warning: cert install failed: {result.stderr.decode().strip()}", file=sys.stderr)
    else:
        print(f"[ni] CA cert installed in login keychain.")


def is_running():
    if not PID_PATH.exists():
        return False
    pid = int(PID_PATH.read_text().strip())
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        PID_PATH.unlink(missing_ok=True)
        return False


def start():
    if is_running():
        print("Proxy is already running.")
        return

    s = socket.socket()
    try:
        s.bind(("127.0.0.1", PORT))
    except OSError:
        print(f"Error: port {PORT} is already in use.", file=sys.stderr)
        sys.exit(1)
    finally:
        s.close()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [
            MITMDUMP,
            "-s", str(ADDON_PATH),
            "-p", str(PORT),
            "--set", f"confdir={DATA_DIR}",
            "--quiet",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PID_PATH.write_text(str(proc.pid))

    # Wait for mitmproxy to generate its CA cert
    for _ in range(10):
        if CERT_PATH.exists():
            break
        time.sleep(0.5)

    _install_cert()
    _set_system_proxy(True)
    print(f"Proxy started on port {PORT} (PID {proc.pid}).")
    print(f"CA cert: {CERT_PATH}")


def stop():
    _set_system_proxy(False)
    if not PID_PATH.exists():
        print("Proxy is not running.")
        return
    pid = int(PID_PATH.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Proxy stopped (PID {pid}).")
    except ProcessLookupError:
        print("Proxy process was already gone.")
    PID_PATH.unlink(missing_ok=True)


def status():
    from .mocks import list_mocks
    running = is_running()
    active_mocks = [m for m in list_mocks() if m.get("enabled")]
    print(f"Proxy:        {'running' if running else 'stopped'}")
    if running:
        pid = PID_PATH.read_text().strip()
        print(f"PID:          {pid}")
        print(f"Port:         {PORT}")
    print(f"Active mocks: {len(active_mocks)}")
