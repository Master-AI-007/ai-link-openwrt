# -*- coding: utf-8 -*-
"""OTA 端到端功能测试：本地起 HTTP 服务提供 version.json，跑真实的 check_plugin_update。"""
import hashlib, json, os, socket, subprocess, sys, tempfile, threading, time
import urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from _paths import DAEMON, app_version
APP_VER = app_version()
# 测试清单要「比当前版本新」才有升级可测，所以目标版本按当前版本 +1 patch 推算
_p = [int(x) for x in APP_VER.split(".")]
NEXT_VER = f"{_p[0]}.{_p[1]}.{_p[2] + 1}"
lines = DAEMON.read_text(encoding="utf-8").splitlines()


def grab(a, b):
    s = next(i for i, l in enumerate(lines) if l.startswith(a))
    e = next(i for i, l in enumerate(lines) if i > s and l.startswith(b))
    return "\n".join(lines[s:e])


WORK = Path(tempfile.mkdtemp())
MANIFEST = {
    "schema": 1,
    "channel": "stable",
    "latest": NEXT_VER,
    "release_date": "2026-11-02",
    "notes_url": f"https://example.test/changelog#v{NEXT_VER}",
    "highlights": ["新增 XXX 功能", "修复 YYY 问题"],
    "changelog": [{"version": NEXT_VER, "date": "2026-11-02", "items": ["a", "b"]}],
    "packages": {
        "full": {
            "url": f"https://github.com/Master-AI-007/ai-link-openwrt/releases/download/v{NEXT_VER}/AI-LINK-v{NEXT_VER}.tar.gz",
            "mirrors": [f"https://example.test/pkg/AI-LINK-v{NEXT_VER}.tar.gz"],
            "size": 1234567,
            "md5": "0123456789abcdef0123456789abcdef",
            "sha256": "f" * 64,
        }
    },
}
(WORK / "version.json").write_text(json.dumps(MANIFEST, ensure_ascii=False), encoding="utf-8")


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/version.json"):
            b = (WORK / "version.json").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{port}"

src = grab(f'APP_VERSION = "{APP_VER}"', "def acknowledge_update_result")
ns = {
    "re": __import__("re"), "time": time, "json": json, "ssl": __import__("ssl"),
    "urllib": __import__("urllib"), "Path": Path,
    "RUN_DIR": WORK / "run", "CONF_DIR": WORK / "conf",
    "get_ops_settings": lambda c=None: {"gh_mirror": ""},
    "_uci_get_str": lambda k, d="": "",
    "_UPDATE_CHECK_MEMO": {"ts": 0.0, "data": None},
    "_UPDATE_CHECK_TTL": 300,
    "UPDATE_DIR": WORK / "run" / "update",
    "UPDATE_PROGRESS_LOG": WORK / "run" / "update" / "progress.log",
    "UPDATE_PLAN_JSON": WORK / "run" / "update" / "plan.json",
    "UPDATE_SCRIPT": WORK / "run" / "update" / "run_update.sh",
    "UPDATE_STATE_JSON": WORK / "run" / "update" / "state.json",
}
exec(compile(src, "<ota>", "exec"), ns)
# exec 里的常量赋值会覆盖上面的初始值，必须在 exec 之后再指向本地服务
ns["UPDATE_MANIFEST_PRIMARY"] = f"{BASE}/version.json"
ns["UPDATE_MANIFEST_GITHUB"] = f"{BASE}/nope-raw.json"
chk = ns["check_plugin_update"]
start = ns["start_plugin_update"]

print("=" * 74)
print(" OTA 端到端测试")
print("=" * 74)
fails = []


def expect(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


r = chk(WORK / "conf", force=True)
expect("清单拉取成功", r.get("ok") is True, str(r.get("error") or ""))
expect("current 读自 APP_VERSION", r.get("current") == APP_VER, r.get("current"))
expect("latest 解析正确", r.get("latest") == NEXT_VER, r.get("latest"))
expect("has_update = True", r.get("has_update") is True)
expect("release_date 透传", r.get("release_date") == "2026-11-02")
expect("notes_url 透传", r.get("notes_url", "").endswith(f"#v{NEXT_VER}"))
expect("highlights 透传 2 条", len(r.get("highlights") or []) == 2)
expect("changelog 透传", len(r.get("changelog") or []) == 1)
pkg = r.get("package") or {}
expect("package.md5 透传", pkg.get("md5") == MANIFEST["packages"]["full"]["md5"])
expect("package.sha256 透传", pkg.get("sha256") == "f" * 64)
expect("package.size 透传", pkg.get("size") == 1234567)
expect("source 记录了命中地址", BASE in (r.get("source") or ""), r.get("source", ""))

# 缓存：第二次非 force 应命中缓存
r2 = chk(WORK / "conf", force=False)
expect("5 分钟内命中缓存", r2.get("cached") is True)
r3 = chk(WORK / "conf", force=True)
expect("force=1 绕过缓存", r3.get("cached") is False)

# 包地址展开：GitHub 主地址应追加 gh_mirror 前缀
urls = ns["_update_package_urls"](pkg, WORK / "conf")
expect("多源展开 >= 2", len(urls) >= 2, f"{len(urls)} 个")

# 已是最新时拒绝升级
ns["APP_VERSION"] = NEXT_VER
r4 = start(WORK / "conf", force=True)
expect("已最新时拒绝升级", r4.get("ok") is False and r4.get("error") == "already_latest", str(r4.get("error")))
ns["APP_VERSION"] = APP_VER

# 缺 MD5 时拒绝升级
old = json.loads((WORK / "version.json").read_text(encoding="utf-8"))
bad = json.loads(json.dumps(old))
bad["packages"]["full"]["md5"] = ""
(WORK / "version.json").write_text(json.dumps(bad), encoding="utf-8")
r5 = start(WORK / "conf", force=True)
expect("清单缺 MD5 时拒绝升级", r5.get("ok") is False and r5.get("error") == "no_checksum", str(r5.get("error")))
(WORK / "version.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")

# 清单不可达
ns["UPDATE_MANIFEST_PRIMARY"] = "http://127.0.0.1:1/version.json"
ns["UPDATE_MANIFEST_GITHUB"] = "http://127.0.0.1:1/raw.json"
ns["_UPDATE_CHECK_MEMO"] = {"ts": 0.0, "data": None}
r6 = chk(WORK / "conf", force=True)
expect("清单不可达时 ok=False", r6.get("ok") is False and r6.get("error") == "manifest_unreachable")
expect("失败时返回 sources_tried", len(r6.get("sources_tried") or []) >= 1, f"{len(r6.get('sources_tried') or [])} 条")

srv.shutdown()
print("\n" + "=" * 74)
print(f" 失败 {len(fails)} 项")
print("=" * 74)
sys.exit(1 if fails else 0)
