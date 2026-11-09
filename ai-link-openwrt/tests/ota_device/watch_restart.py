# -*- coding: utf-8 -*-
"""观察一次 service restart 的完整时间线：sing-box 多久开放 :7893、nft 何时挂上、有没有被 stop。

用法：设置 AI_LINK_DEVICE_PASS 后 python watch_restart.py [--restart]
不加 --restart 只观察当前状态 60 秒。
"""
import argparse
import re
import sys
import time

import devssh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restart", action="store_true")
    ap.add_argument("--seconds", type=int, default=90)
    args = ap.parse_args()

    c = devssh.connect()
    q = lambda cmd, t=40: devssh.run(c, cmd, timeout=t)[1]   # noqa: E731

    t0 = time.time()
    before_logs = set(q("logread").splitlines())

    if args.restart:
        print("执行 /etc/init.d/ai-link restart ...")
        devssh.run(c, "/etc/init.d/ai-link restart >/dev/null 2>&1", timeout=60)

    print(f"\n{'秒':>4}  {'7893':<5} {'nft':<4} {'core':<5} {'daemon':<7} 说明")
    last = None
    while time.time() - t0 < args.seconds:
        el = int(time.time() - t0)
        ports = q("ss -lntu")
        p7893 = "Y" if re.search(r":7893\s", ports) else "-"
        nft = "Y" if "inet ai_link" in q("nft list tables") else "-"
        st = q("/etc/init.d/ai-link svc_state").strip()
        m = re.search(r"core=(\d).*nft=(\d)", st) or re.search(r"daemon=(\d)", st)
        core = re.search(r"core=(\d)", st)
        dmn = re.search(r"daemon=(\d)", st)
        row = (p7893, nft, core.group(1) if core else "?", dmn.group(1) if dmn else "?")
        if row != last:
            print(f"{el:>4}  {p7893:<5} {nft:<4} {row[2]:<5} {row[3]:<7} {st}")
            last = row
        time.sleep(3)

    print("\n本次新增日志：")
    new = [l for l in q("logread").splitlines() if l not in before_logs][-25:]
    print("\n".join("  " + l for l in new) or "  <无>")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
