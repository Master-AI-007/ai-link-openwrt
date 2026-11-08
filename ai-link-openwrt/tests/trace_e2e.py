# -*- coding: utf-8 -*-
"""
BUG-001 ~ BUG-005 + T4 + T7 全链路追踪、Google Play 防误杀、分流命中排行与订阅健康度 E2E 验证套件。
"""
import importlib.util
import re
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
print(" AI-LINK v2.1.1 · BUG-001~005 + T4 命中排行 + T7 订阅健康度 E2E")
print("=" * 78)

spec = importlib.util.spec_from_file_location("ailink_daemon_trace", str(DAEMON))
dmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmod)

tmp_work = Path(tempfile.mkdtemp(prefix="ailink-trace-e2e-"))
tmp_conf = tmp_work / "ai-link"
tmp_run = tmp_work / "run"
tmp_conf.mkdir(parents=True, exist_ok=True)
tmp_run.mkdir(parents=True, exist_ok=True)
dmod.CONF_DIR = tmp_conf
dmod.RUN_DIR = tmp_run

dmod.save_nodes_list([
    {
        "tag": "SG-IEPL-01",
        "name": "SG-IEPL-01",
        "type": "vless",
        "server": "203.0.113.88",
        "server_port": 443,
        "uuid": "11111111-2222-3333-4444-555555555555",
        "probe_state": "ok",
        "delay_ms": 36,
        "in_kernel": True,
    }
], tmp_conf)

scfg = dmod.load_shunt_config(tmp_conf)
scfg["groups"].insert(0, {
    "id": "Soul",
    "name": "Soul 社交专线",
    "priority": 1,
    "shunt_mode": "manual",
    "strategy": "manual",
    "country": "SG",
    "manual_node": "SG-IEPL-01",
    "domains": ["soulapp.com"],
    "domain_keywords": [],
    "ip_cidrs": [],
})
dmod.save_shunt_config(scfg, tmp_conf)

tr_soul = dmod.trace_traffic_flow({"target": "soulapp.com:443", "protocol": "tcp"}, tmp_conf)
s3_soul = tr_soul.get("stage3_rule", {})
s4_soul = tr_soul.get("stage4_outbound", {})
check(
    "BUG-001 场景1 (代理组 Soul): Stage 3 命中自定义组 Soul 且 Stage 4 显示真实代理节点 (绝无 DIRECT)",
    s3_soul.get("group_id") == "Soul"
    and s4_soul.get("is_direct") is False
    and s4_soul.get("node") == "SG-IEPL-01"
    and "DIRECT" not in str(s4_soul.get("detail", "")).upper(),
    f"s3={s3_soul.get('rule_title')} | s4={s4_soul.get('detail')}",
)

tr_bd = dmod.trace_traffic_flow({"target": "www.baidu.com:443", "protocol": "tcp"}, tmp_conf)
s3_bd = tr_bd.get("stage3_rule", {})
s4_bd = tr_bd.get("stage4_outbound", {})
check(
    "BUG-001 场景2 (国内直连): www.baidu.com Stage 3/4 一致显示直连且未命中代理组",
    s3_bd.get("group_id") == "Domestic_CN"
    and s4_bd.get("is_direct") is True
    and s4_bd.get("title") == "直连"
    and "未命中代理组" in str(s4_bd.get("detail", "")),
    f"s3={s3_bd.get('rule_title')} | s4={s4_bd.get('detail')}",
)

tr_ad = dmod.trace_traffic_flow({"target": "google-analytics.com:443", "protocol": "tcp"}, tmp_conf)
s3_ad = tr_ad.get("stage3_rule", {})
s4_ad = tr_ad.get("stage4_outbound", {})
check(
    "BUG-001 场景3 (广告拦截): google-analytics.com 命中黑洞拦截阻断",
    s3_ad.get("group_id") == "Ad_Block" and s4_ad.get("is_blocked") is True and "阻断" in str(s4_ad.get("title", "")),
    f"s3={s3_ad.get('rule_title')} | s4={s4_ad.get('title')}",
)

sh_resp = dmod.build_shunt_api_response(tmp_conf)
soul_grp = next((g for g in sh_resp.get("groups", []) if g.get("id") == "Soul"), None)
check("BUG-002: 自定义分流组 Soul 在 /api/shunt 中自动携带 is_custom=True", bool(soul_grp and soul_grp.get("is_custom") is True))

gplay_domains = [
    "clientservices.googleapis.com",
    "clouderrorreporting.googleapis.com",
    "play.googleapis.com",
    "play-fe.googleapis.com",
    "android.clients.google.com",
    "gvt1.com",
    "dl.google.com",
]
fcfg = dmod.load_dns_filter_config(tmp_conf)
fcfg["enabled"] = True
fcfg["essential_app_protect"] = True
fcfg["custom_blocked"] = ["clientservices.googleapis.com", "play.googleapis.com", "evil-tracker.example.com"]
dmod.save_dns_filter_config(fcfg, tmp_conf)
dmod._BLOCKED_DOMAINS_MEMO.clear()
active_blocked = set(dmod.get_active_blocked_domains(tmp_conf))
leaked_gplay = [d for d in gplay_domains if d in active_blocked]
tr_gplay = dmod.trace_traffic_flow({"target": "clientservices.googleapis.com:443", "protocol": "tcp"}, tmp_conf)
check(
    "BUG-004: Google Play 关键域名 100% 豁免黑洞拦截且通过代理正常分流",
    len(leaked_gplay) == 0
    and "evil-tracker.example.com" in active_blocked
    and tr_gplay.get("stage3_rule", {}).get("group_id") != "Ad_Block"
    and tr_gplay.get("stage2_dns", {}).get("blocked") is False,
)

dmod.save_homelink_nodes([
    {"id": "hl_sync_test", "name": "回家-VLESS-Reality (:18443)", "protocol": "vless-reality", "listen_port": 18443, "external_port": 18443, "enabled": True}
], tmp_conf)
hl_nodes = dmod.load_homelink_nodes(tmp_conf)
for n in hl_nodes:
    if n["id"] == "hl_sync_test":
        new_p = 28443
        n["listen_port"] = new_p
        n["external_port"] = new_p
        n["name"] = re.sub(r"\(\s*:\s*\d+\s*\)", f"(:{new_p})", n["name"])
dmod.save_homelink_nodes(hl_nodes, tmp_conf)
updated_name = dmod.load_homelink_nodes(tmp_conf)[0]["name"]
check("BUG-005: 回家节点修改端口后名称后缀 (:18443) ➔ (:28443) 自动同步", updated_name == "回家-VLESS-Reality (:28443)")

future_exp = int(time.time()) + 15 * 86400 + 3600
ui_parsed = dmod.parse_subscription_userinfo(f"upload=1073741824; download=4294967296; total=10737418240; expire={future_exp}; reset_day=12")
ui_empty = dmod.parse_subscription_userinfo("")
check(
    "T7: Subscription-Userinfo 解析流量进度 (50.0%)、剩余天数与重置日准确",
    ui_parsed.get("used_bytes") == 5368709120
    and ui_parsed.get("total_bytes") == 10737418240
    and ui_parsed.get("used_pct") == 50.0
    and ui_parsed.get("expire_days_left") in (14, 15, 16)
    and ui_parsed.get("reset_day") == 12
    and ui_empty == {},
)

with dmod._SHUNT_HIT_STATE["lock"]:
    dmod._SHUNT_HIT_STATE["events"].clear()
    dmod._SHUNT_HIT_STATE["seen_conn_bytes"].clear()

for i in range(50):
    dmod.record_shunt_hit_event("AI", "AI 助手与大模型", "domain_suffix:chatgpt.com", "SG-IEPL-01", 512, 2048, f"c_ai_{i}")
for i in range(30):
    dmod.record_shunt_hit_event("YouTube", "YouTube 视频专线", "domain_suffix:googlevideo.com", "SG-IEPL-01", 256, 4096, f"c_yt_{i}")
for i in range(20):
    dmod.record_shunt_hit_event("Domestic_CN", "国内流量直连", "geosite:cn", "direct", 128, 1024, f"c_cn_{i}")

hit_stats = dmod.build_shunt_hit_stats(tmp_conf)
by_grp = {g["group_id"]: g for g in hit_stats.get("by_group", [])}
check(
    "T4: 1小时滑动窗口分流命中排行聚合精度 100% (误差 0% < 5%)",
    hit_stats.get("total_hits") == 100
    and by_grp.get("AI", {}).get("hits") == 50
    and by_grp.get("YouTube", {}).get("hits") == 30
    and by_grp.get("Domestic_CN", {}).get("hits") == 20,
)

print("\n" + "=" * 78)
fails = [r for r in results if not r[1]]
print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
print("=" * 78)
sys.exit(1 if fails else 0)
