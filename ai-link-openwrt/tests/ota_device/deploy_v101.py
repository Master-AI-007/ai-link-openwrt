# -*- coding: utf-8 -*-
"""把测试机从 v1.0.0 手动升到 v1.0.1（OTA 冷启动前置步骤）。

做四件事：
  1. 备份设备上的 /etc/ai-link 与 /etc/config/ai-link 到 /root/ai-link-final-backup/，并拉一份到本机
  2. 上传官方 AI-LINK-v1.0.1.tar.gz
  3. 用 install.sh --upgrade 安装（后台跑，轮询日志，避免 SSH 断连误判）
  4. 等版本文件变成 1.0.1、:9099 起来

用法：
  set AI_LINK_DEVICE_PASS
  python deploy_v101.py [--package <tar.gz>] [--no-upload]
"""
import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import devssh

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
DEFAULT_PKG = PROJECT / "site" / "AI-LINK-v1.0.1.tar.gz"
STAGE = "/tmp/ailink-upgrade"
LOG = "/tmp/ailink-install.log"


def sh(c, cmd, timeout=120):
    return devssh.run(c, cmd, timeout=timeout)


def step(n, msg):
    print(f"\n[{n}] {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default=str(DEFAULT_PKG))
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    pkg = Path(args.package)
    if not args.no_upload and not pkg.is_file():
        raise SystemExit(f"找不到包：{pkg}")

    c = devssh.connect()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    step(1, "备份设备配置")
    rc, o, e = sh(c, f"mkdir -p /root/ai-link-final-backup && "
                     f"tar czf /root/ai-link-final-backup/pre-v101-{ts}.tgz -C / etc/ai-link etc/config/ai-link 2>&1; "
                     f"ls -l /root/ai-link-final-backup/pre-v101-{ts}.tgz")
    print((o + e).strip())
    local_backup = HERE / f"device-backup-pre-v101-{ts}.tgz"
    try:
        n = devssh.get_file(c, f"/root/ai-link-final-backup/pre-v101-{ts}.tgz", local_backup)
        print(f"  已拉回本机：{local_backup}（{n:,} B）")
    except Exception as ex:  # noqa: BLE001
        print(f"  ⚠ 拉回本机失败（设备上仍有备份）：{ex}")

    if not args.no_upload:
        step(2, f"上传 {pkg.name}")
        sh(c, f"rm -rf {STAGE} && mkdir -p {STAGE}")
        remote = f"{STAGE}/{pkg.name}"
        t0 = time.time()
        n = devssh.put_file(c, str(pkg), remote)
        print(f"  {n:,} B 用时 {time.time() - t0:.1f}s")
        rc, o, e = sh(c, f"ls -l {remote}")
        print("  " + (o + e).strip())

    step(3, "解包并执行 install.sh --upgrade（后台）")
    rc, o, e = sh(c, f"cd {STAGE} && tar xzf AI-LINK-v1.0.1.tar.gz && ls -d ai-link-openwrt")
    print("  " + (o + e).strip())
    rc, o, e = sh(c, f"cd {STAGE}/ai-link-openwrt && chmod +x install.sh && "
                     f"setsid sh -c './install.sh --upgrade > {LOG} 2>&1' </dev/null >/dev/null 2>&1 & echo started")
    print("  " + (o + e).strip())

    step(4, "轮询安装进度")
    deadline = time.time() + 420
    last = ""
    while time.time() < deadline:
        time.sleep(6)
        rc, o, e = sh(c, f"cat {LOG} 2>/dev/null | tail -6")
        body = (o + e).strip()
        if body and body != last:
            print("  " + body.replace("\n", "\n  "))
            last = body
        rc, ver, _ = sh(c, "cat /etc/ai-link/version 2>/dev/null")
        rc2, port, _ = sh(c, "netstat -tln 2>/dev/null | grep -c ':9099'")
        if ver.strip().startswith("1.0.1") and port.strip() not in ("", "0"):
            print(f"\n  ✓ 版本 {ver.strip()}，:9099 已监听")
            break
    else:
        print("\n  ⚠ 超时，最后日志如下")
        print(sh(c, f"tail -30 {LOG}")[1])

    step(5, "安装后状态")
    for cmd in ("cat /etc/ai-link/version",
                "/etc/init.d/ai-link svc_state 2>&1 | head -2",
                "pgrep -f 'ai-link-dae[m]on' | wc -l",
                "netstat -tln 2>/dev/null | grep ':9099' || echo '<9099 未监听>'",
                "curl -s --noproxy '*' -m 8 -o /dev/null -w 'api_status=%{http_code}\\n' http://127.0.0.1:9099/api/status"):
        rc, o, e = sh(c, cmd)
        print(f"  $ {cmd}\n    {(o + e).strip()}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
