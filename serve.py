"""REPLAY web server — serves the static board + API endpoints.

Usage:
  python3 serve.py              # default port 8080
  PORT=3000 python3 serve.py    # custom port
"""
import http.server
import json
import os
import sys

PORT = int(os.environ.get("PORT", "8080"))
BOARD_DIR = os.path.join(os.path.dirname(__file__), "rift_board")
STORE = os.environ.get("REPLAY_STORE", ".replay_store")


class ReplayHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BOARD_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/data":
            self._serve_data()
        elif self.path == "/":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def _serve_data(self):
        data = {"runs": [], "incidents": [], "worlds": [], "replays": [], "fixes": [], "exports": []}
        import glob as g
        for kind in data:
            pattern = os.path.join(STORE, kind, "*.json")
            for path in sorted(g.glob(pattern)):
                try:
                    with open(path) as f:
                        data[kind].append(json.load(f))
                except Exception:
                    pass
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        if "/api/" not in str(args[0]):
            super().log_message(format, *args)


if __name__ == "__main__":
    with http.server.HTTPServer(("", PORT), ReplayHandler) as httpd:
        print(f"REPLAY serving on http://localhost:{PORT}")
        print(f"  Landing:  http://localhost:{PORT}/")
        print(f"  Dashboard: http://localhost:{PORT}/dashboard.html")
        print(f"  API:      http://localhost:{PORT}/api/data")
        httpd.serve_forever()
