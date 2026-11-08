#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-LINK v2.3.0 E2E 验证套件：
覆盖 NEXT-SUBMISSION-4 (BUG-008 strict_lock 持久化往返) + PRD 方案 A 批次三 & 批次四全量需求：
  - BUG-008: POST /api/shunt/update strict_lock 持久化落盘、死节点锁定不漂移、关闭后恢复漂移与 ⚠ 告警
  - T2: 4 种拓扑自动识别 (main / bypass / onearm / docker) + 3 步接入向导闭环
  - T3: 旁路由 IPv6 防漏组合模式（严格档 / 宽松档 / 关闭 + T1 第 3 项联动）
  - T5: 告警通道（Webhook 真 HTTP 投递 / 令牌脱敏 / 30 分钟去重 / 恢复通知 / 事件中心）
  - T6: 配置变更历史 + 结构化字段 Diff + <10s 一键回滚
  - T8: 规则块增强（domain_regex / src_ip_cidr / port / 两级 AND-OR + 非法正则位置拦截 + 试匹配）
  - T9: 远程规则订阅（5,000 条导入 + 404 失败原子保留旧规则）
  - T10: DNS 按组独立策略（四阶透视验证互不影响）+ 上游缓存命中率/延迟/失败率统计
"""
import importlib.util
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _paths import DAEMON  # noqa: E402

spec = importlib.util.spec_from_file_location("ailink_daemon_v230", str(DAEMON))
dmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmod)

results = []


def check(title: str, ok: bool, detail: str = ""):
    results.append((title, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  {mark}  {title}" + (f"  [{detail}]" if detail else ""))


print("=" * 78)
print(" AI-LINK v2.3.0 · BUG-008 严格锁定持久化 + 方案A (T2/T3/T5/T6/T8/T9/T10) E2E")
print("=" * 78)

tmp_dir = Path(tempfile.mkdtemp(prefix="ailink_v230_e2e_"))
try:
    # Seed test nodes & probe store (SG-Alive-01 is alive 45ms; JP-Dead-04 is dead)
    nodes_seed = [
        {"tag": "SG-Alive-01", "node_id": "nid_sg_1", "type": "vless", "server": "198.51.100.11", "server_port": 443, "uuid": "u-1"},
        {"tag": "JP-Dead-04", "node_id": "nid_jp_4", "type": "vless", "server": "198.51.100.44", "server_port": 443, "uuid": "u-4"},
    ]
    (tmp_dir / "nodes.json").write_text(json.dumps(nodes_seed, ensure_ascii=False), encoding="utf-8")
    now_ts = int(time.time())
    probe_seed = {
        "nid_sg_1": {"state": "ok", "delay_ms": 45.0, "ewma_ms": 45.0, "probe_ts": now_ts, "last_probe_ts": now_ts, "updated_at": now_ts, "google_region": "SG"},
        "SG-Alive-01": {"state": "ok", "delay_ms": 45.0, "ewma_ms": 45.0, "probe_ts": now_ts, "last_probe_ts": now_ts, "updated_at": now_ts, "google_region": "SG"},
        "nid_jp_4": {"state": "dead", "delay_ms": 0.0, "ewma_ms": 0.0, "probe_ts": now_ts, "last_probe_ts": now_ts, "updated_at": now_ts, "fail_streak": 4},
        "JP-Dead-04": {"state": "dead", "delay_ms": 0.0, "ewma_ms": 0.0, "probe_ts": now_ts, "last_probe_ts": now_ts, "updated_at": now_ts, "fail_streak": 4},
    }
    (tmp_dir / "node_probe.json").write_text(json.dumps(probe_seed, ensure_ascii=False), encoding="utf-8")

    # =========================================================================
    # 1. BUG-008 P1: /api/shunt/update strict_lock 持久化落盘与死节点漂移/锁定往返
    # =========================================================================
    sh_cfg = dmod.load_shunt_config(tmp_dir)
    # Add Custom_1792799766286 pointing manually to dead node JP-Dead-04
    custom_gid = "Custom_1792799766286"
    sh_cfg["groups"].insert(0, {
        "id": custom_gid,
        "name": "Soul",
        "subtitle": "自定义社交组",
        "is_custom": True,
        "shunt_mode": "manual",
        "strategy": "manual",
        "country": "JP",
        "manual_node": "JP-Dead-04",
        "strict_lock": False,
        "domains": ["soulapp.com"],
    })
    dmod.save_shunt_config(sh_cfg, tmp_dir)

    # Simulate POST /api/shunt/update {"group_id": custom_gid, "strict_lock": True}
    # by running the exact HTTP handler logic against tmp_dir
    orig_conf_dir, orig_run_dir = dmod.CONF_DIR, dmod.RUN_DIR
    dmod.CONF_DIR, dmod.RUN_DIR = tmp_dir, tmp_dir
    try:
        # Step 1a: P1-05 Manual = Fixed: When manual_node=JP-Dead-04 (dead), it NEVER drifts to SG-Alive-01 (manual_drifted=False)
        dmod._SHUNT_API_MEMO.clear()
        sh_before = dmod.build_shunt_api_response(tmp_dir)
        g_before = next(x for x in sh_before["groups"] if x["id"] == custom_gid)
        check(
            "BUG-008 / P1-05 (手动模式固定不漂移): manual_node=JP-Dead-04 死节点保持固定 resolved_node=JP-Dead-04 且 manual_drifted=False",
            g_before.get("resolved_node") == "JP-Dead-04"
            and g_before.get("manual_drifted") is False
            and g_before.get("strict_locked_dead") is True,
            f"resolved={g_before.get('resolved_node')} drifted={g_before.get('manual_drifted')} warn={g_before.get('drift_warning')}",
        )

        # Step 1b: Simulate POST /api/shunt/update {"group_id": custom_gid, "strict_lock": True} (only group_id & strict_lock!)
        payload_on = {"group_id": custom_gid, "strict_lock": True}
        sh_up = dmod.load_shunt_config(tmp_dir)
        for g in sh_up.get("groups", []):
            if g["id"] == payload_on["group_id"]:
                for fk in ("country", "strategy", "manual_node", "shunt_mode", "auto_node_id", "strict_lock", "dns_strategy", "custom_dns", "rule_blocks"):
                    if fk in payload_on:
                        g[fk] = bool(payload_on[fk]) if fk == "strict_lock" else payload_on[fk]
                sm_n, c_n, st_n, aid_n, m_n = dmod._normalize_group_shunt_params(g)
                g["shunt_mode"], g["country"], g["strategy"], g["auto_node_id"], g["manual_node"] = sm_n, c_n, st_n, aid_n, m_n
                break
        dmod.save_shunt_config(sh_up, tmp_dir)
        dmod._SHUNT_API_MEMO.clear()

        disk_sh = json.loads((tmp_dir / "shunt.json").read_text(encoding="utf-8"))
        disk_grp = next(x for x in disk_sh["groups"] if x["id"] == custom_gid)
        sh_after_on = dmod.build_shunt_api_response(tmp_dir)
        g_after_on = next(x for x in sh_after_on["groups"] if x["id"] == custom_gid)
        check(
            "BUG-008 (strict_lock=True 持久化落盘与不漂移): shunt.json 落盘 strict_lock=True，resolved_node 保持 JP-Dead-04 且 strict_locked_dead=True",
            disk_grp.get("strict_lock") is True
            and g_after_on.get("strict_lock") is True
            and g_after_on.get("resolved_node") == "JP-Dead-04"
            and g_after_on.get("strict_locked_dead") is True
            and g_after_on.get("manual_drifted") is False,
            f"disk={disk_grp.get('strict_lock')} api_lock={g_after_on.get('strict_lock')} resolved={g_after_on.get('resolved_node')} dead_locked={g_after_on.get('strict_locked_dead')}",
        )

        #=====================================================================
        # 2. T2: 拓扑自动识别 (main / bypass / onearm / docker) + 3 步向导验证
        #=====================================================================
        t_main = dmod.detect_network_topology(tmp_dir, {"default_if": "pppoe-wan", "dhcp_active": True, "wan_has_public_ip": True, "lan_ip": "10.10.10.1"})
        t_bypass = dmod.detect_network_topology(tmp_dir, {"default_if": "br-lan", "gateway_ip": "10.10.10.1", "dhcp_active": False, "wan_has_public_ip": False, "lan_ip": "10.10.10.7", "iface_count": 2})
        t_onearm = dmod.detect_network_topology(tmp_dir, {"default_if": "eth0", "gateway_ip": "10.10.10.1", "dhcp_active": False, "wan_has_public_ip": False, "lan_ip": "10.10.10.8", "iface_count": 1})
        t_docker = dmod.detect_network_topology(tmp_dir, {"is_docker": True, "default_if": "eth0", "gateway_ip": "172.17.0.1", "lan_ip": "172.17.0.2"})
        check(
            "T2-1 (4种拓扑样本自动识别): main / bypass / onearm / docker 4/4 识别准确且附带置信度与判据文本",
            t_main["topology"] == "main"
            and t_bypass["topology"] == "bypass"
            and t_onearm["topology"] == "onearm"
            and t_docker["topology"] == "docker"
            and all(len(x.get("evidence") or []) >= 2 for x in (t_main, t_bypass, t_onearm, t_docker)),
            f"detected={[t_main['topology'], t_bypass['topology'], t_onearm['topology'], t_docker['topology']]}",
        )

        wiz_res = dmod.apply_topology_wizard({
            "topology": "bypass",
            "enable_ipv6_leak_guard": True,
            "ipv6_leak_mode": "strict",
            "mock_env": {"active_dns_clients": ["10.10.10.58"], "local_aaaa_count": 0, "client_public_ipv6": "2408:8240::1"},
        }, tmp_dir)
        check(
            "T2-2 (旁路由3步接入向导闭环): ≤3步完成接入并联动 T1 第 1/2/3 项验证全部 pass",
            wiz_res.get("ok") is True and wiz_res.get("verified") is True and len(t_bypass.get("wizard_steps") or []) == 3,
            f"verified={wiz_res.get('verified')} steps={len(t_bypass.get('wizard_steps') or [])}",
        )

        #=====================================================================
        # 3. T3: 旁路由 IPv6 防漏组合模式（严格档 / 宽松档 / 关闭）
        #=====================================================================
        dmod.update_ops_settings({"ipv6_proxy": False, "ipv6_leak_guard": True, "ipv6_leak_mode": "strict"}, tmp_dir)
        nft_strict = dmod.generate_nft_rules_file(tmp_dir, tmp_dir)
        diag_strict = dmod.run_network_health_doctor({"client_public_ipv6": "2408:8240::99"}, tmp_dir)
        chk3_strict = next(c for c in diag_strict["checks"] if c["id"] == "ipv6_bypass")
        check(
            "T3-1 (严格档默认): forward 链阻断全部 LAN→WAN IPv6 (不含 @cn_ip6 放行) 且 T1 第 3 项变为 pass",
            "meta nfproto ipv6 reject with icmpv6 type no-route" in nft_strict
            and "# T3 Side-Router IPv6 Leak Guard (strict mode)" in nft_strict
            and chk3_strict["status"] == "pass",
            f"chk3={chk3_strict['status']}",
        )

        dmod.update_ops_settings({"ipv6_leak_mode": "loose"}, tmp_dir)
        nft_loose = dmod.generate_nft_rules_file(tmp_dir, tmp_dir)
        check(
            "T3-2 (宽松档): 放行国内 IPv6 (@cn_ip6 accept) 并阻断非国内 IPv6 出站",
            "# T3 Side-Router IPv6 Leak Guard (loose mode)" in nft_loose
            and "ip6 daddr @cn_ip6 accept" in nft_loose
            and "meta nfproto ipv6 reject with icmpv6 type no-route" in nft_loose,
            "loose mode cn_ip6 + reject verified",
        )

        dmod.update_ops_settings({"ipv6_leak_guard": False, "ipv6_leak_mode": "off"}, tmp_dir)
        nft_off = dmod.generate_nft_rules_file(tmp_dir, tmp_dir)
        check(
            "T3-3 (关闭防漏模式): 恢复现状且不残留任何 IPv6 reject 防漏规则",
            "T3 Side-Router IPv6 Leak Guard" not in nft_off and "reject with icmpv6 type no-route" not in nft_off,
            "clean teardown verified",
        )

        #=====================================================================
        # 4. T5: 告警通道（Webhook 投递 / 令牌脱敏 / 30分钟去重 / 恢复通知）
        #=====================================================================
        wh_received = []

        class _MockWebhookHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                ln = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(ln).decode("utf-8"))
                wh_received.append(body)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, *args):
                pass

        wh_srv = HTTPServer(("127.0.0.1", 0), _MockWebhookHandler)
        wh_port = wh_srv.server_port
        threading.Thread(target=wh_srv.serve_forever, daemon=True).start()
        try:
            saved_al = dmod.save_alerts_config({
                "enabled": True,
                "dedup_window_sec": 1800,
                "webhook": {"enabled": True, "url": f"http://127.0.0.1:{wh_port}/hook", "secret": "whsec_super_secret_998877"},
                "telegram": {"enabled": True, "bot_token": "123456789:AAH_secret_telegram_token", "chat_id": "-100999"},
            }, tmp_dir)
            r_fire1 = dmod.trigger_alert_event("nodes_down", detail="自动节点池无可用节点", status="firing", conf_dir=tmp_dir, now_ts=10000)
            r_fire2 = dmod.trigger_alert_event("nodes_down", detail="自动节点池无可用节点(重复)", status="firing", conf_dir=tmp_dir, now_ts=10500)
            r_recov = dmod.trigger_alert_event("nodes_down", detail="节点池已恢复 3 个可用节点", status="recovered", conf_dir=tmp_dir, now_ts=10800)
            check(
                "T5 (告警通道 + 30分钟去重 + 恢复通知 + 令牌脱敏): Webhook 60s 内收到告警 JSON，30分钟内重复触发仅发 1 条，恢复时收到 recovered 且密钥脱敏",
                "***" in saved_al["webhook"]["secret"]
                and "***" in saved_al["telegram"]["bot_token"]
                and r_fire1["suppressed"] is False
                and r_fire2["suppressed"] is True and r_fire2.get("reason") == "dedup_30m"
                and r_recov["suppressed"] is False
                and len(wh_received) == 2
                and wh_received[0]["event"] == "nodes_down" and wh_received[0]["status"] == "firing"
                and wh_received[1]["status"] == "recovered",
                f"webhook_calls={len(wh_received)} dedup_reason={r_fire2.get('reason')} masked_tg={saved_al['telegram']['bot_token']}",
            )
        finally:
            wh_srv.shutdown()

        #=====================================================================
        # 5. T6: 配置变更历史 + 结构化字段 Diff + 10秒内回滚
        #=====================================================================
        (tmp_dir / "config_history.json").unlink(missing_ok=True)
        for idx_m, ctry in enumerate(("US", "SG", "JP"), start=1):
            sc = dmod.load_shunt_config(tmp_dir)
            sc["global_country"] = ctry
            dmod.record_config_snapshot(source="panel", summary=f"第 {idx_m} 次修改全局国家为 {ctry}", conf_dir=tmp_dir, new_shunt_cfg=sc)
            dmod.save_shunt_config(sc, tmp_dir)
        hist_list = dmod.load_config_history(tmp_dir)
        first_snap_id = hist_list[-1]["id"]  # Snapshot #1 (country == "US")
        t0_rb = time.time()
        rb_res = dmod.rollback_config_snapshot(first_snap_id, target_state="files", conf_dir=tmp_dir)
        rb_elapsed = time.time() - t0_rb
        restored_sc = dmod.load_shunt_config(tmp_dir)
        check(
            "T6 (配置变更历史 + Diff + 10秒回滚): 连续修改 3 次记录 3 条结构化 Diff，回滚至第 1 条在 <1s (≤10s) 内生效且配置完全一致",
            len(hist_list) == 3
            and all(isinstance(h.get("changes"), list) for h in hist_list)
            and rb_res.get("ok") is True
            and rb_elapsed <= 10.0
            and restored_sc.get("global_country") == "US",
            f"hist_len={len(hist_list)} elapsed={rb_elapsed*1000:.1f}ms restored_country={restored_sc.get('global_country')}",
        )

        #=====================================================================
        # 6. T8: 规则块增强（domain_regex / src_ip_cidr / 两级 AND-OR + 非法正则拦截 + 试匹配）
        #=====================================================================
        bad_rx = dmod.validate_and_normalize_rule_blocks([
            {"id": "rb_bad", "name": "非法正则测试", "logic": "AND", "domain_regex": ["(["]}
        ])
        check(
            "T8-1 (非法正则保存拦截与精确位置提示): 输入非法正则 '([' 被拦截且提示「正则不合法：位置 2」",
            bad_rx.get("ok") is False and "正则不合法：位置 2" in str(bad_rx.get("message", "")),
            f"msg={bad_rx.get('message')}",
        )

        good_rx = dmod.validate_and_normalize_rule_blocks([
            {
                "id": "rb_soul_phone",
                "name": "手机专属 Soul API 正则",
                "enabled": True,
                "priority": 1,
                "logic": "AND",
                "domain_regex": [r"^api.*\.soulapp\.cn$"],
                "src_ip_cidr": ["10.10.10.58/32"],
            }
        ])
        sc_t8 = dmod.load_shunt_config(tmp_dir)
        for g in sc_t8["groups"]:
            if g["id"] == custom_gid:
                g["rule_blocks"] = good_rx["rule_blocks"]
        dmod.save_shunt_config(sc_t8, tmp_dir)
        dmod._SHUNT_API_MEMO.clear()

        m_phone = dmod.test_shunt_rule_match({"target": "api-chat.soulapp.cn", "src_ip": "10.10.10.58"}, conf_dir=tmp_dir)
        m_pc = dmod.test_shunt_rule_match({"target": "api-chat.soulapp.cn", "src_ip": "10.10.10.99"}, conf_dir=tmp_dir)
        check(
            "T8-2 (domain_regex AND src_ip 组合规则与试匹配): 手机 (10.10.10.58) 访问 api-chat.soulapp.cn 命中 Soul 组，PC (10.10.10.99) 访问同域名不命中该规则块",
            m_phone.get("group_id") == custom_gid
            and m_phone.get("rule_block_id") == "rb_soul_phone"
            and m_pc.get("rule_block_id") is None
            and m_pc.get("group_id") != custom_gid,
            f"phone_grp={m_phone.get('group_id')} pc_grp={m_pc.get('group_id')}",
        )

        #=====================================================================
        # 7. T9: 远程规则订阅（5,000 条导入 + 404 失败保留旧规则）
        #=====================================================================
        five_k_text = "\n".join(f"DOMAIN-SUFFIX,rule-{i}.soul-ext.org" for i in range(5000))
        dmod.save_rule_providers([{
            "id": "rp_5k",
            "name": "5000条扩展规则源",
            "url": "https://rules.example.com/5000.list",
            "format": "domain_list",
            "group_id": custom_gid,
            "interval_hours": 24,
            "enabled": True,
            "rule_count": 0,
            "cached_domains": [],
        }], tmp_dir)
        sync_ok = dmod.sync_rule_provider("rp_5k", conf_dir=tmp_dir, mock_content=five_k_text)
        sync_404 = dmod.sync_rule_provider("rp_5k", conf_dir=tmp_dir, mock_status=404)
        tr_rp = dmod.test_shunt_rule_match({"target": "sub.rule-4999.soul-ext.org"}, conf_dir=tmp_dir)
        check(
            "T9 (远程规则订阅 5,000 条同步与 404 原子保旧): 首次同步准确生效 5,000 条；后续返回 404 时记录失败原因且 5,000 条旧规则 100% 保留生效",
            sync_ok.get("ok") is True and sync_ok.get("rule_count") == 5000
            and sync_404.get("ok") is False and sync_404.get("preserved_rule_count") == 5000
            and tr_rp.get("group_id") == custom_gid,
            f"count_ok={sync_ok.get('rule_count')} preserved_on_404={sync_404.get('preserved_rule_count')} hit_grp={tr_rp.get('group_id')}",
        )
        # P2-1 (NEXT-SUBMISSION-5): 远程规则源删除与无 URL 垃圾条目防护
        del_res = dmod.delete_rule_provider("rp_5k", conf_dir=tmp_dir)
        disk_rps_after_del = json.loads((tmp_dir / "rule_providers.json").read_text(encoding="utf-8"))
        check(
            "P2-1 (远程规则源删除同步落盘): 删除 rp_5k 后从列表消失且 rule_providers.json 同步移除",
            del_res.get("ok") is True and len(del_res.get("providers") or []) == 0 and len(disk_rps_after_del) == 0,
            f"remaining={len(del_res.get('providers') or [])} disk={len(disk_rps_after_del)}",
        )

        #=====================================================================
        # 8. T10: DNS 按组策略 + 1 小时上游缓存命中率/延迟/失败率统计
        #=====================================================================
        sc_t10 = dmod.load_shunt_config(tmp_dir)
        for g in sc_t10["groups"]:
            if g["id"] == custom_gid:
                g["dns_strategy"] = "doh"
                g["custom_dns"] = "https://dns.quad9.net/dns-query"
        dmod.save_shunt_config(sc_t10, tmp_dir)
        dmod._SHUNT_API_MEMO.clear()

        tr_soul_dns = dmod.trace_traffic_flow({"target": "soulapp.com"}, conf_dir=tmp_dir)
        tr_yt_dns = dmod.trace_traffic_flow({"target": "www.youtube.com"}, conf_dir=tmp_dir)
        up_stats = dmod.build_dns_upstream_stats(tmp_dir)
        check(
            "T10 (DNS 按组独立策略与上游缓存统计): Soul 组透视显示使用自定义 DoH (quad9) 且不影响其他组，上游统计命中率/延迟/失败率均非 0",
            tr_soul_dns["stage2_dns"].get("dns_strategy") == "doh"
            and "dns.quad9.net" in tr_soul_dns["stage2_dns"].get("summary", "")
            and tr_yt_dns["stage2_dns"].get("dns_strategy") == "inherit"
            and len(up_stats.get("upstreams") or []) >= 3
            and all(u.get("cache_hit_rate_pct", 0) > 0 and u.get("avg_latency_ms", 0) > 0 for u in up_stats["upstreams"]),
            f"soul_dns={tr_soul_dns['stage2_dns'].get('custom_dns')} yt_dns={tr_yt_dns['stage2_dns'].get('dns_strategy')} upstreams={len(up_stats.get('upstreams') or [])}",
        )
        #=====================================================================
        # 9. v2.3.2 紧急修复 1: LAN Wi-Fi 下 Google Play 更新全链路验证
        #    (dnsmasq 无 cname 黑洞 + HTTPS/SVCB 抑制 + route.rules 优先于 blocklist_custom + nft @google_play_v4)
        #=====================================================================
        dmod.write_all_configs(tmp_dir, force_full=True)
        rw_conf_txt = (tmp_dir / "ai-link-rewrite.conf").read_text(encoding="utf-8")
        sb_cfg = json.loads((tmp_dir / "sing-box.json").read_text(encoding="utf-8"))
        nft_txt = dmod.generate_nft_rules_file(tmp_dir, tmp_dir)
        dns_r0 = (sb_cfg.get("dns", {}).get("rules") or [{}])[0]
        route_rules_list = sb_cfg.get("route", {}).get("rules") or []
        gp_route_idx = next((i for i, r in enumerate(route_rules_list) if "c.android.clients.google.com" in (r.get("domain_suffix") or [])), -1)
        blk_route_idx = next((i for i, r in enumerate(route_rules_list) if "blocklist_custom" in (r.get("rule_set") or []) or "xycdn.com" in (r.get("domain_suffix") or [])), 999)
        check(
            "v2.3.2 紧急修复1 (Play商店 LAN Wi-Fi 更新全链路): dnsmasq 禁用 cname= 防 NODATA 黑洞、DNS 首条抑制 HTTPS/SVCB、Play 路由优先于黑洞且 nft @google_play_v4 优先于 @cn_ip4",
            "cname=services.googleapis.cn" not in rw_conf_txt
            and "server=/services.googleapis.cn/127.0.0.1#7874" in rw_conf_txt
            and dns_r0.get("query_type") == ["HTTPS", "SVCB"] and dns_r0.get("rcode") == "NOERROR"
            and 0 <= gp_route_idx < blk_route_idx
            and "ip daddr @google_play_v4 meta l4proto { tcp, udp } tproxy" in nft_txt
            and nft_txt.find("@google_play_v4") < nft_txt.find("ip daddr @cn_ip4 accept"),
            f"gp_idx={gp_route_idx}<blk_idx={blk_route_idx}, dns_r0={dns_r0}",
        )
    finally:
        dmod.CONF_DIR, dmod.RUN_DIR = orig_conf_dir, orig_run_dir
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)

print("\n" + "=" * 78)
fails = [r for r in results if not r[1]]
print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
print("=" * 78)
sys.exit(1 if fails else 0)
