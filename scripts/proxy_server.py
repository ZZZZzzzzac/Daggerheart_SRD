"""proxy_server.py — 服务端编辑器代理
提供端点:
    GET  /api/page-list    — 列出 src/pages/ 下的 .md 文件
    GET  /api/get-file     — 读取指定文件内容  (?path=src/pages/...)
    POST /api/save         — 保存文件并重建站点  {path, content}

零依赖，纯 Python 标准库。
认证由 nginx auth_basic 处理，本服务不检查密码。
"""

import json
import time
import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
PAGES_DIR = os.path.join(PROJECT_DIR, 'src', 'pages')
BUILD_SCRIPT = os.path.join(SCRIPT_DIR, 'build_srd.py')

LISTEN_HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("PROXY_PORT", "5000"))


def list_pages():
    """列出 src/pages/ 下所有 .md 文件（相对 PROJECT_DIR 的路径）"""
    pages = []
    for dirpath, dirnames, filenames in os.walk(PAGES_DIR):
        for fn in filenames:
            if fn.endswith('.md'):
                rel = os.path.relpath(os.path.join(dirpath, fn), PROJECT_DIR)
                pages.append(rel.replace('\\', '/'))
    return sorted(pages)


def _resolve_path(path):
    """安全路径解析，返回规范化后的完整路径，非法路径返回 None"""
    if not path.startswith('src/pages/'):
        return None
    full = os.path.normpath(os.path.join(PROJECT_DIR, path))
    if not full.startswith(PAGES_DIR):
        return None
    return full


def read_file(path):
    """读取 src/pages/ 下的文件内容"""
    full = _resolve_path(path)
    if not full or not os.path.exists(full):
        return None
    with open(full, 'r', encoding='utf-8') as f:
        return f.read()


def save_and_build(path, content):
    """保存文件 → 重建站点 → git 备份"""
    full = _resolve_path(path)
    if not full:
        return False, "只允许编辑 src/pages/ 下的文件"

    if not content.strip():
        return False, "内容不能为空"

    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)

    # 允许 Hugo 写入 public/（nginx 以 www-data 运行，public/ 可能被其持有）
    public_dir = os.path.join(PROJECT_DIR, 'public')
    if os.path.isdir(public_dir):
        try:
            subprocess.run(['sudo', 'chown', '-R', 'ubuntu:ubuntu', public_dir],
                           capture_output=True, timeout=10)
        except Exception:
            pass

    try:
        result = subprocess.run(
            ['python3', BUILD_SCRIPT],
            cwd=PROJECT_DIR,
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return False, f"构建失败:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "构建超时（超过 120 秒）"
    except Exception as e:
        return False, f"构建异常: {e}"
    finally:
        # 恢复 public/ 权限供 nginx 读取
        if os.path.isdir(public_dir):
            try:
                subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', public_dir],
                               capture_output=True, timeout=10)
            except Exception:
                pass

    # Git 备份（非阻塞，失败不影响）
    try:
        subprocess.run(['git', 'add', path], cwd=PROJECT_DIR,
                       capture_output=True, timeout=10)
        subprocess.run(['git', 'commit', '-m', f'编辑: {path}'],
                       cwd=PROJECT_DIR, capture_output=True, timeout=10)
        subprocess.run(['git', 'push'], cwd=PROJECT_DIR,
                       capture_output=True, timeout=30)
    except Exception:
        pass

    return True, "保存成功，站点已更新"


class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/api/page-list':
            try:
                pages = list_pages()
                self._json(200, {"pages": pages})
            except Exception as e:
                self._json(500, {"error": str(e)})

        elif parsed.path == '/api/get-file':
            params = parse_qs(parsed.query)
            path = params.get('path', [None])[0]
            if not path:
                self._json(400, {"error": "缺少 path 参数"})
                return
            try:
                content = read_file(path)
                if content is None:
                    self._json(404, {"error": f"文件不存在或不可访问: {path}"})
                else:
                    self._json(200, {"content": content})
            except Exception as e:
                self._json(500, {"error": str(e)})

        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != '/api/save':
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

        try:
            ok, msg = save_and_build(file_path, content)
            self._json(200 if ok else 400,
                       {"message": msg} if ok else {"error": msg})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
    server = HTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    print(f"编辑器代理已启动: http://{LISTEN_HOST}:{LISTEN_PORT}")
    print(f"  GET  /api/page-list")
    print(f"  GET  /api/get-file?path=...")
    print(f"  POST /api/save")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n代理已停止")
        server.server_close()
