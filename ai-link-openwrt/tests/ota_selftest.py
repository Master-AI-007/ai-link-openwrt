# -*- coding: utf-8 -*-
"""把 _update_script_body() 真实生成的 shell 脚本导出，供 sh -n 语法校验。"""
import json, os, sys, tempfile
from pathlib import Path

from _paths import DAEMON, app_version
APP_VER = app_version()
lines = DAEMON.read_text(encoding="utf-8").splitlines()


def grab(start, end):
    s = next(i for i, l in enumerate(lines) if l.startswith(start))
    e = next(i for i, l in enumerate(lines) if i > s and l.startswith(end))
    return "\n".join(lines[s:e])


src = grab(f'APP_VERSION = "{APP_VER}"', "def start_plugin_update")
ns = {
    "re": __import__("re"), "time": __import__("time"), "json": json,
    "ssl": __import__("ssl"), "urllib": __import__("urllib"),
    "Path": Path, "RUN_DIR": Path("/var/run/ai-link"),
    "CONF_DIR": Path("/etc/ai-link"),
    "get_ops_settings": lambda c=None: {"gh_mirror": "https://gh-proxy.com/"},
    "_uci_get_str": lambda k, d="": "",
}
exec(compile(src, "<ota>", "exec"), ns)

plan = {
    "target": "1.0.2",
    "current": "1.0.1",
    "md5": "d41d8cd98f00b204e9800998ecf8427e",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "size": 1234567,
    "package_urls": [
        "https://ai-link-official.pages.dev/pkg/AI-LINK-v1.0.2.tar.gz",
        "https://github.com/Master-AI-007/ai-link-openwrt/releases/download/v1.0.2/AI-LINK-v1.0.2.tar.gz",
        "https://gh-proxy.com/https://github.com/Master-AI-007/ai-link-openwrt/releases/download/v1.0.2/AI-LINK-v1.0.2.tar.gz",
    ],
}
body = ns["_update_script_body"](plan)
out = Path(os.environ.get("OTA_SCRIPT_OUT") or (Path(tempfile.mkdtemp()) / "ota_script_gen.sh"))
out.write_text(body, encoding="utf-8", newline="\n")
print(f"written {out} ({len(body.encode('utf-8'))} bytes, {body.count(chr(10))} lines)")

# 顺带验证版本比较
pv, nv = ns["parse_app_version"], ns["is_version_newer"]
cases = [
    ("1.0.2", "1.0.1", True), ("1.0.1", "1.0.1", False), ("1.0.0", "1.0.1", False),
    ("1.1.0", "1.0.9", True), ("v2.0.0", "1.9.9", True),
    ("1.0.1-beta1", "1.0.1", False), ("1.0.1", "1.0.1-beta1", True),
]
print("\n版本比较用例:")
bad = 0
for a, b, exp in cases:
    got = nv(a, b)
    ok = got == exp
    bad += 0 if ok else 1
    print(f"  is_newer({a!r:14}, {b!r:12}) = {str(got):5} 期望 {str(exp):5} {'✓' if ok else '✗'}")
print(f"\n失败 {bad} 条")
sys.exit(1 if bad else 0)
