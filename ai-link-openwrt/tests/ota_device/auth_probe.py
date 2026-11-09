# -*- coding: utf-8 -*-
"""面板鉴权面探测（只读请求，不修改任何东西）。

检查项：
  1. `GET /` 未登录时是否下发 ailink_token Cookie（若能，密码形同虚设）
  2. 用该 Cookie 访问需要鉴权的 /api/* 是否放行
  3. 不带任何凭据直接访问 /api/* 在局域网内是否放行（trusted_cidr 默认值）
  4. /api/status 是否泄露敏感字段

用法：设置 AI_LINK_DEVICE_PASS 后 python auth_probe.py [--host 10.10.10.77]
"""
import argparse
import re
import sys

import devssh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="10.10.10.77")
    ap.add_argument("--port", default="9099")
    args = ap.parse_args()

    c = devssh.connect()
    q = lambda cmd: devssh.run(c, cmd, timeout=60)[1]   # noqa: E731
    base = f"http://{args.host}:{args.port}"

    print("=== 1) GET / 是否下发令牌 Cookie（未登录）===")
    hdr = q(f"curl -s --noproxy '*' -D - -o /dev/null {base}/ | tr -d '\\r'")
    cookies = [l for l in hdr.splitlines() if l.lower().startswith("set-cookie")]
    print("  响应头 Set-Cookie:", cookies or "<无>")
    token = ""
    for l in cookies:
        m = re.search(r"ailink_token=([^;]+)", l)
        if m:
            token = m.group(1)

    print("\n=== 2) 用该 Cookie 访问需要鉴权的接口 ===")
    if token:
        code = q(f"curl -s --noproxy '*' -o /dev/null -w '%{{http_code}}' -H 'Cookie: ailink_token={token}' "
                 f"{base}/api/ops/settings").strip()
        print(f"  Cookie 访问 /api/ops/settings -> {code}")
        code2 = q(f"curl -s --noproxy '*' -o /dev/null -w '%{{http_code}}' -H 'X-AI-Link-Token: {token}' "
                  f"{base}/api/nodes").strip()
        print(f"  Token 头访问 /api/nodes -> {code2}")
    else:
        print("  未取得 Cookie，跳过")

    print("\n=== 3) 不带任何凭据访问 /api/*（本机回环 vs 局域网地址）===")
    for label, host in (("回环 127.0.0.1", "127.0.0.1"), (f"局域网 {args.host}", args.host)):
        for path in ("/api/status", "/api/ops/settings", "/api/nodes", "/api/ops/backup"):
            code = q(f"curl -s --noproxy '*' -m 8 -o /dev/null -w '%{{http_code}}' http://{host}:{args.port}{path}").strip()
            print(f"  {label:<18} {path:<20} -> {code}")

    print("\n=== 4) ops_settings 现行鉴权配置 ===")
    print("  " + q(f"curl -s --noproxy '*' {base}/api/ops/settings | head -c 500"))

    print("\n=== 5) /api/status 是否含敏感信息（截取关键字）===")
    body = q(f"curl -s --noproxy '*' {base}/api/status")
    for kw in ("password", "secret", "token", "uuid", "private_key", "psk"):
        hits = len(re.findall(kw, body, re.I))
        print(f"  {kw:<12} 命中 {hits} 次")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
