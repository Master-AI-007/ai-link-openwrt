#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-LINK v2.3.2 双源合并审计报告 (Consolidated Audit Round 1~5) + Apple级视觉与壁纸级3D星图 全量自动化验收套件
"""
import importlib.util
import json
import os
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from _paths import ROOT, DAEMON

spec = importlib.util.spec_from_file_location("ailink_daemon", str(DAEMON))
dmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmod)

passed = 0
failed = 0
failures = []


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}" + (f"  [{detail}]" if detail else ""))
    else:
        failed += 1
        failures.append((name, detail))
        print(f"  FAIL  {name}" + (f"  [{detail}]" if detail else ""))


print("=" * 78)
print(" AI-LINK v2.3.2 合并审计报告 (Round 1~5) & 壁纸级 3D 星图 E2E 回归套件")
print("=" * 78)

with tempfile.TemporaryDirectory(prefix="ailink_audit_e2e_") as tmpdir:
    tmp_conf = Path(tmpdir)
    from http.server import ThreadingHTTPServer
    dmod.CONF_DIR = tmp_conf
    dmod.WEBUI_DIR = ROOT / "root/usr/share/ai-link/webui"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), dmod.AILinkRequestHandler)
    srv_port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    BASE_URL = f"http://127.0.0.1:{srv_port}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def raw_req(path, method="GET", body=None, headers=None):
        hdrs = dict(headers or {})
        data = body
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        elif isinstance(body, str):
            data = body.encode("utf-8")
        req = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method, headers=hdrs)
        try:
            with opener.open(req, timeout=8) as r:
                raw = r.read()
                return r.status, dict(r.headers), raw
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    # --- [Round 1] Security & 21-field OPS_PERSIST_KEYS ---
    print("\n[Round 1] P0/P1 安全边界、CSRF、PBKDF2 密码哈希与 21 字段持久化")
    check("C-P0-09: OPS_PERSIST_KEYS 完整覆盖 21 项设置",
          len(dmod.OPS_PERSIST_KEYS) >= 21 and {"ipv6_leak_guard", "ipv6_leak_mode", "topology_mode", "tcp_mss_clamp"}.issubset(set(dmod.OPS_PERSIST_KEYS)),
          f"count={len(dmod.OPS_PERSIST_KEYS)}")

    st_csrf, _, body_csrf = raw_req("/api/ops/settings", "POST", {"block_quic": False}, {"Origin": "http://evil.example.com"})
    check("C-P0-02: 跨源 POST 请求被 CSRF 守卫拦截 (403 csrf_forbidden)",
          st_csrf == 403 and b"csrf_forbidden" in body_csrf, f"status={st_csrf}")

    st_unauth_bk, _, _ = raw_req("/api/ops/backup_archive", "GET", headers={"X-Enforce-Auth": "1"})
    check("C-P0-01: 未携带有效令牌访问 /api/ops/backup_archive 返回 401",
          st_unauth_bk == 401, f"status={st_unauth_bk}")

    st_login, _, body_login = raw_req("/api/login", "POST", {"password": "ai-link-2026"})
    tok = json.loads(body_login.decode("utf-8")).get("token", "")
    auth_hdr = {"X-AI-Link-Token": tok}

    st_ssrf, _, body_ssrf = raw_req("/api/subscriptions/add", "POST", {"name": "Evil", "url": "file:///etc/shadow"}, auth_hdr)
    check("C-P0-04 & C-P1-13: 订阅 URL 拒绝 file:// 协议 (400)",
          st_ssrf == 400, f"status={st_ssrf}")

    # --- [Round 2] Ring-Buffer DNS Stats, Real WOL & Diagnostic Guards ---
    print("\n[Round 2] P0/P1 假数据清零、DNS 环形缓冲统计与 WOL 校验")
    dns_up = dmod.build_dns_upstream_stats(tmp_conf)
    up_rates = [u.get("cache_hit_rate") for u in dns_up.get("upstreams", [])]
    check("C-P0-07: 冷启动 DNS 上游统计无硬编码假数据 (82.4/76.8/79.5)",
          not any(r in (82.4, 76.8, 79.5) for r in up_rates), f"rates={up_rates}")

    st_wol_bad, _, _ = raw_req("/api/wol", "POST", {"mac": "00:00:00:00:00:00"}, auth_hdr)
    st_wol_ok, _, body_wol_ok = raw_req("/api/wol", "POST", {"mac": "BC:24:11:45:67:89", "broadcast_ip": "127.0.0.1"}, auth_hdr)
    check("C-P1-07: /api/wol 拒绝全零占位 MAC (400) 且真实发送 102 字节 Magic Packet",
          st_wol_bad == 400 and st_wol_ok == 200 and json.loads(body_wol_ok.decode("utf-8")).get("packet_bytes") == 102,
          f"bad={st_wol_bad}, ok={st_wol_ok}")

    # --- [Round 3] Transport-Aware Node Dedup, Gzip, Reference Reconcile & Validation ---
    print("\n[Round 3] P1/P2 节点传输层指纹、Gzip 压缩、引用自愈与参数校验")
    n_ws1 = {"type": "vless", "server": "cdn.example.com", "server_port": 443, "uuid": "u1", "transport": {"type": "ws", "path": "/vless-a", "headers": {"Host": "a.example.com"}}}
    n_ws2 = {"type": "vless", "server": "cdn.example.com", "server_port": 443, "uuid": "u1", "transport": {"type": "ws", "path": "/vless-b", "headers": {"Host": "b.example.com"}}}
    check("C-P1-02: 同主机端口不同 WS path/Host 的节点生成独立 node_id 与 node_key",
          dmod.compute_node_id(n_ws1) != dmod.compute_node_id(n_ws2) and dmod.compute_node_key(n_ws1) != dmod.compute_node_key(n_ws2),
          f"{dmod.compute_node_id(n_ws1)} != {dmod.compute_node_id(n_ws2)}")

    st_gz, hdr_gz, raw_gz = raw_req("/nexus.js", "GET", headers={"Accept-Encoding": "gzip"})
    check("C-P1-01 & C-P2-01: 静态资源支持 Gzip 压缩 (<110KB) 与 Cache-Control 缓存头",
          st_gz == 200 and hdr_gz.get("Content-Encoding") == "gzip" and len(raw_gz) < 110 * 1024 and "max-age=86400" in hdr_gz.get("Cache-Control", ""),
          f"gzip_bytes={len(raw_gz)}")

    st_bad_json, _, _ = raw_req("/api/ops/settings", "POST", "{bad_json", auth_hdr)
    st_bad_enum, _, _ = raw_req("/api/shunt/update", "POST", {"routing_mode": "invalid_mode_xyz"}, auth_hdr)
    check("C-P1-22 & C-P2-15: 畸形 JSON 与非法枚举均返回 HTTP 400",
          st_bad_json == 400 and st_bad_enum == 400, f"bad_json={st_bad_json}, bad_enum={st_bad_enum}")

    # --- [Round 4 & Round 5] Accessibility, 12px Font Floor, Apple HIG & Wallpaper 3D Galaxy ---
    print("\n[Round 4 & 5] 无障碍契约、12px 字号下限、Apple HIG 材质与壁纸级 3D 星图 E2E")
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    chrome_opts = Options()
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1600,960"]:
        chrome_opts.add_argument(arg)
    driver = webdriver.Chrome(options=chrome_opts)
    try:
        driver.get("about:blank")
        three_js_src = (ROOT / "root/usr/share/ai-link/webui/assets/three.min.js").read_text(encoding="utf-8")
        driver.execute_script(three_js_src)
        html_raw = (ROOT / "root/usr/share/ai-link/webui/index.html").read_text(encoding="utf-8")
        import re as _re
        html_clean = _re.sub(r"<script[^>]+src=[^>]+></script>", "", html_raw)
        driver.execute_script("""
            window.fetch = async function(u, o) {
                return { status: 200, ok: true, json: async () => ({ ok: true }) };
            };
            document.open();
            document.write(arguments[0]);
            document.close();
        """, html_clean)
        driver.execute_script((ROOT / "root/usr/share/ai-link/webui/nexus3d.js").read_text(encoding="utf-8"))
        driver.execute_script((ROOT / "root/usr/share/ai-link/webui/nexus.js").read_text(encoding="utf-8"))
        time.sleep(1.0)
        ui_audit = driver.execute_script("""
            const controls = Array.from(document.querySelectorAll('input:not([type="hidden"]), select, textarea'));
            const unlabeled = controls.filter(el => {
                if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.getAttribute('title') || el.getAttribute('placeholder')) return false;
                if (el.closest('label')) return false;
                if (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)) return false;
                return true;
            });
            const wpBtn = document.getElementById('wallpaper-toggle');
            const wpHud = document.getElementById('wallpaper-hud');
            if (wpBtn) wpBtn.click();
            const shell = document.getElementById('scene-shell');
            const wpActive = shell && shell.classList.contains('wallpaper-mode');
            const sc = window.__nexusScene;
            const hasEcliptic = Boolean(sc && sc.eclipticPlane);
            const hasCometTrails = Boolean(sc && sc.packets && sc.packets.length && sc.packets[0].trailSprites && sc.packets[0].trailSprites.length === 3);
            if (wpBtn) wpBtn.click();
            return {
                unlabeledCount: unlabeled.length,
                hasWpBtn: Boolean(wpBtn),
                hasWpHud: Boolean(wpHud),
                wpActive,
                hasEcliptic,
                hasCometTrails
            };
        """)
        check("C-P1-15: 全部表单控件 100% 具备无障碍标签 (unlabeledCount == 0)",
              ui_audit.get("unlabeledCount") == 0, str(ui_audit))
        check("Round 5 (壁纸级 3D 星图与沉浸模式): 包含黄道星盘网格、3阶彗尾流光粒子与一键壁纸沉浸模式 (#wallpaper-toggle & #wallpaper-hud)",
              ui_audit.get("hasWpBtn") and ui_audit.get("hasWpHud") and ui_audit.get("wpActive") and ui_audit.get("hasEcliptic") and ui_audit.get("hasCometTrails"),
              str(ui_audit))
    finally:
        driver.quit()
        httpd.shutdown()

print("\n" + "=" * 78)
print(f" 合计 {passed + failed} 项，通过 {passed}，失败 {failed}")
print("=" * 78)
raise SystemExit(0 if failed == 0 else 1)
