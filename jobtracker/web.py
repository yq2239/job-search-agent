from __future__ import annotations

import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from .core import JobStore, VALID_STATUSES
from .web_ui import DASHBOARD_HTML

MAX_BODY_BYTES = 8192


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def make_handler(store: JobStore) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "JobTracker/1.0"

        def end_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
            )
            super().end_headers()

        def log_message(self, format: str, *args: object) -> None:
            print(f"[jobtracker] {self.address_string()} {format % args}")

        def reply(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def reply_json(self, status: int, value: object) -> None:
            self.reply(status, json_bytes(value), "application/json; charset=utf-8")

        def read_json(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("request body is empty or too large")
            value = json.loads(self.rfile.read(length))
            if not isinstance(value, dict):
                raise ValueError("request body must be a JSON object")
            return value

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/":
                body = DASHBOARD_HTML.encode("utf-8")
                self.reply(HTTPStatus.OK, body, "text/html; charset=utf-8")
                return
            if path == "/api/jobs":
                jobs = sorted(store.list(), key=lambda job: int(job.get("fit_score", 0)), reverse=True)
                self.reply_json(HTTPStatus.OK, {"jobs": jobs, "statuses": sorted(VALID_STATUSES)})
                return
            self.reply_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_PATCH(self) -> None:
            self.mutate("status")

        def do_POST(self) -> None:
            self.mutate("notes")

        def mutate(self, action: str) -> None:
            parts = [unquote(part) for part in urlsplit(self.path).path.split("/") if part]
            if len(parts) != 4 or parts[:2] != ["api", "jobs"] or parts[3] != action:
                self.reply_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            self.apply_mutation(parts[2], action)

        def apply_mutation(self, job_id: str, action: str) -> None:
            try:
                payload = self.read_json()
                job = self.update_job(job_id, action, payload)
                self.reply_json(HTTPStatus.OK, {"job": job})
            except KeyError:
                self.reply_json(HTTPStatus.NOT_FOUND, {"error": "job not found"})
            except (ValueError, json.JSONDecodeError) as exc:
                self.reply_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def update_job(self, job_id: str, action: str, payload: dict[str, object]) -> dict:
            if action == "status":
                status = str(payload.get("status", ""))
                note = str(payload.get("note", ""))
                return store.set_status(job_id, status, note)
            return store.add_note(job_id, str(payload.get("body", "")))

    return DashboardHandler


def create_server(store: JobStore, host: str, port: int) -> ThreadingHTTPServer:
    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return ThreadingHTTPServer((host, port), make_handler(store))


def run_server(store: JobStore, host: str, port: int, open_browser: bool = True) -> None:
    server = create_server(store, host, port)
    actual_port = server.server_address[1]
    url = f"http://{host}:{actual_port}/"
    print(f"Smart Job Tracker: {url}")
    if open_browser:
        threading.Timer(0.2, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
