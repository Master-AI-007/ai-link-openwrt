# -*- coding: utf-8 -*-
"""v1.0.2 安全与回滚修复的回归测试（纯本地，不需要真机）。

覆盖：
  SEC-1  end_headers 不再给未登录客户端下发 ailink_token Cookie
  SEC-2  /api/status 的脱敏函数 + 缓存键包含鉴权状态
  SEC-3  homelink 脱敏时 uri 里的明文凭据也要遮掉
  CORE-1 BusyBox pgrep -x 失效，init.d 改用 pidof 探针
  RB-1   回滚收尾会主动 restore_proxy

用法：python test_security_fixes.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import ROOT, DAEMON, app_version  # noqa: E402

INITD = ROOT / "root/etc/init.d/ai-link"
SRC = DAEMON.read_text(encoding="utf-8")
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def slice_func(text, start_marker, end_marker):
    lines = text.splitlines()
    s = next(i for i, l in enumerate(lines) if l.startswith(start_marker))
    e = next(i for i, l in enumerate(lines) if i > s and l.startswith(end_marker))
    return "\n".join(lines[s:e])


print("=" * 74)
print(" v1.0.2 安全与回滚修复回归")
print("=" * 74)

def strip_comments(text):
    """去掉注释行，避免注释里提到旧代码就误判成「还在」。"""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        out.append(line.split("  #", 1)[0] if "  #" in line else line)
    return "\n".join(out)


# ---------------- SEC-1 ----------------
print("\n[SEC-1] 首页不再下发令牌 Cookie")
mb = re.search(r"    def end_headers\(self\):(.*?)\n    def ", SRC, re.S)
body = strip_comments(mb.group(1) if mb else "")
check("end_headers 里没有 Set-Cookie", "Set-Cookie" not in body, body.strip()[:60].replace("\n", " "))
check("end_headers 里没有 ailink_token", "ailink_token" not in body)
check("end_headers 仍设置 no-store", "no-store" in body)

# ---------------- SEC-2 ----------------
print("\n[SEC-2] /api/status 脱敏")
ns = {"re": re, "copy": __import__("copy")}
exec(compile(slice_func(SRC, "def _mask_status_secrets", "def build_status_api_response"),
             "<mask>", "exec"), ns)
mask = ns["_mask_status_secrets"]

sample = {
    "ok": True,
    "homelink": {"nodes": [
        {"name": "回家 01", "protocol": "hysteria2", "password": "ailink_home_2026",
         "uuid": "a891f02b-2026-4f88-9b1c-8899aabbccdd",
         "private_key": "PRIVKEY", "uri": "hysteria2://ailink_home_2026@x.y:20443/?sni=a#n"},
        {"name": "回家 02", "protocol": "vless-reality", "uuid": "11111111-2222-3333-4444-555555555555",
         "private_key": "PK2", "uri": "vless://11111111-2222-3333-4444-555555555555@x.y:18443?a=1#n"},
    ]},
    "subscriptions": [
        {"id": "sub_main", "url": "https://x.pages.dev/sub?token=4c52013555faa98fb3c8e2c58ffdedd6"},
        {"id": "plain", "url": "https://y.example/sub"},
    ],
    "version": "1.0.2",
}
import copy as _copy
orig = _copy.deepcopy(sample)
out = mask(sample)

blob = str(out)
check("password 被遮", "ailink_home_2026" not in blob)
check("uuid 被遮", "a891f02b-2026-4f88-9b1c-8899aabbccdd" not in blob and "11111111-2222" not in blob)
check("private_key 被遮", "PRIVKEY" not in blob and "PK2" not in blob)
check("uri 里的密码被遮", "hysteria2://***@" in blob, [n.get("uri") for n in out["homelink"]["nodes"]][0][:40])
check("uri 里的 uuid 被遮", "vless://***@" in blob)
check("订阅 token 被遮", "4c52013555faa98fb3c8e2c58ffdedd6" not in blob and "token=***" in blob)
check("无 token 的订阅地址保持原样", out["subscriptions"][1]["url"] == "https://y.example/sub")
check("非敏感字段不动", out.get("version") == "1.0.2" and out["homelink"]["nodes"][0]["name"] == "回家 01")
check("不修改入参（deepcopy）", sample == orig)

# 缓存键包含鉴权状态
wk = re.search(r"    def _make_wire_key\(self\):(.*?)return None", SRC, re.S)
wk_body = wk.group(1) if wk else ""
check("wire key 含鉴权状态", "self._auth_ok()" in wk_body)

# 路由确实调用了脱敏
check("/api/status 路由调用脱敏", "status_payload = _mask_status_secrets(status_payload)" in SRC)

# ---------------- SEC-3 ----------------
print("\n[SEC-3] homelink 脱敏含 uri")
sec3_hits = len(re.findall(r'://\[\^@/\]\+@', SRC)) + len(re.findall(r'"://\*\*\*@"', SRC)) + len(re.findall(r':=.*?://\[\^@/\]', SRC))
_uri_sub_expr = 're.sub(r"://[^@/]+@", "://***@"'
check("两处脱敏都处理 uri", SRC.count(_uri_sub_expr) >= 2, f"{SRC.count(_uri_sub_expr)} 处")

# ---------------- CORE-1 ----------------
print("\n[CORE-1] BusyBox pgrep -x 探针")
initd = INITD.read_text(encoding="utf-8")
initd_code = strip_comments(initd).replace("\n\t", "\n")
check("init.d 已无 pgrep -x sing-box", "pgrep -x sing-box" not in initd_code)
check("init.d 定义了 singbox_alive", "singbox_alive()" in initd)
check("singbox_alive 使用 pidof", "pidof sing-box" in initd)
check("svc_state 用 singbox_alive", re.search(r"singbox_alive && core_up=1", initd) is not None)
check("reload 兜底用 singbox_alive", re.search(r"! singbox_alive; then", initd) is not None)

# ---------------- RB-1 ----------------
print("\n[RB-1] 回滚收尾重挂透明代理")
ns2 = {"re": re, "time": __import__("time"), "json": __import__("json"),
       "ssl": __import__("ssl"), "urllib": __import__("urllib"), "Path": Path,
       "RUN_DIR": Path("/var/run/ai-link"), "CONF_DIR": Path("/etc/ai-link"),
       "get_ops_settings": lambda c=None: {"gh_mirror": ""},
       "_uci_get_str": lambda k, d="": ""}
v = app_version()
exec(compile(slice_func(SRC, f'APP_VERSION = "{v}"', "def start_plugin_update"), "<ota>", "exec"), ns2)
script = ns2["_update_script_body"]({
    "target": "9.9.9", "current": v,
    "md5": "a" * 32, "sha256": "b" * 64, "size": 100,
    "package_urls": ["https://x/y.tar.gz"],
})
rb = script.split("# ---------- 8. 回滚 ----------")[-1]
check("回滚段调用 restore_proxy", "restore_proxy" in rb)

print("\n" + "=" * 74)
fails = [r for r in results if not r[1]]
print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
for n, ok, d in results:
    if not ok:
        print(f"   ✗ {n}  {d}")
print("=" * 74)
sys.exit(1 if fails else 0)
