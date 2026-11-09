# -*- coding: utf-8 -*-
"""v1.0.2 RC 安全验收（真机 + 从开发机模拟「局域网未鉴权客户端」）。

做法：
  1. 设备本机（回环，永远可信）把 require_lan_auth 打开
  2. 开发机 10.10.10.62 作为「未鉴权局域网客户端」发请求，检查：
       · GET /            不应再下发 ailink_token Cookie（SEC-1）
       · GET /api/status  应返回脱敏数据（SEC-2/SEC-3）
       · GET /api/ops/backup 应 401
  3. 设备本机把 require_lan_auth 关回去，并确认局域网恢复可用

用法：设置 AI_LINK_DEVICE_PASS 后 python rc_accept.py
"""
import json
import re
import sys

import devssh

DEV_IP = "10.10.10.77"
PC_IP = "10.10.10.62"
PORT = 9099
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def main():
    c = devssh.connect()
    q = lambda cmd, t=60: devssh.run(c, cmd, timeout=t)[1]   # noqa: E731

    def dev_curl(path, method="GET", data=None):
        d = f" -X {method} -H 'Content-Type: application/json' -d '{data}'" if data else ""
        return q(f"curl -s --noproxy '*' -m 15{d} http://127.0.0.1:{PORT}{path}")

    print("=" * 74)
    print(" v1.0.2 RC 安全验收")
    print("=" * 74)
    print("版本:", q("cat /etc/ai-link/version").strip())
    print("鉴权配置(前):", dev_curl("/api/ops/settings")[:160])

    print("\n[0] 打开 require_lan_auth（设备本机回环，无需令牌）")
    r = dev_curl("/api/ops/settings", "POST", '{"require_lan_auth": true}')
    print("  ", r[:160])
    auth_on = '"require_lan_auth":true' in r.replace(" ", "")
    check("require_lan_auth 已开启", auth_on)

    try:
        import urllib.request
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def pc_get(path, timeout=20):
            req = urllib.request.Request(f"http://{DEV_IP}:{PORT}{path}")
            try:
                with opener.open(req, timeout=timeout) as resp:
                    return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
            except Exception as e:  # noqa: BLE001
                return 0, {}, f"{type(e).__name__}: {e}"

        print("\n[1] SEC-1: 未鉴权访问首页不应下发令牌")
        st, hdrs, _ = pc_get("/")
        cookie = hdrs.get("Set-Cookie", "")
        check("GET / 不返回 Set-Cookie", "ailink_token" not in cookie, cookie[:60] or "<无>")

        print("\n[2] SEC-2/SEC-3: 未鉴权 /api/status 应脱敏")
        st, _, body = pc_get("/api/status")
        check("/api/status 仍可用（不要求 401）", st == 200, f"HTTP {st}")
        blob = body
        check("不含回家密码明文", "ailink_home_2026" not in blob)
        check("不含回家 uuid 明文", not re.search(r'"uuid":"[0-9a-f]{8}-[0-9a-f]{4}', blob))
        check("不含 homelink private_key", '"private_key":"***' in blob or "private_key" not in blob)
        check("homelink uri 已遮", "://***@" in blob or '"uri"' not in blob)
        check("订阅 token 已遮", "token=***" in blob or "token=" not in blob)
        try:
            j = json.loads(body)
            hl = (j.get("homelink") or {}).get("nodes") or []
            print(f"      homelink 节点数 {len(hl)}，首个 uri: {(hl[0].get('uri') or '')[:48] if hl else '<无>'}")
            subs = j.get("subscriptions") or []
            print(f"      订阅数 {len(subs)}，首个 url: {(subs[0].get('url') or '')[:60] if subs else '<无>'}")
        except Exception as e:  # noqa: BLE001
            print("      解析失败:", e)

        print("\n[3] 受保护接口未鉴权应 401")
        st, _, _ = pc_get("/api/ops/backup")
        check("GET /api/ops/backup -> 401", st == 401, f"HTTP {st}")
    finally:
        print("\n[4] 恢复 require_lan_auth=false")
        r = dev_curl("/api/ops/settings", "POST", '{"require_lan_auth": false}')
        print("  ", r[:160])

    # 局域网恢复
    import urllib.request
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://{DEV_IP}:{PORT}/api/status", timeout=20) as resp:
            body2 = resp.read().decode("utf-8", "replace")
        check("局域网恢复后 /api/status 可用", resp.status == 200)
        check("恢复后回到完整数据（含 homelink 明文密码）", "ailink_home_2026" in body2,
              "说明脱敏只作用于未鉴权客户端" if "ailink_home_2026" in body2 else "未见明文，可能无回家节点")
    except Exception as e:  # noqa: BLE001
        check("局域网恢复后 /api/status 可用", False, str(e))

    print("\n[5] 设备本机（回环）仍应拿到完整数据")
    st_body = dev_curl("/api/status")
    check("回环 /api/status 未脱敏", "ailink_home_2026" in st_body)

    print("\n[6] svc_state 探针")
    stt = q("/etc/init.d/ai-link svc_state").strip()
    print("  ", stt)
    m = re.search(r"core=(\d)", stt)
    check("core 正确反映 sing-box（pidof 探针）", bool(m) and m.group(1) == "1", stt)

    c.close()
    print("\n" + "=" * 74)
    fails = [x for x in results if not x[1]]
    print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
    for n, ok, d in results:
        if not ok:
            print(f"   ✗ {n}  {d}")
    print("=" * 74)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
