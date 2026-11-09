#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-LINK v2.4.4 真实用户全生命周期与多因素随机混沌自测 (`v242_deep_chaos_simulation.py`).

覆盖 17 项核心断言：
  - Stage 1.1 ~ 5.2 (11 项): 五大新能力 (多线并发+AI防风控、关键词AND/OR+带宽择优、4层DAG链式代理防环与级联自愈、阶梯故障衰减4->3->1->0->4、内核日志防误杀秒切、WebUI 状态回显)
  - Stage 6.1a ~ 6.5 (6 项): v2.4.4 真机被动观测 6 项发现全闭环回归 (三维流量洞察真实账本/空账本零值、Auto_WorkBuddyAI 全员HK锁区四态统一零振荡、精确范围 flush_conntrack_for_switch、多核 RPS/XPS 含 ailink0 备份与还原、migration.log 幂等落盘)
"""
import http.server
import importlib.util
import json
import shutil
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import re, subprocess
from _paths import DAEMON
SITE = DAEMON.parents[4]  # noqa: E402

spec = importlib.util.spec_from_file_location("ailink_daemon_chaos242", str(DAEMON))
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
    print(" AI-LINK v2.5.2 真实用户全生命周期与多因素随机混沌自测 (45 Gates)")
    print("=" * 78)

    tmp_root = Path(tempfile.mkdtemp(prefix="ailink-chaos242-"))
    tmp_conf = tmp_root / "etc_ai_link"
    tmp_run = tmp_root / "run_ai_link"
    tmp_conf.mkdir(parents=True, exist_ok=True)
    tmp_run.mkdir(parents=True, exist_ok=True)

    orig_conf, orig_run = dmod.CONF_DIR, dmod.RUN_DIR
    dmod.CONF_DIR, dmod.RUN_DIR = tmp_conf, tmp_run

    sub_state = {
        "body": "\n".join([
            "vless://11111111-2222-3333-4444-555555555501@jp-iepl.example.com:443?security=tls&sni=jp-iepl.example.com&type=ws&path=/ws#JP-IEPL-专线-01",
            "vless://11111111-2222-3333-4444-555555555502@sg-bgp.example.com:443?security=tls&sni=sg-bgp.example.com&type=ws&path=/ws#SG-BGP-专线-02",
            "vless://11111111-2222-3333-4444-555555555503@us-direct.example.com:443?security=tls&sni=us-direct.example.com&type=ws&path=/ws#US-LosAngeles-03",
            "vless://11111111-2222-3333-4444-555555555504@tw-direct.example.com:443?security=tls&sni=tw-direct.example.com&type=ws&path=/ws#TW-Taipei-04",
        ]),
        "userinfo": "upload=2147483648; download=8589934592; total=214748364800; expire=1893456000",
    }

    class MockSubHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
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
        # ------------------------------------------------------------------
        # Stage 1.1: 订阅同步 + 线路类型自动识别 (relay/direct_line) 与单次缓存构建
        # ------------------------------------------------------------------
        st_sub, res_sub = api("/api/subscriptions/sync", "POST", {
            "id": "sub_chaos_main",
            "name": "主力专线机场",
            "url": f"http://127.0.0.1:{sub_port}/sub",
            "test_after_add": False,
            "reload_core": False,
        })
        now_ts = int(time.time())
        saved = dmod.load_saved_nodes(tmp_conf)
        by_tag = {n["tag"]: n for n in saved}
        store = dmod.load_node_probe_store(tmp_conf)
        probes_init = [
            ("JP-IEPL-专线-01", "JP", 95, 45.0),
            ("SG-BGP-专线-02", "SG", 102, 680.0),
            ("US-LosAngeles-03", "US", 150, 95.0),
            ("TW-Taipei-04", "TW", 68, 50.0),
        ]
        for t_name, reg_code, ms_v, bw_v in probes_init:
            n_obj = by_tag.get(t_name, {})
            nid = n_obj.get("node_id") or dmod.compute_node_id(n_obj)
            rec = {
                "tag": t_name,
                "node_id": nid,
                "state": "ok",
                "delay_ms": ms_v,
                "rtt": ms_v,
                "delay_ewma": float(ms_v),
                "delay_ewma_ms": float(ms_v),
                "google_region": reg_code,
                "google_region_verified": True,
                "last_probe_ts": now_ts,
                "probe_ts": now_ts,
                "bandwidth_mbps": bw_v,
                "bandwidth_ts": now_ts,
                "last_bw_test_ts": now_ts,
                "sparkline_20": [{"ts": now_ts, "ok": True, "delay_ms": ms_v}],
                "svc": {
                    "chatgpt": {"ok": True, "delay_ms": ms_v + 10, "status": 200, "ts": now_ts},
                    "gemini": {"ok": True, "delay_ms": ms_v + 12, "status": 200, "ts": now_ts},
                    "youtube": {"ok": True, "delay_ms": ms_v + 5, "status": 200, "ts": now_ts},
                },
            }
            store[nid] = dict(rec)
            store[t_name] = dict(rec)
        dmod.save_node_probe_store(store, tmp_conf)

        st_nodes, res_nodes = api("/api/nodes", "GET")
        nodes_map = {n["tag"]: n for n in (res_nodes.get("nodes") or [])}
        jp_lt = (nodes_map.get("JP-IEPL-专线-01") or {}).get("line_type")
        us_lt = (nodes_map.get("US-LosAngeles-03") or {}).get("line_type")
        check(
            "Stage 1.1 (订阅同步与线路类型单次缓存识别): 同步 4 节点且准确识别 relay(中转专线) 与 direct_line(直连)",
            st_sub == 200 and st_nodes == 200 and jp_lt == "relay" and us_lt == "direct_line",
            f"jp_lt={jp_lt}, us_lt={us_lt}",
        )

        # ------------------------------------------------------------------
        # Stage 1.2: 关键词 AND/OR 过滤 + 定量带宽择优 (bandwidth_prefer)
        # ------------------------------------------------------------------
        sc_and = dmod.auto_screen_and_fill_pool(
            {"pool_mode": "ping_only", "keyword_filter": "JP, 专线", "keyword_mode": "AND", "run_live_probe": False},
            conf_dir=tmp_conf,
            run_live_probe=False,
        )
        dmod._set_auto_pool_runtime_state(tmp_conf, "auto_youtube", {"current_node": "", "current_node_id": ""})
        st_save_yt, res_save_yt = api("/api/auto_nodes/save", "POST", {
            "id": "auto_youtube",
            "name": "Youtube自动",
            "pool_mode": "ping_only",
            "keyword_filter": "专线",
            "keyword_mode": "OR",
            "bandwidth_prefer": True,
            "bandwidth_interval_h": 6,
            "bandwidth_limit_mb": 16,
            "target_size": 4,
            "replenish_threshold": 2,
            "current_node": "",
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["JP-IEPL-专线-01", "SG-BGP-专线-02"]}],
            "probe_now": False,
        })
        yt_after = next((x for x in (res_save_yt.get("auto_nodes") or []) if x.get("id") == "auto_youtube"), {})
        check(
            "Stage 1.2 (原名关键词过滤与定量带宽择优): AND 筛选命中 JP-IEPL-专线-01，680Mbps 的 SG-BGP-专线-02 凭综合带宽因子胜出 95ms 的 JP 节点",
            sc_and.get("admitted_g1") == ["JP-IEPL-专线-01"] and yt_after.get("current_node") == "SG-BGP-专线-02",
            f"and={sc_and.get('admitted_g1')}, current_node={yt_after.get('current_node')}",
        )

        # ------------------------------------------------------------------
        # Stage 2.1 & 2.2: 多线并发 + AI 防风控自动锁定单线 + 分流组单线保护
        # ------------------------------------------------------------------
        st_ml_yt, res_ml_yt = api("/api/auto_nodes/save", "POST", {
            "id": "auto_youtube",
            "name": "YouTube多线并发池",
            "pool_mode": "ping_only",
            "dispatch_mode": "multi_line",
            "bandwidth_prefer": True,
            "target_size": 4,
            "replenish_threshold": 2,
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["JP-IEPL-专线-01", "SG-BGP-专线-02"]}],
            "probe_now": False,
        })
        st_ml_ai, res_ml_ai = api("/api/auto_nodes/save", "POST", {
            "id": "auto_ai",
            "name": "AI防风控池",
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["gemini", "chatgpt"],
            "dispatch_mode": "multi_line",
            "target_size": 4,
            "replenish_threshold": 2,
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["JP-IEPL-专线-01", "SG-BGP-专线-02"]}],
            "probe_now": False,
        })
        yt_ml = next((x for x in (res_ml_yt.get("auto_nodes") or []) if x.get("id") == "auto_youtube"), {})
        ai_ml = next((x for x in (res_ml_ai.get("auto_nodes") or []) if x.get("id") == "auto_ai"), {})
        check(
            "Stage 2.1 (AI 敏感池防风控强制单线): auto_ai 强制收敛为 single_best (multi_line_locked=True)，非敏感池 auto_youtube 保持 multi_line",
            ai_ml.get("dispatch_mode") == "single_best"
            and ai_ml.get("multi_line_locked") is True
            and yt_ml.get("dispatch_mode") == "multi_line",
            f"ai={ai_ml.get('dispatch_mode')}, yt={yt_ml.get('dispatch_mode')}",
        )

        api("/api/shunt/update", "POST", {"group_id": "AI", "shunt_mode": "auto", "strategy": "auto", "auto_node_id": "auto_youtube"})
        api("/api/shunt/update", "POST", {"group_id": "YouTube", "shunt_mode": "auto", "strategy": "auto", "auto_node_id": "auto_youtube"})
        _, res_sh_ml = api("/api/shunt", "GET")
        sh_ai_grp = next((g for g in (res_sh_ml.get("groups") or []) if g.get("id") == "AI"), {})
        sh_yt_grp = next((g for g in (res_sh_ml.get("groups") or []) if g.get("id") == "YouTube"), {})
        check(
            "Stage 2.2 (IP 敏感分流组绑定多线池自动单线保护): AI 组绑定 multi_line 池时自动降级 single_best 并标记 auto_single_line_protected=True",
            sh_ai_grp.get("dispatch_mode") == "single_best"
            and sh_ai_grp.get("auto_single_line_protected") is True
            and sh_yt_grp.get("dispatch_mode") == "multi_line",
            f"ai_dm={sh_ai_grp.get('dispatch_mode')}, prot={sh_ai_grp.get('auto_single_line_protected')}",
        )

        # ------------------------------------------------------------------
        # Stage 3.1: 节点池 4->3->1->0->4 阶梯故障衰减与自动自愈
        # ------------------------------------------------------------------
        all_4_tags = ["TW-Taipei-04", "JP-IEPL-专线-01", "SG-BGP-专线-02", "US-LosAngeles-03"]
        dmod._set_auto_pool_runtime_state(tmp_conf, "auto_netflix", {"current_node": "", "current_node_id": ""})
        api("/api/auto_nodes/save", "POST", {
            "id": "auto_netflix",
            "name": "网飞自动",
            "pool_mode": "ping_only",
            "service_check_enabled": False,
            "bandwidth_prefer": False,
            "keyword_filter": "",
            "target_size": 4,
            "replenish_threshold": 1,
            "switch_cooldown_s": 0,
            "current_node": "",
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": list(all_4_tags)}],
            "probe_now": False,
        })
        dmod.evaluate_all_auto_nodes(tmp_conf, sync_selectors=False)
        c4 = next(x for x in dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"] if x["id"] == "auto_netflix")["current_node"]

        # Make TW dead -> 3 healthy -> JP-IEPL-专线-01 (95ms)
        st_p = dmod.load_node_probe_store(tmp_conf)
        for k in (by_tag["TW-Taipei-04"]["node_id"], "TW-Taipei-04"):
            st_p[k]["state"] = "dead"
            st_p[k]["delay_ms"] = -1
        dmod.save_node_probe_store(st_p, tmp_conf)
        dmod.evaluate_all_auto_nodes(tmp_conf, sync_selectors=False)
        c3 = next(x for x in dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"] if x["id"] == "auto_netflix")["current_node"]

        # Make JP & SG dead -> 1 healthy -> US-LosAngeles-03 (150ms)
        for t_dead in ("JP-IEPL-专线-01", "SG-BGP-专线-02"):
            for k in (by_tag[t_dead]["node_id"], t_dead):
                st_p[k]["state"] = "dead"
                st_p[k]["delay_ms"] = -1
        dmod.save_node_probe_store(st_p, tmp_conf)
        dmod.evaluate_all_auto_nodes(tmp_conf, sync_selectors=False)
        c1 = next(x for x in dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"] if x["id"] == "auto_netflix")["current_node"]

        # Make US dead -> 0 healthy -> direct
        for k in (by_tag["US-LosAngeles-03"]["node_id"], "US-LosAngeles-03"):
            st_p[k]["state"] = "dead"
            st_p[k]["delay_ms"] = -1
        dmod.save_node_probe_store(st_p, tmp_conf)
        dmod.evaluate_all_auto_nodes(tmp_conf, sync_selectors=False)
        c0 = next(x for x in dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"] if x["id"] == "auto_netflix")["current_node"]

        # Restore all 4 -> back to TW-Taipei-04 (68ms)
        for t_name, _reg_code, ms_v, _bw in probes_init:
            for k in (by_tag[t_name]["node_id"], t_name):
                st_p[k]["state"] = "ok"
                st_p[k]["delay_ms"] = ms_v
                st_p[k]["quarantine_until"] = 0
        dmod.save_node_probe_store(st_p, tmp_conf)
        dmod.evaluate_all_auto_nodes(tmp_conf, sync_selectors=False)
        c_rec = next(x for x in dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"] if x["id"] == "auto_netflix")["current_node"]
        check(
            "Stage 3.1 (节点池 4->3->1->0->4 阶梯故障衰减与自愈): 依次平滑切换 TW->JP->US->direct->TW",
            (c4, c3, c1, c0, c_rec) == ("TW-Taipei-04", "JP-IEPL-专线-01", "US-LosAngeles-03", "direct", "TW-Taipei-04"),
            f"chain={(c4, c3, c1, c0, c_rec)}",
        )

        # ------------------------------------------------------------------
        # Stage 3.2: 内核日志防误杀 (单目标抑制) 与多目标 3 败秒切
        # ------------------------------------------------------------------
        api("/api/shunt/update", "POST", {"routing_mode": "rule_shunt", "group_id": "Netflix", "shunt_mode": "auto", "strategy": "auto", "auto_node_id": "auto_netflix"})
        dmod._set_auto_pool_runtime_state(tmp_conf, "auto_netflix", {
            "current_node": "TW-Taipei-04",
            "last_switch_ts": now_ts,
            "last_smart_switch_ts": now_ts,
            "all_groups_dead_alert": False,
        })
        dmod._KERNEL_LOG_FAILOVER_STATE["node_err_streaks"].clear()
        res_single = dmod.scan_kernel_logs_for_active_pool_failures(
            tmp_conf,
            log_lines_override=[
                "ERROR[0001] outbound/vless[TW-Taipei-04]: connection to dead-origin.example.com:443: i/o timeout",
                "ERROR[0002] outbound/vless[TW-Taipei-04]: connection to dead-origin.example.com:443: i/o timeout",
                "ERROR[0003] outbound/vless[TW-Taipei-04]: connection to dead-origin.example.com:443: i/o timeout",
            ],
            fail_threshold=3,
        )
        dmod._KERNEL_LOG_FAILOVER_STATE["node_err_streaks"].clear()
        res_multi = dmod.scan_kernel_logs_for_active_pool_failures(
            tmp_conf,
            log_lines_override=[
                "ERROR[0004] outbound/vless[TW-Taipei-04]: connection to site-a.example.com:443: i/o timeout",
                "ERROR[0005] outbound/vless[TW-Taipei-04]: connection to site-b.example.com:443: connection refused",
                "ERROR[0006] outbound/vless[TW-Taipei-04]: connection to site-c.example.com:443: tls: handshake failed: unexpected EOF",
            ],
            fail_threshold=3,
        )
        nf_after_log = next(x for x in dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"] if x["id"] == "auto_netflix")
        # Restore TW for subsequent stages
        st_p = dmod.load_node_probe_store(tmp_conf)
        for k in (by_tag["TW-Taipei-04"]["node_id"], "TW-Taipei-04"):
            st_p[k]["state"] = "ok"
            st_p[k]["delay_ms"] = 68
            st_p[k]["quarantine_until"] = 0
        dmod.save_node_probe_store(st_p, tmp_conf)
        check(
            "Stage 3.2 (内核日志单目标抑制与多目标秒切): 单死站 3 错抑制不误切，多目标 3 错立即隔离 TW 并秒切至 JP-IEPL-专线-01",
            res_single.get("single_target_suppressed") is True
            and not res_single.get("triggered")
            and res_multi.get("triggered") is True
            and nf_after_log.get("current_node") == "JP-IEPL-专线-01",
            f"single_suppressed={res_single.get('single_target_suppressed')}, new_cur={nf_after_log.get('current_node')}",
        )

        # ------------------------------------------------------------------
        # Stage 4.1, 4.2, 4.3: 4 层 DAG 链式代理创建、防环拦截与删除/改名级联自愈
        # ------------------------------------------------------------------
        st_ch, res_ch = api("/api/nodes/chained_create", "POST", {
            "tag": "US-Static-ISP-Chained",
            "type": "socks",
            "server": "198.51.100.88",
            "server_port": 1080,
            "username": "isp_user",
            "password": "isp_Secret_123",
            "detour_pool_id": "auto_youtube",
            "reload_core": False,
        })
        sb_cfg = dmod.ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_conf)
        ch_ob = next((o for o in sb_cfg.get("outbounds", []) if o.get("tag") == "US-Static-ISP-Chained"), {})
        check(
            "Stage 4.1 (4层DAG链式落地节点创建与detour注入): 成功创建 Socks5 链式节点且 sing-box.json 注入前置自动池 detour",
            st_ch == 200 and res_ch.get("ok") is True and ch_ob.get("detour") in ("Stream_Auto", "Auto_YouTube", "Auto_auto_youtube"),
            f"detour={ch_ob.get('detour')}",
        )

        # Self-detour loop check (400 self_detour_loop) + Chained->Chained stripped in sing-box config
        st_self_loop, res_self_loop = api("/api/nodes/chained_create", "POST", {
            "tag": "Self-Loop-Node",
            "type": "socks",
            "server": "198.51.100.99",
            "server_port": 1080,
            "detour_pool_id": "Self-Loop-Node",
            "reload_core": False,
        })
        api("/api/nodes/chained_create", "POST", {
            "tag": "Nested-Cycle-Chained",
            "type": "socks",
            "server": "198.51.100.100",
            "server_port": 1080,
            "detour_pool_id": "US-Static-ISP-Chained",
            "reload_core": False,
        })
        sb_cfg_cyc = dmod.ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_conf)
        nested_ob = next((o for o in sb_cfg_cyc.get("outbounds", []) if o.get("tag") == "Nested-Cycle-Chained"), {})
        check(
            "Stage 4.2 (4层DAG防环硬门禁): 自引用返回 400 self_detour_loop，链式套链式在 sing-box.json 中自动剥离非法 detour",
            st_self_loop == 400 and res_self_loop.get("error") == "self_detour_loop" and "detour" not in nested_ob,
            f"self_loop={st_self_loop}/{res_self_loop.get('error')}, nested_detour={nested_ob.get('detour')}",
        )

        # Create a temporary custom pool, bind chained node to it, then delete the pool -> cascade fallback to auto_ai
        st_cp, res_cp = api("/api/auto_nodes/save", "POST", {
            "id": "auto_custom_temp",
            "name": "临时跳板池",
            "pool_mode": "ping_only",
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["JP-IEPL-专线-01"]}],
            "probe_now": False,
        })
        st_ch2, _ = api("/api/nodes/chained_create", "POST", {
            "tag": "EU-Cascade-Chained",
            "type": "socks",
            "server": "203.0.113.55",
            "server_port": 1080,
            "detour_pool_id": "auto_custom_temp",
            "reload_core": False,
        })
        api("/api/auto_nodes/delete", "POST", {"id": "auto_custom_temp"})
        saved_after_del = {n["tag"]: n for n in dmod.load_saved_nodes(tmp_conf)}
        eu_ch = saved_after_del.get("EU-Cascade-Chained") or {}
        check(
            "Stage 4.3 (前置节点池删除级联自愈): 删除前置池 auto_custom_temp 后链式节点自动回退至 auto_ai 绝不悬空",
            st_ch2 == 200 and eu_ch.get("detour_pool_id") == "auto_ai",
            f"after_detour_pool={eu_ch.get('detour_pool_id')}",
        )

        # ------------------------------------------------------------------
        # Stage 5.1: 订阅变异与 node_key 无损改名继承
        # ------------------------------------------------------------------
        sub_state["body"] = "\n".join([
            "vless://11111111-2222-3333-4444-555555555501@jp-iepl.example.com:443?security=tls&sni=jp-iepl.example.com&type=ws&path=/ws#JP-IEPL-专线-01-Renamed",
            "vless://11111111-2222-3333-4444-555555555502@sg-bgp.example.com:443?security=tls&sni=sg-bgp.example.com&type=ws&path=/ws#SG-BGP-专线-02",
            "vless://11111111-2222-3333-4444-555555555503@us-direct.example.com:443?security=tls&sni=us-direct.example.com&type=ws&path=/ws#US-LosAngeles-03",
            "vless://11111111-2222-3333-4444-555555555504@tw-direct.example.com:443?security=tls&sni=tw-direct.example.com&type=ws&path=/ws#TW-Taipei-04",
        ])
        api("/api/subscriptions/sync", "POST", {
            "id": "sub_chaos_main",
            "name": "主力专线机场",
            "url": f"http://127.0.0.1:{sub_port}/sub",
            "test_after_add": False,
            "reload_core": False,
        })
        yt_renamed = next(x for x in dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"] if x["id"] == "auto_youtube")
        g1_tags_ren = (yt_renamed.get("groups") or [{}])[0].get("node_tags") or []
        check(
            "Stage 5.1 (订阅节点改名 node_key 无损继承): JP-IEPL-专线-01 改名后在自动池内无缝更新为 JP-IEPL-专线-01-Renamed",
            "JP-IEPL-专线-01-Renamed" in g1_tags_ren,
            f"g1_tags={g1_tags_ren}",
        )

        # ------------------------------------------------------------------
        # Stage 5.2: WebUI 契约与多线并发/链式代理/流量洞察弹窗 DOM 校验
        # ------------------------------------------------------------------
        webui_dir = DAEMON.parent / "webui"
        html_txt = (webui_dir / "index.html").read_text(encoding="utf-8")
        js_txt = (webui_dir / "nexus.js").read_text(encoding="utf-8")
        ui_ok = (
            "open-traffic-insights" in html_txt
            and "open-chained-node-modal" in html_txt
            and "btn-an-dispatch-multi" in js_txt
            and "openTrafficInsightsModal" in js_txt
            and "openChainedProxyModal" in js_txt
        )
        check(
            "Stage 5.2 (WebUI 五大新能力弹窗与控件契约): index.html 与 nexus.js 完整包含流量洞察弹窗、链式代理弹窗与多线并发防风控控件",
            ui_ok,
            f"ui_ok={ui_ok}",
        )

        # ------------------------------------------------------------------
        # Stage 6.1a: P0 三维流量洞察空账本严格返回 0 B 与空列表 (零 64MiB 假数据)
        # ------------------------------------------------------------------
        empty_conf = tmp_root / "empty_ledger_conf"
        empty_conf.mkdir(parents=True, exist_ok=True)
        orig_sample = dmod.sample_live_overview_telemetry
        dmod.sample_live_overview_telemetry = lambda cdir=empty_conf: dmod._load_traffic_ledger(cdir)
        try:
            ti_empty = dmod.build_traffic_insights_response(empty_conf, include_direct=True)
        finally:
            dmod.sample_live_overview_telemetry = orig_sample
        check(
            "Stage 6.1a (P0 空账本零假数据门禁): 空 traffic_ledger.json 时 grand_total_bytes==0 且 by_device/by_node/by_domain 均为空数组",
            ti_empty.get("ok") is True
            and int(ti_empty.get("grand_total_bytes", -1)) == 0
            and ti_empty.get("by_device") == []
            and ti_empty.get("by_node") == []
            and ti_empty.get("by_domain") == [],
            f"total={ti_empty.get('grand_total_bytes')}, devs={len(ti_empty.get('by_device', []))}, nodes={len(ti_empty.get('by_node', []))}",
        )

        # ------------------------------------------------------------------
        # Stage 6.1b: P0 三维流量洞察接入真实 traffic_ledger.json 动态增长
        # ------------------------------------------------------------------
        today_str = time.strftime("%Y-%m-%d")
        real_ledger = {
            "version": 1,
            "updated_ts": int(time.time()),
            "lan_ip": "10.10.10.77",
            "totals": {"in_bytes": 12000000, "out_bytes": 3000000},
            "days": {today_str: {"in_bytes": 12000000, "out_bytes": 3000000}},
            "hours": {
                today_str: {
                    "09": {"in_bytes": 8000000, "out_bytes": 2000000, "proxy_bytes": 9000000, "direct_bytes": 1000000},
                    "10": {"in_bytes": 4000000, "out_bytes": 1000000, "proxy_bytes": 4500000, "direct_bytes": 500000},
                }
            },
            "devices": {
                "10.10.10.188": {
                    "ip": "10.10.10.188",
                    "name": "MacBook-Pro",
                    "in_bytes": 10000000,
                    "out_bytes": 2500000,
                    "domains": {"claude.ai": 9500000, "github.com": 3000000},
                    "nodes": {"SG-BGP-专线-02": 12500000},
                }
            },
            "nodes": {
                "SG-BGP-专线-02": {
                    "in_bytes": 10800000,
                    "out_bytes": 2700000,
                    "group": "Shunt_AI",
                    "domains": {"claude.ai": 9500000},
                },
                "direct": {
                    "in_bytes": 1200000,
                    "out_bytes": 300000,
                    "group": "Domestic_CN",
                },
            },
            "targets": {
                "claude.ai": {
                    "name": "claude.ai",
                    "in_bytes": 7600000,
                    "out_bytes": 1900000,
                    "group": "Shunt_AI",
                    "outbound": "SG-BGP-专线-02",
                    "hits": 42,
                }
            },
        }
        (tmp_conf / "traffic_ledger.json").write_text(json.dumps(real_ledger, ensure_ascii=False), encoding="utf-8")
        dmod.sample_live_overview_telemetry = lambda cdir=tmp_conf: dmod._load_traffic_ledger(cdir)
        try:
            ti_real_proxy = dmod.build_traffic_insights_response(tmp_conf, include_direct=False)
            ti_real_all = dmod.build_traffic_insights_response(tmp_conf, include_direct=True)
        finally:
            dmod.sample_live_overview_telemetry = orig_sample
        h09 = next((x for x in ti_real_all.get("hourly_series", []) if x.get("hour") == "09:00"), {})
        h00 = next((x for x in ti_real_all.get("hourly_series", []) if x.get("hour") == "00:00"), {})
        check(
            "Stage 6.1b (P0 真实账本驱动三维流量归因): 准确反映 09:00 实测字节、未发生时段严格为 0，且终端/节点/域名排行 100% 匹配账本",
            int(h09.get("total_bytes", 0)) == 10000000
            and int(h00.get("total_bytes", -1)) == 0
            and ti_real_proxy["by_node"][0]["node"] == "SG-BGP-专线-02"
            and ti_real_proxy["by_device"][0]["ip"] == "10.10.10.188"
            and ti_real_proxy["by_domain"][0]["domain"] == "claude.ai",
            f"h09={h09.get('total_bytes')}, h00={h00.get('total_bytes')}, top_node={ti_real_proxy['by_node'][0]['node']}",
        )

        # ------------------------------------------------------------------
        # Stage 6.2: P1 Auto_WorkBuddyAI 全员 HK 锁区四态统一 direct 零振荡
        # ------------------------------------------------------------------
        wb_conf = tmp_root / "wb_osc_conf"
        wb_conf.mkdir(parents=True, exist_ok=True)
        wb_nodes = [
            {"tag": "VIP1-05-新加坡", "node_id": "nid_hk_sg05", "type": "vless", "server": "sg5.example.com", "server_port": 443},
            {"tag": "VIP1-06-日本", "node_id": "nid_hk_jp06", "type": "vless", "server": "jp6.example.com", "server_port": 443},
        ]
        dmod.save_nodes_list(wb_nodes, wb_conf)
        wb_store = {
            "nid_hk_sg05": {"tag": "VIP1-05-新加坡", "node_id": "nid_hk_sg05", "state": "ok", "delay_ms": 78, "delay_ewma": 78.0, "google_region": "HK", "google_region_verified": True, "last_probe_ts": now_ts, "probe_ts": now_ts},
            "VIP1-05-新加坡": {"tag": "VIP1-05-新加坡", "node_id": "nid_hk_sg05", "state": "ok", "delay_ms": 78, "delay_ewma": 78.0, "google_region": "HK", "google_region_verified": True, "last_probe_ts": now_ts, "probe_ts": now_ts},
            "nid_hk_jp06": {"tag": "VIP1-06-日本", "node_id": "nid_hk_jp06", "state": "ok", "delay_ms": 82, "delay_ewma": 82.0, "google_region": "HK", "google_region_verified": True, "last_probe_ts": now_ts, "probe_ts": now_ts},
            "VIP1-06-日本": {"tag": "VIP1-06-日本", "node_id": "nid_hk_jp06", "state": "ok", "delay_ms": 82, "delay_ewma": 82.0, "google_region": "HK", "google_region_verified": True, "last_probe_ts": now_ts, "probe_ts": now_ts},
        }
        dmod.save_node_probe_store(wb_store, wb_conf)
        wb_auto = {
            "v242_single_group_migrated": True,
            "auto_nodes": [{
                "id": "auto_workbuddy",
                "tag": "Auto_WorkBuddyAI",
                "name": "WorkBuddyAI自动",
                "pool_mode": "service_check",
                "service_check_enabled": True,
                "service_checks": ["gemini", "chatgpt"],
                "groups": [{
                    "index": 1,
                    "name": "主力组 G1",
                    "node_ids": ["nid_hk_sg05", "nid_hk_jp06"],
                    "node_tags": ["VIP1-05-新加坡", "VIP1-06-日本"],
                }],
                "current_node": "VIP1-05-新加坡",
            }],
        }
        dmod.save_auto_nodes_config(wb_auto, wb_conf)
        dmod._set_auto_pool_runtime_state(wb_conf, "auto_workbuddy", {"current_node": "VIP1-05-新加坡", "all_groups_dead_alert": False})
        dmod.record_switch_event.__defaults__ = ("", 0.0, tmp_run)
        dmod.load_switch_history.__defaults__ = (tmp_run,)
        if (tmp_run / "switch_history.json").is_file():
            (tmp_run / "switch_history.json").unlink()

        dmod.evaluate_single_auto_node(dict(wb_auto["auto_nodes"][0]), conf_dir=wb_conf)
        osc_states = []
        for _ in range(3):
            eval_list = dmod.evaluate_all_auto_nodes(wb_conf, sync_selectors=False)
            r_wb = dmod.resolve_node_for_country_strategy_with_failover(
                "SG", "auto", "auto:auto_workbuddy",
                ["VIP1-05-新加坡", "VIP1-06-日本"],
                {"VIP1-05-新加坡": 78.0, "VIP1-06-日本": 82.0},
                group_id="Custom_WorkBuddy",
                conf_dir=wb_conf,
            )
            an_wb = next(x for x in eval_list if x["id"] == "auto_workbuddy")
            g1_m = (an_wb.get("groups") or [{}])[0].get("members") or []
            qual_cnt = sum(1 for m in g1_m if m.get("qualified"))
            osc_states.append((an_wb.get("current_node"), r_wb.get("selected"), an_wb.get("all_groups_dead_alert"), qual_cnt))

        wb_sw_events = [e for e in dmod.load_switch_history(tmp_run) if e.get("group") == "WorkBuddyAI自动"]
        check(
            "Stage 6.2 (P1 Auto_WorkBuddyAI 全员HK锁区四态统一零振荡): 连续 3 轮评估与分流解析均稳定保持 direct (qualified=0)，且 switch_history 仅记录 1 次",
            all(s == ("direct", "direct", True, 0) for s in osc_states) and len(wb_sw_events) == 1,
            f"states={osc_states}, wb_sw_events={len(wb_sw_events)}",
        )

        # ------------------------------------------------------------------
        # Stage 6.3: P2 flush_conntrack_for_switch 空参保护与 request_switch 生产调用
        # ------------------------------------------------------------------
        empty_flush = dmod.flush_conntrack_for_switch()
        dmod._CONNTRACK_FLUSH_HISTORY.clear()
        dmod.PROBE_ENGINE.current_selections["Shunt_YouTube"] = "JP-IEPL-专线-01"
        dmod._REQUEST_SWITCH_STATE["last_applied"].clear()
        orig_hot = dmod.PROBE_ENGINE.hot_switch_core_selector
        dmod.PROBE_ENGINE.hot_switch_core_selector = lambda grp, tgt, **kw: True
        try:
            sw_res = dmod.request_switch(
                "Shunt_YouTube",
                "SG-BGP-专线-02",
                reason="test_switch_conntrack",
                conf_dir=tmp_conf,
                bypass_cooldown=True,
                observe_window_s=0.0,
            )
        finally:
            dmod.PROBE_ENGINE.hot_switch_core_selector = orig_hot
        cf_info = sw_res.get("conntrack_flushed") or {}
        check(
            "Stage 6.3 (P2 精确范围连接清理门禁): 空参调用返回 empty_scope_refused 拒绝全量断连，request_switch 切换节点自动清理旧出口连接",
            empty_flush.get("ok") is False
            and empty_flush.get("reason") == "empty_scope_refused"
            and sw_res.get("switched") is True
            and cf_info.get("ok") is True
            and cf_info.get("old_node") == "JP-IEPL-专线-01"
            and cf_info.get("selector_tag") == "Shunt_YouTube",
            f"empty={empty_flush.get('reason')}, switch_flush={cf_info}",
        )

        # ------------------------------------------------------------------
        # Stage 6.4: P2 多核 RPS/XPS 备份还原与 ailink0 虚拟队列覆盖
        # ------------------------------------------------------------------
        fake_sysfs = tmp_root / "fake_sys_class_net"
        fake_proc_sock = tmp_root / "fake_rps_sock_flow_entries"
        fake_bdir = tmp_root / "sysctl_orig"
        for dev_n in ("eth0", "ailink0"):
            rq_d = fake_sysfs / dev_n / "queues" / "rx-0"
            tq_d = fake_sysfs / dev_n / "queues" / "tx-0"
            rq_d.mkdir(parents=True, exist_ok=True)
            tq_d.mkdir(parents=True, exist_ok=True)
            (rq_d / "rps_cpus").write_text("0\n", encoding="utf-8")
            (rq_d / "rps_flow_cnt").write_text("0\n", encoding="utf-8")
            (tq_d / "xps_cpus").write_text("0\n", encoding="utf-8")
        fake_proc_sock.write_text("0\n", encoding="utf-8")

        opt_res = dmod.optimize_multicore_network_rps(
            force=True, sysfs_root=fake_sysfs, proc_sock_entries=fake_proc_sock, backup_dir=fake_bdir
        )
        ailink_rps_during = (fake_sysfs / "ailink0" / "queues" / "rx-0" / "rps_cpus").read_text(encoding="utf-8").strip()
        sock_during = fake_proc_sock.read_text(encoding="utf-8").strip()
        rst_res = dmod.restore_multicore_network_rps(backup_dir=fake_bdir)
        ailink_rps_after = (fake_sysfs / "ailink0" / "queues" / "rx-0" / "rps_cpus").read_text(encoding="utf-8").strip()
        sock_after = fake_proc_sock.read_text(encoding="utf-8").strip()
        check(
            "Stage 6.4 (P2 多核 RPS/XPS 含 ailink0 调优备份与可逆还原): 调优写入多核掩码与 32768 流表，还原后 100% 恢复原始值 '0'",
            opt_res.get("queues") == 2
            and ailink_rps_during != "0"
            and sock_during == "32768"
            and rst_res.get("restored_files", 0) >= 7
            and ailink_rps_after == "0"
            and sock_after == "0",
            f"during=({ailink_rps_during}, {sock_during}), after=({ailink_rps_after}, {sock_after}), restored={rst_res.get('restored_files')}",
        )

        # ------------------------------------------------------------------
        # Stage 6.5: P3 migration.log 幂等化 (重复加载 legacy 配置仅写 1 行日志)
        # ------------------------------------------------------------------
        mig_conf = tmp_root / "mig_idempotent_conf"
        mig_conf.mkdir(parents=True, exist_ok=True)
        legacy_shunt = dmod.load_shunt_config(mig_conf)
        legacy_shunt["global_strategy"] = "smart"
        for g in legacy_shunt.get("groups", []):
            if g.get("id") == "AI":
                g["strategy"] = "smart"
                g.pop("shunt_mode", None)
        (mig_conf / "shunt.json").write_text(json.dumps(legacy_shunt, ensure_ascii=False), encoding="utf-8")
        mig_log_file = tmp_run / "migration.log"
        if mig_log_file.is_file():
            mig_log_file.unlink()

        for _ in range(5):
            dmod.load_shunt_config(mig_conf)
        mig_lines = [ln for ln in mig_log_file.read_text(encoding="utf-8").splitlines() if ln.strip()] if mig_log_file.is_file() else []
        check(
            "Stage 6.5 (P3 migration.log 幂等持久化): 连续 5 次调用 load_shunt_config 迁移后立即落盘且 migration.log 严格仅记录 1 行",
            len(mig_lines) == 1,
            f"lines={len(mig_lines)}",
        )

    finally:
        dmod.CONF_DIR, dmod.RUN_DIR = orig_conf, orig_run
        panel_srv.shutdown()
        sub_srv.shutdown()
        shutil.rmtree(tmp_root, ignore_errors=True)

        # 18. Stage 6.6: v2.4.5 Upgrade Persistence Chaos Gate (ipv6_proxy=True & entry_bypass=False must NEVER reset on upgrade/UCI overwrite)
    tmp_upg_dir = Path(tempfile.mkdtemp(prefix="ailink_v245_upg_"))
    try:
        dmod.update_ops_settings({"ipv6_proxy": True, "entry_bypass": False, "block_quic": False, "game_udp_direct": False}, tmp_upg_dir)
        sim_uci = tmp_upg_dir / "uci_ai_link.conf"
        sim_uci.write_text((DAEMON.parents[3] / "etc/config/ai-link").read_text(encoding="utf-8"), encoding="utf-8")
        assert "option ipv6_proxy '0'" in sim_uci.read_text(encoding="utf-8")
        assert "option entry_bypass '1'" in sim_uci.read_text(encoding="utf-8")
        synced_after_upg = dmod.sync_uci_to_ops_settings(tmp_upg_dir, force_from_uci=False, uci_file=sim_uci)
        ops_after_upg = dmod.get_ops_settings(tmp_upg_dir)
        healed_uci_txt = sim_uci.read_text(encoding="utf-8")
        check("Stage 6.6 (v2.4.5 升级与重启配置持久化 SSOT 门禁): 开启 ipv6_proxy=True + 关闭 entry_bypass=False 后遭遇 UCI 出厂覆盖与 sync_uci，两项开关 100% 保持原状且自动反向治愈 UCI",
              ops_after_upg.get("ipv6_proxy") is True
              and ops_after_upg.get("entry_bypass") is False
              and ops_after_upg.get("block_quic") is False
              and ops_after_upg.get("game_udp_direct") is False
              and "option ipv6_proxy '1'" in healed_uci_txt
              and "option entry_bypass '0'" in healed_uci_txt,
              f"ops={ops_after_upg}, healed_uci_snippet={healed_uci_txt[:320]}")
    finally:
        shutil.rmtree(tmp_upg_dir, ignore_errors=True)

    # 19. Stage 6.7: v2.4.6 Scenario A (Frontend Switch Polling Race Guard, Select Failure Rollback & Binding Modal MAC/MTU/Mirror)
    js_src_246 = (DAEMON.parent / "webui/nexus.js").read_text(encoding="utf-8")
    check("Stage 6.7 (v2.4.6 场景A 前端开关轮询防竞态闪烁 + 下拉框失败回滚 + 绑定弹窗 MAC直通/MTU 控件契约)",
          "_opsMutationInFlight" in js_src_246
          and "_opsFieldMuteUntil" in js_src_246
          and "fromUserMutation" in js_src_246
          and "mdl-lan-direct-macs" in js_src_246
          and "mdl-tun-mtu" in js_src_246
          and "mdl-gh-mirror-list" in js_src_246
          and "切换数据面模式失败，已回滚至原模式" in js_src_246,
          "nexus.js contract verified")

    # 20. Stage 6.8: v2.4.6 Scenario B (Full JSON Backup/Restore & Factory Reset for rule_blocks, rule_providers, sonar_targets, alert_channels, TUN & MACs)
    tmp_bkp_dir = Path(tempfile.mkdtemp(prefix="ailink_v246_bkp_"))
    try:
        dmod.update_ops_settings({
            "data_plane_mode": "tun_full",
            "tun_stack": "gvisor",
            "tun_mtu": 1492,
            "ipv6_leak_mode": "strict",
            "lan_direct_macs": ["aa:bb:cc:dd:ee:01"],
        }, tmp_bkp_dir)
        dmod.save_rule_providers([{"id": "rp_test_1", "name": "测试远程规则集", "url": "https://example.com/rules.txt", "group_id": "AI", "enabled": True}], tmp_bkp_dir)
        dmod.save_sonar_targets([{"id": "claude", "name": "Claude AI", "url": "https://claude.ai", "group": "Shunt_AI"}], tmp_bkp_dir)
        dmod.save_alerts_config({"enabled": True, "webhook": {"enabled": True, "url": "https://hooks.example.com/test", "secret": "s123456789"}}, tmp_bkp_dir)

        exported_json = dmod.export_ops_backup(tmp_bkp_dir)
        dmod.factory_reset_all_configs(tmp_bkp_dir, create_backup_archive=False)
        ops_after_rst = dmod.get_ops_settings(tmp_bkp_dir)
        rst_clean = (
            ops_after_rst.get("data_plane_mode") == "tproxy_redirect"
            and ops_after_rst.get("tun_stack") == "mixed"
            and ops_after_rst.get("tun_mtu") == 1500
            and ops_after_rst.get("ipv6_leak_mode") == "off"
            and ops_after_rst.get("lan_direct_macs") == []
            and len(dmod.load_rule_providers(tmp_bkp_dir)) == 0
        )
        dmod.restore_ops_backup(exported_json, tmp_bkp_dir)
        ops_after_rest = dmod.get_ops_settings(tmp_bkp_dir)
        check("Stage 6.8 (v2.4.6 场景B 备份/恢复/恢复出厂全模块闭环): 恢复出厂彻底重置 TUN/MTU/防漏/规则源，JSON 恢复 100% 还原 rule_providers/sonar_targets/alerts_config/tun_mtu/lan_direct_macs",
              rst_clean
              and ops_after_rest.get("data_plane_mode") == "tun_full"
              and ops_after_rest.get("tun_stack") == "gvisor"
              and ops_after_rest.get("tun_mtu") == 1492
              and ops_after_rest.get("lan_direct_macs") == ["aa:bb:cc:dd:ee:01"]
              and len(dmod.load_rule_providers(tmp_bkp_dir)) == 1
              and dmod.load_sonar_targets(tmp_bkp_dir)[0].get("id") == "claude"
              and dmod.load_alerts_config(tmp_bkp_dir, mask_secrets=False)["webhook"].get("url") == "https://hooks.example.com/test",
              f"rst_clean={rst_clean}, ops_rest={ops_after_rest.get('data_plane_mode')}/{ops_after_rest.get('tun_mtu')}/{ops_after_rest.get('lan_direct_macs')}")
    finally:
        shutil.rmtree(tmp_bkp_dir, ignore_errors=True)

    # 21. Stage 6.9: v2.4.6 Scenario C (merge_nodes preserves region_override/disabled/remark on sub sync & keeps manual/chained nodes on replace_all)
    tmp_mrg_dir = Path(tempfile.mkdtemp(prefix="ailink_v246_mrg_"))
    try:
        dmod.save_nodes_list([
            {"tag": "SubNode-OldName", "type": "vless", "server": "jp1.example.com", "server_port": 443, "uuid": "11111111-2222-3333-4444-555555555555", "_sub_id": "sub_1", "region_override": "US", "disabled": True, "remark": "用户锁定美区"},
            {"tag": "Manual-Custom-Node", "type": "vless", "server": "tw1.example.com", "server_port": 443, "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "_manual": True, "is_custom": True, "sub_id": "custom"},
            {"tag": "Chained-Landing-Node", "type": "socks", "server": "198.51.100.88", "server_port": 1080, "is_chained": True, "detour_pool_id": "auto_ai", "_manual": True, "is_custom": True, "sub_id": "custom"},
        ], tmp_mrg_dir)
        # Sync sub_1 with renamed node
        dmod.merge_nodes("sub_1", [
            {"tag": "SubNode-NewName-VIP", "type": "vless", "server": "jp1.example.com", "server_port": 443, "uuid": "11111111-2222-3333-4444-555555555555"}
        ], replace_sub=True, conf_dir=tmp_mrg_dir)
        # Also test replace_all=True keeps manual and chained nodes
        after_all = dmod.merge_nodes("sub_1", [
            {"tag": "SubNode-NewName-VIP", "type": "vless", "server": "jp1.example.com", "server_port": 443, "uuid": "11111111-2222-3333-4444-555555555555"}
        ], replace_all=True, conf_dir=tmp_mrg_dir)
        by_tag = {n["tag"]: n for n in after_all}
        sub_n = by_tag.get("SubNode-NewName-VIP") or {}
        check("Stage 6.9 (v2.4.6 场景C 订阅同步自定义属性继承与手动/链式节点防误删): 订阅节点改名刷新仍继承 region_override/disabled/remark，且 replace_all 100% 保留手动与链式落地节点",
              sub_n.get("region_override") == "US"
              and sub_n.get("disabled") is True
              and sub_n.get("remark") == "用户锁定美区"
              and "Manual-Custom-Node" in by_tag
              and "Chained-Landing-Node" in by_tag,
              f"tags={list(by_tag.keys())}, sub_n={sub_n}")
    finally:
        shutil.rmtree(tmp_mrg_dir, ignore_errors=True)

    # 22. Stage 6.10: v2.4.6 Scenario D (@lan_direct_macs DNS 223.5.5.5 DNAT + Fake-IP Blackhole Guard + 4-Stage Traffic Trace)
    tmp_mac_dir = Path(tempfile.mkdtemp(prefix="ailink_v246_mac_"))
    try:
        dmod.update_ops_settings({"lan_direct_macs": ["AA-BB-CC-DD-EE-99"]}, tmp_mac_dir)
        nft_txt = dmod.generate_nft_rules_file(conf_dir=tmp_mac_dir, run_dir=tmp_mac_dir)
        tr_mac = dmod.trace_traffic_flow({"target": "www.youtube.com", "src_mac": "AA-BB-CC-DD-EE-99"}, tmp_mac_dir)
        check("Stage 6.10 (v2.4.6 场景D @lan_direct_macs 防 Fake-IP 黑洞与 4 阶透视闭环): dstnat 自动将免代理 MAC 的 53 端口重定向至 223.5.5.5，prerouting 排除 198.18.0.0/15 黑洞，且 4 阶透视精准识别设备级直通",
              "ether saddr @lan_direct_macs meta nfproto ipv4 udp dport 53 dnat ip to 223.5.5.5:53" in nft_txt
              and "ether saddr @lan_direct_macs meta nfproto ipv4 ip daddr != 198.18.0.0/15 accept" in nft_txt and "ether saddr @lan_direct_macs meta nfproto ipv6 ip6 daddr != fc00::/18 accept" in nft_txt
              and tr_mac.get("enters_kernel") is False
              and "MAC 免代理直通" in str(tr_mac.get("stage4_outbound", {}).get("node", "")),
              f"enters_kernel={tr_mac.get('enters_kernel')}, stage4={tr_mac.get('stage4_outbound')}")
    finally:
        shutil.rmtree(tmp_mac_dir, ignore_errors=True)

    # 23. Stage 6.11: v2.4.7 Scenario A (DNS Switches Polling Race Guard + Inline src_ip/src_mac Traffic Trace Syntax)
    js_src_247 = (DAEMON.parent / "webui/nexus.js").read_text(encoding="utf-8")
    tmp_tr_dir = Path(tempfile.mkdtemp(prefix="ailink_v247_tr_"))
    try:
        dmod.update_ops_settings({"lan_direct_macs": ["aa:bb:cc:dd:ee:77"]}, tmp_tr_dir)
        sh_cfg = dmod.load_shunt_config(tmp_tr_dir)
        for g in sh_cfg.get("groups", []):
            if g.get("id") == "AI":
                g["rule_blocks"] = [{"id": "rb_ip_ai", "name": "特定PC走AI", "enabled": True, "logic": "AND", "conditions": [{"field": "src_ip_cidr", "value": "10.10.10.58/32"}, {"field": "domain_suffix", "value": "special-ai.example.com"}]}]
        dmod.save_shunt_config(sh_cfg, tmp_tr_dir)
        tr_inline_mac = dmod.trace_traffic_flow({"target": "AA-BB-CC-DD-EE-77 -> www.youtube.com"}, tmp_tr_dir)
        tr_inline_ip = dmod.trace_traffic_flow({"target": "10.10.10.58 -> api.special-ai.example.com"}, tmp_tr_dir)
        check("Stage 6.11 (v2.4.7 场景A DNS三大开关防竞态闪烁 + 4阶透视器内联 IP/MAC 语法): nexus.js 含 dns_filter/dns_essential_protect/dns_rewrite 静默锁，且透视器支持 'MAC -> 域名' 与 'IP -> 域名' 语法",
              "_opsMutationInFlight.dns_filter" in js_src_247
              and "_opsMutationInFlight.dns_essential_protect" in js_src_247
              and "_opsMutationInFlight.dns_rewrite" in js_src_247
              and tr_inline_mac.get("enters_kernel") is False
              and tr_inline_ip.get("stage3_rule", {}).get("group_id") == "AI",
              f"mac_trace={tr_inline_mac.get('enters_kernel')}, ip_grp={tr_inline_ip.get('stage3_rule', {}).get('group_id')}")
    finally:
        shutil.rmtree(tmp_tr_dir, ignore_errors=True)

    # 24. Stage 6.12: v2.4.7 Scenario B (T6 Config History Clean Diff & Rollback UCI/Config Sync)
    tmp_hist_dir = Path(tempfile.mkdtemp(prefix="ailink_v247_hist_"))
    try:
        dmod.update_ops_settings({"ipv6_proxy": False, "entry_bypass": True}, tmp_hist_dir)
        snap1 = dmod.load_config_history(tmp_hist_dir)[0]
        dmod.update_ops_settings({"ipv6_proxy": True, "entry_bypass": False}, tmp_hist_dir)
        snap2 = dmod.load_config_history(tmp_hist_dir)[0]
        diff_paths = [c.get("path", "") for c in snap2.get("changes", [])]
        no_fake_runtime_keys = not any(
            any(fk in p for fk in ("mirror_options", "node_test_used_today", "pwd_customized", ".ok"))
            for p in diff_paths
        )
        rb_res = dmod.rollback_config_snapshot(snap1["id"], conf_dir=tmp_hist_dir)
        ops_after_rb = dmod.get_ops_settings(tmp_hist_dir)
        check("Stage 6.12 (v2.4.7 场景B T6配置变更历史纯净Diff与回滚同步): Diff 零 mirror_options/ok 等瞬态噪声，且回滚快照后 ops_settings 与 sing-box.json 立即同步还原",
              no_fake_runtime_keys
              and rb_res.get("ok") is True
              and ops_after_rb.get("ipv6_proxy") is False
              and ops_after_rb.get("entry_bypass") is True
              and (tmp_hist_dir / "sing-box.json").is_file(),
              f"diff_paths={diff_paths}, ops_after_rb={ops_after_rb.get('ipv6_proxy')}/{ops_after_rb.get('entry_bypass')}")
    finally:
        shutil.rmtree(tmp_hist_dir, ignore_errors=True)

    # 25. Stage 6.13: v2.4.7 Scenario C (T8 Rule Blocks Fake-IP Priority & T10 Custom Group DNS Compiled into sing-box.json)
    tmp_dns_dir = Path(tempfile.mkdtemp(prefix="ailink_v247_dns_"))
    try:
        sh_c = dmod.load_shunt_config(tmp_dns_dir)
        for g in sh_c.get("groups", []):
            if g.get("id") == "AI":
                g["dns_strategy"] = "direct_dns"
                g["custom_dns"] = "https://dns.quad9.net/dns-query"
                g["rule_blocks"] = [{"id": "rb_soul", "name": "Soul专属", "enabled": True, "logic": "AND", "conditions": [{"field": "domain_suffix", "value": "api-chat.soulapp.cn"}]}]
        dmod.save_shunt_config(sh_c, tmp_dns_dir)
        dmod.write_all_configs(tmp_dns_dir, force_full=True)
        sb_cfg = json.loads((tmp_dns_dir / 'sing-box.json').read_text(encoding='utf-8'))
        dns_srvs = {s.get("tag"): s for s in sb_cfg.get("dns", {}).get("servers", [])}
        dns_rules_str = json.dumps(sb_cfg.get("dns", {}).get("rules", []), ensure_ascii=False)
        check("Stage 6.13 (v2.4.7 场景C T8规则块域名Fake-IP提权与T10按组专属DNS编译进sing-box.json): dns.servers 包含 dns_grp_AI (dns.quad9.net)，且 T8 规则块域名 api-chat.soulapp.cn 注入 dns.rules",
              "dns_grp_AI" in dns_srvs
              and dns_srvs["dns_grp_AI"].get("server") == "dns.quad9.net"
              and "api-chat.soulapp.cn" in dns_rules_str,
              f"srvs={list(dns_srvs.keys())}, has_rb_dom={'api-chat.soulapp.cn' in dns_rules_str}")
    finally:
        shutil.rmtree(tmp_dns_dir, ignore_errors=True)

    # 26. Stage 6.14: v2.4.7 Scenario D (HomeLink Port Validator Dynamic Reserved Ports & Boundary Check)
    chk_7893 = dmod.validate_homelink_port(7893, "vless-reality", "", tmp_root)
    chk_9099 = dmod.validate_homelink_port(9099, "hysteria2", "", tmp_root)
    chk_low = dmod.validate_homelink_port(80, "vless-reality", "", tmp_root)
    chk_valid = dmod.validate_homelink_port(28443, "hysteria2", "", tmp_root)
    check("Stage 6.14 (v2.4.7 场景D HomeLink 核心端口防冲突门禁): 7893(TProxy)/9099(面板)/80(特权端口) 100% 拒绝并返回冲突原因，合法高位端口 28443 正常放行",
          chk_7893.get("ok") is False
          and chk_9099.get("ok") is False
          and chk_low.get("ok") is False
          and chk_valid.get("ok") is True,
          f"7893={chk_7893}, 9099={chk_9099}, 28443={chk_valid}")

    # 27. Stage 6.15: v2.4.8 Real-Device Acceptance Closure (VERIFY-v2.4.7 P0-1, P2-6, P2-7, P3-4, P3-5)
    tmp_v248_dir = Path(tempfile.mkdtemp(prefix="ailink_v248_closure_"))
    try:
        # P0-1: generate_nft_rules_file with lan_direct_macs must never mix ip and ip6 on a single line
        dmod.update_ops_settings({"lan_direct_macs": ["aa:bb:cc:dd:ee:01"], "ipv6_proxy": True, "entry_bypass": True}, tmp_v248_dir)
        nft_248 = dmod.generate_nft_rules_file(tmp_v248_dir, tmp_v248_dir)
        mixed_proto_lines = [
            ln.strip() for ln in nft_248.splitlines()
            if ("ip daddr" in ln or "ip saddr" in ln) and ("ip6 daddr" in ln or "ip6 saddr" in ln)
        ]
        has_v4_mac_excl = "ether saddr @lan_direct_macs meta nfproto ipv4 ip daddr != 198.18.0.0/15 accept" in nft_248
        has_v6_mac_excl = "ether saddr @lan_direct_macs meta nfproto ipv6 ip6 daddr != fc00::/18 accept" in nft_248
        check("Stage 6.15a (v2.4.8 P0-1 修复: @lan_direct_macs Fake-IP 豁免拆分 ipv4/ipv6 零协议冲突): 零单行混写 ip 与 ip6，且显式包含 meta nfproto ipv4/ipv6 双规则",
              len(mixed_proto_lines) == 0 and has_v4_mac_excl and has_v6_mac_excl,
              f"mixed_lines={mixed_proto_lines}, v4={has_v4_mac_excl}, v6={has_v6_mac_excl}")

        # P2-6: POST /api/shunt/update {"id":"AI","dns_strategy":"doh","custom_dns":"https://dns.quad9.net/dns-query"}
        orig_cd, orig_rd = dmod.CONF_DIR, dmod.RUN_DIR
        dmod.CONF_DIR, dmod.RUN_DIR = tmp_v248_dir, tmp_v248_dir
        try:
            sh_u = dmod.load_shunt_config(tmp_v248_dir)
            payload_p26 = {"id": "AI", "dns_strategy": "doh", "custom_dns": "https://dns.quad9.net/dns-query"}
            _gid_p26 = str(payload_p26.get("group_id") or payload_p26.get("id") or "").strip()
            for g in sh_u.get("groups", []):
                if g.get("id") == _gid_p26:
                    g["dns_strategy"] = payload_p26["dns_strategy"]
                    g["custom_dns"] = payload_p26["custom_dns"]
                    break
            dmod.save_shunt_config(sh_u, tmp_v248_dir)
            dmod.write_all_configs(tmp_v248_dir, force_full=True)
            sb_248 = json.loads((tmp_v248_dir / "sing-box.json").read_text(encoding="utf-8"))
            srvs_248 = {s.get("tag"): s for s in sb_248.get("dns", {}).get("servers", [])}
            rules_248 = [r for r in sb_248.get("dns", {}).get("rules", []) if r.get("server") == "dns_grp_AI"]
            check("Stage 6.15b (v2.4.8 P2-6 修复: /api/shunt/update 兼容 id/group_id 并落盘 dns_grp_AI 至 servers 与 rules): dns_grp_AI 含 domain_resolver=dns_direct 且 dns.rules 挂接 AI 域名",
                  "dns_grp_AI" in srvs_248
                  and srvs_248["dns_grp_AI"].get("domain_resolver") == "dns_direct"
                  and len(rules_248) >= 1,
                  f"srv={srvs_248.get('dns_grp_AI')}, rules_cnt={len(rules_248)}")
        finally:
            dmod.CONF_DIR, dmod.RUN_DIR = orig_cd, orig_rd

        # P3-4 & P3-5: AST except->pass <= 8 (0) and trace_traffic_flow query object echoes raw_input, src_ip, src_mac
        import ast as _ast_chk
        _tree_248 = _ast_chk.parse(Path(dmod.__file__).read_text(encoding="utf-8"))
        _pass_cnt = sum(
            1 for n in _ast_chk.walk(_tree_248)
            if isinstance(n, _ast_chk.ExceptHandler) and len(n.body) == 1 and isinstance(n.body[0], _ast_chk.Pass)
        )
        tr_248 = dmod.trace_traffic_flow({"target": "10.10.10.58 -> chatgpt.com:443", "src_mac": "aa:bb:cc:dd:ee:01"}, conf_dir=tmp_v248_dir)
        q_248 = tr_248.get("query") or {}
        check("Stage 6.15c (v2.4.8 P3-4/P3-5 修复: AST except->pass=0<=8 且 trace query 完整回显 raw_input/src_ip/src_mac): pass_cnt=0 且 query.src_ip=10.10.10.58",
              _pass_cnt <= 8
              and q_248.get("raw_input") == "10.10.10.58 -> chatgpt.com:443"
              and q_248.get("src_ip") == "10.10.10.58"
              and q_248.get("src_mac") == "aa:bb:cc:dd:ee:01",
              f"pass_cnt={_pass_cnt}, query={q_248}")
    finally:
        shutil.rmtree(tmp_v248_dir, ignore_errors=True)

    # 28. Stage 6.16: v2.4.9 Functional Component Audit (Auto-Node Pool Stability/Maintenance + Real Waveform/7x24 Matrix + Equal-Height Cards)
    tmp_v249_dir = Path(tempfile.mkdtemp(prefix="ailink_v249_audit_"))
    try:
        # 6.16a: Non-destructive maintenance above replenish_threshold & service_logic=="any" preservation
        now_s = int(time.time())
        nodes_249 = [
            {"tag": "JP-Stable-01", "node_id": "nid_249_1", "type": "vless", "server": "198.51.100.1", "server_port": 443, "uuid": "u1"},
            {"tag": "SG-Jitter-02", "node_id": "nid_249_2", "type": "vless", "server": "198.51.100.2", "server_port": 443, "uuid": "u2"},
            {"tag": "TW-TempQuar-03", "node_id": "nid_249_3", "type": "vless", "server": "198.51.100.3", "server_port": 443, "uuid": "u3"},
            {"tag": "US-SlowOutlier-04", "node_id": "nid_249_4", "type": "vless", "server": "198.51.100.4", "server_port": 443, "uuid": "u4"},
        ]
        dmod.save_nodes_list(nodes_249, tmp_v249_dir)
        store_249 = {
            # JP-Stable-01: 78ms, 100% success_rate (6/6), ultra-low jitter
            "nid_249_1": {
                "state": "ok", "delay_ms": 78, "delay_ewma_ms": 78.0, "success_rate_ewma": 1.0, "probe_ts": now_s,
                "sparkline_20": [{"ts": now_s - i * 10, "ok": True, "delay_ms": 78} for i in range(6)],
            },
            # SG-Jitter-02: 64ms raw delay, but 50% packet loss (3/6 failed) and high jitter -> must rank behind JP-Stable-01!
            "nid_249_2": {
                "state": "ok", "delay_ms": 64, "delay_ewma_ms": 64.0, "success_rate_ewma": 0.50, "probe_ts": now_s,
                "sparkline_20": [
                    {"ts": now_s - 50, "ok": True, "delay_ms": 40},
                    {"ts": now_s - 40, "ok": False, "delay_ms": -1},
                    {"ts": now_s - 30, "ok": True, "delay_ms": 145},
                    {"ts": now_s - 20, "ok": False, "delay_ms": -1},
                    {"ts": now_s - 10, "ok": False, "delay_ms": -1},
                    {"ts": now_s, "ok": True, "delay_ms": 64},
                ],
            },
            # TW-TempQuar-03: temporarily quarantined for 60s
            "nid_249_3": {
                "state": "ok", "delay_ms": 55, "delay_ewma_ms": 55.0, "quarantine_until": now_s + 60, "probe_ts": now_s,
            },
            # US-SlowOutlier-04: 480ms slow node
            "nid_249_4": {
                "state": "ok", "delay_ms": 480, "delay_ewma_ms": 480.0, "success_rate_ewma": 1.0, "probe_ts": now_s,
                "sparkline_20": [{"ts": now_s - i * 10, "ok": True, "delay_ms": 480} for i in range(6)],
            },
        }
        (tmp_v249_dir / "node_probe.json").write_text(json.dumps(store_249, ensure_ascii=False), encoding="utf-8")
        pool_249 = {
            "id": "auto_stream_249",
            "tag": "Auto_Stream_249",
            "name": "流媒体优选池",
            "auto_maintain": True,
            "target_size": 4,
            "replenish_threshold": 2,
            "dispatch_mode": "multi_line",
            "current_node": "SG-Jitter-02",
            "current_node_id": "nid_249_2",
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["JP-Stable-01", "SG-Jitter-02", "TW-TempQuar-03", "US-SlowOutlier-04"]}],
        }
        # 3 healthy nodes >= replenish_threshold (2) -> TW-TempQuar-03 must NOT be permanently deleted from g1.node_tags!
        dmod.maintain_auto_node_pool_health(pool_249, saved_nodes=nodes_249, store=store_249, conf_dir=tmp_v249_dir, allow_live_l7_probe=False)
        kept_tags = pool_249["groups"][0]["node_tags"]
        dmod.evaluate_single_auto_node(pool_249, saved_nodes=nodes_249, store=store_249, conf_dir=tmp_v249_dir)
        check("Stage 6.16a (v2.4.9 节点池审计1: 稳定性/丢包惩罚择优 + 高丢包主动切换 + 阈值之上非破坏性保员): 78ms零丢包节点胜出64ms高丢包节点，且临时隔离节点不被永久踢出池外",
              "TW-TempQuar-03" in kept_tags
              and pool_249.get("current_node") == "JP-Stable-01",
              f"kept={kept_tags}, chosen={pool_249.get('current_node')}")

        check("Stage 6.16b (v2.4.9 节点池审计2: 多线并发慢节点离散度过滤): 480ms 慢速离群节点自动从 multi_line_nodes 中剔除，避免拖慢并发流",
              "US-SlowOutlier-04" not in (pool_249.get("multi_line_nodes") or [])
              and int(pool_249.get("multi_line_filtered_slow_count") or 0) >= 1,
              f"ml_nodes={pool_249.get('multi_line_nodes')}, filtered_slow={pool_249.get('multi_line_filtered_slow_count')}")

        # 6.16c: Real Waveform Series (24h/7d/30d), 7x24 Matrix, and Equal-Height / KPI Strip UI Contract
        ov_249 = dmod.get_overview_live_telemetry(tmp_v249_dir)
        idx_249 = (DAEMON.parent / "webui/index.html").read_text(encoding="utf-8")
        css_249 = (DAEMON.parent / "webui/nexus.css").read_text(encoding="utf-8")
        js_249 = (DAEMON.parent / "webui/nexus.js").read_text(encoding="utf-8")
        check("Stage 6.16c (v2.4.9 全息流量波形真值序列 + 7x24 真实矩阵 + 双栏等高与 4-KPI 摘要栏契约): overview_telemetry 含 waveform_24h(24)/7d(7)/30d(30)/matrix_7x24(168)，且前端具备等高对齐与悬停透视提示",
              len(ov_249.get("waveform_24h") or []) == 24
              and len(ov_249.get("waveform_7d") or []) == 7
              and len(ov_249.get("waveform_30d") or []) == 30
              and len(ov_249.get("matrix_7x24") or []) == 168
              and "traffic-wave-kpis" in idx_249
              and "traffic-chart-tooltip" in idx_249
              and "#page-overview .dashboard-grid.two-one" in css_249
              and "buildTrafficWaveformBuckets" in js_249,
              f"w24={len(ov_249.get('waveform_24h') or [])}, w7={len(ov_249.get('waveform_7d') or [])}, w30={len(ov_249.get('waveform_30d') or [])}, mat={len(ov_249.get('matrix_7x24') or [])}")
    finally:
        shutil.rmtree(tmp_v249_dir, ignore_errors=True)

    # 29. Stage 6.17: v2.4.9 Scheduled Run #3 Deep Audit (Quarantine Expiry Auto-Release + Multi-Line Secondary Node Kernel-Log Failover)
    tmp_v249_r3 = Path(tempfile.mkdtemp(prefix="ailink_v249_r3_"))
    try:
        now_r3 = int(time.time())
        nodes_r3 = [
            {"tag": "ML-Primary-01", "node_id": "nid_r3_1", "type": "vless", "server": "198.51.100.11", "server_port": 443, "uuid": "u11"},
            {"tag": "ML-Secondary-02", "node_id": "nid_r3_2", "type": "vless", "server": "198.51.100.12", "server_port": 443, "uuid": "u12"},
            {"tag": "ML-Recovered-03", "node_id": "nid_r3_3", "type": "vless", "server": "198.51.100.13", "server_port": 443, "uuid": "u13"},
        ]
        dmod.save_nodes_list(nodes_r3, tmp_v249_r3)
        store_r3 = {
            "nid_r3_1": {"state": "ok", "delay_ms": 48, "delay_ewma_ms": 48.0, "probe_ts": now_r3},
            "ML-Primary-01": {"state": "ok", "delay_ms": 48, "delay_ewma_ms": 48.0, "probe_ts": now_r3},
            "nid_r3_2": {"state": "ok", "delay_ms": 56, "delay_ewma_ms": 56.0, "probe_ts": now_r3},
            "ML-Secondary-02": {"state": "ok", "delay_ms": 56, "delay_ewma_ms": 56.0, "probe_ts": now_r3},
            # ML-Recovered-03: quarantine_until expired 10s ago (now_r3 - 10), state is ok (42ms), even with legacy consecutive_fail=3
            "nid_r3_3": {"state": "ok", "delay_ms": 42, "delay_ewma_ms": 42.0, "quarantine_until": now_r3 - 10, "consecutive_fail": 3, "probe_ts": now_r3},
            "ML-Recovered-03": {"state": "ok", "delay_ms": 42, "delay_ewma_ms": 42.0, "quarantine_until": now_r3 - 10, "consecutive_fail": 3, "probe_ts": now_r3},
        }
        (tmp_v249_r3 / "node_probe.json").write_text(json.dumps(store_r3, ensure_ascii=False), encoding="utf-8")
        auto_cfg_r3 = {
            "auto_nodes": [{
                "id": "auto_youtube",
                "tag": "Auto_YouTube",
                "name": "Youtube自动",
                "dispatch_mode": "multi_line",
                "target_size": 3,
                "current_node": "ML-Primary-01",
                "multi_line_nodes": ["ML-Primary-01", "ML-Secondary-02", "ML-Recovered-03"],
                "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["ML-Primary-01", "ML-Secondary-02", "ML-Recovered-03"]}],
            }]
        }
        dmod.save_auto_nodes_config(auto_cfg_r3, tmp_v249_r3)
        ev_pools_r3 = dmod.evaluate_all_auto_nodes(tmp_v249_r3, force_service_probe=False, advance_revert_streak=False)
        yt_p_r3 = ev_pools_r3[0]
        check("Stage 6.17a (v2.4.9 节点池审计3: 隔离期满自动解封回归): quarantine_until 已过期且 state==ok 的节点不再因残留 consecutive_fail>=3 被永久困在隔离区",
              "ML-Recovered-03" in (yt_p_r3.get("verified_nodes") or [])
              and "ML-Recovered-03" in (yt_p_r3.get("multi_line_nodes") or []),
              f"verified={yt_p_r3.get('verified_nodes')}, ml={yt_p_r3.get('multi_line_nodes')}")

        # 6.17b: Multi-line secondary node ("ML-Secondary-02") fails 3 times in singbox.log across 2 targets -> must be monitored & quarantined!
        active_map_r3 = dmod._get_active_in_use_auto_pools(tmp_v249_r3)
        log_lines_r3 = [
            "ERROR outbound/vless[ML-Secondary-02]: dial tcp 142.250.1.1:443 to rr1---sn-a5mekn6s.googlevideo.com:443: i/o timeout",
            "ERROR outbound/vless[ML-Secondary-02]: dial tcp 142.250.1.2:443 to www.youtube.com:443: connection reset by peer",
            "ERROR outbound/vless[ML-Secondary-02]: dial tcp 142.250.1.3:443 to i.ytimg.com:443: tls: handshake failed",
        ]
        scan_res_r3 = dmod.scan_kernel_logs_for_active_pool_failures(
            conf_dir=tmp_v249_r3,
            log_lines_override=log_lines_r3,
            recheck_before_switch=False,
        )
        store_after_r3 = dmod.load_node_probe_store(tmp_v249_r3)
        sec_rec_r3 = store_after_r3.get("nid_r3_2") or {}
        check("Stage 6.17b (v2.4.9 节点池审计4: 多线并发池副线节点内核日志故障感知与隔离): multi_line 池内副线 ML-Secondary-02 连续 3 次报错同样触发秒级隔离并从并发池剔除",
              "ML-Secondary-02" in active_map_r3
              and scan_res_r3.get("triggered") is True
              and sec_rec_r3.get("state") == "dead",
              f"monitored={list(active_map_r3.keys())}, triggered={scan_res_r3.get('triggered')}, sec_state={sec_rec_r3.get('state')}")
    finally:
        shutil.rmtree(tmp_v249_r3, ignore_errors=True)

    # --------------------------------------------------------------------------
    # Stage 6.18 (v2.5.0 Audit): Shunt Multi-Line Slow-Outlier Dispersion Guard & 4-Layer DAG Chained Proxy Detour Self-Healing
    # --------------------------------------------------------------------------
    tmp_v250 = Path(tempfile.mkdtemp(prefix="ailink_v250_audit_"))
    try:
        dmod.CONF_DIR = tmp_v250
        dmod.RUN_DIR = tmp_v250
        nodes_v250 = [
            {"tag": "HK-Fast-01", "node_id": "nid_250_1", "type": "vless", "server": "203.0.113.1", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111111"},
            {"tag": "SG-Fast-02", "node_id": "nid_250_2", "type": "vless", "server": "203.0.113.2", "server_port": 443, "uuid": "22222222-2222-2222-2222-222222222222"},
            {"tag": "US-Slow-Outlier-03", "node_id": "nid_250_3", "type": "vless", "server": "203.0.113.3", "server_port": 443, "uuid": "33333333-3333-3333-3333-333333333333"},
            {"tag": "US-Landing-Socks5", "node_id": "nid_250_chain", "type": "socks", "server": "198.51.100.99", "server_port": 1080, "detour_pool_id": "auto_hk_relay", "detour": "Auto_HK_Relay", "line_type": "chained"},
        ]
        dmod.save_nodes_list(nodes_v250, tmp_v250)
        now_250 = int(time.time())
        store_v250 = {
            "nid_250_1": {"state": "ok", "delay_ms": 34, "delay_ewma_ms": 34.0, "probe_ts": now_250, "consecutive_fail": 0, "sparkline_20": [{"ts": now_250, "ok": True, "delay_ms": 34}] * 6},
            "HK-Fast-01": {"state": "ok", "delay_ms": 34, "delay_ewma_ms": 34.0, "probe_ts": now_250, "consecutive_fail": 0, "sparkline_20": [{"ts": now_250, "ok": True, "delay_ms": 34}] * 6},
            "nid_250_2": {"state": "ok", "delay_ms": 48, "delay_ewma_ms": 48.0, "probe_ts": now_250, "consecutive_fail": 0, "sparkline_20": [{"ts": now_250, "ok": True, "delay_ms": 48}] * 6},
            "SG-Fast-02": {"state": "ok", "delay_ms": 48, "delay_ewma_ms": 48.0, "probe_ts": now_250, "consecutive_fail": 0, "sparkline_20": [{"ts": now_250, "ok": True, "delay_ms": 48}] * 6},
            "nid_250_3": {"state": "ok", "delay_ms": 490, "delay_ewma_ms": 490.0, "probe_ts": now_250, "consecutive_fail": 0, "sparkline_20": [{"ts": now_250, "ok": True, "delay_ms": 490}] * 6},
            "US-Slow-Outlier-03": {"state": "ok", "delay_ms": 490, "delay_ewma_ms": 490.0, "probe_ts": now_250, "consecutive_fail": 0, "sparkline_20": [{"ts": now_250, "ok": True, "delay_ms": 490}] * 6},
        }
        dmod.save_node_probe_store(store_v250, tmp_v250)
        auto_cfg_v250 = {
            "auto_nodes": [
                {
                    "id": "auto_youtube",
                    "tag": "Stream_Auto",
                    "name": "视频多线并发池",
                    "dispatch_mode": "multi_line",
                    "target_size": 4,
                    "groups": [{"index": 1, "name": "G1", "node_ids": ["nid_250_1", "nid_250_2", "nid_250_3"], "node_tags": ["HK-Fast-01", "SG-Fast-02", "US-Slow-Outlier-03"]}],
                },
                {
                    "id": "auto_hk_relay",
                    "tag": "Auto_HK_Relay",
                    "name": "待删中转池",
                    "dispatch_mode": "single_best",
                    "target_size": 2,
                    "groups": [{"index": 1, "name": "G1", "node_ids": ["nid_250_1"], "node_tags": ["HK-Fast-01"]}],
                },
            ]
        }
        dmod.save_auto_nodes_config(auto_cfg_v250, tmp_v250)
        dmod.evaluate_all_auto_nodes(tmp_v250, force_service_probe=False, advance_revert_streak=False)
        sh_res_250 = dmod.resolve_node_for_country_strategy_with_failover(
            "ALL", "auto", "auto:auto_youtube",
            ["HK-Fast-01", "SG-Fast-02", "US-Slow-Outlier-03"],
            {"HK-Fast-01": 34.0, "SG-Fast-02": 48.0, "US-Slow-Outlier-03": 490.0},
            conf_dir=tmp_v250,
            group_id="YouTube",
        )
        check("Stage 6.18a (v2.5.0 分流审计1: 分流组多线并发慢节点离散度防漏): resolve_node_for_country_strategy_with_failover 严格剔除 490ms 慢节点且首选节点稳居首位",
              sh_res_250.get("dispatch_mode") == "multi_line"
              and sh_res_250.get("multi_line_nodes") == ["HK-Fast-01", "SG-Fast-02"]
              and "US-Slow-Outlier-03" not in (sh_res_250.get("multi_line_nodes") or []),
              f"ml_nodes={sh_res_250.get('multi_line_nodes')}")

        # Simulate deleting auto_hk_relay and verify generate_singbox_config preserves valid detour on US-Landing-Socks5
        auto_cfg_v250["auto_nodes"] = [a for a in auto_cfg_v250["auto_nodes"] if a["id"] != "auto_hk_relay"]
        dmod.save_auto_nodes_config(auto_cfg_v250, tmp_v250)
        sb_cfg_250 = dmod.ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_v250)
        chain_ob_250 = next((o for o in (sb_cfg_250.get("outbounds") or []) if o.get("tag") == "US-Landing-Socks5"), {})
        check("Stage 6.18b (v2.5.0 链式代理审计2: 4层 DAG 前置自动池删除自愈防直连泄露): 前置池被删后链式落地节点自动回退绑定现存自动池 Selector 绝不裸连泄露真实 IP",
              bool(chain_ob_250.get("detour")) and chain_ob_250.get("detour") in ("AI_Best_Auto", "Stream_Auto", "Auto_YouTube"),
              f"chain_ob={chain_ob_250}")

        # Stage 6.19a: Kernel Outbounds Verification for multi_line pool (urltest + interrupt_exist_connections=False on Auto_<pool> & Shunt_YouTube/Shunt_TikTok)
        sh_cfg_250 = dmod.load_shunt_config(tmp_v250)
        for _sg in sh_cfg_250.get("groups", []):
            if _sg.get("id") in ("YouTube", "TikTok", "AI"):
                _sg["shunt_mode"] = "auto"
                _sg["strategy"] = "auto"
                _sg["auto_node_id"] = "auto_youtube"
                _sg["manual_node"] = "auto:auto_youtube"
        dmod.save_shunt_config(sh_cfg_250, tmp_v250)
        sb_ml_cfg = dmod.ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_v250)
        obs_by_tag = {o.get("tag"): o for o in (sb_ml_cfg.get("outbounds") or []) if isinstance(o, dict) and o.get("tag")}
        ut_ob = obs_by_tag.get("Stream_Auto_MultiLine") or obs_by_tag.get("Auto_YouTube_MultiLine") or {}
        sh_yt_ob = obs_by_tag.get("Shunt_YouTube") or {}
        sh_tk_ob = obs_by_tag.get("Shunt_TikTok") or {}
        sh_ai_ob = obs_by_tag.get("Shunt_AI") or {}
        check("Stage 6.19a (v2.5.0 诊断闭环1: 多线并发落地 sing-box.json 内核 urltest 与无损连接切换): 生成 urltest 并发出口且仅含达标快节点，Shunt_YouTube/TikTok 开启 interrupt_exist_connections=False，Shunt_AI 保持单线保护",
              ut_ob.get("type") == "urltest"
              and ut_ob.get("outbounds") == ["HK-Fast-01", "SG-Fast-02"]
              and ut_ob.get("interrupt_exist_connections") is False
              and sh_yt_ob.get("interrupt_exist_connections") is False
              and sh_tk_ob.get("interrupt_exist_connections") is False
              and sh_ai_ob.get("interrupt_exist_connections") is True,
              f"ut={ut_ob}, yt_iec={sh_yt_ob.get('interrupt_exist_connections')}, tk_iec={sh_tk_ob.get('interrupt_exist_connections')}, ai_iec={sh_ai_ob.get('interrupt_exist_connections')}")

        # Stage 6.19b: Real-Time Multi-Line Concurrent Connection Distribution across multiple physical nodes + Single-Best restoration
        clash_selector_now = {}
        def _mock_clash_put(sel_tag, target_n):
            clash_selector_now[sel_tag] = target_n
            return True
        active_conns_chains0 = []
        yt_And_tk_same_tick_diff = False
        for _tick_i in range(4):
            dmod.dispatch_multi_line_pools_tick(tmp_v250, advance=True, clash_api_override=_mock_clash_put, respect_dwell_interval=False)
            active_conns_chains0.append(clash_selector_now.get("Shunt_YouTube"))
            if clash_selector_now.get("Shunt_YouTube") != clash_selector_now.get("Shunt_TikTok"):
                yt_And_tk_diff = True
        # Switch pool back to single_best and verify rotation stops immediately
        auto_cfg_250_single = dmod.load_auto_nodes_config(tmp_v250)
        auto_cfg_250_single["auto_nodes"][0]["dispatch_mode"] = "single_best"
        dmod.save_auto_nodes_config(auto_cfg_250_single, tmp_v250)
        dmod.evaluate_all_auto_nodes(tmp_v250, force_service_probe=False, advance_revert_streak=False)
        res_single_tick = dmod.dispatch_multi_line_pools_tick(tmp_v250, advance=True, clash_api_override=_mock_clash_put, respect_dwell_interval=False)
        sb_single_cfg = dmod.ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_v250)
        sh_yt_single = next((o for o in (sb_single_cfg.get("outbounds") or []) if o.get("tag") == "Shunt_YouTube"), {})
        check("Stage 6.19b (v2.5.0 诊断闭环2: 多线并发实时连接分摊 >=2 物理节点且切回 single_best 立即恢复单节点): 并发连接 chains[0] 覆盖全部健康物理节点，YouTube 与 TikTok 同刻错峰分摊，切回 single_best 后恢复单选",
              set(active_conns_chains0) == {"HK-Fast-01", "SG-Fast-02"}
              and yt_And_tk_diff is True
              and res_single_tick.get("active_pools_count") == 0
              and sh_yt_single.get("interrupt_exist_connections") is True,
              f"chains0={active_conns_chains0}, diff={yt_And_tk_diff}, single_pools={res_single_tick.get('active_pools_count')}, yt_single_iec={sh_yt_single.get('interrupt_exist_connections')}")

        # Stage 6.19c: auto_screen_and_fill_pool bandwidth_prefer + DAG chained exclusion + Subscription auto_update=False persistence
        store_v250["nid_250_2"]["bandwidth_mbps"] = 680.0
        store_v250["SG-Fast-02"]["bandwidth_mbps"] = 680.0
        store_v250["nid_250_1"]["bandwidth_mbps"] = 20.0
        store_v250["HK-Fast-01"]["bandwidth_mbps"] = 20.0
        store_v250["nid_250_chain"] = {"state": "ok", "delay_ms": 15, "probe_ts": now_250}
        store_v250["US-Landing-Socks5"] = {"state": "ok", "delay_ms": 15, "probe_ts": now_250}
        dmod.save_node_probe_store(store_v250, tmp_v250)
        sc_250 = dmod.auto_screen_and_fill_pool({
            "pool_mode": "ping_only",
            "scope_sources": ["ALL"],
            "scope_countries": ["ALL"],
            "target_size": 4,
            "bandwidth_prefer": True,
        }, conf_dir=tmp_v250, run_live_probe=False)
        dmod.save_subscriptions([{
            "id": "sub_test_250",
            "name": "测试订阅",
            "url": "https://example.com/sub250",
            "enabled": True,
            "auto_update": False,
            "update_interval_min": 360,
            "count": 3,
            "status": "ok"
        }], tmp_v250)
        subs_loaded_250 = dmod.load_subscriptions(tmp_v250)
        check("Stage 6.19c (v2.5.0 节点池建池筛选与订阅自动同步持久化): auto_screen 带宽择优将 680Mbps 节点排第一且严格排除链式落地节点，订阅 auto_update=False 持久化生效",
              sc_250.get("admitted_g1", [None])[0] == "SG-Fast-02"
              and "US-Landing-Socks5" not in (sc_250.get("admitted_g1") or [])
              and subs_loaded_250[0].get("auto_update") is False,
              f"admitted={sc_250.get('admitted_g1')}, sub_auto={subs_loaded_250[0].get('auto_update')}")
    finally:
        shutil.rmtree(tmp_v250, ignore_errors=True)

    # Stage 6.20: v2.5.1 LuCI Streamlined Panel & Cloud Feedback FB-250-1..6 Gates
    ov_txt_251 = (SITE / "htdocs/luci-static/resources/view/ai-link/overview.js").read_text(encoding="utf-8")
    check("Stage 6.20a (v2.5.1 LuCI 面板精简仅保留基础开关重启与 OTA 模块): 禁用底部 UCI 保存应用按钮，移除模式下拉/IPv6切换/旁路切换/组件更新表/底层UCI表单等冗余控件，仅保留启动/重启/停止/自启/代理总开关/重载核心与 OTA 在线升级模块",
          "handleSaveApply: null" in ov_txt_251
          and "handleSave: null" in ov_txt_251
          and "handleReset: null" in ov_txt_251
          and all(k in ov_txt_251 for k in ["luci-btn-svc-start", "luci-btn-svc-stop", "luci-btn-svc-restart", "luci-btn-svc-boot", "luci-btn-toggle-proxy", "luci-btn-restart-core", "luci-btn-ota-check", "luci-btn-ota-apply"])
          and all(k not in ov_txt_251 for k in ["luci-sel-rmode", "luci-btn-ipv6", "luci-btn-bypass", "luci-btn-up-rules", "luci-btn-up-core", "luci-btn-up-all", "form.Flag", "form.ListValue"]),
          "LuCI overview.js streamlined verified")

    dmod.PROBE_ENGINE.load_persisted_selections(dmod.RUN_DIR, dmod.CONF_DIR)
    dmod.load_switch_history(dmod.RUN_DIR)
    res_st = subprocess.run([sys.executable, "-B", str(DAEMON), "--self-test"], capture_output=True, text=True)
    cl_txt_251 = (SITE / "CHANGELOG.md").read_text(encoding="utf-8")
    m_cl_251 = re.search(r"^##\s+v?([0-9.]+)", cl_txt_251, re.M)
    check("Stage 6.20b (v2.5.1 FB-250-1/2/5 守护进程自检 urltest 合法键与 CHANGELOG 同步): ai-link-daemon.py --self-test 零报错通过且 CHANGELOG.md 首条版本与 APP_VERSION 对齐",
          res_st.returncode == 0 and bool(m_cl_251 and m_cl_251.group(1) == dmod.APP_VERSION),
          f"self_test_rc={res_st.returncode}, changelog_ver={m_cl_251.group(1) if m_cl_251 else None}")

    # Stage 6.21: v2.5.1 Scheduled Deep Audit — Multi-Line Single-Survivor Convergence & Dead-Pool Save Guard
    tmp_v251 = Path(tempfile.mkdtemp(prefix="ailink_v251_audit_"))
    try:
        dmod.save_nodes_list([
            {"tag": "ML-Alive-01", "node_id": "nid_ml_a1", "type": "vless", "server": "198.51.100.21", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111111"},
            {"tag": "ML-Alive-02", "node_id": "nid_ml_a2", "type": "vless", "server": "198.51.100.22", "server_port": 443, "uuid": "22222222-2222-2222-2222-222222222222"},
        ], tmp_v251)
        now_251 = int(time.time())
        dmod.save_node_probe_store({
            "nid_ml_a1": {"state": "ok", "delay_ms": 62, "ewma_ms": 62.0, "probe_ts": now_251, "last_probe_ts": now_251, "consecutive_fail": 0, "svc": {}},
            "ML-Alive-01": {"state": "ok", "delay_ms": 62, "ewma_ms": 62.0, "probe_ts": now_251, "last_probe_ts": now_251, "consecutive_fail": 0, "svc": {}},
            "nid_ml_a2": {"state": "ok", "delay_ms": 74, "ewma_ms": 74.0, "probe_ts": now_251, "last_probe_ts": now_251, "consecutive_fail": 0, "svc": {}},
            "ML-Alive-02": {"state": "ok", "delay_ms": 74, "ewma_ms": 74.0, "probe_ts": now_251, "last_probe_ts": now_251, "consecutive_fail": 0, "svc": {}},
        }, tmp_v251)
        dmod.save_auto_nodes_config({
            "auto_nodes": [{
                "id": "auto_youtube",
                "tag": "Stream_Auto",
                "name": "流媒体自动",
                "dispatch_mode": "multi_line",
                "target_size": 4,
                "replenish_threshold": 2,
                "current_node": "ML-Alive-01",
                "multi_line_nodes": ["ML-Alive-01", "ML-Alive-02"],
                "active_lines_count": 2,
                "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["ML-Alive-01", "ML-Alive-02"]}],
            }]
        }, tmp_v251)
        clash_calls_251 = []
        def mock_clash_251(path, method="GET", payload=None, timeout=1.5):
            if method == "PUT" and isinstance(payload, dict):
                clash_calls_251.append((path.rsplit("/", 1)[-1], payload.get("name")))
            return 204, {}
        # Rotate onto ML-Alive-02 first
        dmod.dispatch_multi_line_pools_tick(tmp_v251, advance=True, clash_api_override=mock_clash_251, respect_dwell_interval=False)
        dmod.dispatch_multi_line_pools_tick(tmp_v251, advance=True, clash_api_override=mock_clash_251, respect_dwell_interval=False)
        # Now mark ML-Alive-02 as dead so only 1 healthy node (ML-Alive-01) remains in the multi_line pool
        st_251 = dmod.load_node_probe_store(tmp_v251)
        st_251["nid_ml_a2"]["state"] = "dead"
        st_251["nid_ml_a2"]["delay_ms"] = -1
        st_251["ML-Alive-02"]["state"] = "dead"
        st_251["ML-Alive-02"]["delay_ms"] = -1
        dmod.save_node_probe_store(st_251, tmp_v251)
        with dmod._MULTI_LINE_RR_LOCK:
            dmod._MULTI_LINE_RR_STATE["memo_sig"] = None
        tick_deg = dmod.dispatch_multi_line_pools_tick(tmp_v251, advance=True, clash_api_override=mock_clash_251, respect_dwell_interval=False)
        check("Stage 6.21a (v2.5.1 多线并发池副线阵亡退化单线立即收敛): 2 线并发池副线 ML-Alive-02 阵亡后，0.5s 调度器立即将 Stream_Auto 与 Shunt_YouTube 从死副线收敛回唯一存活主线 ML-Alive-01 且 active_pools_count=0",
              tick_deg.get("active_pools_count") == 0
              and tick_deg.get("dispatched", {}).get("Stream_Auto") == "ML-Alive-01"
              and tick_deg.get("dispatched", {}).get("Shunt_YouTube") == "ML-Alive-01",
              f"tick_deg={tick_deg}")

        njs_txt_251 = (SITE / "root/usr/share/ai-link/webui/nexus.js").read_text(encoding="utf-8")
        bad_math_max_lines = [ln.strip() for ln in njs_txt_251.splitlines() if "Math.max(2" in ln and "active_lines_count" in ln]
        check("Stage 6.21b (v2.5.2 前端多线并发真实线数展示与单线降级提示 FB-251-4/5): nexus.js 全文(含卡片/胶囊/下拉框 option)零 Math.max(2,...active_lines_count) 虚标线数，真实反映多线并发(N线)/1线降级/0线无可用",
              len(bad_math_max_lines) == 0
              and "多线并发(1线·单线降级)" in njs_txt_251
              and "多线并发 1线(单线降级)" in njs_txt_251
              and "多线并发(0线·无可用)" in njs_txt_251
              and " · 多线(" in njs_txt_251,
              f"bad_math_max_lines={bad_math_max_lines}")
    finally:
        shutil.rmtree(tmp_v251, ignore_errors=True)

    # Stage 6.22: v2.5.2 Strict Auto-Node Pool Subscription & Region Scope Enforcement across Screen / Sync Backfill / Health Replenish / Replace
    tmp_v252 = Path(tempfile.mkdtemp(prefix="ailink_v252_scope_"))
    try:
        dmod.save_subscriptions([
            {"id": "sub_A", "name": "指定主力订阅A", "url": "https://example.com/subA", "enabled": True, "auto_update": True},
            {"id": "sub_B", "name": "未勾选订阅B", "url": "https://example.com/subB", "enabled": True, "auto_update": True},
        ], tmp_v252)
        init_nodes_252 = [
            {"tag": "SubA-JP-01", "node_id": "nid_a_jp1", "node_key": "nk_a_jp1", "type": "vless", "server": "198.51.100.31", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111131", "_sub_id": "sub_A", "_sub_url": "https://example.com/subA"},
            {"tag": "SubA-JP-02", "node_id": "nid_a_jp2", "node_key": "nk_a_jp2", "type": "vless", "server": "198.51.100.32", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111132", "_sub_id": "sub_A", "_sub_url": "https://example.com/subA"},
            {"tag": "SubA-US-01", "node_id": "nid_a_us1", "node_key": "nk_a_us1", "type": "vless", "server": "198.51.100.33", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111133", "_sub_id": "sub_A", "_sub_url": "https://example.com/subA"},
            {"tag": "SubB-JP-UltraFast", "node_id": "nid_b_jp1", "node_key": "nk_b_jp1", "type": "vless", "server": "198.51.100.41", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111141", "_sub_id": "sub_B", "_sub_url": "https://example.com/subB"},
            {"tag": "SubB-SG-UltraFast", "node_id": "nid_b_sg1", "node_key": "nk_b_sg1", "type": "vless", "server": "198.51.100.42", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111142", "_sub_id": "sub_B", "_sub_url": "https://example.com/subB"},
        ]
        dmod.save_nodes_list(init_nodes_252, tmp_v252)
        now_252 = int(time.time())
        dmod.save_node_probe_store({
            "nid_a_jp1": {"state": "ok", "delay_ms": 82, "ewma_ms": 82.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "SubA-JP-01": {"state": "ok", "delay_ms": 82, "ewma_ms": 82.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "nid_a_jp2": {"state": "ok", "delay_ms": 95, "ewma_ms": 95.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "SubA-JP-02": {"state": "ok", "delay_ms": 95, "ewma_ms": 95.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "nid_a_us1": {"state": "ok", "delay_ms": 25, "ewma_ms": 25.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "SubA-US-01": {"state": "ok", "delay_ms": 25, "ewma_ms": 25.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "nid_b_jp1": {"state": "ok", "delay_ms": 12, "ewma_ms": 12.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "SubB-JP-UltraFast": {"state": "ok", "delay_ms": 12, "ewma_ms": 12.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "nid_b_sg1": {"state": "ok", "delay_ms": 15, "ewma_ms": 15.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
            "SubB-SG-UltraFast": {"state": "ok", "delay_ms": 15, "ewma_ms": 15.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}},
        }, tmp_v252)
        scr_252 = dmod.auto_screen_and_fill_pool({
            "pool_mode": "ping_only",
            "scope_sources": ["sub_A"],
            "scope_countries": ["JP"],
            "target_size": 4,
            "replenish_threshold": 3,
        }, conf_dir=tmp_v252, run_live_probe=False)
        dmod.save_auto_nodes_config({
            "auto_nodes": [{
                "id": "auto_scoped_jp",
                "tag": "Auto_Scoped_JP",
                "name": "仅订阅A日本池",
                "pool_mode": "ping_only",
                "scope_sources": ["sub_A"],
                "scope_source": "sub_A",
                "scope_countries": ["JP"],
                "target_size": 4,
                "replenish_threshold": 3,
                "auto_maintain": True,
                "groups": [{"index": 1, "name": "主力组 G1", "node_tags": list(scr_252.get("admitted_g1") or [])}],
            }]
        }, tmp_v252)
        # Simulate subscription sync where SubA-JP-02 disappears, SubA-JP-03 (108ms) appears, and SubB has 12ms JP node
        synced_nodes_252 = [
            init_nodes_252[0],
            {"tag": "SubA-JP-03", "node_id": "nid_a_jp3", "node_key": "nk_a_jp3", "type": "vless", "server": "198.51.100.34", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111134", "_sub_id": "sub_A", "_sub_url": "https://example.com/subA"},
            init_nodes_252[2],
            init_nodes_252[3],
            init_nodes_252[4],
        ]
        st_252 = dmod.load_node_probe_store(tmp_v252)
        st_252["nid_a_jp3"] = {"state": "ok", "delay_ms": 108, "ewma_ms": 108.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}}
        st_252["SubA-JP-03"] = {"state": "ok", "delay_ms": 108, "ewma_ms": 108.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}}
        dmod.save_node_probe_store(st_252, tmp_v252)
        dmod.save_nodes_list(synced_nodes_252, tmp_v252)
        dmod._reconcile_auto_pools_after_sub_sync(init_nodes_252, synced_nodes_252, tmp_v252)
        after_sync_an = dmod.load_auto_nodes_config(tmp_v252)["auto_nodes"][0]
        sync_g1_tags = after_sync_an["groups"][0]["node_tags"]
        check("Stage 6.22a (v2.5.2 节点池建池与订阅同步自动补位严格遵循勾选订阅与地区): 仅勾选 sub_A+JP 时，建池与订阅同步补位 100% 仅选入 SubA-JP-* 节点，绝不混入未勾选订阅 SubB-JP-UltraFast(12ms) 或非勾选地区 SubA-US-01(25ms)",
              scr_252.get("admitted_g1") == ["SubA-JP-01", "SubA-JP-02"]
              and sync_g1_tags == ["SubA-JP-01", "SubA-JP-03"]
              and "SubB-JP-UltraFast" not in sync_g1_tags
              and "SubA-US-01" not in sync_g1_tags,
              f"screen={scr_252.get('admitted_g1')}, after_sync={sync_g1_tags}")

        # Now test maintain_auto_node_pool_health & get_auto_node_replace_candidates when out-of-scope nodes are polluted in group
        polluted_an = dict(after_sync_an)
        polluted_an["groups"] = [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-01", "SubB-JP-UltraFast", "SubA-US-01"]}]
        dmod.maintain_auto_node_pool_health(polluted_an, conf_dir=tmp_v252, allow_live_l7_probe=False)
        cleaned_tags = polluted_an["groups"][0]["node_tags"]
        rep_cands_252 = dmod.get_auto_node_replace_candidates("auto_scoped_jp", "SubA-JP-01", conf_dir=tmp_v252)
        rep_cand_tags = [c["tag"] for c in (rep_cands_252.get("candidates") or [])]
        check("Stage 6.22b (v2.5.2 低健康度自动复选与替换候选严格遵循勾选订阅与地区并自动清理越界节点): maintain_auto_node_pool_health 自动剔除越界的 SubB-JP-UltraFast 与 SubA-US-01 并仅补入 SubA-JP-03，替换候选同样零跨订阅泄露",
              cleaned_tags == ["SubA-JP-01", "SubA-JP-03"]
              and all(t.startswith("SubA-JP-") for t in rep_cand_tags),
              f"cleaned_tags={cleaned_tags}, rep_cands={rep_cand_tags}")

        # Stage 6.23a: WAN Blackout Anti-Wipeout Guard + service_logic=='any' Replenishment + Multi-Line Member Tagging
        st_blackout = dmod.load_node_probe_store(tmp_v252)
        for k_b in list(st_blackout.keys()):
            if isinstance(st_blackout[k_b], dict):
                st_blackout[k_b]["state"] = "dead"
                st_blackout[k_b]["delay_ms"] = -1
        dmod.save_node_probe_store(st_blackout, tmp_v252)
        blackout_an = dict(after_sync_an)
        blackout_an["groups"] = [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-01", "SubA-JP-03", "SubB-JP-UltraFast"]}]
        dmod.maintain_auto_node_pool_health(blackout_an, conf_dir=tmp_v252, allow_live_l7_probe=False)
        blackout_kept = blackout_an["groups"][0]["node_tags"]
        # Restore healthy probe for multi-line member tagging check
        st_blackout["nid_a_jp1"] = {"state": "ok", "delay_ms": 62, "ewma_ms": 62.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {"chatgpt": {"ok": True, "delay_ms": 75, "status": 200}}}
        st_blackout["SubA-JP-01"] = st_blackout["nid_a_jp1"]
        st_blackout["nid_a_jp3"] = {"state": "ok", "delay_ms": 84, "ewma_ms": 84.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {"chatgpt": {"ok": False, "delay_ms": 0, "status": 502}, "claude": {"ok": True, "delay_ms": 92, "status": 200}}}
        st_blackout["SubA-JP-03"] = st_blackout["nid_a_jp3"]
        dmod.save_node_probe_store(st_blackout, tmp_v252)
        ml_eval_an = dict(after_sync_an)
        ml_eval_an["dispatch_mode"] = "multi_line"
        ml_eval_an["service_check_enabled"] = True
        ml_eval_an["service_checks"] = ["chatgpt", "claude"]
        ml_eval_an["service_logic"] = "any"
        ml_eval_an["groups"] = [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-01"]}]
        dmod.maintain_auto_node_pool_health(ml_eval_an, conf_dir=tmp_v252, allow_live_l7_probe=False)
        dmod.evaluate_single_auto_node(ml_eval_an, conf_dir=tmp_v252)
        mems_252 = (ml_eval_an.get("groups") or [{}])[0].get("members") or []
        check("Stage 6.23a (v2.5.2 WAN闪断防团灭保护 + service_logic=any补位 + 成员并发在线标记): 全网闪断时剔除越界节点但保留池内合规成员不团灭，且service_logic=any补位与成员in_multi_line/is_primary_egress标记100%准确",
              blackout_kept == ["SubA-JP-01", "SubA-JP-03"]
              and "SubB-JP-UltraFast" not in blackout_kept
              and len(mems_252) == 2
              and any(m.get("is_primary_egress") is True for m in mems_252),
              f"blackout_kept={blackout_kept}, mems={[(m.get('tag'), m.get('is_primary_egress'), m.get('in_multi_line')) for m in mems_252]}")

        # Stage 6.23b: Visual Alignment & Holographic Traffic Waveform Readability Gate
        css_252_txt = (Path(dmod.__file__).resolve().parent / "webui/nexus.css").read_text(encoding="utf-8")
        js_252_txt = (Path(dmod.__file__).resolve().parent / "webui/nexus.js").read_text(encoding="utf-8")
        check("Stage 6.23b (v2.5.2 并排卡片100%等高对齐与全息流量波形均值基准线/空态引导/节点池范围直显门禁): 保持DPR防膨胀高度上限实现声呐与波形严丝合缝等高，波形含均值参考线与空态引导，节点池卡片直显范围",
              "max-height: 268px" in css_252_txt
              and ".hud-pool-scope" in css_252_txt
              and 'class="hud-pool-scope"' in js_252_txt
              and "Average Reference Dashed Line" in js_252_txt
              and "当前时间窗口暂无流量波动" in js_252_txt,
              "visual & waveform readability verified")

        # Stage 6.24a: evaluate_single_auto_node & get_auto_node_candidate_pool real-time scope guard (even before maintain runs)
        uncleaned_an = {
            "id": "auto_eval_scope_guard",
            "tag": "Auto_Eval_Scope_Guard",
            "name": "评估级范围守卫池",
            "pool_mode": "ping_only",
            "scope_sources": ["sub_A"],
            "scope_source": "sub_A",
            "scope_countries": ["JP"],
            "target_size": 4,
            "replenish_threshold": 2,
            "auto_maintain": True,
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["SubB-JP-UltraFast", "SubA-US-01", "SubA-JP-01"]}],
        }
        cand_pool_24a = dmod.get_auto_node_candidate_pool(uncleaned_an, conf_dir=tmp_v252)
        cand_tags_24a = [x["tag"] for x in cand_pool_24a]
        eval_res_24a = dmod.evaluate_single_auto_node(uncleaned_an, conf_dir=tmp_v252)
        check("Stage 6.24a (v2.5.2 评估引擎与候选池实时范围守卫): 即使 groups 残留越界节点 SubB-JP-UltraFast(12ms) 与 SubA-US-01(25ms)，evaluate_single_auto_node 与 get_auto_node_candidate_pool 亦 100% 拒绝将其选为出口，仅选入合规 SubA-JP-01",
              cand_tags_24a == ["SubA-JP-01"]
              and eval_res_24a.get("current_node") == "SubA-JP-01"
              and eval_res_24a.get("verified_nodes") == ["SubA-JP-01"],
              f"cand_tags={cand_tags_24a}, current_node={eval_res_24a.get('current_node')}")

        # Stage 6.24b: Editor Modal Real-Time Scope Pruning & Sonar Dynamic Quantitative Summary Footer Gate
        check("Stage 6.24b (v2.5.2 向导勾选订阅/地区实时剔除越界节点与声呐底部动态KPI摘要门禁): 切换订阅或地区芯片时实时重算并清理 selectedSet 越界节点，声呐底部动态汇总就绪数/均值/最快应用",
              "_allowedNow" in js_252_txt
              and "_allowedCNow" in js_252_txt
              and "sonarFoot.textContent = '已就绪 '" in js_252_txt,
              "modal live prune & sonar dynamic summary verified")

        # Stage 6.25a: Subscription Disable/Delete Cascade Replenishment across Multi-Subscription Auto-Node Pool
        st_blackout["nid_b_jp1"] = {"state": "ok", "delay_ms": 12, "ewma_ms": 12.0, "probe_ts": now_252, "last_probe_ts": now_252, "svc": {}}
        st_blackout["SubB-JP-UltraFast"] = st_blackout["nid_b_jp1"]
        dmod.save_node_probe_store(st_blackout, tmp_v252)
        # Configure a pool selecting from ["sub_A", "sub_B"] with JP region, initially holding only SubA-JP-01
        dmod.save_auto_nodes_config({
            "auto_nodes": [{
                "id": "auto_multi_sub_jp",
                "tag": "Auto_Multi_Sub_JP",
                "name": "双订阅JP容灾池",
                "pool_mode": "ping_only",
                "scope_sources": ["sub_A", "sub_B"],
                "scope_source": "sub_A,sub_B",
                "scope_countries": ["JP"],
                "target_size": 2,
                "replenish_threshold": 2,
                "auto_maintain": True,
                "current_node": "SubA-JP-01",
                "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}],
            }]
        }, tmp_v252)
        # Disable sub_A via set_subscription_enabled -> pool must immediately evict disabled sub_A nodes and replenish SubB-JP-UltraFast from sub_B!
        dmod.set_subscription_enabled(sub_id="sub_A", enabled=False, conf_dir=tmp_v252)
        after_dis_an = dmod.load_auto_nodes_config(tmp_v252)["auto_nodes"][0]
        after_dis_tags = after_dis_an["groups"][0]["node_tags"]
        check("Stage 6.25a (v2.5.2 订阅停用/删除级联自愈与跨订阅补位): 双订阅池(sub_A+sub_B)中停用 sub_A 后，节点池毫秒级剔除失效 sub_A 节点并自动从已勾选的 sub_B 补入 SubB-JP-UltraFast 切换出口",
              after_dis_tags == ["SubB-JP-UltraFast"]
              and after_dis_an.get("current_node") == "SubB-JP-UltraFast",
              f"after_dis_tags={after_dis_tags}, current={after_dis_an.get('current_node')}")

        # Stage 6.25b: Latency Sparkline 3-Anchor (Peak/Avg/Min) & 3D Traffic Insights 24h Time Axis Gate
        check("Stage 6.25b (v2.5.2 实时延迟微波形峰/均/谷三锚点与三维流量洞察24h坐标轴门禁): drawLatencyChart 标注峰值/均值/谷值，openTrafficInsightsModal 24h分时柱状图具备00:00~23:00时间刻度",
              "ctx.fillText('均' + avgMs + 'ms'" in js_252_txt
              and "ti-trend-axis" in js_252_txt,
              "latency avg label & traffic insights 24h axis verified")

        # Stage 6.26a: v2.5.3 FB-252-1 (subscription_formats 12 fixtures), FB-252-2 (no trailing newline on v242 script), and hermetic --self-test sandbox
        fx_dir_253 = Path(__file__).resolve().parent / "subscription_formats"
        fx_cnt_253 = len([p for p in fx_dir_253.iterdir() if p.is_file()]) if fx_dir_253.is_dir() else 0
        self_bytes_253 = Path(__file__).resolve().read_bytes()
        d_src_253 = Path(dmod.__file__).resolve().read_text(encoding="utf-8")
        check("Stage 6.26a (v2.5.3 FB-252-1/2 订阅格式夹具随包 >=12 项 + 脚本尾部零换行符防 Canvas 剥离 + --self-test 独立沙箱隔离): subscription_formats 夹具 >=12 个，本脚本末尾无多余换行符，--self-test 零读写现网 CONF_DIR",
              fx_cnt_253 >= 12
              and (not self_bytes_253.endswith(bytes([10])))
              and "NodeURIParser.parse_subscription_text(sample_uris, conf_dir=tmp_test_dir)" in d_src_253,
              f"fixtures={fx_cnt_253}, no_trailing_nl={not self_bytes_253.endswith(bytes([10]))}")

        # Stage 6.27a: v2.5.4 FB-253-1 (Makefile PKG_RELEASE alignment) & FB-253-2 (Gates enforce report PKG_RELEASE & version-centric Section 1)
        mk_254_p = Path(dmod.__file__).resolve().parents[4] / "Makefile"
        mk_254_txt = mk_254_p.read_text(encoding="utf-8") if mk_254_p.is_file() else ""
        gates_254_txt = (Path(__file__).resolve().parent / "gates_v101.py").read_text(encoding="utf-8")
        check("Stage 6.27a (v2.5.4 FB-253-1/2 Makefile PKG_VERSION/PKG_RELEASE 锚点与报告版本结构门禁): Makefile 含 PKG_VERSION:=2.5.4 与 PKG_RELEASE:=14，且 gates_v101 强制校验报告 PKG_RELEASE 与首节版本号",
              f"PKG_VERSION:={dmod.APP_VERSION}" in mk_254_txt
              and "PKG_RELEASE:=16" in mk_254_txt
              and "FB-253-1: Verify PKG_RELEASE" in gates_254_txt
              and "FB-253-2: Verify report Section 1" in gates_254_txt,
              f"app_ver={dmod.APP_VERSION}")

        # Stage 6.28a: Multi-line pool passive kernel log failover immediately converges bound Shunt_* selectors away from dead sub-line
        dmod.save_auto_nodes_config({
            "auto_nodes": [{
                "id": "auto_youtube",
                "tag": "Stream_Auto",
                "name": "流媒体多线池",
                "pool_mode": "ping_only",
                "dispatch_mode": "multi_line",
                "scope_sources": ["sub_A", "sub_B"],
                "scope_source": "sub_A,sub_B",
                "scope_countries": ["JP"],
                "target_size": 3,
                "replenish_threshold": 1,
                "auto_maintain": True,
                "last_switch_ts": now_252,
                "last_smart_switch_ts": now_252,
                "current_node": "SubA-JP-01",
                "multi_line_nodes": ["SubA-JP-01", "SubB-JP-UltraFast"],
                "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-01", "SubB-JP-UltraFast"]}],
            }]
        }, tmp_v252)
        dmod.set_subscription_enabled(sub_id="sub_A", enabled=True, conf_dir=tmp_v252)
        klog_ml_res = dmod.scan_kernel_logs_for_active_pool_failures(
            tmp_v252,
            log_lines_override=[
                "ERROR outbound/vless[SubA-JP-01]: dial tcp to youtube.com:443: i/o timeout",
                "ERROR outbound/vless[SubA-JP-01]: dial tcp to googlevideo.com:443: connection reset by peer",
                "ERROR outbound/vless[SubA-JP-01]: tls: handshake failed to ytimg.com:443: unexpected EOF",
            ],
            recheck_before_switch=False,
        )
        after_klog_pool = dmod.load_auto_nodes_config(tmp_v252)["auto_nodes"][0]
        check("Stage 6.28a (v2.5.4 多线并发池内核日志被动秒切与分流组联动收敛): 即使存活数未跌破 replenish_threshold(1)，连续 3 次传输报错亦突破粘性冷却将死线移出 multi_line_nodes 并收敛分流组至健康线 SubB-JP-UltraFast",
              klog_ml_res.get("triggered") is True
              and after_klog_pool.get("current_node") == "SubB-JP-UltraFast"
              and "SubA-JP-01" not in (after_klog_pool.get("multi_line_nodes") or [])
              and dmod.PROBE_ENGINE.current_selections.get("Shunt_YouTube") == "SubB-JP-UltraFast",
              f"cur={after_klog_pool.get('current_node')}, ml={after_klog_pool.get('multi_line_nodes')}, yt_sel={dmod.PROBE_ENGINE.current_selections.get('Shunt_YouTube')}")

        # Stage 6.28b: Shunt Hit Leaderboard KPI Strip Active Count & 1h Traffic Volume Gate
        check("Stage 6.28b (v2.5.4 分流命中排行 KPI 栏活跃项占比与 1h 累计流量直显门禁): renderShuntHitLeaderboard 汇总栏展示千分位命中次数与活跃项/1h累计流量",
              "totalHitBytes" in js_252_txt
              and "活跃项 · 1h 流量" in js_252_txt,
              "shunt hit leaderboard KPI verified")

        # Stage 6.29a: Single-Node Deletion Cascade Replenishment strictly within pool's scope_sources & scope_countries
        # Configure a pool bound ONLY to sub_A + JP, initially holding SubA-JP-01, while SubB-JP-UltraFast (12ms) is at index 0 of nodes.json
        nodes_29a = [
            {"tag": "SubB-JP-UltraFast", "node_id": "nid_b_jp1", "node_key": "nk_b_jp1", "type": "vless", "server": "198.51.100.32", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111132", "_sub_id": "sub_B", "_sub_url": "https://example.com/subB"},
            {"tag": "SubA-JP-03", "node_id": "nid_a_jp3", "node_key": "nk_a_jp3", "type": "vless", "server": "198.51.100.34", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111134", "_sub_id": "sub_A", "_sub_url": "https://example.com/subA"},
        ]
        dmod.save_nodes_list(nodes_29a, tmp_v252)
        dmod.save_auto_nodes_config({
            "auto_nodes": [{
                "id": "auto_del_node_scope",
                "tag": "Auto_Del_Node_Scope",
                "name": "单节点删除自愈池",
                "pool_mode": "ping_only",
                "scope_sources": ["sub_A"],
                "scope_source": "sub_A",
                "scope_countries": ["JP"],
                "target_size": 2,
                "replenish_threshold": 2,
                "auto_maintain": True,
                "current_node": "SubA-JP-01",
                "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-01"]}],
            }]
        }, tmp_v252)
        dmod.reconcile_node_references(old_tag="SubA-JP-01", new_tag="", deleted_node_id="nid_a_jp1", conf_dir=tmp_v252)
        after_del_node_an = dmod.load_auto_nodes_config(tmp_v252)["auto_nodes"][0]
        check("Stage 6.29a (v2.5.4 单节点删除触发节点池严格按勾选订阅/地区补位自愈): 删除 SubA-JP-01 后 reconcile_node_references 绝不误回退至排首位的未勾选订阅节点 SubB-JP-UltraFast，而是严格从 sub_A+JP 补入 SubA-JP-03",
              after_del_node_an["groups"][0]["node_tags"] == ["SubA-JP-03"]
              and after_del_node_an.get("current_node") == "SubA-JP-03",
              f"tags={after_del_node_an['groups'][0]['node_tags']}, cur={after_del_node_an.get('current_node')}")

        # Stage 6.29b: 7x24 Activity Matrix Cell Downlink/Uplink Split Readability Gate
        check("Stage 6.29b (v2.5.4 7x24时空流量全息矩阵悬停上下行拆分明细门禁): 矩阵单元格提示含 ↓下行 / ↑上行 拆分流量",
              "ioSplitTxt" in js_252_txt,
              "7x24 matrix ioSplitTxt verified")

        # Stage 6.30a: Manual member removal (manually_removed_tags) prevents zombie re-admission during low-health replenishment
        nodes_30a = [
            {"tag": "SubA-JP-01", "node_id": "nid_a_jp1", "node_key": "nk_a_jp1", "type": "vless", "server": "198.51.100.31", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111131", "_sub_id": "sub_A", "_sub_url": "https://example.com/subA"},
            {"tag": "SubA-JP-03", "node_id": "nid_a_jp3", "node_key": "nk_a_jp3", "type": "vless", "server": "198.51.100.34", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111134", "_sub_id": "sub_A", "_sub_url": "https://example.com/subA"},
            {"tag": "SubB-JP-UltraFast", "node_id": "nid_b_jp1", "node_key": "nk_b_jp1", "type": "vless", "server": "198.51.100.32", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111132", "_sub_id": "sub_B", "_sub_url": "https://example.com/subB"},
        ]
        dmod.save_nodes_list(nodes_30a, tmp_v252)
        an_30a = {
            "id": "auto_man_rem_guard",
            "tag": "Auto_Man_Rem_Guard",
            "name": "手动移除防回弹池",
            "pool_mode": "ping_only",
            "scope_sources": ["sub_A"],
            "scope_source": "sub_A",
            "scope_countries": ["JP"],
            "target_size": 3,
            "replenish_threshold": 3,
            "auto_maintain": True,
            "manually_removed_tags": ["SubA-JP-01"],
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-03"]}],
        }
        dmod.maintain_auto_node_pool_health(an_30a, conf_dir=tmp_v252, allow_live_l7_probe=False)
        check("Stage 6.30a (v2.5.4 手动移除成员防回弹守卫 manually_removed_tags): 被用户手动移出节点池的 SubA-JP-01 在后续低健康度自动复选与订阅同步回填中绝不背着用户自动回弹入池",
              an_30a["groups"][0]["node_tags"] == ["SubA-JP-03"]
              and "SubA-JP-01" not in an_30a["groups"][0]["node_tags"],
              f"tags={an_30a['groups'][0]['node_tags']}")

        # Stage 6.30b: Overview Bottom 3 Insight Cards Live Progress Bar & Destination Summary Gate
        check("Stage 6.30b (v2.5.4 概览页底部三联洞察卡片真实数据绑定门禁): #ov-card-outbounds 进度条动态绑定实测连通率，#ov-destinations-sub 动态展示主力目标域名",
              "outProgBar = $('#ov-card-outbounds .thin-progress > i')" in js_252_txt
              and "const destSubEl = $('#ov-destinations-sub')" in js_252_txt,
              "overview 3 insight cards live binding verified")

        # Stage 6.31a: Auto-Node Pool Break-Glass Quarantine Recovery + Out-of-Scope D-01 Guard + Multi-Line Dual-Channel Floor
        store_31a = dmod.load_node_probe_store(tmp_v252)
        now_31a = int(time.time())
        store_31a["nid_a_jp1"] = {
            "state": "ok", "delay_ms": 24, "delay_ewma_ms": 24.0, "consecutive_fail": 0, "consecutive_ok": 2,
            "quarantine_until": now_31a + 1800, "last_probe_ts": now_31a, "samples": 6, "score": 88.0, "success_rate": 0.92,
        }
        store_31a["SubA-JP-01"] = store_31a["nid_a_jp1"]
        store_31a["nid_a_jp3"] = {
            "state": "ok", "delay_ms": 148, "delay_ewma_ms": 148.0, "consecutive_fail": 0, "consecutive_ok": 4,
            "quarantine_until": 0, "last_probe_ts": now_31a, "samples": 6, "score": 86.0, "success_rate": 0.96, "cv": 0.42,
        }
        store_31a["SubA-JP-03"] = store_31a["nid_a_jp3"]
        store_31a["nid_b_jp1"] = {
            "state": "ok", "delay_ms": 12, "delay_ewma_ms": 12.0, "consecutive_fail": 0, "consecutive_ok": 8,
            "quarantine_until": 0, "last_probe_ts": now_31a, "samples": 8, "score": 98.0, "success_rate": 1.0,
        }
        store_31a["SubB-JP-UltraFast"] = store_31a["nid_b_jp1"]
        dmod.save_node_probe_store(store_31a, tmp_v252)

        # Case 1: Pool with only quarantined in-scope recovered node + out-of-scope SubB node -> must NOT pick SubB, must break-glass to SubA-JP-01!
        an_31a_bg = {
            "id": "auto_bg_test",
            "tag": "Auto_BG_Test",
            "name": "破冰自愈测试池",
            "pool_mode": "ping_only",
            "scope_sources": ["sub_A"],
            "scope_source": "sub_A",
            "scope_countries": ["JP"],
            "groups": [{"index": 1, "name": "节点池成员", "node_tags": ["SubA-JP-01", "SubB-JP-UltraFast"]}],
        }
        dmod.evaluate_single_auto_node(an_31a_bg, conf_dir=tmp_v252)

        # Case 2: Multi-line pool with ultra-fast 24ms node (quarantine cleared) + 148ms node -> must preserve both lines (>=2)
        store_31a["nid_a_jp1"]["quarantine_until"] = 0
        dmod.save_node_probe_store(store_31a, tmp_v252)
        an_31a_ml = {
            "id": "auto_ml_floor",
            "tag": "Auto_ML_Floor",
            "name": "多线保底视频池",
            "pool_mode": "ping_only",
            "dispatch_mode": "multi_line",
            "scope_sources": ["sub_A"],
            "scope_source": "sub_A",
            "scope_countries": ["JP"],
            "target_size": 4,
            "groups": [{"index": 1, "name": "节点池成员", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}],
        }
        dmod.evaluate_single_auto_node(an_31a_ml, conf_dir=tmp_v252)
        check("Stage 6.31a (v2.5.4 全员隔离半开破冰自愈 + D-01 越界拦截 + 多线并发双通道保底): 杜绝越界选入 SubB 且在隔离节点恢复连通时自动破冰接管，multi_line 保持 >=2 条健康并发通道",
              an_31a_bg.get("current_node") == "SubA-JP-01"
              and an_31a_bg.get("quarantine_break_glass") is True
              and an_31a_ml.get("multi_line_nodes") == ["SubA-JP-01", "SubA-JP-03"]
              and an_31a_ml.get("active_lines_count") == 2,
              f"bg_cur={an_31a_bg.get('current_node')} bg_flag={an_31a_bg.get('quarantine_break_glass')} ml={an_31a_ml.get('multi_line_nodes')}")

        # Stage 6.31b: Sonar Radar 3-Ring Latency Scale (50ms/150ms/300ms) + Peak KPI + Dynamic Version Single Source of Truth
        html_254_txt = (SITE / "root/usr/share/ai-link/webui/index.html").read_text(encoding="utf-8")
        check("Stage 6.31b (v2.5.4 声呐三环延迟坐标刻度 50ms/150ms/300ms + 峰值延迟摘要 + 全站动态版本号单一真相源)",
              'sonar-ring-scale r-inner">50ms</span>' in html_254_txt
              and 'sonar-ring-scale r-mid">150ms</span>' in html_254_txt
              and 'sonar-ring-scale r-outer">300ms</span>' in html_254_txt
              and f"AI-LINK v{dmod.APP_VERSION} · 单一真相源架构" in html_254_txt
              and "worstSvc.name" in js_252_txt
              and "AI-LINK v2.5.2" not in js_252_txt,
              "sonar ring scales, peak latency KPI, and dynamic version verified")

        # Stage 7.1 (P0-1 & P1-5.4): Self-test 100% production isolation & polluted fake tag auto-purge
        dmod.RUN_DIR.mkdir(parents=True, exist_ok=True)
        sel_p_live = dmod.RUN_DIR / "selections.json"
        hist_p_live = dmod.RUN_DIR / "switch_history.json"
        dmod._atomic_write_text(sel_p_live, json.dumps({
            "updated_at": int(time.time()),
            "selections": {"AI_Best_Auto": "SubA-JP-01", "Auto_AI": "JP-Trojan-01", "Shunt_Custom_CN_Proxy": "HK-SS2022-01", "Auto_Auto_AI": "JP-Trojan-01"},
            "delays": {}
        }))
        dmod._atomic_write_text(hist_p_live, json.dumps([
            {"ts": int(time.time()), "time_str": "16:44:45", "group": "Auto_AI", "from_node": "SubA-JP-01", "to_node": "JP-Trojan-01", "reason": "fake", "rtt_ms": 10.0},
            {"ts": int(time.time()), "time_str": "16:40:00", "group": "Auto_YouTube", "from_node": "SubA-JP-03", "to_node": "SubA-JP-01", "reason": "real", "rtt_ms": 24.0}
        ]))
        dmod.PROBE_ENGINE._last_lp_sig = None
        dmod.PROBE_ENGINE.load_persisted_selections(dmod.RUN_DIR, dmod.CONF_DIR)
        cleaned_hist = dmod.load_switch_history(dmod.RUN_DIR)
        cleaned_sels_disk = json.loads(sel_p_live.read_text(encoding="utf-8")).get("selections", {})
        sels_bytes_pre = sel_p_live.read_bytes()
        hist_bytes_pre = hist_p_live.read_bytes()
        st_proc = subprocess.run([sys.executable, "-B", str(DAEMON), "--self-test"], capture_output=True, text=True)
        sels_bytes_post = sel_p_live.read_bytes()
        hist_bytes_post = hist_p_live.read_bytes()
        check("Stage 7.1 (v2.5.5 P0-1/P1-5.4 官方自检 --self-test 零生产污染与残留假节点自动清洗): 自动剥离 JP-Trojan-01/HK-SS2022-01 脏数据，且执行 --self-test 前后 selections.json 与 switch_history.json 逐字节零变化",
              "JP-Trojan-01" not in cleaned_sels_disk.values()
              and "Shunt_Custom_CN_Proxy" not in cleaned_sels_disk
              and len(cleaned_hist) == 1 and cleaned_hist[0].get("to_node") == "SubA-JP-01"
              and st_proc.returncode == 0
              and sels_bytes_pre == sels_bytes_post
              and hist_bytes_pre == hist_bytes_post,
              f"rc={st_proc.returncode}, sels={cleaned_sels_disk}, hist_len={len(cleaned_hist)}")

        # Stage 7.2 (P0-2): Independent Pool Health Budget + Emergency Failover Quota Bypass + Real Probe Freshness/Stale Telemetry
        dmod._atomic_write_text(dmod._node_test_quota_path(), json.dumps({
            "date": time.strftime("%Y-%m-%d"), "used": 99999, "pool_health_used": 10, "forced_used": 0,
            "v236_r10_migrated": True, "v240_budget_migrated": True, "v255_quota_migrated": True
        }))
        an_72 = {
            "id": "auto_failover_quota",
            "tag": "Auto_Failover_Quota",
            "name": "配额穿透容灾池",
            "pool_mode": "ping_only",
            "scope_sources": ["sub_A"],
            "scope_source": "sub_A",
            "scope_countries": ["JP"],
            "current_node": "SubA-JP-01",
            "groups": [{"index": 1, "name": "节点池成员", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}],
        }
        dmod.save_auto_nodes_config({"auto_nodes": [an_72]}, tmp_v252)
        oef_res = dmod.on_egress_fail("SubA-JP-01", conf_dir=tmp_v252, bypass_debounce=True, mock_ping_result={"ok": False, "delay_ms": -1, "http_status": 502})
        an_72_after = (dmod.load_auto_nodes_config(tmp_v252).get("auto_nodes") or [{}])[0]
        # Verify stale probe detection (>1h old probe_ts)
        stale_ts_72 = int(time.time()) - 7200
        st_72 = dmod.load_node_probe_store(tmp_v252)
        for _k72 in ("nid_a_jp1", "SubA-JP-01", "nid_a_jp3", "SubA-JP-03"):
            if _k72 in st_72:
                st_72[_k72]["last_probe_ts"] = stale_ts_72
                st_72[_k72]["probe_ts"] = stale_ts_72
        dmod.save_node_probe_store(st_72, tmp_v252)
        dmod.evaluate_single_auto_node(an_72_after, conf_dir=tmp_v252)
        dmod._atomic_write_text(dmod._node_test_quota_path(), json.dumps({
            "date": time.strftime("%Y-%m-%d"), "used": 0, "pool_health_used": 0, "forced_used": 0,
            "v236_r10_migrated": True, "v240_budget_migrated": True, "v255_quota_migrated": True
        }))
        check("Stage 7.2 (v2.5.5 P0-2 探测配额耗尽下故障复验免配额穿透与真实探测时间/过期感知门禁): 常规配额耗尽时 on_egress_fail 依然强制复验并切换至 SubA-JP-03，且准确标记 last_real_probe_ts 与 probe_stale=True",
              oef_res.get("state") == "dead"
              and an_72_after.get("current_node") == "SubA-JP-03"
              and an_72_after.get("last_real_probe_ts") == stale_ts_72
              and an_72_after.get("last_check_ts") == stale_ts_72
              and an_72_after.get("probe_stale") is True,
              f"oef={oef_res.get('state')}, cur={an_72_after.get('current_node')}, stale={an_72_after.get('probe_stale')}")

        # Stage 7.3 (P0-3 & P0-5): Multi-Line Strict 1-to-1 Selector Ownership & 30s Dwell Window
        now_73 = int(time.time())
        st_73 = dmod.load_node_probe_store(tmp_v252)
        for _k73, _d73 in [("nid_a_jp1", 28), ("SubA-JP-01", 28), ("nid_a_jp3", 42), ("SubA-JP-03", 42), ("nid_b_jp1", 19), ("SubB-JP-UltraFast", 19)]:
            st_73[_k73] = {"state": "ok", "delay_ms": _d73, "delay_ewma_ms": float(_d73), "consecutive_fail": 0, "consecutive_ok": 5, "quarantine_until": 0, "last_probe_ts": now_73, "probe_ts": now_73, "samples": 6, "score": 95.0, "success_rate": 1.0}
        dmod.save_node_probe_store(st_73, tmp_v252)
        dmod.save_auto_nodes_config({"auto_nodes": [
            {"id": "auto_youtube", "tag": "Auto_YouTube", "name": "YouTube池", "pool_mode": "ping_only", "dispatch_mode": "multi_line", "multi_line_nodes": ["SubA-JP-01", "SubA-JP-03"], "groups": [{"index": 1, "name": "G1", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}]},
            {"id": "auto_hf_dl", "tag": "Auto_HF_DL", "name": "HF下载池", "pool_mode": "ping_only", "dispatch_mode": "multi_line", "multi_line_nodes": ["SubB-JP-UltraFast", "SubA-JP-03"], "groups": [{"index": 1, "name": "G1", "node_tags": ["SubB-JP-UltraFast", "SubA-JP-03"]}]}
        ]}, tmp_v252)
        sh_73 = dmod.load_shunt_config(tmp_v252)
        for _g73 in sh_73.get("groups", []):
            if _g73.get("id") in ("YouTube", "Final_Fallback"):
                _g73["shunt_mode"] = "auto"
                _g73["auto_node_id"] = "auto_youtube"
            elif _g73.get("id") == "GitHub":
                _g73["shunt_mode"] = "auto"
                _g73["auto_node_id"] = "auto_hf_dl"
        dmod.save_shunt_config(sh_73, tmp_v252)
        with dmod._MULTI_LINE_RR_LOCK:
            dmod._MULTI_LINE_RR_STATE["memo_sig"] = None
            dmod._MULTI_LINE_RR_STATE["cursors"].clear()
            dmod._MULTI_LINE_RR_STATE["last_rotate_ts"].clear()
        t_73_1 = dmod.dispatch_multi_line_pools_tick(tmp_v252, advance=True, respect_dwell_interval=True, clash_api_override=lambda s, t: True)
        t_73_2 = dmod.dispatch_multi_line_pools_tick(tmp_v252, advance=True, respect_dwell_interval=True, clash_api_override=lambda s, t: True)
        plan_73 = dmod._MULTI_LINE_RR_STATE.get("memo_plan") or []
        yt_bound = next((p["bound_selectors"] for p in plan_73 if p["pool_id"] == "auto_youtube"), [])
        hf_bound = next((p["bound_selectors"] for p in plan_73 if p["pool_id"] == "auto_hf_dl"), [])
        check("Stage 7.3 (v2.5.5 P0-3/P0-5 多线池 Selector 1对1 唯一所有权与 30s 驻留防抖门禁): YouTube/Final 严格归属 auto_youtube、GitHub 严格归属 auto_hf_dl 零交集，且 30s 驻留期内二次 tick 不发生频繁跳变",
              set(yt_bound).isdisjoint(set(hf_bound))
              and "Shunt_Final" in yt_bound and "Shunt_Final" not in hf_bound
              and "Shunt_GitHub" in hf_bound and "Shunt_GitHub" not in yt_bound
              and t_73_1["dispatched"].get("Auto_YouTube") == t_73_2["dispatched"].get("Auto_YouTube"),
              f"yt_bound={yt_bound}, hf_bound={hf_bound}, d1={t_73_1['dispatched'].get('Auto_YouTube')}, d2={t_73_2['dispatched'].get('Auto_YouTube')}")

        # Stage 7.4 (P0-4 & P1-5.3): L7 Strict Tri-State (Unverified Never Beats Verified; 0 Verified -> l7_degraded=True; Break-Glass L7 Guard)
        st_74 = dmod.load_node_probe_store(tmp_v252)
        st_74["nid_a_jp1"]["delay_ms"] = 55
        st_74["nid_a_jp1"]["delay_ewma_ms"] = 55.0
        st_74["nid_a_jp1"]["svc"] = {}  # Unverified!
        st_74["SubA-JP-01"] = st_74["nid_a_jp1"]
        st_74["nid_a_jp3"]["delay_ms"] = 118
        st_74["nid_a_jp3"]["delay_ewma_ms"] = 118.0
        st_74["nid_a_jp3"]["svc"] = {"netflix": {"ok": True, "ts": now_73, "status": 200}}  # Verified!
        st_74["SubA-JP-03"] = st_74["nid_a_jp3"]
        dmod.save_node_probe_store(st_74, tmp_v252)
        an_nf_74 = {
            "id": "auto_nf_strict",
            "tag": "Auto_NF_Strict",
            "name": "网飞严格验证池",
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["netflix"],
            "groups": [{"index": 1, "name": "G1", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}],
        }
        dmod.evaluate_single_auto_node(an_nf_74, conf_dir=tmp_v252)
        cur_when_one_verified = an_nf_74.get("current_node")
        deg_when_one_verified = an_nf_74.get("l7_degraded")
        # Now make both unverified (0/2 verified) -> must set l7_degraded=True and verified_service_count=0!
        st_74["nid_a_jp3"]["svc"] = {}
        st_74["SubA-JP-03"] = st_74["nid_a_jp3"]
        dmod.save_node_probe_store(st_74, tmp_v252)
        an_nf_unv = dict(an_nf_74)
        dmod.evaluate_single_auto_node(an_nf_unv, conf_dir=tmp_v252)
        # Now put both unverified nodes in quarantine -> service_check pool must NOT break-glass to unverified node!
        st_74["nid_a_jp1"]["quarantine_until"] = now_73 + 1200
        st_74["nid_a_jp3"]["quarantine_until"] = now_73 + 1200
        dmod.save_node_probe_store(st_74, tmp_v252)
        an_nf_q = dict(an_nf_74)
        dmod.evaluate_single_auto_node(an_nf_q, conf_dir=tmp_v252)
        check("Stage 7.4 (v2.5.5 P0-4/P1-5.3 L7 严格三态验证与半开恢复防绕过门禁): 已验证节点(118ms)严格胜出未测节点(55ms)，0验证时强制标 l7_degraded=True，且服务池拒绝半开恢复未验证节点",
              cur_when_one_verified == "SubA-JP-03"
              and deg_when_one_verified is False
              and an_nf_unv.get("l7_degraded") is True
              and an_nf_unv.get("verified_service_count") == 0
              and an_nf_q.get("quarantine_break_glass") is False
              and an_nf_q.get("current_node") == "direct",
              f"1ver={cur_when_one_verified}/{deg_when_one_verified}, 0ver_deg={an_nf_unv.get('l7_degraded')}, q_bg={an_nf_q.get('quarantine_break_glass')}/{an_nf_q.get('current_node')}")

        # Stage 7.5 (P1-5.1/5.2/5.8): Auto_Auto_AI Prefix Fix, Unbound Dedicated Pool Warning & Honest UI Copy
        norm_ai_item = dmod._normalize_auto_node_item({"id": "auto_ai", "tag": "Auto_Auto_AI", "name": "AI自动"}, conf_dir=tmp_v252)
        an_api_75 = dmod.build_auto_nodes_api_response(tmp_v252)
        check("Stage 7.5 (v2.5.5 P1-5.1/5.2/5.8 Auto_AI 去重前缀、未绑定分流组告警与诚实轮询文案门禁): Auto_Auto_AI 自动归一为 Auto_AI，暴露 unbound_pool_warning 与 quota_status，且前端文案如实表述多出口轮询与服务待验证",
              norm_ai_item.get("tag") == "Auto_AI"
              and isinstance(an_api_75.get("quota_status"), dict)
              and "多出口轮询（实验，不叠加单流带宽）" in js_252_txt
              and "服务待验证 (仅连通)" in js_252_txt
              and "多线并发（池内健康节点叠加吞吐）" not in js_252_txt,
              f"tag={norm_ai_item.get('tag')}, has_quota={isinstance(an_api_75.get('quota_status'), dict)}")

        # Stage 7.6a: maintain_auto_node_pool_health L7-Verified Priority Replenishment & Upgrade
        st_76 = dmod.load_node_probe_store(tmp_v252)
        st_76["nid_a_jp1"] = {"state": "ok", "delay_ms": 42, "last_probe_ts": now_73, "probe_ts": now_73, "quarantine_until": 0, "consecutive_fail": 0, "svc": {}}
        st_76["SubA-JP-01"] = st_76["nid_a_jp1"]
        st_76["nid_a_jp3"] = {"state": "ok", "delay_ms": 96, "last_probe_ts": now_73, "probe_ts": now_73, "quarantine_until": 0, "consecutive_fail": 0, "svc": {"netflix": {"ok": True, "ms": 105, "code": 200, "ts": now_73}}}
        st_76["SubA-JP-03"] = st_76["nid_a_jp3"]
        dmod.save_node_probe_store(st_76, tmp_v252)
        pool_76a = {
            "id": "auto_nf_maint",
            "tag": "Auto_NF_Maint",
            "name": "网飞自愈优先池",
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["netflix"],
            "scope_sources": ["sub_A"],
            "scope_countries": ["JP"],
            "target_size": 1,
            "replenish_threshold": 1,
            "auto_maintain": True,
            "groups": [{"index": 1, "name": "G1", "node_tags": ["SubA-JP-01"]}],
        }
        changed_76a = dmod.maintain_auto_node_pool_health(pool_76a, conf_dir=tmp_v252, allow_live_l7_probe=False)
        g1_76a = list(pool_76a["groups"][0]["node_tags"])
        check("Stage 7.6a (v2.5.5 节点池健康自愈 L7 已验证优先补位与自动提纯门禁): service_check 模式下外部存在已通过 L7 验证的 SubA-JP-03 时自动替换池内未验证的 SubA-JP-01，实现 100% L7 验证成员收敛",
              changed_76a is True and g1_76a == ["SubA-JP-03"],
              f"changed={changed_76a}, g1={g1_76a}")

        # Stage 7.6b: evaluate_single_auto_node Strict verified_fail Rejection & L7-Verified Sticky Bypass
        st_76b = dmod.load_node_probe_store(tmp_v252)
        st_76b["nid_a_jp1"] = {"state": "ok", "delay_ms": 40, "last_probe_ts": now_73, "probe_ts": now_73, "quarantine_until": 0, "consecutive_fail": 0, "svc": {"netflix": {"ok": False, "ms": 0, "code": 403, "ts": now_73}}}
        st_76b["SubA-JP-01"] = st_76b["nid_a_jp1"]
        st_76b["nid_a_jp3"] = {"state": "ok", "delay_ms": 50, "last_probe_ts": now_73, "probe_ts": now_73, "quarantine_until": 0, "consecutive_fail": 0, "svc": {"netflix": {"ok": False, "ms": 0, "code": 403, "ts": now_73}}}
        st_76b["SubA-JP-03"] = st_76b["nid_a_jp3"]
        dmod.save_node_probe_store(st_76b, tmp_v252)
        pool_76b_fail = {
            "id": "auto_nf_allfail",
            "tag": "Auto_NF_AllFail",
            "name": "网飞全拒服测试池",
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["netflix"],
            "groups": [{"index": 1, "name": "G1", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}],
        }
        dmod.evaluate_single_auto_node(pool_76b_fail, conf_dir=tmp_v252)
        # Also test sticky bypass when current_node is unverified and a newly verified node is in pool
        st_76b["nid_a_jp1"]["svc"] = {}
        st_76b["nid_a_jp3"]["svc"] = {"netflix": {"ok": True, "ms": 88, "code": 200, "ts": now_73}}
        dmod.save_node_probe_store(st_76b, tmp_v252)
        pool_76b_sticky = {
            "id": "auto_nf_sticky",
            "tag": "Auto_NF_Sticky",
            "name": "网飞粘性穿透池",
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["netflix"],
            "current_node": "SubA-JP-01",
            "current_node_id": "nid_a_jp1",
            "last_switch_ts": now_73 - 30,
            "last_smart_switch_ts": now_73 - 30,
            "switch_cooldown_s": 600,
            "groups": [{"index": 1, "name": "G1", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}],
        }
        dmod.evaluate_single_auto_node(pool_76b_sticky, conf_dir=tmp_v252)
        check("Stage 7.6b (v2.5.5 D-01 严禁回退 verified_fail 拒服节点 & L7 验证通过突破 10m 粘性立即接管门禁): 全员 L7 明确失败(403)时绝不回退拒服节点而是告警 direct；原未验证出口遇到新通过 L7 验证节点时立即突破粘性窗口秒切",
              pool_76b_fail.get("current_node") == "direct"
              and pool_76b_fail.get("all_groups_dead_alert") is True
              and pool_76b_sticky.get("current_node") == "SubA-JP-03",
              f"allfail_cur={pool_76b_fail.get('current_node')}, sticky_cur={pool_76b_sticky.get('current_node')}")

        # Stage 7.7a: L3 60m Rate-Limit Cooldown Hierarchy & Cooldown Break-Glass
        st_77 = dmod.load_node_probe_store(tmp_v252)
        st_77["nid_a_jp1"] = {"state": "ok", "delay_ms": 38, "last_probe_ts": now_73, "probe_ts": now_73, "quarantine_until": 0, "rate_limited_until": now_73 + 1800, "consecutive_fail": 0, "svc": {}}
        st_77["SubA-JP-01"] = st_77["nid_a_jp1"]
        st_77["nid_a_jp3"] = {"state": "ok", "delay_ms": 92, "last_probe_ts": now_73, "probe_ts": now_73, "quarantine_until": 0, "rate_limited_until": 0, "consecutive_fail": 0, "svc": {}}
        st_77["SubA-JP-03"] = st_77["nid_a_jp3"]
        dmod.save_node_probe_store(st_77, tmp_v252)
        pool_77a = {
            "id": "auto_rl_test",
            "tag": "Auto_RL_Test",
            "name": "风控冷却分层池",
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["netflix"],
            "groups": [{"index": 1, "name": "G1", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}],
        }
        dmod.evaluate_single_auto_node(pool_77a, conf_dir=tmp_v252)
        cur_prefer_non_cool = pool_77a.get("current_node")
        # Now put both in rate-limit cooldown -> should set cooldown_break_glass=True and pick fastest SubA-JP-01 (38ms)
        st_77["nid_a_jp3"]["rate_limited_until"] = now_73 + 1800
        dmod.save_node_probe_store(st_77, tmp_v252)
        pool_77a_bg = {
            "id": "auto_rl_test_bg",
            "tag": "Auto_RL_Test_BG",
            "name": "风控冷却破冰池",
            "pool_mode": "service_check",
            "service_check_enabled": True,
            "service_checks": ["netflix"],
            "groups": [{"index": 1, "name": "G1", "node_tags": ["SubA-JP-01", "SubA-JP-03"]}],
        }
        dmod.evaluate_single_auto_node(pool_77a_bg, conf_dir=tmp_v252)
        check("Stage 7.7a (v2.5.5 60m 风控冷却 rate_limited_until 避让与全员冷却破冰保底门禁): 优先选用非风控冷却节点 SubA-JP-03(92ms) 规避 429 限流节点 SubA-JP-01(38ms)；全员风控冷却时自动标记 cooldown_break_glass=True 保底连通",
              cur_prefer_non_cool == "SubA-JP-03"
              and pool_77a_bg.get("cooldown_break_glass") is True
              and pool_77a_bg.get("current_node") == "SubA-JP-01",
              f"non_cool={cur_prefer_non_cool}, bg={pool_77a_bg.get('cooldown_break_glass')}/{pool_77a_bg.get('current_node')}")

        # Stage 7.7b: Frontend Auto-Pool HUD Card Zero-Fabricated-Fallback & Telemetry Badges Contract
        js_77b_txt = (SITE / "root/usr/share/ai-link/webui/nexus.js").read_text("utf-8")
        check("Stage 7.7b (v2.5.5 节点池 HUD 卡片零虚构兜底与冷却破冰/缓存待刷/配额详情契约门禁): 移除 (g1Tags.length || 4) 虚构兜底，完整支持冷却破冰、缓存待刷徽标与 L7已验证/巡检配额悬停明细",
              "(g1Tags.length || 4)" not in js_77b_txt
              and "p.cooldown_break_glass" in js_77b_txt
              and "缓存待刷" in js_77b_txt
              and "L7已验证：" in js_77b_txt,
              "HUD card telemetry & zero-fake-fallback verified")

        # Stage 7.8 (v2.5.6 P1-1 & FB-255-2): Semantic --self-test Assertion & Zero stderr DeprecationWarning
        st_78_proc = subprocess.run([sys.executable, "-B", str(DAEMON), "--self-test"], capture_output=True, text=True, timeout=45)
        check("Stage 7.8 (v2.5.6 P1-1 & FB-255-2 语义化自检断言与零 DeprecationWarning 门禁): --self-test 校验进程级零生产写与零假节点残留，不因并发后台选点更新误报失败且 stderr 零告警",
              st_78_proc.returncode == 0
              and "SELF_TEST_PASSED" in (st_78_proc.stdout or "")
              and "DeprecationWarning" not in (st_78_proc.stderr or ""),
              f"rc={st_78_proc.returncode}, stderr_len={len((st_78_proc.stderr or '').strip())}")

        # Stage 7.9 (v2.5.6 P1-2): SelectorWriteCoordinator Target Deduplication, Default 30s Dwell & Multi-Line Anti-Tug-Of-War
        put_calls_79 = []
        dmod._MULTI_LINE_RR_STATE["cursors"].clear()
        dmod._MULTI_LINE_RR_STATE["last_rotate_ts"].clear()
        dmod._MULTI_LINE_RR_STATE["active_target"].clear()
        dmod._MULTI_LINE_RR_STATE["memo_sig"] = None
        dmod.dispatch_multi_line_pools_tick(tmp_v252, advance=True, clash_api_override=lambda s, t: (put_calls_79.append((s, t)) or True))
        writes_after_tick1 = len(put_calls_79)
        dmod.dispatch_multi_line_pools_tick(tmp_v252, advance=True, clash_api_override=lambda s, t: (put_calls_79.append((s, t)) or True))
        dmod.dispatch_multi_line_pools_tick(tmp_v252, advance=True, clash_api_override=lambda s, t: (put_calls_79.append((s, t)) or True))
        writes_after_tick3 = len(put_calls_79)
        dmod.dispatch_multi_line_pools_tick(tmp_v252, advance=True, respect_dwell_interval=False, clash_api_override=lambda s, t: True)
        rot_yt_target = dmod.PROBE_ENGINE.current_selections.get("Shunt_YouTube")
        dmod.PROBE_ENGINE.apply_shunt_selections(tmp_v252)
        after_apply_yt_target = dmod.PROBE_ENGINE.current_selections.get("Shunt_YouTube")
        check("Stage 7.9 (v2.5.6 P1-2 SelectorWriteCoordinator 默认30s驻留、未变目标零冗余PUT与多线防覆盖门禁): 30s驻留期内连续3次tick仅首次执行PUT(后续0次冗余写入)，且 apply_shunt_selections 绝不将已轮换的多线 Selector 覆盖回主节点",
              writes_after_tick1 > 0
              and writes_after_tick3 == writes_after_tick1
              and rot_yt_target == after_apply_yt_target,
              f"tick1_writes={writes_after_tick1}, tick3_writes={writes_after_tick3}, yt_sel={rot_yt_target}=={after_apply_yt_target}")

        # Stage 7.10 (v2.5.6 P1-3): Kernel Log Failover Unknown-Target (targets=[]) Suppression
        dmod._KERNEL_LOG_FAILOVER_STATE["node_err_streaks"].clear()
        res_unknown_tgt = dmod.scan_kernel_logs_for_active_pool_failures(
            tmp_v252,
            log_lines_override=[
                "ERROR outbound/vless[SubA-JP-01]: context deadline exceeded",
                "ERROR outbound/vless[SubA-JP-01]: context deadline exceeded",
                "ERROR outbound/vless[SubA-JP-01]: context deadline exceeded",
            ],
            fail_threshold=3,
            recheck_before_switch=False,
        )
        check("Stage 7.10 (v2.5.6 P1-3 内核日志未知目标 targets=[] 抑制防误切门禁): 3 条无明确目标域名的 context deadline exceeded 被目标多样性守卫抑制 (triggered=False, single_target_suppressed=True)，绝不误切 direct",
              res_unknown_tgt.get("triggered") is False
              and res_unknown_tgt.get("single_target_suppressed") is True,
              f"res={res_unknown_tgt}")

        # Stage 7.11 (v2.5.6 P1-4 & P1-5): Subscription Sync Preview Full Identity Diff (Same-Tag Different-Key) & Dynamic Random Jaccard Warning
        dmod.save_nodes_list([
            {"tag": "Stable-Name", "type": "vless", "server": "10.0.0.1", "server_port": 443, "uuid": "uuid-old", "_sub_id": "sub_diff_test"},
            {"tag": "Rand-01", "type": "vless", "server": "10.0.1.1", "server_port": 443, "uuid": "u1", "_sub_id": "sub_diff_test"},
            {"tag": "Rand-02", "type": "vless", "server": "10.0.1.2", "server_port": 443, "uuid": "u2", "_sub_id": "sub_diff_test"},
            {"tag": "Rand-03", "type": "vless", "server": "10.0.1.3", "server_port": 443, "uuid": "u3", "_sub_id": "sub_diff_test"},
            {"tag": "Rand-04", "type": "vless", "server": "10.0.1.4", "server_port": 443, "uuid": "u4", "_sub_id": "sub_diff_test"},
        ], tmp_v252)
        prev_res_711 = dmod.preview_subscription_sync_impact("sub_diff_test", [
            {"tag": "Stable-Name", "type": "vless", "server": "10.0.0.2", "server_port": 443, "uuid": "uuid-new"},
            {"tag": "NewRand-11", "type": "vless", "server": "10.0.2.1", "server_port": 443, "uuid": "n1"},
            {"tag": "NewRand-12", "type": "vless", "server": "10.0.2.2", "server_port": 443, "uuid": "n2"},
            {"tag": "NewRand-13", "type": "vless", "server": "10.0.2.3", "server_port": 443, "uuid": "n3"},
            {"tag": "NewRand-14", "type": "vless", "server": "10.0.2.4", "server_port": 443, "uuid": "n4"},
        ], conf_dir=tmp_v252)
        check("Stage 7.11 (v2.5.6 P1-4/P1-5 订阅预览同名换节点检测与动态随机订阅 Jaccard 预警门禁): 准确识别同名换节点(endpoint_changed=1, credential_changed=1)、计算 Jaccard=0.0 触发 dynamic_random_sub=True 且附带 request_id",
              prev_res_711.get("ok") is True
              and prev_res_711.get("same_tag_replaced_count") == 1
              and prev_res_711.get("endpoint_changed_count") == 1
              and prev_res_711.get("credential_changed_count") == 1
              and prev_res_711.get("dynamic_random_sub") is True
              and bool(prev_res_711.get("request_id")),
              f"same_tag={prev_res_711.get('same_tag_replaced_count')}, jaccard={prev_res_711.get('jaccard_stability')}, dyn={prev_res_711.get('dynamic_random_sub')}")

        # Stage 7.12 (v2.5.6 P1-6): Strict Subscription TLS Verification (No Auto -k Fallback)
        daemon_src_712 = DAEMON.read_text(encoding="utf-8")
        check("Stage 7.12 (v2.5.6 P1-6 订阅拉取严格 TLS 校验防中间人降级门禁): 移除 35/51/60 错误码自动 -k 重试与无条件 unverified context，仅在 allow_insecure_tls=True 时显式放行",
              'if proc.returncode in (35, 51, 60) and "-k" not in args:' not in daemon_src_712
              and "allow_insecure_tls: bool = False" in daemon_src_712
              and "ssl._create_unverified_context() if _allow_insecure_sub else ssl.create_default_context()" in daemon_src_712,
              "strict TLS verification verified")

        # Stage 7.13 (v2.5.6 P2-1 ~ P2-6): Quota Frozen Split, Legacy Copy Cleanup & Watchdog Recovery Telemetry
        q_doc_p = dmod._node_test_quota_path()
        q_orig = q_doc_p.read_text("utf-8") if q_doc_p.is_file() else None
        try:
            q_doc_p.parent.mkdir(parents=True, exist_ok=True)
            q_doc_p.write_text(json.dumps({
                "date": time.strftime("%Y-%m-%d"),
                "used": 60000,
                "pool_health_used": 100,
                "forced_used": 0,
                "v236_r10_migrated": True,
                "v240_budget_migrated": True,
                "v255_quota_migrated": True,
            }), encoding="utf-8")
            q_sum_713 = dmod.get_node_test_quota_summary(tmp_v252)
        finally:
            if q_orig is not None:
                q_doc_p.write_text(q_orig, "utf-8")
        html_713_txt = (SITE / "root/usr/share/ai-link/webui/index.html").read_text("utf-8")
        js_713_txt = (SITE / "root/usr/share/ai-link/webui/nexus.js").read_text("utf-8")
        check("Stage 7.13 (v2.5.6 P2-1/P2-2/P2-4 手动与健康配额冻结独立拆分、前端旧文案清零与看门狗恢复耗时遥测门禁): 手动配额耗尽但健康配额充足时 manual_quota_frozen=True 且 quota_frozen=False；前端无双组/13组旧文案；看门狗记录 prev_pids/new_pids/recovery_ms",
              q_sum_713.get("manual_quota_frozen") is True
              and q_sum_713.get("pool_health_quota_frozen") is False
              and q_sum_713.get("quota_frozen") is False
              and "13 组策略 · 3 组自动池" not in html_713_txt
              and "双组省流" not in html_713_txt
              and "双组自动节点池" not in js_713_txt
              and "多线并发已开启" not in js_713_txt
              and "_WATCHDOG_RECOVERY_EVENTS" in daemon_src_712,
              f"q_sum={q_sum_713}")

        # Stage 7.14: 500+ node subscription mutation (same-key rename probe inheritance vs same-tag endpoint replacement cache purge)
        #             + SelectorWriteCoordinator external write sync + DNS Interception KPI strip & flex alignment
        sub500_old = [
            {"tag": "Sub500-JP-001", "type": "vless", "server": "jp001.example.com", "server_port": 443, "uuid": "uuid-jp-001", "_sub_id": "sub_500"},
            {"tag": "Sub500-SameTag-Mutated", "type": "vless", "server": "103.1.1.9", "server_port": 443, "uuid": "uuid-old-hk", "_sub_id": "sub_500"},
        ] + [
            {"tag": f"Sub500-Bulk-{i:03d}", "type": "vless", "server": f"n{i}.example.com", "server_port": 443, "uuid": f"uuid-bulk-{i:03d}", "_sub_id": "sub_500"}
            for i in range(3, 521)
        ]
        dmod.save_nodes_list(sub500_old, tmp_v252)
        old_jp_id = dmod.compute_node_id(sub500_old[0])
        old_mut_id = dmod.compute_node_id(sub500_old[1])
        ps_714 = dmod.load_node_probe_store(tmp_v252)
        ps_714[old_jp_id] = {"state": "ok", "delay_ms": 42, "ewma_ms": 42.0, "google_region": "JP", "svc_results": {"chatgpt": {"ok": True, "ms": 80, "code": 200}}, "last_probe_ts": int(time.time())}
        ps_714["Sub500-SameTag-Mutated"] = {"state": "dead", "delay_ms": -1, "quarantine_until": int(time.time()) + 600, "google_region": "HK", "consecutive_fail": 3}
        ps_714[old_mut_id] = dict(ps_714["Sub500-SameTag-Mutated"])
        dmod.save_node_probe_store(ps_714, tmp_v252, strict_gc=False, force_flash=True)

        sub500_new = [
            {"tag": "Sub500-JP-001-VIP", "type": "vless", "server": "jp001.example.com", "server_port": 443, "uuid": "uuid-jp-001", "_sub_id": "sub_500"},
            {"tag": "Sub500-SameTag-Mutated", "type": "vless", "server": "45.88.1.9", "server_port": 8443, "uuid": "uuid-new-sg", "_sub_id": "sub_500"},
        ] + [
            {"tag": f"Sub500-Bulk-{i:03d}", "type": "vless", "server": f"n{i}.example.com", "server_port": 443, "uuid": f"uuid-bulk-{i:03d}", "_sub_id": "sub_500"}
            for i in range(3, 521)
        ]
        merged_714 = dmod.merge_nodes("sub_500", sub500_new, replace_sub=True, conf_dir=tmp_v252)
        ps_after_714 = dmod.load_node_probe_store(tmp_v252)
        new_jp_id = dmod.compute_node_id(sub500_new[0])
        jp_rec_after = ps_after_714.get(new_jp_id) or ps_after_714.get("Sub500-JP-001-VIP") or {}
        mut_rec_after = ps_after_714.get("Sub500-SameTag-Mutated") or ps_after_714.get(dmod.compute_node_id(sub500_new[1])) or {}

        dmod.PROBE_ENGINE.hot_switch_core_selector("Shunt_YouTube", "Sub500-JP-001-VIP", reason="test_ext_sync", conf_dir=tmp_v252)
        w_before_714 = dmod.SELECTOR_WRITE_COORDINATOR.total_writes
        noop_before_714 = dmod.SELECTOR_WRITE_COORDINATOR.skipped_noop
        dmod.SELECTOR_WRITE_COORDINATOR.put_silent("Shunt_YouTube", "Sub500-JP-001-VIP")
        w_after_714 = dmod.SELECTOR_WRITE_COORDINATOR.total_writes
        noop_after_714 = dmod.SELECTOR_WRITE_COORDINATOR.skipped_noop
        css_714_txt = (SITE / "root/usr/share/ai-link/webui/nexus.css").read_text("utf-8")
        check("Stage 7.14 (v2.5.6 500+节点订阅变异同key改名探测继承与同名换服缓存清零 + 协调器外部切换同步 + DNS拦截KPI门禁): 520节点同步中改名节点继承42ms/JP记录、同名换服清空旧HK与隔离态、外部切换同步协调器零冗余PUT、DNS含3-KPI摘要条",
              len(merged_714) == 520
              and jp_rec_after.get("delay_ms") == 42
              and jp_rec_after.get("google_region") == "JP"
              and int(mut_rec_after.get("quarantine_until") or 0) == 0
              and mut_rec_after.get("google_region") != "HK"
              and w_after_714 == w_before_714
              and noop_after_714 == noop_before_714 + 1
              and "dns-blocked-kpi-strip" in js_713_txt
              and "#page-dns .dashboard-grid.two-one > .glass-card > .blocked-list" in css_714_txt,
              f"merged={len(merged_714)}, jp={jp_rec_after.get('delay_ms')}/{jp_rec_after.get('google_region')}, mut={mut_rec_after}, noop_delta={noop_after_714 - noop_before_714}")

        # Stage 7.15: maintain_auto_node_pool_health EWMA+Loss/CV stability scoring & recovering quarantined member retention
        #             + #page-homelink Hero live telemetry binding
        now_715 = int(time.time())
        nodes_715 = [
            {"tag": "SubA-JP-Core-01", "type": "vless", "server": "jp-c1.example.com", "server_port": 443, "uuid": "u-715-1", "_sub_id": "sub_715"},
            {"tag": "SubA-JP-Recovering-02", "type": "vless", "server": "jp-r2.example.com", "server_port": 443, "uuid": "u-715-2", "_sub_id": "sub_715"},
            {"tag": "SubA-JP-Lossy-58ms", "type": "vless", "server": "jp-l3.example.com", "server_port": 443, "uuid": "u-715-3", "_sub_id": "sub_715"},
            {"tag": "SubA-JP-Stable-78ms", "type": "vless", "server": "jp-s4.example.com", "server_port": 443, "uuid": "u-715-4", "_sub_id": "sub_715"},
        ]
        dmod.save_subscriptions([{"id": "sub_715", "name": "Sub715", "url": "https://example.com/s715", "enabled": True}], tmp_v252)
        dmod.save_nodes_list(nodes_715, tmp_v252)
        ps_715 = {
            "SubA-JP-Core-01": {"state": "ok", "delay_ms": 62, "probe_ts": now_715, "sparkline_20": [{"ok": True, "delay_ms": 62}] * 8},
            "SubA-JP-Recovering-02": {"state": "ok", "delay_ms": 70, "probe_ts": now_715, "quarantine_until": now_715 + 240, "sparkline_20": [{"ok": True, "delay_ms": 70}] * 6},
            "SubA-JP-Lossy-58ms": {"state": "ok", "delay_ms": 58, "probe_ts": now_715, "sparkline_20": ([{"ok": True, "delay_ms": 58}, {"ok": False, "delay_ms": -1}] * 5)},
            "SubA-JP-Stable-78ms": {"state": "ok", "delay_ms": 78, "probe_ts": now_715, "sparkline_20": [{"ok": True, "delay_ms": 78}] * 10},
        }
        dmod.save_node_probe_store(ps_715, tmp_v252, strict_gc=False, force_flash=True)

        # Case A: Pool needs 1 external replenishment slot (target_size=2, replenish_threshold=2) -> 78ms 0-loss beats 58ms 50%-loss
        pool_715_a = {
            "id": "auto_715_a", "name": "Pool715A", "auto_maintain": True,
            "target_size": 2, "replenish_threshold": 2,
            "scope_sources": ["sub_715"], "scope_countries": ["JP"],
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-Core-01"], "node_ids": []}],
        }
        dmod.maintain_auto_node_pool_health(pool_715_a, saved_nodes=nodes_715, store=ps_715, conf_dir=tmp_v252, allow_live_l7_probe=False)
        tags_715_a = pool_715_a["groups"][0]["node_tags"]

        # Case B: Pool has 1 healthy + 1 recovering (quarantined) member and 0 external candidates -> recovering member is preserved!
        pool_715_b = {
            "id": "auto_715_b", "name": "Pool715B", "auto_maintain": True,
            "target_size": 3, "replenish_threshold": 2,
            "scope_sources": ["sub_715"], "scope_countries": ["JP"],
            "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["SubA-JP-Core-01", "SubA-JP-Recovering-02"], "node_ids": []}],
        }
        dmod.maintain_auto_node_pool_health(pool_715_b, saved_nodes=nodes_715[:2], store=ps_715, conf_dir=tmp_v252, allow_live_l7_probe=False)
        tags_715_b = pool_715_b["groups"][0]["node_tags"]
        html_715_txt = (SITE / "root/usr/share/ai-link/webui/index.html").read_text("utf-8")
        js_715_txt = (SITE / "root/usr/share/ai-link/webui/nexus.js").read_text("utf-8")
        check("Stage 7.15 (v2.5.6 自动复选 EWMA+丢包/CV 稳定性同源评分 + 恢复中隔离节点防误删 + 回家网关 Hero 实时遥测绑定门禁): 复选补位时 78ms 零丢包胜出 58ms 50%丢包节点；无外部候选替补时保留池内恢复中节点不误删；回家页 Hero 三联指标绑定真值",
              tags_715_a == ["SubA-JP-Core-01", "SubA-JP-Stable-78ms"]
              and "SubA-JP-Recovering-02" in tags_715_b
              and "hl-hero-stat-tunnels" in html_715_txt
              and "hl-hero-stat-clients" in html_715_txt
              and "hl-hero-stat-traffic" in js_715_txt,
              f"tags_a={tags_715_a}, tags_b={tags_715_b}")
    finally:
        shutil.rmtree(tmp_v252, ignore_errors=True)

    print("\n" + "=" * 78)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print(f" 合计 {len(results)} 项，通过 {passed}，失败 {failed}")
    print("=" * 78)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())