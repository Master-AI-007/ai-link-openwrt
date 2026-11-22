#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OPT-278-05: Standalone fast unit tests for ailink_diag.py (zero daemon import)."""
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

    fails = [r for r in results if not r[1]]
    print("=" * 78)
    print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
    print("=" * 78)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
