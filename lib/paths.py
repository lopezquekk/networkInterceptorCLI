from pathlib import Path

DATA_DIR = Path.home() / ".networkinterceptor"
DB_PATH = DATA_DIR / "captures.db"
MOCKS_PATH = DATA_DIR / "mocks.json"
CERT_PATH = DATA_DIR / "mitmproxy-ca-cert.pem"
PID_PATH = DATA_DIR / "proxy.pid"
