import json
import uuid
from fnmatch import fnmatch
from pathlib import Path

from .paths import MOCKS_PATH


def _load():
    MOCKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MOCKS_PATH.exists():
        return []
    return json.loads(MOCKS_PATH.read_text())


def _save(rules):
    MOCKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MOCKS_PATH.write_text(json.dumps(rules, indent=2))


def add_mock(pattern, file_path, status=200):
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Mock file not found: {path}")
    rules = _load()
    rule = {
        "id": str(uuid.uuid4())[:8],
        "pattern": pattern,
        "file": str(path),
        "status": status,
        "enabled": True,
    }
    rules.append(rule)
    _save(rules)
    return rule


def list_mocks():
    return _load()


def remove_mock(rule_id):
    rules = _load()
    new_rules = [r for r in rules if r["id"] != rule_id]
    if len(new_rules) == len(rules):
        raise KeyError(f"Mock rule not found: {rule_id}")
    _save(new_rules)


def match_mock(url):
    for rule in _load():
        if rule.get("enabled") and fnmatch(url, rule["pattern"]):
            return rule
    return None
