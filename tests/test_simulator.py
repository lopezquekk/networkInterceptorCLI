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
