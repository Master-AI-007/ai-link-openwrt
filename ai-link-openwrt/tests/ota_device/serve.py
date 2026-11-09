# -*- coding: utf-8 -*-
"""给真机用的临时 HTTP 服务：把 dist/ 目录挂到 0.0.0.0:8000，路由器按 URL 取清单和包。

用法：
  python serve.py --root dist --port 8000 --bind 0.0.0.0

说明：
  * 只读，不做任何写入；日志实时打印请求，便于确认设备真的来拉过包
  * Windows 首次监听可能弹出防火墙提示，需要允许「专用网络」入站
"""
import argparse
import http.server
import os
import socket
import sys
from pathlib import Path


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, directory=None, **kw):
        super().__init__(*a, directory=directory, **kw)

    def log_message(self, fmt, *args):
        sys.stdout.write("  %s %s\n" % (self.address_string(), fmt % args))
        sys.stdout.flush()


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.10.10.77", 22))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent / "dist"))
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--bind", default="0.0.0.0")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not (root / "version.json").is_file():
        raise SystemExit(f"{root} 下没有 version.json，先跑 build_test_pkg.py")

    os.chdir(root)
    httpd = http.server.ThreadingHTTPServer((args.bind, args.port), lambda *a, **k: Handler(*a, directory=str(root), **k))
    print(f"服务目录 {root}")
    print(f"设备应访问 http://{lan_ip()}:{args.port}/version.json")
    print("Ctrl+C 结束\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
