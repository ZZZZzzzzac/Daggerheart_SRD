import json
import base64
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from preview_server import PreviewHandler


def test_local_preview_serves_editor_api():
    server = ThreadingHTTPServer(("127.0.0.1", 0), PreviewHandler)
    server.admin_password = "test-password"
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/SRD/api/page-list"
        try:
            urlopen(url, timeout=3)
            raise AssertionError("管理接口不应允许匿名访问")
        except HTTPError as error:
            assert error.code == 401
            assert error.headers["WWW-Authenticate"].startswith("Basic ")

        request = Request(url, headers={
            "Authorization": "Basic " + base64.b64encode(b"admin:test-password").decode("ascii"),
        })
        with urlopen(request, timeout=3) as response:
            assert response.status == 200
            assert response.headers.get_content_type() == "application/json"
            payload = json.load(response)
        assert payload["pages"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_local_preview_protects_admin_pages_but_not_reader_home():
    server = ThreadingHTTPServer(("127.0.0.1", 0), PreviewHandler)
    server.admin_password = "test-password"
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base_url + "/SRD/", timeout=3) as response:
            assert response.status == 200
        for path in ("/SRD/edit/", "/SRD/admin/"):
            try:
                urlopen(base_url + path, timeout=3)
                raise AssertionError(f"{path} 不应允许匿名访问")
            except HTTPError as error:
                assert error.code == 401
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
