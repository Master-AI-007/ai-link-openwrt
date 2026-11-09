# -*- coding: utf-8 -*-
"""回滚后可观测状态复查：nftables 表、服务状态、API、sing-box 进程。

用法：设置 AI_LINK_DEVICE_PASS 后 python check_after.py [--restart]
"""
import argparse
import sys
import time

import devssh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restart", action="store_true")
    args = ap.parse_args()

    c = devssh.connect()
    q = lambda cmd: devssh.run(c, cmd, timeout=90)[1].strip()   # noqa: E731

    print("版本      :", q("cat /etc/ai-link/version"))
    print("svc_state :", q("/etc/init.d/ai-link svc_state"))
    print("nft 表    :", " | ".join(q("nft list tables").splitlines()))
    print("ai_link 表:", q("nft list table inet ai_link 2>&1 | head -3") or "<无>")
    print("api/status:", q("curl -s --noproxy '*' -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:9099/api/status"))
    print("sing-box  :", q("pgrep -f sing-box | wc -l"))
    print("dnsmasq   :", q("uci get dhcp.@dnsmasq[0].server 2>/dev/null | tr ' ' ','"))

    if args.restart:
        print("\n--- 执行 restart ---")
        print(q("/etc/init.d/ai-link restart 2>&1 | tail -8"))
        time.sleep(10)
        print("svc_state :", q("/etc/init.d/ai-link svc_state"))
        print("nft 表    :", " | ".join(q("nft list tables").splitlines()))
        print("api/status:", q("curl -s --noproxy '*' -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:9099/api/status"))
        print("sing-box  :", q("pgrep -f sing-box | wc -l"))

    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
