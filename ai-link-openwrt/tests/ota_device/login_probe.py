# -*- coding: utf-8 -*-
"""面板登录接口的最小验证：错误密码必须 401 且不返回令牌；正确密码需要用户提供，不在此测试。"""
import json
import sys

import devssh


def main():
    c = devssh.connect()
    q = lambda cmd: devssh.run(c, cmd, timeout=40)[1]   # noqa: E731
    body = '{"password":"definitely-wrong-123"}'
    out = q(f"curl -s --noproxy '*' -m 10 -o /tmp/login.out -w '%{{http_code}}' "
            f"-X POST -H 'Content-Type: application/json' -d '{body}' http://127.0.0.1:9099/api/login")
    resp = q("cat /tmp/login.out")
    print(f"错误密码 -> HTTP {out.strip()}")
    print("响应:", resp.strip()[:200])
    ok = out.strip() == "401" and '"token"' not in resp
    print("PASS 拒绝错误密码且不签发令牌" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
