"""Build and serve the complete local site under its production /SRD/ path."""

from __future__ import annotations

import argparse
import base64
import hmac
import secrets
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from .proxy_server import ProxyHandler
except ImportError:  # Running as ``python scripts/preview_server.py``.
    from proxy_server import ProxyHandler


PROJECT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = PROJECT_DIR / "public"


class PreviewHandler(ProxyHandler, SimpleHTTPRequestHandler):
    def _requires_auth(self) -> bool:
        path = urlparse(self.path).path.rstrip("/") + "/"
        if path.startswith(("/SRD/edit/", "/SRD/admin/")):
            return True
        if path.startswith("/SRD/api/") and path != "/SRD/api/feedback/":
            return True
        return False

    def _authorized(self) -> bool:
        password = getattr(self.server, "admin_password", "")
        if not password:
            return True
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
            username, supplied_password = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(username, "admin") and hmac.compare_digest(supplied_password, password)

    def _require_authorization(self) -> bool:
        if not self._requires_auth() or self._authorized():
            return False
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Daggerheart SRD Admin", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return True

    def _dispatch_api(self, method):
        original_path = self.path
        self.path = self.path[len("/SRD") :]
        try:
            method(self)
        finally:
            self.path = original_path

    def do_GET(self):
        if self._require_authorization():
            return
        if urlparse(self.path).path.startswith("/SRD/api/"):
            self._dispatch_api(ProxyHandler.do_GET)
            return
        if urlparse(self.path).path == "/":
            self.send_response(302)
            self.send_header("Location", "/SRD/")
            self.end_headers()
            return
        SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self._require_authorization():
            return
        if urlparse(self.path).path.startswith("/SRD/api/"):
            self._dispatch_api(ProxyHandler.do_POST)
            return
        self.send_error(404, "File not found")

    def translate_path(self, request_path):
        path = unquote(urlparse(request_path).path)
        if path == "/SRD":
            path = "/"
        elif path.startswith("/SRD/"):
            path = path[len("/SRD/") :]
        else:
            path = "__not_found__"
        candidate = (PUBLIC_DIR / path.lstrip("/")).resolve()
        try:
            candidate.relative_to(PUBLIC_DIR.resolve())
        except ValueError:
            return str(PUBLIC_DIR / "__not_found__")
        return str(candidate)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--admin-password", help="本地编辑器和反馈后台的密码；不填则每次随机生成")
    args = parser.parse_args()
    if not args.no_build:
        result = subprocess.run([sys.executable, str(PROJECT_DIR / "scripts" / "build_srd.py")], cwd=PROJECT_DIR)
        if result.returncode != 0:
            return result.returncode
    server = ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler)
    server.admin_password = args.admin_password or secrets.token_urlsafe(9)
    print(f"本地完整站点: http://127.0.0.1:{args.port}/SRD/")
    print("管理账号: admin")
    print(f"本次管理密码: {server.admin_password}")
    print("阅读和读者勘误公开；编辑器、反馈后台及管理接口需要上述密码。")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
