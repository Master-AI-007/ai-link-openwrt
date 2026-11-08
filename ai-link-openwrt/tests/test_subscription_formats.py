#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-LINK v2.3.6 订阅格式全量回归测试 (11 种主流客户端/机场格式 + 无 PyYAML 降级回退验证 + HTTP 200 空节点报错分类验证)."""
import argparse
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _paths import DAEMON  # noqa: E402

FIXTURE_DIR = HERE / "subscription_formats"

CASES = [
    ("clash-simple.yaml", True, "Clash 单行 flow"),
    ("clash-block.yaml", True, "Clash 多行块式 YAML"),
    ("clash-nested-flow.yaml", True, "Clash 嵌套 flow 字典 (ws-opts.headers)"),
    ("clash-anchor.yaml", True, "Clash YAML 锚点引用 (&b / <<: *b)"),
    ("uri-list.txt", True, "URI 列表 (vless/ss/trojan...)"),
    ("base64-uri.txt", True, "Base64 编码 URI 订阅"),
    ("singbox.json", True, "Sing-box outbounds JSON"),
    ("surge.txt", True, "Surge INI ([Proxy] / custom / ss)"),
    ("loon.txt", True, "Loon / Quantumult X INI ([Proxy] 位置参数)"),
    ("sip008.json", True, "SIP008 Shadowsocks JSON (servers 数组)"),
    ("v2ray-json.json", True, "V2Ray / v2rayN 客户端 JSON (settings.vnext)"),
]


def run_remote_host_test(host: str) -> int:
    print("=" * 78)
    print(f" AI-LINK 远程订阅格式验收测试 ({host})")
    print("=" * 78)
    mismatch = 0
    for fname, expected, desc in CASES:
        content = (FIXTURE_DIR / fname).read_text(encoding="utf-8")
        body = json.dumps({"uri": content}).encode("utf-8")
        req = urllib.request.Request(
            f"{host.rstrip('/')}/api/nodes/import",
            data=body,
            headers={"Content-Type": "application/json", "Origin": host.rstrip("/")},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                resp = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            resp = json.loads(e.read().decode("utf-8", "replace"))
        actual = bool(resp.get("ok")) and int(resp.get("imported_count", 0)) > 0
        cnt = int(resp.get("imported_count", 0))
        match = actual == expected
        if not match:
            mismatch += 1
        print(f"{fname:<26} {'PASS' if expected else 'FAIL':<10} {'PASS' if actual else 'FAIL':<10} {cnt:<10} {'OK' if match else 'MISMATCH'} ({desc})")
    return 0 if mismatch == 0 else 1


def run_local_regression() -> int:
    print("=" * 78)
    print(" AI-LINK v2.3.6 订阅全格式解析与错误分类回归测试 (11 种格式 + Fallback + 错误分类)")
    print("=" * 78)
    spec = importlib.util.spec_from_file_location("ailink_daemon_subfmt", str(DAEMON))
    dmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dmod)

    results = []

    def check(name: str, ok: bool, detail: str = ""):
        results.append((name, bool(ok), detail))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))

    for fname, expected, desc in CASES:
        fpath = FIXTURE_DIR / fname
        raw = fpath.read_text(encoding="utf-8")
        obs = dmod.NodeURIParser.parse_subscription_text(raw)
        ok = (len(obs) >= 1) == expected
        tags = [o.get("tag") for o in obs]
        check(
            f"Format [{fname}] ({desc}): 解析出 >=1 个有效节点",
            ok,
            f"count={len(obs)}, tags={tags}",
        )

    nested_obs = dmod.NodeURIParser.parse_subscription_text((FIXTURE_DIR / "clash-nested-flow.yaml").read_text(encoding="utf-8"))
    tr_nested = (nested_obs[0].get("transport") or {}) if nested_obs else {}
    check(
        "P1-02 (Clash 嵌套 flow 字典深度保留): ws-opts.path 与 ws-opts.headers.Host 完整映射至 Sing-box transport",
        tr_nested.get("type") == "ws"
        and tr_nested.get("path") == "/"
        and (tr_nested.get("headers") or {}).get("Host") == "c.example.com",
        f"transport={tr_nested}",
    )

    saved_yaml_mod = sys.modules.get("yaml")
    sys.modules["yaml"] = None
    try:
        for fname in ("clash-simple.yaml", "clash-block.yaml", "clash-nested-flow.yaml", "clash-anchor.yaml"):
            raw = (FIXTURE_DIR / fname).read_text(encoding="utf-8")
            obs_fb = dmod.NodeURIParser.parse_subscription_text(raw)
            check(
                f"P1-02 (无 PyYAML 纯手写降级解析 [{fname}]): 依然准确解析出节点",
                len(obs_fb) >= 1 and bool(obs_fb[0].get("server")),
                f"count={len(obs_fb)}, server={obs_fb[0].get('server') if obs_fb else None}",
            )
    finally:
        if saved_yaml_mod is not None:
            sys.modules["yaml"] = saved_yaml_mod
        else:
            sys.modules.pop("yaml", None)

    diag_not_svc = dmod._classify_subscription_failure(200, "Not Service", "", host="2024.user.freecloud.cfd")
    diag_html = dmod._classify_subscription_failure(200, "<!DOCTYPE html><html><title>Welcome to nginx!</title></html>", "", host="dy11.baipiaoyes.com")
    diag_empty_yaml = dmod._classify_subscription_failure(200, "proxies: []\nproxy-groups: []", "", host="sub.example.com")
    check(
        "P1-01 & P2-04 (HTTP 200 零节点精准错误分类): Not Service -> sub_token_invalid, HTML -> sub_html_challenge, 空YAML -> sub_empty_nodes",
        diag_not_svc.get("error_code") == "sub_token_invalid"
        and "Not Service" in diag_not_svc.get("reason", "")
        and diag_html.get("error_code") == "sub_html_challenge"
        and "网页" in diag_html.get("reason", "")
        and diag_empty_yaml.get("error_code") == "sub_empty_nodes",
        f"not_svc={diag_not_svc.get('error_code')}, html={diag_html.get('error_code')}, empty={diag_empty_yaml.get('error_code')}",
    )

    print("\n" + "=" * 78)
    fails = [r for r in results if not r[1]]
    print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
    print("=" * 78)
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="", help="Optional remote AI-LINK panel URL")
    args = ap.parse_args()
    if args.host:
        sys.exit(run_remote_host_test(args.host))
    sys.exit(run_local_regression())


if __name__ == "__main__":
    main()
