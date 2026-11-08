# -*- coding: utf-8 -*-
"""验证脚本共用的路径与解释器解析。

优先级：
  1. 环境变量 AI_LINK_SRC（直接指向 ai-link-openwrt 源码目录）
  2. 环境变量 AI_LINK_SITE（站点仓库根，自动拼 ai-link-openwrt）
  3. 相对本文件：../site/ai-link-openwrt

PYTHON_BIN / NODE_BIN 同 release.py 的约定，缺省回落到当前解释器 / PATH 中的 node。
"""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def src_root() -> Path:
    for env in ("AI_LINK_SRC",):
        v = os.environ.get(env)
        if v and (Path(v) / "install.sh").is_file():
            return Path(v)
    v = os.environ.get("AI_LINK_SITE")
    if v and (Path(v) / "ai-link-openwrt" / "install.sh").is_file():
        return Path(v) / "ai-link-openwrt"
    for cand in (
        HERE.parent / "site" / "ai-link-openwrt",
        HERE.parent / "ai-link-openwrt",
        HERE.parent / "02-源码" / "ai-link-openwrt",
    ):
        if (cand / "install.sh").is_file():
            return cand
    raise SystemExit("找不到 ai-link-openwrt 源码目录：请设置 AI_LINK_SRC 或 AI_LINK_SITE")


ROOT = src_root()
PY = os.environ.get("PYTHON_BIN") or sys.executable
NODE = os.environ.get("NODE_BIN") or shutil.which("node") or shutil.which("node.exe") or ""
BASH = os.environ.get("BASH_BIN") or shutil.which("bash") or shutil.which("sh") or ""

DAEMON = ROOT / "root/usr/share/ai-link/ai-link-daemon.py"


def app_version() -> str:
    import re
    m = re.search(r'^APP_VERSION = "([^"]+)"', DAEMON.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def require(tool: str, value: str) -> str:
    if not value:
        raise SystemExit(f"缺少可执行文件：{tool}（请设置 {tool.upper()}_BIN 或加入 PATH）")
    return value
