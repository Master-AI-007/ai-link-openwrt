# -*- coding: utf-8 -*-
"""从面板 index.html 抽出所有内联 <script> 块，逐个用 node --check 校验语法。"""
import re, subprocess, sys, tempfile, os
from pathlib import Path

from _paths import ROOT, NODE
HTML = ROOT / "root/usr/share/ai-link/webui/index.html"

src = HTML.read_text(encoding="utf-8", errors="replace")
blocks = re.findall(r"<script\b([^>]*)>(.*?)</script>", src, flags=re.S | re.I)
print(f"找到 {len(blocks)} 个 script 块")

tmpdir = Path(tempfile.mkdtemp())
fails = 0
for i, (attrs, body) in enumerate(blocks):
    if "src=" in attrs.lower():
        continue
    body = body.strip()
    if not body:
        continue
    is_module = "module" in attrs.lower()
    f = tmpdir / f"block{i}.{'mjs' if is_module else 'js'}"
    f.write_text(body, encoding="utf-8", newline="\n")
    args = [NODE, "--check", str(f)]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    status = "OK" if r.returncode == 0 else "FAIL"
    if r.returncode != 0:
        fails += 1
    print(f"  block{i:>2} ({len(body):>7}B, {'module' if is_module else 'script'}) -> {status}")
    if r.returncode != 0:
        print((r.stderr or "")[:1200])

print(f"\n失败 {fails} 个")
sys.exit(1 if fails else 0)
