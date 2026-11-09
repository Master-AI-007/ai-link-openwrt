# -*- coding: utf-8 -*-
"""真机 OTA 升级实测：从设备当前版本升到测试清单里的版本。

流程：
  1. 记录当前 UCI 清单地址（normal 情况下未设置）
  2. 把 ai-link.global.update_manifest_url 指向本机测试清单
  3. ai-link update            确认能识别到新版本
  4. ai-link update --apply    启动升级，轮询 progress.log / state.json
  5. 报告结果（版本、服务状态、healthcheck）
  6. 恢复原清单地址（--keep-manifest 可保留，便于连续测试）

用法：
  set AI_LINK_DEVICE_PASS
  python ota_apply_test.py --expect 1.0.2 [--keep-manifest] [--timeout 600]
"""
import argparse
import json
import sys
import time

import devssh

RUN = "/var/run/ai-link/update"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="http://10.10.10.62:8000/version.json")
    ap.add_argument("--expect", required=True)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--keep-manifest", action="store_true")
    ap.add_argument("--fresh", action="store_true", default=True,
                    help="升级前把 /var/run/ai-link/update 清空，保证读到的不是上次的进度")
    args = ap.parse_args()

    c = devssh.connect()
    q = devssh.run

    old_manifest = q(c, "uci get ai-link.global.update_manifest_url 2>/dev/null")[1].strip()
    print(f"原清单地址：{old_manifest or '<未设置>'}")

    print("\n[1] 指向测试清单")
    rc, o, e = q(c, f"uci set ai-link.global.update_manifest_url='{args.manifest}' && uci commit ai-link && "
                    f"uci get ai-link.global.update_manifest_url")
    print("  " + (o + e).strip())
    if rc != 0:
        raise SystemExit("设置清单地址失败")

    print("\n[2] 检查更新")
    rc, o, e = q(c, "ai-link update 2>&1 | tail -12", timeout=120)
    print("  " + (o + e).strip().replace("\n", "\n  "))

    print("\n[3] 启动升级")
    if args.fresh:
        q(c, f"rm -rf {RUN}")
    rc, o, e = q(c, "setsid sh -c 'ai-link update --apply > /tmp/ota-apply.log 2>&1' </dev/null >/dev/null 2>&1 & echo launched")
    print("  " + (o + e).strip())

    print("\n[4] 轮询进度")
    deadline = time.time() + args.timeout
    seen = None
    final = None
    while time.time() < deadline:
        time.sleep(4)
        rc, ln, _ = q(c, f"tail -1 {RUN}/progress.log 2>/dev/null")
        ln = ln.strip()
        stage = pct = msg = ""
        parts = ln.split("|", 3)
        if len(parts) == 4:
            stage, pct, msg = parts[1], parts[2], parts[3]
        if ln and ln != seen:
            print(f"  {pct:>4}%  {stage:<11} {msg[:90]}")
            seen = ln
        if stage in ("done", "failed"):
            final = (stage, pct, msg)
            time.sleep(3)          # 等日志与回滚动作收尾
            break

    print("\n[5] 结果")
    if final:
        print(f"  最终阶段：{final[0]}  {final[1]}%  {final[2]}")
        if final[0] == "failed":
            print("  ⚠ 升级失败——如果开了自动回滚，下面版本应仍是升级前版本")
    rc, o, e = q(c, f"tail -25 {RUN}/progress.log 2>/dev/null")
    print("  --- progress.log ---")
    print("  " + (o + e).strip().replace("\n", "\n  "))
    rc, o, e = q(c, "tail -15 /tmp/ota-apply.log 2>/dev/null")
    print("  --- ai-link update --apply 输出 ---")
    print("  " + (o + e).strip().replace("\n", "\n  "))

    print("\n[6] 升级后状态")
    for label, cmd in [
        ("版本文件", "cat /etc/ai-link/version"),
        ("svc_state", "/etc/init.d/ai-link svc_state"),
        ("进程数", "pgrep -f 'ai-link-dae[m]on' | wc -l"),
        ("api/status", "curl -s --noproxy '*' -m 10 -o /dev/null -w '%{http_code}' http://127.0.0.1:9099/api/status"),
        ("备份文件", "ls -1t /root/ai-link-final-backup/pre-update-v*.tgz 2>/dev/null | head -3"),
    ]:
        rc, o, e = q(c, cmd, timeout=60)
        print(f"  {label:<10}: {(o + e).strip()}")

    if not args.keep_manifest:
        print("\n[7] 恢复原清单地址")
        if old_manifest:
            q(c, f"uci set ai-link.global.update_manifest_url='{old_manifest}' && uci commit ai-link")
            print(f"  恢复为 {old_manifest}")
        else:
            q(c, "uci delete ai-link.global.update_manifest_url 2>/dev/null; uci commit ai-link")
            print("  已删除测试清单地址")

    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
