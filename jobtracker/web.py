from __future__ import annotations

import ipaddress
import json
import re
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .core import JobStore, VALID_STATUSES, load_json
from .web_ui import DASHBOARD_HTML

MAX_BODY_BYTES = 8192
SAFE_IMAGE_DATA_URL = re.compile(
    r"data:image/(?:png|x-icon|vnd\.microsoft\.icon);base64,[A-Za-z0-9+/=]+\Z"
)


def safe_company_icon_url(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if len(value) <= 200_000 and SAFE_IMAGE_DATA_URL.fullmatch(value):
        return value
    parsed = urlsplit(value)
    host = parsed.hostname
    if parsed.scheme != "https" or not host or "." not in host:
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return value
    return None


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def company_icon_urls(companies_path: Path | None) -> dict[str, str]:
    """Build same-purpose favicon URLs from configured public careers sites."""
    if companies_path is None:
        return {}
    try:
        companies = load_json(companies_path).get("companies", [])
    except (OSError, json.JSONDecodeError):
        return {}
    icons: dict[str, str] = {}
    for company in companies if isinstance(companies, list) else []:
        if not isinstance(company, dict):
            continue
        name = company.get("name")
        careers_url = company.get("careers_url")
        if not isinstance(name, str) or not name.strip():
            continue
        configured_icon = safe_company_icon_url(company.get("icon_url"))
        if configured_icon:
            icons[name] = configured_icon
            continue
        if not isinstance(careers_url, str):
            continue
        parsed = urlsplit(careers_url)
        host = parsed.hostname
        if parsed.scheme != "https" or not host or "." not in host:
            continue
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            continue
        icons[name] = f"https://{host}/favicon.ico"
    return icons


def make_handler(store: JobStore, companies_path: Path | None = None) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "JobTracker/1.0"

        def end_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
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
                self.reply_json(
                    HTTPStatus.OK,
                    {
                        "jobs": jobs,
                        "statuses": sorted(VALID_STATUSES),
                        "company_icons": company_icon_urls(companies_path),
                    },
                )
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


def create_server(
    store: JobStore,
    host: str,
    port: int,
    companies_path: Path | None = None,
) -> ThreadingHTTPServer:
    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return ThreadingHTTPServer((host, port), make_handler(store, companies_path))


def run_server(
    store: JobStore,
    host: str,
    port: int,
    open_browser: bool = True,
    companies_path: Path | None = None,
) -> None:
    server = create_server(store, host, port, companies_path)
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
