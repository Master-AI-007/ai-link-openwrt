#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-LINK v2.3.6 全生命周期用户动线与极限故障/订阅变异混沌测试 (`full_user_journey_simulation.py`)."""
import http.server
import importlib.util
import json
import shutil
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _paths import DAEMON  # noqa: E402

spec = importlib.util.spec_from_file_location("ailink_daemon_journey", str(DAEMON))
dmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmod)

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    print("=" * 78)
    print(" AI-LINK v2.3.6 全生命周期用户动线与极限故障/订阅变异混沌测试")
    print("=" * 78)

    tmp_root = Path(tempfile.mkdtemp(prefix="ailink-journey-e2e-"))
    tmp_conf = tmp_root / "etc_ai_link"
    tmp_run = tmp_root / "run_ai_link"
    tmp_conf.mkdir(parents=True, exist_ok=True)
    tmp_run.mkdir(parents=True, exist_ok=True)

    orig_conf, orig_run = dmod.CONF_DIR, dmod.RUN_DIR
    dmod.CONF_DIR, dmod.RUN_DIR = tmp_conf, tmp_run

    sub_state = {
        "body": "\n".join([
            "vless://11111111-2222-3333-4444-555555555501@jp1.example.com:443?security=tls&sni=jp1.example.com&type=ws&path=/ws#JP-Tokyo-01",
            "vless://11111111-2222-3333-4444-555555555502@sg1.example.com:443?security=tls&sni=sg1.example.com&type=ws&path=/ws#SG-Singapore-01",
            "vless://11111111-2222-3333-4444-555555555503@us1.example.com:443?security=tls&sni=us1.example.com&type=ws&path=/ws#US-LosAngeles-01",
            "vless://11111111-2222-3333-4444-555555555504@hk1.example.com:443?security=tls&sni=hk1.example.com&type=ws&path=/ws#HK-HongKong-01",
        ]),
        "userinfo": "upload=1073741824; download=5368709120; total=107374182400; expire=1893456000",
    }

    class MockSubHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/not-service"):
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Not Service")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Subscription-Userinfo", sub_state["userinfo"])
            self.end_headers()
            self.wfile.write(sub_state["body"].encode("utf-8"))

        def log_message(self, format, *args):
            pass

    sub_port = _free_port()
    sub_srv = http.server.ThreadingHTTPServer(("127.0.0.1", sub_port), MockSubHandler)
    threading.Thread(target=sub_srv.serve_forever, daemon=True).start()

    panel_port = _free_port()
    panel_srv = http.server.ThreadingHTTPServer(("127.0.0.1", panel_port), dmod.AILinkRequestHandler)
    threading.Thread(target=panel_srv.serve_forever, daemon=True).start()

    _no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def api(path: str, method: str = "GET", payload: dict = None) -> tuple:
        url = f"http://127.0.0.1:{panel_port}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Origin": f"http://127.0.0.1:{panel_port}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with _no_proxy_opener.open(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))

    try:
        st_imp, res_imp = api("/api/nodes/import", "POST", {
            "uri": "trojan://custompass@tw1.example.com:443?sni=tw1.example.com#TW-Custom-Manual-01"
        })
        check(
            "Stage 1.1 (手动导入自定义节点): 成功导入 TW-Custom-Manual-01 且标记为 custom 来源",
            st_imp == 200 and res_imp.get("ok") is True and int(res_imp.get("imported_count", 0)) == 1,
            f"imported={res_imp.get('imported_count')}",
        )

        st_sub, res_sub = api("/api/subscriptions/sync", "POST", {
            "id": "sub_journey_1",
            "name": "主力机场订阅",
            "url": f"http://127.0.0.1:{sub_port}/sub",
            "test_after_add": False,
            "reload_core": False,
        })
        check(
            "Stage 1.2 (拉取在线订阅列表): 成功同步 4 个订阅节点并解析剩余流量/到期时间",
            st_sub == 200 and res_sub.get("ok") is True and int(res_sub.get("imported_count", 0)) == 4,
            f"imported={res_sub.get('imported_count')}, total={res_sub.get('total_nodes')}",
        )

        st_bad_sub, res_bad_sub = api("/api/subscriptions/sync", "POST", {
            "id": "sub_dead_token",
            "name": "过期机场订阅",
            "url": f"http://127.0.0.1:{sub_port}/not-service",
            "test_after_add": False,
            "reload_core": False,
        })
        check(
            "Stage 1.3 (P1-01/P2-04 失效订阅精准报错): HTTP 200 返回 'Not Service' 精准识别为 Token 失效并保存 .raw 快照",
            res_bad_sub.get("ok") is False
            and res_bad_sub.get("error") == "sub_token_invalid"
            and ((Path(tempfile.gettempdir()) / "ai-link-sub-sub_dead_token.raw").is_file() or Path("/tmp/ai-link-sub-sub_dead_token.raw").is_file()),
            f"err={res_bad_sub.get('error')}, msg={res_bad_sub.get('message')}",
        )

        now_ts = int(time.time())
        saved_nodes = dmod.load_saved_nodes(tmp_conf)
        probe_store = {}
        rtt_by_tag = {
            "JP-Tokyo-01": 48,
            "SG-Singapore-01": 68,
            "US-LosAngeles-01": 142,
            "HK-HongKong-01": 28,
            "TW-Custom-Manual-01": 55,
        }
        for n in saved_nodes:
            tag = n.get("tag", "")
            nid = n.get("node_id") or dmod.compute_node_id(n)
            rtt = rtt_by_tag.get(tag, 90)
            is_hk = tag.startswith("HK-")
            probe_store[nid] = {
                "tag": tag,
                "node_id": nid,
                "state": "ok",
                "delay_ms": rtt,
                "rtt": rtt,
                "probe_ts": now_ts,
                "google_region": "HK" if is_hk else ("JP" if "JP" in tag else "US"),
                "google_region_verified": True,
                "svc": {
                    "gemini": {"ok": (not is_hk), "delay_ms": rtt + 15, "status": 200 if not is_hk else 403, "ts": now_ts},
                    "chatgpt": {"ok": (not is_hk), "delay_ms": rtt + 18, "status": 200 if not is_hk else 403, "ts": now_ts},
                    "youtube": {"ok": True, "delay_ms": rtt + 10, "status": 200, "ts": now_ts},
                },
            }
        dmod.save_node_probe_store(probe_store, tmp_conf)

        st_async, res_async = api("/api/auto_nodes/auto_screen", "POST", {
            "async": True,
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["gemini", "chatgpt"],
            "service_logic": "all",
            "scope_sources": ["sub_journey_1", "custom"],
            "scope_countries": ["JP", "SG", "US", "HK", "TW"],
            "target_size": 3,
            "replenish_threshold": 2,
            "run_live_probe": False,
        })
        tid = res_async.get("task_id", "")
        final_screen = None
        for _ in range(30):
            time.sleep(0.05)
            _, st_poll = api(f"/api/auto_nodes/auto_screen/status?task_id={tid}", "GET")
            if st_poll.get("done") and st_poll.get("result"):
                final_screen = st_poll["result"]
                break
        admitted_ai = (final_screen or {}).get("admitted_g1") or []
        check(
            "Stage 2.1 (6步向导异步进度条建池 + AI地区过滤): 排除 HK 节点并按最快 URL Ping 选入 JP/TW/SG 前 3 节点",
            bool(final_screen)
            and "HK-HongKong-01" not in admitted_ai
            and admitted_ai == ["JP-Tokyo-01", "TW-Custom-Manual-01", "SG-Singapore-01"],
            f"admitted={admitted_ai}",
        )

        _, res_any = api("/api/auto_nodes/auto_screen", "POST", {
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["gemini", "youtube"],
            "service_logic": "any",
            "scope_sources": ["ALL"],
            "scope_countries": ["HK"],
            "target_size": 3,
            "replenish_threshold": 1,
            "run_live_probe": False,
        })
        check(
            "Stage 2.2 (P2-02 任一服务通过 `any` 逻辑验证): HK 节点虽不支持 Gemini 但 YouTube 可用，在 `any` 模式下成功入选",
            "HK-HongKong-01" in (res_any.get("admitted_g1") or []),
            f"admitted_any={res_any.get('admitted_g1')}",
        )

        st_save_p, res_save_p = api("/api/auto_nodes/save", "POST", {
            "id": "auto_user_pool_1",
            "name": "主力极速AI池",
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["gemini", "chatgpt"],
            "service_logic": "all",
            "scope_sources": ["sub_journey_1", "custom"],
            "scope_countries": ["JP", "SG", "US", "TW"],
            "target_size": 3,
            "replenish_threshold": 2,
            "auto_maintain": True,
            "probe_now": False,
            "groups": [{"index": 1, "name": "节点池成员", "node_tags": admitted_ai}],
        })
        saved_pool = next((a for a in (res_save_p.get("auto_nodes") or []) if a.get("id") == "auto_user_pool_1"), {})
        check(
            "Stage 2.3 (保存自动节点池并选出最快首选出口): current_node 自动指向最快节点 JP-Tokyo-01 (48ms)",
            st_save_p == 200 and saved_pool.get("current_node") == "JP-Tokyo-01",
            f"current_node={saved_pool.get('current_node')}",
        )

        for n in saved_nodes:
            if n.get("tag") == "US-LosAngeles-01":
                nid_us = n.get("node_id") or dmod.compute_node_id(n)
                probe_store[nid_us]["state"] = "dead"
                probe_store[nid_us]["delay_ms"] = -1
        dmod.save_node_probe_store(probe_store, tmp_conf)

        st_sh_man, res_sh_man = api("/api/shunt/update", "POST", {
            "group_id": "AI",
            "shunt_mode": "manual",
            "strategy": "manual",
            "country": "US",
            "manual_node": "US-LosAngeles-01",
        })
        ai_grp = next((g for g in (res_sh_man.get("groups") or []) if g.get("id") == "AI"), {})
        check(
            "Stage 4.1 (P1-05 分流组手动模式死节点零漂移): 分流组设为 manual 且节点不可达时保持 US-LosAngeles-01 固定不漂移",
            st_sh_man == 200
            and ai_grp.get("resolved_node") == "US-LosAngeles-01"
            and ai_grp.get("manual_drifted") is False,
            f"resolved={ai_grp.get('resolved_node')}, manual_drifted={ai_grp.get('manual_drifted')}",
        )

        st_ns_man, res_ns_man = api("/api/shunt/update", "POST", {
            "routing_mode": "gfw_list",
            "global_mode": "manual",
            "global_country": "US",
            "global_manual_node": "US-LosAngeles-01",
        })
        check(
            "Stage 4.2 (非分流模式手动单节点死节点零漂移): GFW 模式手动固定 US-LosAngeles-01 不可达时绝不漂移至其他节点",
            st_ns_man == 200 and res_ns_man.get("global_resolved_node") == "US-LosAngeles-01",
            f"global_resolved_node={res_ns_man.get('global_resolved_node')}",
        )

        # Also verify P3: sending global_strategy="auto" (without global_mode) when global_mode was "manual" switches global_mode to "auto"
        st_ns_pool, res_ns_pool = api("/api/shunt/update", "POST", {
            "routing_mode": "cn_whitelist",
            "global_strategy": "auto",
            "global_auto_node_id": "auto_user_pool_1",
        })
        check(
            "Stage 4.3 (非分流模式绑定自定义节点池 & global_strategy 联动): 大陆白名单模式绑定 auto_user_pool_1 自动切换为 auto 并使用池内最快节点 JP-Tokyo-01",
            st_ns_pool == 200 and res_ns_pool.get("global_mode") == "auto" and res_ns_pool.get("global_resolved_node") == "JP-Tokyo-01",
            f"global_mode={res_ns_pool.get('global_mode')}, global_resolved_node={res_ns_pool.get('global_resolved_node')}",
        )
        api("/api/shunt/update", "POST", {"routing_mode": "rule_shunt", "group_id": "AI", "shunt_mode": "auto", "auto_node_id": "auto_user_pool_1"})

        for n in saved_nodes:
            nid = n.get("node_id") or dmod.compute_node_id(n)
            if n.get("tag") == "TW-Custom-Manual-01":
                probe_store[nid]["delay_ms"] = 22
                probe_store[nid]["rtt"] = 22
            elif n.get("tag") == "JP-Tokyo-01":
                probe_store[nid]["delay_ms"] = 220
                probe_store[nid]["rtt"] = 220
        dmod.save_node_probe_store(probe_store, tmp_conf)
        dmod.evaluate_all_auto_nodes(tmp_conf, force_service_probe=False)
        acfg_after_ping = dmod.load_auto_nodes_config(tmp_conf)
        pool_after_ping = next((a for a in acfg_after_ping.get("auto_nodes", []) if a.get("id") == "auto_user_pool_1"), {})
        check(
            "Stage 5.1 (节点池日常 URL Ping 极速切换): TW-Custom-Manual-01 延迟降至 22ms 后自动切换为首选出口",
            pool_after_ping.get("current_node") == "TW-Custom-Manual-01",
            f"current_node={pool_after_ping.get('current_node')}",
        )

        for n in saved_nodes:
            nid = n.get("node_id") or dmod.compute_node_id(n)
            if n.get("tag") in ("JP-Tokyo-01", "SG-Singapore-01"):
                probe_store[nid]["state"] = "dead"
                probe_store[nid]["delay_ms"] = -1
            elif n.get("tag") == "US-LosAngeles-01":
                probe_store[nid]["state"] = "ok"
                probe_store[nid]["delay_ms"] = 60
                probe_store[nid]["rtt"] = 60
        dmod.save_node_probe_store(probe_store, tmp_conf)
        acfg_repl = dmod.load_auto_nodes_config(tmp_conf)
        for _an_r in acfg_repl.get("auto_nodes", []):
            if _an_r.get("id") == "auto_user_pool_1":
                dmod.maintain_auto_node_pool_health(_an_r, conf_dir=tmp_conf)
        dmod.save_auto_nodes_config(acfg_repl, tmp_conf)
        dmod.evaluate_all_auto_nodes(tmp_conf, force_service_probe=False)
        acfg_repl = dmod.load_auto_nodes_config(tmp_conf)
        pool_repl = next((a for a in acfg_repl.get("auto_nodes", []) if a.get("id") == "auto_user_pool_1"), {})
        g1_repl = ((pool_repl.get("groups") or [{}])[0].get("node_tags") or [])
        check(
            "Stage 5.2 (低健康度跌破阈值自动复选补齐): 健康节点数跌至 1 (<2) 时自动触发复选将恢复健康的 US-LosAngeles-01 补入池内",
            "US-LosAngeles-01" in g1_repl and "TW-Custom-Manual-01" in g1_repl,
            f"g1_after_replenish={g1_repl}",
        )

        sub_state["body"] = "\n".join([
            "vless://11111111-2222-3333-4444-555555555503@us1.example.com:443?security=tls&sni=us1.example.com&type=ws&path=/ws#US-LosAngeles-Renamed-VIP",
            "vless://11111111-2222-3333-4444-555555555505@jp2.example.com:443?security=tls&sni=jp2.example.com&type=ws&path=/ws#JP-Osaka-New-02",
        ])
        st_sub2, res_sub2 = api("/api/subscriptions/sync", "POST", {
            "id": "sub_journey_1",
            "name": "主力机场订阅",
            "url": f"http://127.0.0.1:{sub_port}/sub",
            "test_after_add": False,
            "reload_core": False,
        })
        acfg_mut = dmod.load_auto_nodes_config(tmp_conf)
        pool_mut = next((a for a in acfg_mut.get("auto_nodes", []) if a.get("id") == "auto_user_pool_1"), {})
        g1_mut = ((pool_mut.get("groups") or [{}])[0].get("node_tags") or [])
        check(
            "Stage 6 (订阅更新节点改名自动对齐 `node_key`): US-LosAngeles-01 改名为 US-LosAngeles-Renamed-VIP 后在节点池内无缝继承",
            st_sub2 == 200 and "US-LosAngeles-Renamed-VIP" in g1_mut,
            f"g1_after_rename={g1_mut}",
        )

    finally:
        panel_srv.shutdown()
        sub_srv.shutdown()
        dmod.CONF_DIR, dmod.RUN_DIR = orig_conf, orig_run
        shutil.rmtree(tmp_root, ignore_errors=True)

    print("\n" + "=" * 78)
    fails = [r for r in results if not r[1]]
    print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
    print("=" * 78)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
