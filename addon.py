import json
import sys
from pathlib import Path

from mitmproxy import http

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import init_db, write_capture
from lib.mocks import match_mock


class InterceptorAddon:
    def __init__(self):
        init_db()

    def request(self, flow: http.HTTPFlow):
        url = f"{flow.request.pretty_host}{flow.request.path}"
        rule = match_mock(url)
        if rule:
            body = Path(rule["file"]).read_bytes()
            flow.response = http.Response.make(
                rule["status"],
                body,
                {"Content-Type": "application/json"},
            )
            flow.metadata["ni_mocked"] = True

    def response(self, flow: http.HTTPFlow):
        is_mocked = flow.metadata.get("ni_mocked", False)
        try:
            write_capture(
                method=flow.request.method,
                host=flow.request.pretty_host,
                path=flow.request.path,
                status_code=flow.response.status_code,
                request_headers=json.dumps(dict(flow.request.headers)),
                request_body=flow.request.get_text(strict=False),
                response_headers=json.dumps(dict(flow.response.headers)),
                response_body=flow.response.get_text(strict=False),
                is_mocked=is_mocked,
            )
        except Exception as e:
            print(f"[ni] capture error: {e}", file=sys.stderr)


addons = [InterceptorAddon()]
