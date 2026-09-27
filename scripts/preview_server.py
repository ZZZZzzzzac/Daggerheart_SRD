"""Build and serve the complete local site under its production /SRD/ path."""

from __future__ import annotations

import argparse
import base64
import hmac
import subprocess
import sys
import threading
import webbrowser
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
    parser.add_argument("--open", action="store_true", help="启动后在默认浏览器打开术语编辑器")
    parser.add_argument("--admin-password", default="", help="可选的本地管理密码；默认免登录")
    args = parser.parse_args()
    if not args.no_build:
        result = subprocess.run([sys.executable, str(PROJECT_DIR / "scripts" / "build_srd.py")], cwd=PROJECT_DIR)
        if result.returncode != 0:
            return result.returncode
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler)
    except OSError as error:
        print(f"无法启动本地服务器（端口 {args.port}）：{error}", file=sys.stderr)
        print(f"如果已经启动，请打开 http://127.0.0.1:{args.port}/SRD/", file=sys.stderr)
        return 1
    server.admin_password = args.admin_password
    print(f"本地完整站点: http://127.0.0.1:{args.port}/SRD/")
    print("管理账号: admin（使用指定密码）" if server.admin_password else "本地管理页面免登录，用户名和密码无需填写。")
    print("按 Ctrl+C 停止")
    if args.open:
        threading.Thread(target=webbrowser.open, args=(f"http://127.0.0.1:{args.port}/SRD/edit/?path=glossary",), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
