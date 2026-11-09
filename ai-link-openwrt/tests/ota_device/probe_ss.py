# -*- coding: utf-8 -*-
"""看一下设备上 ss / netstat 到底怎么打印监听端口，决定 init 脚本的探针写法。"""
import sys

import devssh


def main():
    c = devssh.connect()
    for cmd in ("ss -lntu", "ss -lnt", "netstat -tln", "cat /proc/net/tcp | head -5"):
        rc, o, e = devssh.run(c, cmd, timeout=30)
        print(f"\n=== {cmd}  (rc={rc}) ===")
        print((o + e).strip()[:1200])
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
