# -*- coding: utf-8 -*-
"""检查 /api/status 与 /api/ops/backup 在未鉴权时返回什么（只读）。"""
import json
import re
import sys

import devssh


def main():
    c = devssh.connect()
    q = lambda cmd: devssh.run(c, cmd, timeout=120)[1]   # noqa: E731

    body = q("curl -s --noproxy '*' http://127.0.0.1:9099/api/status")
    print(f"/api/status 字节数: {len(body)}")
    for kw in ("password", "token", "uuid", "private_key", "psk", "panel_secret"):
        for m in re.finditer(kw, body, re.I):
            print(f"  [{kw}] ...{body[max(0, m.start() - 80):m.start() + 60]}...")
            break

    bak = q("curl -s --noproxy '*' -m 30 http://127.0.0.1:9099/api/ops/backup")
    print(f"\n/api/ops/backup 字节数: {len(bak)}")
    try:
        j = json.loads(bak)
        print("  顶层键:", list(j)[:15])
        for k in ("nodes", "subscriptions", "panel_auth"):
            if k in j:
                v = j[k]
                print(f"  {k}: {type(v).__name__} len={len(v) if hasattr(v, '__len__') else '-'}")
        if "nodes" in j and isinstance(j["nodes"], list) and j["nodes"]:
            n0 = j["nodes"][0]
            print("  首个节点字段:", list(n0)[:20])
            print("  首个节点是否含凭据:", {k: bool(n0.get(k)) for k in ("uuid", "password", "private_key", "psk") if k in n0})
    except Exception as e:  # noqa: BLE001
        print("  非 JSON:", e, bak[:300])
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
