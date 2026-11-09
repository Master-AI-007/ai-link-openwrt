# -*- coding: utf-8 -*-
"""真机（OpenWrt）SSH 小工具：给 OTA 验证脚本共用。

凭据从环境变量读，不落盘：
    AI_LINK_DEVICE_HOST   默认 10.10.10.77
    AI_LINK_DEVICE_USER   默认 root
    AI_LINK_DEVICE_PASS   必需
    AI_LINK_DEVICE_PORT   默认 22
"""
import os
import sys
from pathlib import Path

import paramiko


def connect(timeout=15):
    host = os.environ.get("AI_LINK_DEVICE_HOST", "10.10.10.77")
    user = os.environ.get("AI_LINK_DEVICE_USER", "root")
    pwd = os.environ.get("AI_LINK_DEVICE_PASS")
    port = int(os.environ.get("AI_LINK_DEVICE_PORT", "22"))
    if not pwd:
        raise SystemExit("请先设置 AI_LINK_DEVICE_PASS")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(hostname=host, port=port, username=user, password=pwd,
              timeout=timeout, banner_timeout=timeout, auth_timeout=timeout,
              look_for_keys=False, allow_agent=False)
    return c


def run(c, cmd, timeout=60):
    """执行命令，返回 (rc, stdout, stderr)。"""
    _in, out, err = c.exec_command(cmd, timeout=timeout)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    rc = out.channel.recv_exit_status()
    return rc, o, e


def run_ok(c, cmd, timeout=60):
    rc, o, e = run(c, cmd, timeout=timeout)
    return o.strip() if rc == 0 else f"<rc={rc}> {(e or o).strip()[:300]}"


def put_file(c, local, remote, timeout=600):
    """设备没开 SFTP 子系统（dropbear 默认没有），用 cat 走 stdin 传二进制。"""
    data = Path(local).read_bytes()
    _in, out, err = c.exec_command(f"cat > {remote}", timeout=timeout)
    _in.write(data)
    _in.flush()
    _in.channel.shutdown_write()
    rc = out.channel.recv_exit_status()
    if rc != 0:
        raise RuntimeError(f"上传失败 rc={rc}: {err.read().decode('utf-8', 'replace')[:300]}")
    return len(data)


def get_file(c, remote, local, timeout=600):
    _in, out, err = c.exec_command(f"cat {remote}", timeout=timeout)
    data = out.read()
    rc = out.channel.recv_exit_status()
    if rc != 0:
        raise RuntimeError(f"下载失败 rc={rc}: {err.read().decode('utf-8', 'replace')[:300]}")
    Path(local).write_bytes(data)
    return len(data)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="在设备上执行一条命令")
    ap.add_argument("--cmd", action="append", default=[], help="要执行的命令，可重复")
    ap.add_argument("--download", nargs=2, metavar=("REMOTE", "LOCAL"))
    ap.add_argument("--upload", nargs=2, metavar=("LOCAL", "REMOTE"))
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    c = connect()
    print(f"已连接 {os.environ.get('AI_LINK_DEVICE_USER', 'root')}@"
          f"{os.environ.get('AI_LINK_DEVICE_HOST', '10.10.10.77')}")
    if not (args.cmd or args.download or args.upload):
        rc, o, e = run(c, "uname -a && cat /etc/openwrt_release 2>/dev/null | head -5")
        print(o.strip() or e.strip())
    for cmd in args.cmd:
        rc, o, e = run(c, cmd, timeout=args.timeout)
        print(f"\n$ {cmd}   (rc={rc})")
        print((o + e).strip() or "<空>")
    if args.download:
        n = get_file(c, args.download[0], args.download[1], timeout=args.timeout)
        print(f"\n下载 {args.download[0]} -> {args.download[1]}  {n:,} B")
    if args.upload:
        n = put_file(c, args.upload[0], args.upload[1], timeout=args.timeout)
        print(f"\n上传 {args.upload[0]} -> {args.upload[1]}  {n:,} B")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
