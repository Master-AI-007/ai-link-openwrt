# -*- coding: utf-8 -*-
"""透明代理健康诊断：端口、进程、nft、日志关键行（不做任何修改）。

用法：设置 AI_LINK_DEVICE_PASS 后 python diag_proxy.py
"""
import re
import sys

import devssh


def main():
    c = devssh.connect()
    q = lambda cmd, t=60: devssh.run(c, cmd, timeout=t)[1]   # noqa: E731

    print("=== 监听端口（含 PID）===")
    lines = [l for l in q("netstat -tlnp").splitlines()
             if re.search(r":(9099|7893|7891|7890|7874)\b", l)]
    print("\n".join(lines) or "  <关键端口都没在监听>")

    print("\n=== 进程 ===")
    for l in q("ps w").splitlines():
        if ("sing-box" in l or "ai-link-dae" in l) and "grep" not in l:
            print("  " + l.strip())

    print("\n=== nft 表 ===")
    print("  " + q("nft list tables").replace("\n", "\n  "))

    print("\n=== 服务状态 ===")
    print("  " + q("/etc/init.d/ai-link svc_state").strip())

    print("\n=== UCI 关键项 ===")
    for k in ("enabled", "tproxy_port", "mixed_port", "dns_port", "app_version"):
        print(f"  {k} = {q('uci get ai-link.global.' + k).strip()}")

    print("\n=== logread 最近 30 条 ai-link/sing-box ===")
    logs = q("logread").splitlines()
    hit = [l for l in logs if ("ai-link" in l or "sing-box" in l)][-30:]
    print("\n".join("  " + l for l in hit) or "  <无>")

    print("\n=== sing-box 配置文件检查 ===")
    print("  " + q("ls -l /etc/ai-link/sing-box.json").strip())
    rc, o, e = devssh.run(c, "/usr/bin/sing-box check -c /etc/ai-link/sing-box.json", timeout=60)
    print(f"  sing-box check rc={rc}: {(o + e).strip()[:300]}")

    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
