# -*- coding: utf-8 -*-
"""PWD-1 A/B 验证：把 pkg16(补丁前) 与 pkg17(补丁后) 的真实鉴权函数切出来跑同一组用例。

用法: python pwd_ab.py
"""
import hashlib, json, os, subprocess, tempfile, time
from pathlib import Path

from _paths import DAEMON

# 补丁前基线：v1.0.0 时代的 pkg16 快照（可用 AI_LINK_BASELINE_ROOT 覆盖）
BASE = Path(os.environ.get("AI_LINK_BASELINE_ROOT", r"F:\2026-10-24-06-35-48"))
TARGETS = [
    ("pkg16 (补丁前 v1.0.0-4)", BASE / "pkg16" / "ai-link-openwrt" / "root" / "usr" / "share" / "ai-link" / "ai-link-daemon.py"),
    ("当前源码 (PWD-1~5 补丁后)", DAEMON),
]


def slice_func(lines, start_marker, end_marker):
    s = next(i for i, l in enumerate(lines) if l.startswith(start_marker))
    e = next(i for i, l in enumerate(lines) if i > s and l.startswith(end_marker))
    return "\n".join(lines[s:e])


def build(src: Path):
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        consts = slice_func(lines, "def _get_or_create_initial_secret", "def get_uci_panel_secret() -> str:")
    except StopIteration:
        consts = ("PANEL_PWD_DEFAULT = 'ai-link-2026'\nPANEL_PWD_SENTINEL = '__custom__'\n"
                  "def _uci_secret_is_placeholder(v):\n    return False\n")
    body = slice_func(lines, "def _load_panel_auth", "def is_bypass_active")
    tok_method = slice_func(lines, "    def _is_request_authenticated(self) -> bool:",
                            "    def _auth_ok(self) -> bool:")

    store = {"panel_secret": ""}
    ns = {
        "hashlib": hashlib, "json": json, "os": os, "subprocess": subprocess, "time": time, "_chmod_0600_safe": lambda p: None,
        "Path": Path, "CONF_DIR": Path(tempfile.mkdtemp()),
        "get_uci_panel_secret": lambda: store["panel_secret"],
        "PANEL_PWD_DEFAULT": "ai-link-2026",
    }
    exec(compile(consts + "\n" + body, "<slice>", "exec"), ns)

    probe_ns = dict(ns)
    exec(compile("class _Probe:\n" + tok_method, "<probe>", "exec"), probe_ns)
    return ns, store, probe_ns["_Probe"]


def run_one(src):
    ns, store, Probe = build(src)
    verify, update, load_auth, conf = ns["_verify_panel_password"], ns["_update_panel_password"], ns["_load_panel_auth"], ns["CONF_DIR"]
    R = {}

    # A 出厂默认
    store["panel_secret"] = "ai-link-2026"
    init_pw = ns["_get_or_create_initial_secret"](conf) if "_get_or_create_initial_secret" in ns else "ai-link-2026"
    R["A 设备初始密码可登录且公开默认口令已禁用"] = verify(init_pw, conf)[0] and (not verify("ai-link-2026", conf)[0] if init_pw != "ai-link-2026" else True)
    R["A 弱默认 admin 可登录"] = verify("admin", conf)[0]

    # B 用户改密后 UCI 被污染成 sha256:hash（self-test 场景）
    REAL = "MyRealPass!2026"
    update(REAL, conf)
    auth = json.loads((conf / "panel_auth.json").read_text(encoding="utf-8"))
    poisoned = "sha256:" + auth["hash"][:24]
    store["panel_secret"] = poisoned
    R["B 真实密码可登录"] = verify(REAL, conf)[0]
    R["B 哈希串当密码可登录"] = verify(poisoned, conf)[0]

    # C 哈希当 Bearer 令牌
    def token_ok(tok):
        p = Probe()
        p.headers = {"X-AI-Link-Token": tok}
        return p._is_request_authenticated()
    R["C 哈希串当令牌可绕过登录"] = token_ok(poisoned)
    real_tok = verify(REAL, conf)[1]
    R["C 真实会话令牌可用"] = token_ok(real_tok) if real_tok else False

    # D auth 文件丢失后的兜底
    (conf / "panel_auth.json").unlink()
    (conf / "panel_token").unlink(missing_ok=True)
    load_auth(conf)
    init_pw2 = ns["_get_or_create_initial_secret"](conf) if "_get_or_create_initial_secret" in ns else "ai-link-2026"
    R["D 丢失后设备初始密码可救急"] = verify(init_pw2, conf)[0]
    R["D 丢失后哈希串可登录"] = verify(poisoned, conf)[0]
    return R, poisoned


print("=" * 80)
print(" PWD-1 A/B 验证：面板密码「哈希当凭据」缺陷，补丁前 vs 补丁后")
print("=" * 80)
allres = {}
for label, src in TARGETS:
    if not src.is_file():
        print(f"  !! 找不到 {src}")
        continue
    res, pois = run_one(src)
    allres[label] = res
    print(f"\n【{label}】")
    print(f"  UCI panel_secret = {pois}")
    for k, v in res.items():
        print(f"    {k:34} -> {'✓ 是' if v else '✗ 否'}")

if len(allres) == 2:
    a, b = list(allres.values())
    print("\n" + "=" * 80)
    print(" 逐项对比")
    print("=" * 80)
    for key in a:
        before, after = a.get(key), b.get(key)
        if before == after:
            tag = "— 无变化"
        elif before is True and after is False:
            tag = "✓ 已修复（应当拒绝）"
        elif before is False and after is True:
            tag = "✓ 已修复（应当放行）"
        else:
            tag = "! 需人工复核"
        print(f"  {key:34} 前={str(before):5} 后={str(after):5}  {tag}")
