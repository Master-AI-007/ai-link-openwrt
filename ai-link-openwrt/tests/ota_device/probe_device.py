# -*- coding: utf-8 -*-
"""设备侧自检与 OTA 相关现状（不改变任何配置）。

用法：设置 AI_LINK_DEVICE_PASS 后 python probe_device.py
"""
import sys

import devssh


def main():
    c = devssh.connect()
    cmds = [
        ("svc_state", "/etc/init.d/ai-link svc_state"),
        ("ai-link probe（内置自检）", "ai-link probe 2>&1 | tail -25"),
        ("当前版本", "ai-link status 2>&1 | head -12"),
        ("清单候选", "grep -n '^UPDATE_MANIFEST_' /usr/share/ai-link/ai-link-daemon.py; "
                    "echo '-- uci 覆盖 --'; uci get ai-link.global.update_manifest_url 2>&1; "
                    "echo '-- gh_mirror --'; uci get ai-link.global.gh_mirror 2>&1"),
        ("外网可达性", "for u in https://ai-link-official.pages.dev/version.json "
                    "https://ghfast.top/https://raw.githubusercontent.com/Master-AI-007/ai-link-openwrt/main/version.json "
                    "https://raw.githubusercontent.com/Master-AI-007/ai-link-openwrt/main/version.json; do "
                    "echo -n \"$u -> \"; curl -s --noproxy '*' -m 12 -o /dev/null -w '%{http_code}\\n' \"$u\"; done"),
        ("本地 API", "curl -s --noproxy '*' -m 8 http://127.0.0.1:9099/api/system/version | head -c 600; echo"),
        ("更新检查", "ai-link update 2>&1 | tail -20"),
    ]
    for name, cmd in cmds:
        rc, o, e = devssh.run(c, cmd, timeout=180)
        print(f"\n### {name}  (rc={rc})")
        print((o + e).strip() or "<空>")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
