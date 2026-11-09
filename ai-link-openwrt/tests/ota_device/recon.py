# -*- coding: utf-8 -*-
"""真机现状侦察：版本、服务、包管理、Python、磁盘、UCI 配置。

用法：设置 AI_LINK_DEVICE_PASS 后 python recon.py
"""
import sys

import devssh

CMDS = [
    ("系统", "cat /etc/openwrt_release | head -3; uname -r"),
    ("AI-LINK 版本", "cat /etc/ai-link/version 2>/dev/null || echo '<缺 /etc/ai-link/version>'"),
    ("包状态", "apk info -e luci-app-ai-link 2>/dev/null; opkg list-installed 2>/dev/null | grep -i ai-link || echo '<opkg 无 ai-link>'"),
    ("主程序", "ls -l /usr/share/ai-link/ai-link-daemon.py /usr/share/ai-link/webui/index.html /usr/bin/ai-link 2>&1"),
    ("LuCI 视图", "ls -l /www/luci-static/resources/view/ai-link/overview.js 2>&1"),
    ("init", "ls -l /etc/init.d/ai-link 2>&1; /etc/init.d/ai-link svc_state 2>&1 | head -3"),
    ("进程", "ps w | grep -c 'ai-link-dae[m]on'; pgrep -f 'ai-link-dae[m]on' | head -3; pgrep -f '[s]ing-box' | head -3"),
    ("端口", "netstat -tlnp 2>/dev/null | grep -E ':(9099|7890|7891|7893|7874)' || echo '<无监听>'"),
    ("Python", "command -v python3 && python3 -V; command -v openssl; command -v curl; command -v wget"),
    ("磁盘", "df -h / /tmp /root 2>/dev/null | sed -n '1,5p'"),
    ("UCI ai-link", "uci show ai-link 2>&1 | head -30"),
    ("清单地址", "uci get ai-link.global.update_manifest_url 2>&1"),
    ("配置目录", "ls /etc/ai-link/ 2>&1 | head -30"),
    ("运行时", "ls -l /var/run/ai-link/ 2>&1 | head -10"),
    ("备份", "ls -l /root/ai-link-final-backup/ 2>&1 | head -5"),
    ("OPKG/APK 源", "grep -m3 -h 'src\\|url' /etc/opkg/distfeeds.conf /etc/apk/repositories 2>/dev/null | head -3"),
]


def main():
    c = devssh.connect()
    for name, cmd in CMDS:
        rc, o, e = devssh.run(c, cmd, timeout=60)
        body = (o + e).strip()
        print(f"\n### {name}")
        print(body if body else "<空>")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
