#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-LINK 线上状态核对（只读）。

读取 ~/.workbuddy-ai/ai-link-release.env 的凭据，核对：
  1. GitHub 仓库 / 最新 Release / 3 个资产
  2. 仓库内 version.json（OTA 备用源）与本地一致性
  3. Cloudflare Pages 最近部署状态

用法：
  python verify_online.py            # 全量核对
  python verify_online.py --json     # 机器可读输出

本脚本不打印任何令牌内容。
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV_FILE = Path.home() / ".workbuddy-ai" / "ai-link-release.env"
CF_PROJECT = "ai-link-official"


def load_env():
    import os
    cfg = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip().lstrip("\ufeff")
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    # B4-17 Fix: Process environment variables take priority over ENV_FILE
    for k in ("GITHUB_TOKEN", "GITHUB_REPO", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "AI_LINK_SITE", "AI_LINK_SRC"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def get(url, token=None, accept="application/vnd.github+json", timeout=30, scheme="token"):
    req = urllib.request.Request(url, headers={"User-Agent": "ai-link-verify"})
    if accept:
        req.add_header("Accept", accept)
    if token:
        req.add_header("Authorization", f"{scheme} {token}")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg = load_env()
    repo = cfg.get("GITHUB_REPO", "Master-AI-007/ai-link-openwrt")
    gh_token = cfg.get("GITHUB_TOKEN")
    cf_token = cfg.get("CLOUDFLARE_API_TOKEN")
    cf_account = cfg.get("CLOUDFLARE_ACCOUNT_ID")
    site = Path(cfg.get("AI_LINK_SITE", ".")).expanduser()

    out = {"repo": repo}

    # 1. 仓库
    me, err = get(f"https://api.github.com/repos/{repo}", gh_token)
    out["repo_reachable"] = bool(me)
    if err:
        out["repo_error"] = err
    elif me:
        out["default_branch"] = me.get("default_branch")
        out["pushed_at"] = me.get("pushed_at")

    # 2. 最新 Release 与资产
    rel, err = get(f"https://api.github.com/repos/{repo}/releases/latest", gh_token)
    if err:
        out["release_error"] = err
    elif rel:
        out["release_tag"] = rel.get("tag_name")
        out["release_url"] = rel.get("html_url")
        out["release_assets"] = [
            {"name": a["name"], "size": a["size"], "state": a.get("state")}
            for a in rel.get("assets", [])
        ]

    # 3. 仓库内 version.json（raw 备用源，走 contents API 绕过被墙的 raw 域名）
    man, err = get(f"https://api.github.com/repos/{repo}/contents/version.json", gh_token)
    remote_manifest = None
    if err:
        out["manifest_error"] = err
    elif man and man.get("content"):
        import base64
        remote_manifest = json.loads(base64.b64decode(man["content"]).decode("utf-8"))
        out["remote_manifest"] = {
            "latest": remote_manifest.get("latest"),
            "size": (remote_manifest.get("packages", {}).get("full") or {}).get("size"),
            "md5": (remote_manifest.get("packages", {}).get("full") or {}).get("md5"),
            "sha256": (remote_manifest.get("packages", {}).get("full") or {}).get("sha256"),
        }

    # 4. 本地清单
    local_path = site / "version.json"
    if local_path.is_file():
        local = json.loads(local_path.read_text(encoding="utf-8"))
        full = local.get("packages", {}).get("full", {})
        out["local_manifest"] = {
            "latest": local.get("latest"), "size": full.get("size"),
            "md5": full.get("md5"), "sha256": full.get("sha256"),
        }
        if remote_manifest:
            r, l = out["remote_manifest"], out["local_manifest"]
            out["manifest_consistent"] = all(r.get(k) == l.get(k) for k in ("latest", "size", "md5", "sha256"))
    else:
        out["local_manifest_error"] = f"找不到 {local_path}"

    # 5. Cloudflare Pages 最近部署
    if cf_token and cf_account:
        dep, err = get(
            f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/pages/projects/{CF_PROJECT}/deployments?per_page=1",
            cf_token, accept="application/json", scheme="Bearer")
        if err:
            out["deploy_error"] = err
        elif dep:
            items = dep.get("result") or []
            if items:
                d0 = items[0]
                out["latest_deploy"] = {
                    "id": d0.get("short_id"),
                    "status": (d0.get("latest_stage") or {}).get("status"),
                    "created_on": d0.get("created_on"),
                    "url": d0.get("url"),
                    "commit": ((d0.get("deployment_trigger") or {}).get("metadata") or {}).get("commit_hash", "")[:7],
                }
            else:
                out["deploy_error"] = "无部署记录"
    else:
        out["deploy_error"] = "未配置 Cloudflare 凭据"

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    def line(k, v):
        print(f"  {k:<18}{v}")

    print("=== AI-LINK 线上状态核对 ===")
    line("仓库", repo)
    line("仓库可达", "✓" if out.get("repo_reachable") else f"✗ {out.get('repo_error', '')}")
    if out.get("release_tag"):
        line("最新 Release", out["release_tag"])
        for a in out.get("release_assets", []):
            line("  资产", f"{a['name']}  {a['size']:,} B  {a['state']}")
    else:
        line("最新 Release", f"✗ {out.get('release_error', '')}")
    if out.get("remote_manifest"):
        m = out["remote_manifest"]
        line("线上清单 latest", m["latest"])
        line("线上 md5", m["md5"])
    elif out.get("manifest_error"):
        line("线上清单", f"✗ {out['manifest_error']}")
    if out.get("local_manifest"):
        line("本地 md5", out["local_manifest"]["md5"])
        if "manifest_consistent" in out:
            line("清单一致性", "✓ 一致" if out["manifest_consistent"] else "✗ 不一致")
    if out.get("latest_deploy"):
        d = out["latest_deploy"]
        line("最近部署", f"{d['id']}  {d['status']}  commit={d['commit']}  {d['created_on']}")
    else:
        line("最近部署", f"✗ {out.get('deploy_error', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
