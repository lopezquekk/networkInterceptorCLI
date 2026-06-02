#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def cmd_start(args):
    from lib.proxy import start
    start()


def cmd_stop(args):
    from lib.proxy import stop
    stop()


def cmd_status(args):
    from lib.proxy import status
    status()


def cmd_list(args):
    from lib.db import init_db, list_captures
    init_db()
    captures = list_captures(url_pattern=args.url)
    if not captures:
        print("No captures.")
        return
    for c in captures:
        mocked = " [MOCKED]" if c["is_mocked"] else ""
        print(f"{c['id']}  {c['timestamp']}  {c['method']} {c['host']}{c['path']}  {c['status_code']}{mocked}")


def cmd_get(args):
    from lib.db import get_capture, init_db
    init_db()
    c = get_capture(args.id)
    if not c:
        print(f"No capture found: {args.id}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(c, indent=2))


def cmd_clear(args):
    from lib.db import clear_captures, init_db
    init_db()
    clear_captures()
    print("Captures cleared.")


def cmd_mock_add(args):
    from lib.mocks import add_mock
    try:
        rule = add_mock(args.pattern, args.file, status=args.status)
        print(f"Added [{rule['id']}]  {rule['pattern']} → {rule['file']}  HTTP {rule['status']}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_mock_list(args):
    from lib.mocks import list_mocks
    rules = list_mocks()
    if not rules:
        print("No mock rules.")
        return
    for r in rules:
        state = "on " if r.get("enabled") else "off"
        print(f"[{r['id']}]  {state}  {r['pattern']} → {r['file']}  HTTP {r['status']}")


def cmd_mock_remove(args):
    from lib.mocks import remove_mock
    try:
        remove_mock(args.id)
        print(f"Removed mock rule: {args.id}")
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(prog="ni", description="Network Interceptor")
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    sub.add_parser("start", help="Start proxy and set system proxy")
    sub.add_parser("stop", help="Stop proxy and restore system proxy")
    sub.add_parser("status", help="Show proxy status")

    p_list = sub.add_parser("list", help="List captured requests")
    p_list.add_argument("--url", metavar="PATTERN", help="Filter by URL substring")

    p_get = sub.add_parser("get", help="Show full capture detail")
    p_get.add_argument("id", help="Capture ID")

    sub.add_parser("clear", help="Delete all captures")

    mock_p = sub.add_parser("mock", help="Manage mock rules")
    mock_sub = mock_p.add_subparsers(dest="mock_command")
    mock_sub.required = True

    p_add = mock_sub.add_parser("add", help="Add a mock rule")
    p_add.add_argument("pattern", help="URL glob pattern, e.g. '*/api/users*'")
    p_add.add_argument("file", help="Path to JSON response file")
    p_add.add_argument("--status", type=int, default=200, metavar="CODE", help="HTTP status code (default: 200)")

    mock_sub.add_parser("list", help="List all mock rules")

    p_rm = mock_sub.add_parser("remove", help="Remove a mock rule")
    p_rm.add_argument("id", help="Rule ID")

    args = parser.parse_args()

    if args.command == "mock":
        {"add": cmd_mock_add, "list": cmd_mock_list, "remove": cmd_mock_remove}[args.mock_command](args)
    else:
        {"start": cmd_start, "stop": cmd_stop, "status": cmd_status,
         "list": cmd_list, "get": cmd_get, "clear": cmd_clear}[args.command](args)


if __name__ == "__main__":
    main()
