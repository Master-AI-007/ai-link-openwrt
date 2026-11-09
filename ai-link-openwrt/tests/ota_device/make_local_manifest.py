# -*- coding: utf-8 -*-
"""把仓库里真实的发布清单改成本地可访问版本，供真机 OTA 拉取 RC 包。

用法：
  python make_local_manifest.py --version 1.0.2 --base-url http://10.10.10.62:8002 \
      --site F:\\deepailink\\project\\site --out dist-rc

产物：<out>/version.json + <out>/pkg/AI-LINK-v<version>.tar.gz
只改 url/mirrors，md5/sha256/size 保持与真实包一致（校验仍走真实指纹）。
"""
import argparse
import json
import shutil
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--site", default=r"F:\deepailink\project\site")
    ap.add_argument("--out", default="dist-rc")
    args = ap.parse_args()

    site = Path(args.site)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "pkg").mkdir(parents=True)

    manifest = json.loads((site / "version.json").read_text(encoding="utf-8"))
    if manifest.get("latest") != args.version:
        raise SystemExit(f"清单 latest={manifest.get('latest')} 与 --version {args.version} 不一致")
    pkg_name = f"AI-LINK-v{args.version}.tar.gz"
    src_pkg = site / pkg_name
    if not src_pkg.is_file():
        raise SystemExit(f"找不到包：{src_pkg}")
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    text = text.replace(manifest["packages"]["full"]["url"],
                        f"{args.base_url}/pkg/{pkg_name}")
    for m in manifest["packages"]["full"].get("mirrors") or []:
        text = text.replace(m, f"{args.base_url}/pkg/{pkg_name}")
    (out / "version.json").write_text(text, encoding="utf-8", newline="\n")
    shutil.copy2(src_pkg, out / "pkg" / pkg_name)

    full = manifest["packages"]["full"]
    print(f"清单 {out / 'version.json'}")
    print(f"  latest {manifest['latest']}  size {full['size']:,}  md5 {full['md5']}")
    print(f"  url    {args.base_url}/pkg/{pkg_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
