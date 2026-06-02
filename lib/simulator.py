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
