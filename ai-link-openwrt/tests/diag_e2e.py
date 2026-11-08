# -*- coding: utf-8 -*-
"""
T1: 网络健康医生 + 一键修复 (Network Health Doctor & 1-Click Auto Fix + BUG-006 AI 地区体检) E2E 验证套件。
"""
import importlib.util
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import DAEMON  # noqa: E402

results = []


def check(name: str, cond: bool, detail: str = ""):
    results.append((name, bool(cond), str(detail)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


print("=" * 78)
print(" AI-LINK v2.1.1 · T1 网络健康医生 8 项并发诊断 & 一键修复闭环 E2E")
print("=" * 78)

spec = importlib.util.spec_from_file_location("ailink_daemon_diag", str(DAEMON))
dmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmod)

tmp_work = Path(tempfile.mkdtemp(prefix="ailink-diag-e2e-"))
tmp_conf = tmp_work / "ai-link"
tmp_run = tmp_work / "run"
tmp_conf.mkdir(parents=True, exist_ok=True)
tmp_run.mkdir(parents=True, exist_ok=True)
dmod.CONF_DIR = tmp_conf
dmod.RUN_DIR = tmp_run

dmod.save_nodes_list([
    {
        "tag": "US-BGP-01",
        "name": "US-BGP-01",
        "type": "vless",
        "server": "198.51.100.10",
        "server_port": 443,
        "uuid": "11111111-2222-3333-4444-555555555555",
        "probe_state": "ok",
        "delay_ms": 42,
        "in_kernel": True,
    }
], tmp_conf)

t0 = time.time()
rep = dmod.run_network_health_doctor(
    {"mock_env": {"client_dns_queries_10m": 42, "aaaa_leaked_count": 0, "client_public_ipv6": "", "pmtu": 1500, "lan_mtu": 1500}},
    tmp_conf,
)
elapsed = time.time() - t0
checks_by_id = {c["id"]: c for c in rep.get("checks", [])}
expected_ids = {
    "client_dns",
    "aaaa_suppress",
    "ipv6_bypass",
    "homelink_ddns",
    "homelink_port",
    "upstream_health",
    "mtu_pmtu",
    "essential_apps",
}

check("T1-1: 并发返回完整 8 项诊断结果且顶层含 status/score", set(checks_by_id.keys()) == expected_ids and rep.get("status") == "pass" and rep.get("score") == 100, f"status={rep.get('status')} score={rep.get('score')}")
check("T1-2: 8 项并发体检总耗时 ≤ 10s", elapsed <= 10.0 and rep.get("duration_ms", 99999) <= 10000, f"elapsed={elapsed:.3f}s ({rep.get('duration_ms')}ms)")

rep_f1 = dmod.run_network_health_doctor(
    {"mock_env": {"client_dns_queries_10m": 0, "lan_ip": "10.10.10.7"}},
    tmp_conf,
)
c_f1 = {c["id"]: c for c in rep_f1["checks"]}["client_dns"]
check("T1-Fault1: 模拟客户端 DNS 绕过被 #1 client_dns 准确检出", c_f1["status"] in ("warn", "fail") and c_f1["fixable"] is True)

rep_f2 = dmod.run_network_health_doctor(
    {"mock_env": {"aaaa_leaked_count": 8, "client_public_ipv6": "240e:3b0:1234::88", "ipv6_proxy": False}},
    tmp_conf,
)
c_f2_aaaa = {c["id"]: c for c in rep_f2["checks"]}["aaaa_suppress"]
c_f2_v6 = {c["id"]: c for c in rep_f2["checks"]}["ipv6_bypass"]
check("T1-Fault2: 模拟 IPv6 绕过与 AAAA 泄漏被 #2/#3 准确检出", c_f2_aaaa["status"] == "fail" and c_f2_v6["status"] == "warn")

fix_v6 = dmod.apply_network_health_fix({"action": "fix_all", "recheck": True}, tmp_conf)
rep_after_v6 = dmod.run_network_health_doctor({"mock_env": {"client_public_ipv6": "240e:3b0:1234::88"}}, tmp_conf)
c_v6_after = {c["id"]: c for c in rep_after_v6["checks"]}["ipv6_bypass"]
check("T1-Fix-IPv6闭环: 执行 fix_all 后 ipv6_leak_guard 持久化落盘且 #3 ipv6_bypass 恢复为 pass",
      dmod.get_ops_settings(tmp_conf).get("ipv6_leak_guard") is True and c_v6_after["status"] == "pass",
      f"ipv6_leak_guard={dmod.get_ops_settings(tmp_conf).get('ipv6_leak_guard')}, status={c_v6_after['status']}")

rep_f3 = dmod.run_network_health_doctor(
    {"mock_env": {"ddns_override": {"domain": "luyou.nolo.rest", "rcode": "NXDOMAIN", "authoritative_ns": "launch1.spaceship.net", "ddns_provider": "Cloudflare"}}},
    tmp_conf,
)
c_f3 = {c["id"]: c for c in rep_f3["checks"]}["homelink_ddns"]
check("T1-Fault3: 模拟回家 DDNS NXDOMAIN 权威 NS 错位被 #4 homelink_ddns 准确检出", c_f3["status"] == "fail" and "launch1.spaceship.net" in c_f3["summary"])

fcfg = dmod.load_dns_filter_config(tmp_conf)
fcfg["enabled"] = True
fcfg["essential_app_protect"] = False
fcfg["custom_blocked"] = ["clientservices.googleapis.com"]
dmod.save_dns_filter_config(fcfg, tmp_conf)
dmod._BLOCKED_DOMAINS_MEMO.clear()
rep_f4 = dmod.run_network_health_doctor({}, tmp_conf)
c_f4 = {c["id"]: c for c in rep_f4["checks"]}["essential_apps"]
check("T1-Fault4: 模拟关闭关键应用防误杀保护且拦截 Play 域名被 #8 essential_apps 准确检出", c_f4["status"] == "fail" and c_f4["fix_action"] == "enable_essential_app_protect")

fix_res = dmod.apply_network_health_fix({"fix_action": "enable_essential_app_protect", "recheck": True}, tmp_conf)
c_f4_after = {c["id"]: c for c in fix_res.get("recheck", {}).get("checks", [])}.get("essential_apps", {})
check("T1-Fix: 执行一键修复 enable_essential_app_protect 后自动复检恢复为 pass", fix_res.get("ok") is True and c_f4_after.get("status") == "pass")

rep_f5 = dmod.run_network_health_doctor({"mock_env": {"ai_node_google_region": "HK"}}, tmp_conf)
c_f5 = {c["id"]: c for c in rep_f5["checks"]}["essential_apps"]
check("T1-BUG006: AI 出口节点 Google 地区为 HK 时体检准确报出「Gemini 不支持；建议切换到 US/JP/SG 节点」",
      c_f5["status"] == "fail" and "Google 地区为 HK" in c_f5["summary"] and "US/JP/SG" in c_f5["summary"],
      c_f5["summary"])

false_positives = 0
for _ in range(10):
    r_ok = dmod.run_network_health_doctor(
        {"mock_env": {"client_dns_queries_10m": 25, "aaaa_leaked_count": 0, "client_public_ipv6": "", "pmtu": 1500, "lan_mtu": 1500}},
        tmp_conf,
    )
    if r_ok.get("summary", {}).get("fail", 0) > 0 or r_ok.get("summary", {}).get("warn", 0) > 0:
        false_positives += 1

check("T1-Stability: 正常环境连续运行 10 次体检零误报 (0 fail / 0 warn)", false_positives == 0, f"false_positives={false_positives}/10")

print("\n" + "=" * 78)
fails = [r for r in results if not r[1]]
print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
print("=" * 78)
sys.exit(1 if fails else 0)
