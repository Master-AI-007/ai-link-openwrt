#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比 AI-LINK 配置状态：输出每个状态文件的 md5 + UCI 关键键值"""
import hashlib, json, subprocess
from pathlib import Path

C = Path("/etc/ai-link")
FILES = ("nodes.json", "subscriptions.json", "homelink.json", "shunt.json",
         "dns_filters.json", "dns_rewrite.json", "ops_settings.json", "auto_nodes.json")
KEYS = ("enabled", "entry_bypass", "gh_mirror", "ipv6_proxy", "block_quic",
        "game_udp_direct", "auto_mute_conflicts", "panel_port", "panel_secret")


def uci(k):
    r = subprocess.run(["uci", "-q", "get", f"ai-link.global.{k}"], capture_output=True, text=True)
    return (r.stdout or "").strip() or "-"


out = {}
for f in FILES:
    p = C / f
    out[f] = hashlib.md5(p.read_bytes()).hexdigest()[:12] if p.is_file() else "MISSING"
for k in KEYS:
    out["uci." + k] = uci(k)
print(json.dumps(out, ensure_ascii=False, indent=0))
