#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-LINK 残留扫描器：安装/卸载前后各跑一次，逐项列出痕迹"""
import subprocess, glob, os, json
from pathlib import Path


def sh(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def exists(p):
    return Path(p).exists()


CHECKS = []


def add(group, name, fn):
    CHECKS.append((group, name, fn))


# --- 进程 ---
add("进程", "ai-link-daemon", lambda: sh("pgrep -f ai-link-dae[m]on.py | wc -l"))
add("进程", "sing-box", lambda: sh("pidof sing-box | wc -w"))

# --- nft / 路由 ---
add("内核", "nft table inet ai_link", lambda: "存在" if sh("nft list table inet ai_link 2>/dev/null | wc -l") not in ("0", "") else "无")
add("内核", "nft table ip ai_link", lambda: "存在" if sh("nft list table ip ai_link 2>/dev/null | wc -l") not in ("0", "") else "无")
add("内核", "ip rule fwmark 0x162", lambda: sh("ip rule show | grep -c 'fwmark 0x162'"))
add("内核", "ip -6 rule fwmark 0x162", lambda: sh("ip -6 rule show | grep -c 'fwmark 0x162'"))
add("内核", "ip rule pref 8999", lambda: sh("ip rule show | grep -c 'pref 8999'"))
add("内核", "route table 162", lambda: sh("ip route show table 162 2>/dev/null | wc -l"))
add("内核", "fc00::/18 路由", lambda: sh("ip -6 route show 2>/dev/null | grep -c 'fc00::/18'"))
add("内核", "nf_conntrack_tcp_be_liberal", lambda: sh("sysctl -n net.netfilter.nf_conntrack_tcp_be_liberal 2>/dev/null") or "n/a")

# --- 文件 ---
for p in (
    "/etc/init.d/ai-link",
    "/etc/config/ai-link",
    "/etc/ai-link",
    "/usr/share/ai-link",
    "/usr/bin/ai-link",
    "/www/luci-static/resources/view/ai-link",
    "/usr/share/luci/menu.d/luci-app-ai-link.json",
    "/usr/share/rpcd/acl.d/luci-app-ai-link.json",
    "/lib/upgrade/keep.d/ai-link",
    "/var/run/ai-link",
):
    add("文件", p, (lambda pp: (lambda: "存在" if exists(pp) else "无"))(p))

add("文件", "/etc/rc.d/*ai-link*", lambda: str(len(glob.glob("/etc/rc.d/*ai-link*"))))
add("文件", "/tmp/ai-link*", lambda: str(len(glob.glob("/tmp/ai-link*"))))
add("文件", "/tmp/dnsmasq*.d/ai-link-*.conf", lambda: str(len(glob.glob("/tmp/dnsmasq*.d/ai-link-*.conf"))))

# --- 配置 / 包 ---
add("配置", "uci ai-link 段", lambda: sh("uci show ai-link 2>/dev/null | wc -l"))
add("配置", "apk 包记录", lambda: sh("apk list --installed 2>/dev/null | grep -c ai-link") or "0")
add("配置", "crontab 提及", lambda: sh("crontab -l 2>/dev/null | grep -c ai-link") or "0")
add("配置", "sysctl.d 提及", lambda: sh("grep -rl 'conntrack_tcp_be_liberal' /etc/sysctl.d/ /etc/sysctl.conf 2>/dev/null | wc -l"))

rows = []
for group, name, fn in CHECKS:
    try:
        val = fn()
    except Exception as e:
        val = f"ERR:{e}"
    rows.append((group, name, str(val)))

print(f"{'分组':<6}{'检查项':<46}{'结果'}")
print("-" * 78)
for g, n, v in rows:
    print(f"{g:<6}{n:<46}{v}")

# 汇总：哪些是"有痕迹"
print("\n--- 判定 ---")
dirty = [f"{g}/{n}={v}" for g, n, v in rows if v not in ("0", "无", "n/a", "0\n")]
print("痕迹项数:", len(dirty))
for d in dirty:
    print("  ·", d)
