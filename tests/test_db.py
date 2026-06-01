import pytest
from pathlib import Path
from lib import db
from lib.paths import DB_PATH


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_init_db_creates_table(tmp_path, monkeypatch):
    import sqlite3
    test_path = tmp_path / "init_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_path)
    db.init_db()
    conn = sqlite3.connect(test_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='captures'"
    ).fetchall()
    assert tables, "captures table should exist"


def test_write_capture_returns_id():
    row_id = db.write_capture(
        method="GET", host="api.example.com", path="/users",
        status_code=200,
        request_headers="{}", request_body="",
        response_headers="{}", response_body='{"ok": true}',
    )
    assert row_id and len(row_id) == 8


def test_list_captures_returns_all():
    db.write_capture("GET", "a.com", "/x", 200, "{}", "", "{}", "body1")
    db.write_capture("POST", "b.com", "/y", 201, "{}", "data", "{}", "body2")
    captures = db.list_captures()
    assert len(captures) == 2


def test_list_captures_filters_by_url():
    db.write_capture("GET", "api.example.com", "/users", 200, "{}", "", "{}", "[]")
    db.write_capture("GET", "other.com", "/stuff", 200, "{}", "", "{}", "ok")
    captures = db.list_captures(url_pattern="example.com")
    assert len(captures) == 1
    assert captures[0]["host"] == "api.example.com"


def test_get_capture_returns_full_record():
    row_id = db.write_capture(
        "GET", "example.com", "/ping", 200, "{}", "", "{}", "pong"
    )
    c = db.get_capture(row_id)
    assert c is not None
    assert c["method"] == "GET"
    assert c["host"] == "example.com"
    assert c["response_body"] == "pong"


def test_get_capture_missing_returns_none():
    assert db.get_capture("doesnotexist") is None


def test_clear_captures_deletes_all():
    db.write_capture("GET", "x.com", "/", 200, "{}", "", "{}", "ok")
    db.clear_captures()
    assert db.list_captures() == []


def test_is_mocked_flag_stored():
    row_id = db.write_capture(
        "GET", "api.com", "/mock", 200, "{}", "", "{}", "mocked",
        is_mocked=True,
    )
    c = db.get_capture(row_id)
    assert c["is_mocked"] == 1
