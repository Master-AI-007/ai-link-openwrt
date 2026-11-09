# -*- coding: utf-8 -*-
"""按当前工作区重新打包并回写清单（版本号不变，用于 RC 迭代）。

与 release.py publish 的区别：只做「打包 + 回写清单」，不改版本号、不提交、不发布。
版本号已经在工作区里了（由 publish --dry-run 或手工同步）。

用法：python rebuild_rc.py --version 1.0.2
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SITE = PROJECT / "site"
SKILL = Path.home() / ".workbuddy-ai" / "skills" / "ai-link-release" / "scripts"
sys.path.insert(0, str(SKILL))
import release as R  # noqa: E402

HIGHLIGHTS = [
    "安全加固：移除首页令牌 Cookie 下发，/api/status、/api/nodes/share_uri 与 /api/ops/logs 全面鉴权脱敏",
    "凭据重构：UCI 彻底移除 panel_secret，改用布尔 panel_pwd_customized=0/1，并永久下线弱默认密码 admin",
    "启动与防黑洞：修复无 ss 环境 25s 假等待与 BusyBox pgrep 失效；看门狗与 restore_proxy 挂载前强制校验 :7893 端口监听",
    "备份恢复增强：面板与 LuCI 新增 .tgz / .json 浏览器直接上传恢复、.tgz 一键导出与 CLI ai-link restore <file> 命令",
    "OTA 与稳定性：回滚后立即 restore_proxy 消除 10s 空窗；升级进度落盘闪存防断电丢失；auto_nodes.json 剥离探测噪声保持 MD5 恒定",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--highlight", action="append", default=None)
    args = ap.parse_args()

    cfg = {"site": SITE, "src": SITE / "ai-link-openwrt",
           "GITHUB_REPO": "Master-AI-007/ai-link-openwrt"}
    cur = R.read_app_version(cfg["src"])
    if cur != args.version:
        raise SystemExit(f"工作区版本是 {cur}，与 --version {args.version} 不一致")

    import tempfile
    out = Path(tempfile.mkdtemp()) / "dist"
    meta = R.build_package(cfg, out, args.version)
    print(f"包：{meta['path'].name}  {meta['size']:,} B  md5={meta['md5']}  sha256={meta['sha256'][:16]}…  文件 {meta['files']}")

    notes_url = f"https://ai-link-official.pages.dev/changelog.html#v{args.version}"
    changed = R.update_manifests(cfg, args.version, meta, notes_url,
                                 args.highlight if args.highlight else HIGHLIGHTS)
    print("回写：", "、".join(changed))

    m = json.loads((SITE / "version.json").read_text(encoding="utf-8"))
    full = m["packages"]["full"]
    assert m["latest"] == args.version and full["md5"] == meta["md5"], "清单回写不一致"
    print(f"清单校验通过：latest={m['latest']} md5={full['md5']} size={full['size']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
