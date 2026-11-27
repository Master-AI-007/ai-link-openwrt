#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OPT-278-05: Standalone fast unit tests for diag.py (zero daemon import)."""
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIAG_DIR = ROOT / "root/usr/share/ai-link"
if str(DIAG_DIR) not in sys.path:
    sys.path.insert(0, str(DIAG_DIR))

import ailink_diag as diag  # noqa: E402


def main() -> int:
    results = []

    def check(name: str, ok: bool, detail: str = ""):
        results.append((name, bool(ok), detail))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


    # 11. OPT-279-01..10
    snap = diag.save_shunt_undo_snapshot({"groups": [{"id": "AI"}]}, reason="test", now_ts=1000.0)
    assert snap["ok"] is True
    undone = diag.restore_shunt_undo_snapshot(now_ts=1010.0)
    assert undone["ok"] is True and undone["shunt"]["groups"][0]["id"] == "AI"
    print("  PASS  OPT-279-01 分流规则 30s 撤销快照")

    doh = diag.evaluate_custom_doh_fallback(consecutive_timeouts=3, custom_doh_url="https://dns.quad9.net/dns-query")
    assert doh["fallback_active"] is True and "223.5.5.5" in doh["fallback_dns"]
    jit = diag.compute_node_jitter_stats([{"ok": True, "delay_ms": 50}, {"ok": True, "delay_ms": 140}])
    assert jit["jitter_ms"] == 90 and jit["high_jitter"] is True
    hl = diag.summarize_homelink_clients([{"name": "iPhone", "online": True, "latest_handshake_ts": 1700000100}], now_ts=1700000120)
    assert hl["online_count"] == 1
    dq = diag.check_disk_quota_warning(paths=["/etc/ai-link"], usage_override={"/etc/ai-link": 88.5})
    assert dq["warning_active"] is True
    fo = diag.detect_flow_offloading_conflict(firewall_conf_text="option flow_offloading '1'", data_plane_mode="tproxy_redirect")
    assert fo["conflict"] is True
    wd = diag.format_watchdog_recovery_event(reason="oom", downtime_s=3.2, recovered_node="JP-01")
    assert "JP-01" in wd["summary"]
    gw = diag.detect_upstream_gateway_mac_change("10.10.10.1", "aa:bb:cc:dd:ee:02", "aa:bb:cc:dd:ee:01")
    assert gw["changed"] is True
    print("  PASS  OPT-279-02..10 诊断与自愈纯函数套件")


    # 12. OPT-280-01..10
    sb_r = diag.export_shunt_to_singbox_route_rules({"groups": [{"id": "AI", "domains": ["openai.com"]}]})
    assert sb_r["count"] == 1 and sb_r["route"]["rules"][0]["outbound"] == "Shunt_AI"
    ecs = diag.build_dns_ecs_privacy_patch(True)
    assert ecs["ecs_strip_enabled"] is True and ecs["client_subnet"] == "0.0.0.0/0"
    cd = diag.compute_node_cooldown_progress({"rate_limited_until": 2000}, now_ts=1500, total_cooldown_s=1000)
    assert cd["in_cooldown"] is True and cd["remaining_s"] == 500
    pk = diag.record_disk_peak_usage({"/etc/ai-link": 72.5})
    assert pk["peaks"]["/etc/ai-link"] >= 72.5
    vpns = diag.get_vpn_bypass_interfaces(["eth0", "wg0", "tailscale0", "ailink0"])
    assert vpns["interfaces"] == ["tailscale0", "wg0"]
    assert diag.verify_ipk_conffiles_preservation("conffiles\n/etc/config/ai-link")["has_conffiles"] is True
    bg = diag.evaluate_bypass_boot_grace(uptime_s=12.0, gw_reachable=False)
    assert bg["suppress_offline_alert"] is True
    print("  PASS  OPT-280-01..10 路由导出/隐私/冷却/峰值/VPN白名单/开机宽限")


    # 13. OPT-281-01..10
    ro = diag.reorder_shunt_group_rules([{"id": "A"}, {"id": "B"}], "B", "up")
    assert ro["moved"] is True and ro["groups"][0]["id"] == "B"
    dns_dt = diag.compute_dns_dual_track_latency_stats({"domestic": [10, 20, 30], "overseas": [80, 120, 200]})
    assert dns_dt["domestic"]["p50_ms"] == 20.0 and dns_dt["overseas"]["p95_ms"] >= 120.0
    tl = diag.format_failover_timeline_24h([{"ts": 2000, "pool_id": "auto_ai", "from_node": "N1", "to_node": "N2"}], now_ts=2500)
    assert tl["count"] == 1
    assert diag.validate_singbox_log_level("info")["ok"] is True
    assert diag.check_vpn_tun_mtu_compatibility(["wg0"], 1500)["conflict"] is True
    assert diag.reconcile_upstream_recovery_alert(prev_alert=True, gw_reachable=True)["auto_cleared"] is True
    print("  PASS  OPT-281-01..10 排序/DNS分布/时间线/日志级别/MTU/恢复自愈")

    print("=" * 78)
    print(" AI-LINK ailink_diag 独立模块单元测试 (OPT-278-05)")
    print("=" * 78)

    # 1. Tag sanitization & deduplication
    t1 = diag.sanitize_singbox_outbound_tag("🚀 日本-VIP\x00\n", max_bytes=16)
    d1 = diag.deduplicate_outbound_tags(["JP-01", "JP-01", "JP-01"])
    check("标签清洗与去重", ("\x00" not in t1) and len(d1) == 3 and len(set(d1)) == 3, str(d1))

    # 2. Backup schema validation & migration
    mig = diag.validate_and_migrate_backup_schema({"version": "2.5.0", "proxy_enabled": True, "bypass_mode": False})
    check("备份 Schema 自动迁移 (<v2.6.0)", mig.get("migrated") is True and mig.get("schema_version") == diag.DIAG_MODULE_VERSION, str(mig.get("migration_changes")))

    # 3. Scope sources empty guard
    sc = diag.diagnose_auto_pool_scope_sources({"scope_sources": ["sub_deleted"]}, [{"id": "sub1", "name": "CF1"}], [])
    check("scope_sources 空集保护", sc.get("scope_sources_empty") is True and "已不存在" in sc.get("empty_reason", ""), sc.get("empty_reason", ""))

    # 4. Adaptive probe concurrency
    c_low = diag.get_adaptive_probe_concurrency(16, cpu_count=1)
    c_hi = diag.get_adaptive_probe_concurrency(16, cpu_count=8)
    check("测速并发数按核心数自适应", c_low == 2 and c_hi == 8, f"1core={c_low}, 8core={c_hi}")

    # 5. Atomic DNS cache flush (isolated temp dir)
    with tempfile.TemporaryDirectory() as td:
        fl = diag.flush_dns_caches_atomic("unit_test", run_cmd=lambda *a, **k: type("R", (), {"returncode": 0})(), state_dir=pathlib.Path(td))
        check("DNS 缓存原子刷新", fl.get("ok") is True and (pathlib.Path(td) / "dns_cache_epoch.json").is_file(), str(fl.get("actions")))

    # 6. HomeLink port conflict summary
    hl = diag.check_homelink_port_conflict_summary([{"id": "h1", "name": "HL", "listen_port": 9099}], panel_port=9099, live_tcp_ports=set(), live_udp_ports=set())
    check("HomeLink 端口冲突检测", hl.get("conflict_count") == 1, str(hl.get("conflicts")))

    # 7. IPv6 RA/NDP conflict check
    ra = diag.check_bypass_ipv6_ra_ndp_conflict({"ipv6_proxy": True, "topology_mode": "bypass"}, "option ra 'server'\noption ndp 'relay'")
    check("旁路由 IPv6 RA/NDP 冲突检测", ra.get("has_conflict") is True, ra.get("message", ""))

    # 8. OPT-278-01 Bulk shunt rules validation
    br_ok = diag.parse_and_validate_bulk_shunt_rules("openai.com\n192.168.10.0/24\n# comment\n")
    br_bad = diag.parse_and_validate_bulk_shunt_rules("not a valid domain!!!")
    check("OPT-278-01 分流规则批量解析校验", br_ok.get("ok") is True and len(br_ok.get("domains", [])) == 1 and len(br_ok.get("ip_cidrs", [])) == 1 and len(br_bad.get("invalid", [])) == 1)

    # 9. OPT-278-03 Subscription usage summary
    sub_sum = diag.compute_subscription_usage_summary({"upload": 100, "download": 300, "total": 1000, "expire": 2000000000}, now_ts=1999136000)
    check("OPT-278-03 订阅流量与到期倒计时计算", sub_sum.get("remaining_pct") == 60.0 and sub_sum.get("days_left") == 10, str(sub_sum))

    # 10. OPT-278-09 & OPT-278-10 Schedule preview & multi-subnet forwarding
    sched = diag.compute_next_schedule_preview(interval_hours=6, last_run_ts=1000, now_ts=2000)
    ms = diag.check_bypass_multi_subnet_forwarding({"topology_mode": "bypass"}, "config interface 'lan'\nconfig interface 'guest'\n")
    check("OPT-278-09/10 调度预览与多网段旁路检测", sched.get("next_run_ts") == 1000 + 6 * 3600 and ms.get("multi_subnet") is True, f"next={sched.get('next_run_ts')}, subnets={ms.get('subnets')}")

    # 11. OPT-282-01~06, 10
    hr = diag.rank_shunt_rules_by_heat([{"rule_id": "AI", "hits": 42, "last_hit_ts": 2000}], [{"id": "EmptyRule"}])
    dc = diag.check_doh_cert_expiry_health([{"tag": "cf", "days_remaining": 7}], warn_days=14)
    ip_res = diag.filter_incremental_probe_nodes([{"tag": "ok1", "state": "ok", "delay_ms": 50}, {"tag": "u1", "state": "untested", "delay_ms": -1}])
    al = diag.export_sanitized_audit_log([{"action": "save", "token": "secret123"}])
    sm = diag.detect_external_storage_migration_targets([{"path": "/mnt/sda1", "free_mb": 2048, "writable": True}])
    gp = diag.get_game_udp_platform_presets(["steam", "battlenet"])
    dh = diag.verify_onearm_dhcp_options("10.10.10.77", "10.10.10.77", "10.10.10.1")
    check(
        "OPT-282-01~10 诊断模块全套能力校验",
        hr["ranked"][0]["rule_id"] == "AI"
        and len(dc["warnings"]) == 1
        and ip_res["candidate_count"] == 1
        and al["entries"][0]["token"] == "***"
        and sm["recommended_target"] == "/mnt/sda1"
        and "27000-27050" in gp["merged_udp_ports"]
        and dh["ok"] is False and dh["option3_ok"] is True and dh["option6_ok"] is False,
    )

    # 12. LOCAL-282-01 real no-mock call (mounts=None + real existing temp path)
    sm_nomock = diag.detect_external_storage_migration_targets(mounts=None)
    with tempfile.TemporaryDirectory() as _td_sm:
        sm_real = diag.detect_external_storage_migration_targets([{"path": _td_sm, "free_mb": 256, "writable": True}])
    check(
        "LOCAL-282-01 外置存储探测无 mock 实测 (mounts=None + shutil.disk_usage)",
        sm_nomock.get("ok") is True and sm_real.get("recommended_target") != "",
        f"nomock={sm_nomock}, real={sm_real}",
    )

    # 13. OPT-283-11~20
    au = diag.audit_all_python_undefined_globals([str(pathlib.Path(__file__).resolve().parent.parent / "root/usr/share/ai-link/ailink_diag.py")])
    vr = diag.validate_exported_route_rules_tags([{"rule_set": ["geoip-cn"]}], ["geoip-cn"])
    rc_res = diag.reset_all_node_cooldowns({"n1": {"rate_limited_until": 9999, "quarantine_until": 9999, "consecutive_fail": 3}})
    pc = diag.precheck_restored_config_consistency({"ipv6_proxy": True, "ipv6_leak_guard": False})
    ls = diag.check_external_storage_low_space_warning("/mnt/sda1", free_mb=32.0, warn_threshold_mb=50.0)
    mdns = diag.check_bypass_mdns_multicast_hint({"topology_mode": "bypass"}, mdns_enabled=False)
    check(
        "OPT-283-11~20 全模块符号审计与诊断能力校验",
        au["ok"] is True and vr["ok"] is True and rc_res["cleared_count"] == 1 and pc["ok"] is False and ls["warning"] is True and mdns["hint_active"] is True,
    )

    # 14. OPT-284-01~10
    shd = diag.detect_shunt_rule_shadowing([
        {"id": "G1", "domains": ["*.google.com"]},
        {"id": "G2", "domains": ["dl.google.com"]},
    ])
    ecs = diag.get_dns_ecs_dnssec_status({"dns_ecs_strip": True, "dns_dnssec_enabled": True})
    pol = diag.normalize_pool_cooldown_policy({"fail_threshold": 9, "cooldown_seconds": 10})
    hla = diag.check_homelink_tunnel_downtime_alert({"enabled": True, "downtime_seconds": 120}, threshold_s=60)
    trd = diag.predict_storage_exhaustion_trend([10.0, 20.0, 30.0], free_mb=100.0)
    mtu_rec = diag.recommend_tun_mtu_from_wan_mtu(1492)
    boot = diag.summarize_init_boot_phases({"daemon_init_ms": 100, "rule_gen_ms": 200, "core_ready_ms": 300})
    arp = diag.check_gateway_arp_static_binding("10.10.10.1", [{"ip": "10.10.10.1", "mac": "aa:bb:cc:dd:ee:ff", "permanent": False}])
    check(
        "OPT-284-01~10 分流遮蔽/ECS/冷却/容量/MTU/ARP 诊断能力校验",
        shd["conflict_count"] == 1 and ecs["dnssec_enabled"] is True and pol["fail_threshold"] == 5 and pol["cooldown_seconds"] == 30 and hla["alert"] is True and trd["warning"] is True and mtu_rec["recommended_tun_mtu"] == 1412 and boot["total_boot_ms"] == 600.0 and "nud permanent" in arp["command_hint"],
    )

    # 15. OPT-285-11~20
    dpc = diag.check_dnsmasq_doh_port_conflict(53, 7874)
    dem = diag.demote_l7_failed_node_weight({"l7_consecutive_fail": 1})
    kp = diag.verify_homelink_key_permissions([])
    srs_chk = diag.verify_srs_and_cache_integrity([])
    mss6 = diag.get_ipv6_mss_clamp_recommendation({"ipv6_proxy": True, "tcp_mss_clamp": False}, wan_mtu=1492)
    iss = diag.format_init_status_summary(1234, 20480)
    nat_h = diag.check_bypass_game_nat_guidance({"topology_mode": "bypass"}, nat_type="symmetric")
    check(
        "OPT-285-11~20 端口冲突/L7降权/权限/完整性/IPv6-MSS/NAT 诊断校验",
        dpc["ok"] is True and dem["penalty_ms"] == 500 and kp["ok"] is True and srs_chk["ok"] is True and mss6["recommend_enable"] is True and iss["rss_mb"] == 20.0 and nat_h["hint_active"] is True,
    )

    # 16. OPT-286-01~10
    _st_ext = diag.apply_status_extensions({}, {})
    _iw = diag.interruptible_wait(None, 0.001)
    check(
        "OPT-286-01~10 状态扩展注册表/路由表与可中断等待校验",
        _st_ext.get("status_extension_count", 0) >= 15 and _st_ext.get("declarative_route_count", 0) >= 5 and _iw is False,
    )

    # 17. OPT-287-01~09 ailink_diag primitives
    _sec = diag.summarize_config_pipeline_sections(
        {"log": {}, "dns": {}, "inbounds": [], "outbounds": [], "route": {}, "experimental": {}},
        "table inet ai_link { set x {} chain prerouting_tproxy {} chain output_tproxy {} dport 53 }",
    )
    _th = diag.create_daemon_thread(lambda: None, name="t287")
    _mc = diag.MicroEvalCache(32)
    _mc.put("n1", "h1", 1, {"ms": 42})
    _hit, _val = _mc.get("n1", "h1", 1)
    check(
        "OPT-287-01~09 POST域分发/配置管线/线程工厂与微缓存校验",
        diag.resolve_post_domain("/api/shunt/save") == "shunt"
        and diag.resolve_post_domain("/api/ops/settings") == "ops"
        and len(_sec["singbox_sections_present"]) == 6
        and len(_sec["nft_stages_present"]) == 5
        and _th.daemon is True
        and _hit is True
        and _val["ms"] == 42,
    )

    # 18. OPT-288-01~08 ailink_diag primitives & __all__
    _man = diag.get_daemon_submodule_manifest()
    _rp = diag.resolve_runtime_path("conf", "shunt.json", conf_dir="/tmp/c")
    _tb = diag.get_http_timeout_budget("probe_fast")
    check(
        "OPT-288-01~08 子模块清单/路径收敛/超时预算与__all__导出校验",
        _man.get("module_count", 0) >= 5
        and _rp == "/tmp/c/shunt.json"
        and _tb == 4.0
        and len(getattr(diag, "__all__", [])) >= 20,
    )

    # 19. OPT-289-02~10 ailink_diag primitives & multi-gen migration idempotency
    _cj = diag.compact_json_dumps({"a": 1, "b": "测试"})
    _lo_ok = diag.validate_lock_order(["config_lock", "probe_lock"])
    _lo_bad = diag.validate_lock_order(["ledger_lock", "config_lock"])
    _sb16 = diag.get_singbox_schema_profile_v289("1.16.0")
    _pd = diag.check_ipv6_prefix_drift("240e:1234::/60", "240e:5678::/60")
    _m1 = diag.validate_and_migrate_backup_schema({"proxy_enabled": True})
    _m2 = diag.validate_and_migrate_backup_schema(_m1.get("payload", {}))
    check(
        "OPT-289-02~10 紧凑序列化/锁序校验/1.16+Schema/PD漂移与跨代迁移幂等校验",
        _cj == '{"a":1,"b":"测试"}'
        and _lo_ok is True
        and _lo_bad is False
        and _sb16.get("forward_compat_1_16_plus") is True
        and _pd.get("drifted") is True
        and _m2.get("payload") == _m1.get("payload"),
    )

    # 20. OPT-290-03/04/05/10 chmod_0600, UCI/SSOT alignment, atomic_temp_file, multi-subnet loop guard
    with diag.atomic_temp_file(tempfile.gettempdir(), prefix="v290_", suffix=".json") as (fh, tf_p):
        fh.write('{"ok":true}')
    _mode_ok = (tf_p.stat().st_mode & 0o777) == 0o600
    _chmod_ok = diag.chmod_secret_0600(tf_p)
    _ssot = diag.audit_uci_json_ssot_alignment("option app_version '2.9.0'\noption enabled '1'\n", {"app_version", "enabled"})
    _vlan = diag.check_multi_subnet_loop_guard(["192.168.10.0/24", "192.168.20.0/24"], ["br-lan", "br-iot"], ["32760: from all fwmark 0x162 lookup 162"])
    check(
        "OPT-290-03/04/05/10 0o600权限/UCI对齐/原子临时文件与多VLAN防回环校验",
        _mode_ok and _chmod_ok and _ssot.get("aligned_count") == 2 and _vlan.get("loop_guard_ok") is True,
    )

    # 21. OPT-291-02/05/07/09/10 structured log, subpkgs, zip-bomb guard, hybrid v6, overlay degrade
    import gzip as _gz291
    _log291 = diag.emit_structured_log("info", "v291 ok")
    _sub291 = diag.check_openwrt_python_subpkgs()
    _gzb = _gz291.compress(b"A" * 2048)
    _dec_ok = diag.safe_decompress_limited(_gzb, max_bytes=4096) == b"A" * 2048
    _bomb_blocked = False
    try:
        diag.safe_decompress_limited(_gzb, max_bytes=512)
    except ValueError:
        _bomb_blocked = True
    _hyb = diag.verify_hybrid_ipv6_udp_isolation("tproxy_tcp_tun_udp", True, True)
    _ovl = diag.should_degrade_overlay_log(1.2, 2.0) and (not diag.should_degrade_overlay_log(12.0, 2.0))
    check(
        "OPT-291-02/05/07/09/10 结构化日志/子包依赖/ZipBomb防护/混合v6隔离与overlay降级校验",
        "[INFO] v291 ok" in _log291 and _sub291.get("all_ok") is True and _dec_ok and _bomb_blocked and _hyb.get("isolated_ok") is True and _ovl,
    )

    # 22. OPT-292-01..10 monotonic, bounded executor, env whitelist, safe_unlink, cold-start, QR, ip rule pref
    import time as _t292
    _m0 = _t292.monotonic()
    _el = diag.monotonic_elapsed_s(_m0)
    with diag.create_bounded_executor(2, "t292") as _ex:
        _fut = _ex.submit(lambda: 42).result(timeout=2)
    _env_bad = diag.get_whitelisted_env("UNSAFE_VAR", "def")
    _cs = diag.measure_cold_start_storage_ms([])
    _qr = diag.check_homelink_qr_topology_warning("192.168.1.1")
    _ipr = diag.check_ip_rule_pref_conflict(["50: from all lookup 200", "162: from all fwmark 0x162 lookup 162"], 100)
    check(
        "OPT-292-01..10 单调时钟/有界线程池/环境变量白名单/安全删除/QR提示与pref冲突自检",
        _el >= 0.0 and _fut == 42 and _env_bad == "def" and _cs.get("checked_files") == 0 and _qr.get("lan_only_warning") is True and _ipr.get("has_conflict") is True,
    )

    # 23. OPT-293-01/03/04/05/08 secrets token, socket ctx, cross_fs_atomic_move, stream_file_hashes, domain map
    _tok = diag.secure_token_hex(16)
    _sock_false = diag.probe_tcp_socket_safe("127.0.0.1", 1, timeout=0.05)
    _src293 = pathlib.Path(tempfile.gettempdir()) / f"v293_src_{_tok}.txt"
    _dst293 = pathlib.Path(tempfile.gettempdir()) / f"v293_dst_{_tok}.txt"
    _src293.write_text("v293-stream-test", encoding="utf-8")
    diag.cross_fs_atomic_move(_src293, _dst293)
    _sh293 = diag.stream_file_hashes(_dst293)
    _dst293.unlink(missing_ok=True)
    check(
        "OPT-293-01/03/04/05/08 secrets令牌/Socket释放/跨FS原子移动/流式分块哈希与三域映射校验",
        len(_tok) == 32 and _sock_false is False and _sh293.get("size") == 16 and len(diag.DIAG_DOMAIN_MAP_V293) == 3,
    )

    # 24. OPT-297-06 & OPT-297-10 zero circular import & RA/gateway drift persistence
    import ast as _ast_td
    _dg_src = (ROOT / "root/usr/share/ai-link/ailink_diag.py").read_text(encoding="utf-8")
    _dg_imps = []
    for _n in _ast_td.walk(_ast_td.parse(_dg_src)):
        if isinstance(_n, _ast_td.Import):
            _dg_imps.extend(_a.name for _a in _n.names)
        elif isinstance(_n, _ast_td.ImportFrom) and _n.module:
            _dg_imps.append(_n.module)
    _no_circ = not any("daemon" in _m.lower() for _m in _dg_imps)
    with tempfile.TemporaryDirectory() as _td297:
        _ra_res = diag.record_bypass_ra_and_gateway_drift(
            pathlib.Path(_td297),
            ra_routers=["fe80::1", "fe80::2"],
            expected_gw_v4="10.10.10.77",
            observed_gw_v4="10.10.10.1",
            client_ip="10.10.10.58",
        )
        _ra_file = pathlib.Path(_td297) / diag.RA_GATEWAY_ALERTS_FILENAME
        _ra_ok = (
            _ra_res.get("ra_conflict_active") is True
            and _ra_res.get("gateway_drift_active") is True
            and _ra_res.get("total_alerts") == 2
            and _ra_file.is_file()
        )
    check(
        "OPT-297-06 & OPT-297-10 ailink_diag 零循环依赖与旁路由 IPv6 RA 冲突/网关漂移持久化告警",
        _no_circ and _ra_ok,
    )

    fails = [r for r in results if not r[1]]
    print("=" * 78)
    print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
    print("=" * 78)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
