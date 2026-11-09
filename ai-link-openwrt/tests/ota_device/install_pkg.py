# -*- coding: utf-8 -*-
"""把任意 AI-LINK 包安装到设备（install.sh --upgrade），用于 RC 迭代。

用法：
  set AI_LINK_DEVICE_PASS
  python install_pkg.py --package F:\\...\\AI-LINK-v1.0.2.tar.gz --expect 1.0.2
"""
import argparse
import sys
import time
from pathlib import Path

import devssh

STAGE = "/tmp/ailink-install"
LOG = "/tmp/ailink-install.log"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--expect", required=True)
    ap.add_argument("--timeout", type=int, default=420)
    args = ap.parse_args()

    pkg = Path(args.package)
    if not pkg.is_file():
        raise SystemExit(f"找不到包：{pkg}")

    c = devssh.connect()
    q = lambda cmd, t=120: devssh.run(c, cmd, timeout=t)[1]   # noqa: E731

    print(f"上传 {pkg.name} ({pkg.stat().st_size:,} B)")
    devssh.run(c, f"rm -rf {STAGE} && mkdir -p {STAGE}")
    n = devssh.put_file(c, str(pkg), f"{STAGE}/{pkg.name}")
    print(f"  写入 {n:,} B")

    print("解包并执行 install.sh --upgrade")
    devssh.run(c, f"cd {STAGE} && tar xzf {pkg.name} && cd ai-link-openwrt && chmod +x install.sh")
    devssh.run(c, f"cd {STAGE}/ai-link-openwrt && setsid sh -c './install.sh --upgrade > {LOG} 2>&1' "
                  f"</dev/null >/dev/null 2>&1 & echo started")

    deadline = time.time() + args.timeout
    ok = False
    while time.time() < deadline:
        time.sleep(5)
        ver = q("cat /etc/ai-link/version").strip()
        if ver.startswith(args.expect):
            ok = True
            break
    tail = q(f"tail -8 {LOG}").strip()
    print("  " + tail.replace("\n", "\n  "))

    print(f"\n版本: {q('cat /etc/ai-link/version').strip()}  期望 {args.expect}")
    print("svc_state:", q("/etc/init.d/ai-link svc_state").strip())
    print("api/status:", q("curl -s --noproxy '*' -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:9099/api/status").strip())
    c.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
