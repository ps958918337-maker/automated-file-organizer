"""
web/server.py
A small web dashboard for the File Organizer, built using ONLY the
Python standard library (http.server). No Flask/FastAPI dependency.

Serves:
  GET  /                 -> dashboard HTML
  POST /api/organize     -> run organize() on a given directory
  POST /api/undo         -> undo the last run
  GET  /api/history      -> list past runs
"""

import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

sys.path.append(str(Path(__file__).parent.parent))
from organizer import organize, undo_last_run, list_runs

STATIC_DIR = Path(__file__).parent / "static"


class OrganizerHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    # -- Routing -----------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            index_file = STATIC_DIR / "index.html"
            self._send_html(index_file.read_text(encoding="utf-8"))

        elif parsed.path == "/api/history":
            try:
                runs = list_runs()
                self._send_json({"ok": True, "runs": runs})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=500)

        else:
            self._send_json({"ok": False, "error": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/organize":
            try:
                payload = self._read_json_body()
                directory = payload.get("directory", "").strip()
                dry_run = bool(payload.get("dry_run", False))
                detect_duplicates = bool(payload.get("detect_duplicates", True))

                if not directory:
                    self._send_json(
                        {"ok": False, "error": "Directory is required"}, status=400
                    )
                    return

                result = organize(
                    directory, dry_run=dry_run, detect_duplicates=detect_duplicates
                )
                self._send_json({"ok": True, "result": result})

            except FileNotFoundError as e:
                self._send_json({"ok": False, "error": str(e)}, status=404)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=500)

        elif parsed.path == "/api/undo":
            try:
                result = undo_last_run()
                self._send_json({"ok": True, "result": result})
            except FileNotFoundError as e:
                self._send_json({"ok": False, "error": str(e)}, status=404)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=500)

        else:
            self._send_json({"ok": False, "error": "Not found"}, status=404)

    # Quiet down default logging clutter
    def log_message(self, format, *args):
        print(f"[server] {self.address_string()} - {format % args}")


def run_server(port: int = 8000):
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, OrganizerHandler)
    print(f"\nFile Organizer dashboard running at http://localhost:{port}")
    print("Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
