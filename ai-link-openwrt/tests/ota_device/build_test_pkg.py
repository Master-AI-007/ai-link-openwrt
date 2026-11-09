# -*- coding: utf-8 -*-
"""为真机 OTA 验证构建测试包 + 测试清单（不触碰仓库源码、不发布）。

做法：把 ai-link-openwrt 复制到临时目录 → 用发布工具同一套函数改版本号 → 确定性打包，
因此产出的包与正式发布包结构完全一致，只是版本号不同。

用法：
  python build_test_pkg.py --version 1.0.2 --base-url http://10.10.10.62:8000
  python build_test_pkg.py --version 1.0.2 --base-url http://10.10.10.62:8000 --break-daemon
      --break-daemon 会往包内 daemon 头部塞一行 raise，用来验证「升级后健康检查失败 → 自动回滚」

产物（默认 dist/）：
  AI-LINK-v<version>.tar.gz     测试包
  version.json                  指向 base-url 的测试清单
  MANIFEST.txt                  指纹记录
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent                     # F:\deepailink\project
SITE = PROJECT / "site"
SKILL = Path.home() / ".workbuddy-ai" / "skills" / "ai-link-release" / "scripts"

sys.path.insert(0, str(SKILL))
import release as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--base-url", default="http://10.10.10.62:8000")
    ap.add_argument("--out", default=str(HERE / "dist"))
    ap.add_argument("--break-daemon", action="store_true",
                    help="包内 daemon 启动即抛异常，用于验证升级失败自动回滚")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    work = Path(tempfile.mkdtemp()) / "ai-link-openwrt"
    shutil.copytree(SITE / "ai-link-openwrt", work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    cfg = {"site": SITE, "src": work, "GITHUB_REPO": "Master-AI-007/ai-link-openwrt"}
    date_str = datetime.now().strftime("%Y%m%d")
    changes = R.bump_version(work, args.version, date_str)
    print(f"版本号同步 {len(changes)} 处 → {args.version}")

    if args.break_daemon:
        d = work / "root/usr/share/ai-link/ai-link-daemon.py"
        src = d.read_text(encoding="utf-8")
        marker = 'APP_VERSION = "%s"' % args.version
        assert marker in src, "找不到 APP_VERSION 行"
        head, rest = [], src
        # 保留 shebang / coding 声明，故障注入放在其后，避免变成「解释器都找不到」的低级失败
        while True:
            nl = rest.find("\n")
            if nl < 0:
                break
            line = rest[:nl + 1]
            if line.startswith("#!") or ("coding" in line and line.startswith("#")):
                head.append(line)
                rest = rest[nl + 1:]
            else:
                break
        d.write_text(
            "".join(head) +
            '# --- OTA 回滚测试注入：启动即失败 ---\n'
            'raise SystemExit("OTA rollback test: daemon intentionally broken")\n' + rest,
            encoding="utf-8")
        print("已注入故障：daemon 启动即退出")

    meta = R.build_package(cfg, out, args.version)
    pkg = out / f"AI-LINK-v{args.version}.tar.gz"
    print(f"包：{pkg.name}  {meta['size']:,} B  md5={meta['md5']}  sha256={meta['sha256'][:16]}…  {meta['files']} 个文件")

    manifest = {
        "schema": 1,
        "channel": "stable",
        "latest": args.version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "notes_url": f"{args.base_url}/changelog.html#v{args.version}",
        "highlights": ["OTA 真机验证专用测试包（不要发布）"],
        "changelog": [{"version": args.version, "date": datetime.now().strftime("%Y-%m-%d"),
                       "items": ["真机 OTA 端到端验证"]}],
        "packages": {
            "full": {
                "url": f"{args.base_url}/pkg/AI-LINK-v{args.version}.tar.gz",
                "mirrors": [],
                "size": meta["size"],
                "md5": meta["md5"],
                "sha256": meta["sha256"],
            }
        },
    }
    (out / "version.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    (out / "pkg").mkdir(exist_ok=True)
    shutil.copy2(pkg, out / "pkg" / pkg.name)

    (out / "MANIFEST.txt").write_text(
        f"version   {args.version}\n"
        f"size      {meta['size']}\n"
        f"md5       {meta['md5']}\n"
        f"sha256    {meta['sha256']}\n"
        f"files     {meta['files']}\n"
        f"base_url  {args.base_url}\n"
        f"broken    {args.break_daemon}\n",
        encoding="utf-8", newline="\n")
    print(f"清单：{out / 'version.json'}")
    shutil.rmtree(work.parent, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
