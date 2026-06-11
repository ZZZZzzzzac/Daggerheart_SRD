"""proxy_server.py — GitHub API 代理，持服务端 token 代前端提交 PR。
用法:
    GH_TOKEN=github_pat_xxx python3 scripts/proxy_server.py
    # 或
    export GH_TOKEN=github_pat_xxx && python3 scripts/proxy_server.py

零依赖，纯 Python 标准库。
"""

import json
import time
import urllib.request
import urllib.error
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

REPO = "ZZZZzzzzac/Daggerheart_SRD"
BRANCH = "master"
TOKEN = os.environ.get("GH_TOKEN")
API_BASE = f"https://api.github.com/repos/{REPO}"
LISTEN_HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("PROXY_PORT", "5000"))


def gh_request(method, path, data=None):
    """调用 GitHub REST API，返回解析后的 JSON"""
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} {path} → {e.code}: {err_body}")


def create_pr(file_path, content, description):
    """完整的 GitHub PR 创建流程：分支 → blob → tree → commit → PR"""
    branch_name = f"edit-{_slugify(file_path)}-{int(time.time())}"

    ref = gh_request("GET", f"/git/refs/heads/{BRANCH}")
    master_sha = ref["object"]["sha"]

    gh_request("POST", "/git/refs", {
        "ref": f"refs/heads/{branch_name}",
        "sha": master_sha,
    })

    blob = gh_request("POST", "/git/blobs", {
        "content": content,
        "encoding": "utf-8",
    })

    commit = gh_request("GET", f"/git/commits/{master_sha}")

    tree = gh_request("POST", "/git/trees", {
        "base_tree": commit["tree"]["sha"],
        "tree": [{
            "path": file_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob["sha"],
        }],
    })

    new_commit = gh_request("POST", "/git/commits", {
        "message": f"编辑: {file_path}",
        "tree": tree["sha"],
        "parents": [master_sha],
    })

    gh_request("PATCH", f"/git/refs/heads/{branch_name}", {
        "sha": new_commit["sha"],
        "force": True,
    })

    pr = gh_request("POST", "/pulls", {
        "title": f"编辑: {file_path}",
        "head": branch_name,
        "base": BRANCH,
        "body": description,
    })

    return pr["html_url"]


def _slugify(path):
    return path.replace("/", "-").replace(".md", "")


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/submit-pr":
            self._json(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
        except Exception:
            self._json(400, {"error": "无效的 JSON"})
            return

        file_path = data.get("path", "")
        content = data.get("content", "")
        description = data.get("description", "编辑")

        if not file_path.startswith("src/pages/"):
            self._json(403, {"error": "只允许编辑 src/pages/ 下的文件"})
            return

        if not content.strip():
            self._json(400, {"error": "内容不能为空"})
            return

        try:
            pr_url = create_pr(file_path, content, description)
            self._json(200, {"html_url": pr_url})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {args[0]}")


if __name__ == "__main__":
    if not TOKEN:
        print("错误: 请设置 GH_TOKEN 环境变量")
        print("用法: GH_TOKEN=github_pat_xxx python3 scripts/proxy_server.py")
        exit(1)

    server = HTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    print(f"代理已启动: http://{LISTEN_HOST}:{LISTEN_PORT}/api/submit-pr")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n代理已停止")
        server.server_close()
