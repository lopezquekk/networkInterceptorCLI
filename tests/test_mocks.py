import json
import pytest
from pathlib import Path
from lib import mocks


@pytest.fixture(autouse=True)
def isolated_mocks(tmp_path, monkeypatch):
    monkeypatch.setattr(mocks, "MOCKS_PATH", tmp_path / "mocks.json")


@pytest.fixture
def mock_file(tmp_path):
    f = tmp_path / "response.json"
    f.write_text('{"ok": true}')
    return str(f)


def test_add_mock_returns_rule(mock_file):
    rule = mocks.add_mock("*/api/users*", mock_file)
    assert rule["pattern"] == "*/api/users*"
    assert rule["file"] == mock_file
    assert rule["status"] == 200
    assert rule["enabled"] is True
    assert len(rule["id"]) == 8


def test_add_mock_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        mocks.add_mock("*/api*", "/does/not/exist.json")


def test_add_mock_custom_status(mock_file):
    rule = mocks.add_mock("*/api*", mock_file, status=404)
    assert rule["status"] == 404


def test_list_mocks_empty():
    assert mocks.list_mocks() == []


def test_list_mocks_returns_all(mock_file):
    mocks.add_mock("*/api/a*", mock_file)
    mocks.add_mock("*/api/b*", mock_file)
    assert len(mocks.list_mocks()) == 2


def test_remove_mock(mock_file):
    rule = mocks.add_mock("*/api*", mock_file)
    mocks.remove_mock(rule["id"])
    assert mocks.list_mocks() == []


def test_remove_mock_missing_raises():
    with pytest.raises(KeyError):
        mocks.remove_mock("doesnotexist")


def test_match_mock_returns_rule(mock_file):
    mocks.add_mock("*/api/users*", mock_file)
    matched = mocks.match_mock("api.example.com/api/users")
    assert matched is not None
    assert matched["pattern"] == "*/api/users*"


def test_match_mock_no_match(mock_file):
    mocks.add_mock("*/api/users*", mock_file)
    assert mocks.match_mock("api.example.com/api/products") is None


def test_match_mock_skips_disabled(mock_file):
    rule = mocks.add_mock("*/api/users*", mock_file)
    all_rules = mocks.list_mocks()
    all_rules[0]["enabled"] = False
    mocks._save(all_rules)
    assert mocks.match_mock("api.example.com/api/users") is None


def test_rules_persist_across_calls(mock_file):
    mocks.add_mock("*/x*", mock_file)
    loaded = mocks.list_mocks()
    assert len(loaded) == 1
    assert loaded[0]["pattern"] == "*/x*"
