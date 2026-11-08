# -*- coding: utf-8 -*-
"""
BUG-006 + BUG-007 + 自动节点池 v2 (DESIGN-auto-node-pool-v2.md) 端到端全量验收套件。
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
print(" AI-LINK v2.1.1 · BUG-006 + BUG-007 + 自动节点池 v2 (DESIGN-v2) E2E")
print("=" * 78)

spec = importlib.util.spec_from_file_location("ailink_daemon_apv2", str(DAEMON))
dmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmod)

tmp_work = Path(tempfile.mkdtemp(prefix="ailink-apv2-e2e-"))
tmp_conf = tmp_work / "ai-link"
tmp_run = tmp_work / "run"
tmp_conf.mkdir(parents=True, exist_ok=True)
tmp_run.mkdir(parents=True, exist_ok=True)
dmod.CONF_DIR = tmp_conf
dmod.RUN_DIR = tmp_run

nodes_seed = [
    {
        "tag": "VIP1-HY09-日本",
        "name": "VIP1-HY09-日本",
        "type": "hysteria2",
        "server": "160.16.104.239",
        "server_port": 443,
        "password": "secret_hy09_password",
        "sni": "dingpriest.warcrafthy9.diclaecoleck.com",
        "_sub_id": "sub_main",
    },
    {
        "tag": "JP-Active-01",
        "name": "JP-Active-01",
        "type": "vless",
        "server": "203.0.113.50",
        "server_port": 443,
        "uuid": "22222222-3333-4444-5555-666666666666",
        "sni": "www.apple.com",
        "_sub_id": "sub_main",
    },
    {
        "tag": "US-07",
        "name": "US-07",
        "type": "vless",
        "server": "198.51.100.7",
        "server_port": 443,
        "uuid": "77777777-8888-9999-aaaa-bbbbbbbbbbbb",
        "sni": "www.microsoft.com",
        "_sub_id": "sub_main",
    },
]
dmod.save_nodes_list(nodes_seed, tmp_conf)

dmod.url_ping_single_node("VIP1-HY09-日本", conf_dir=tmp_conf, mock_result={"ok": True, "delay_ms": 65, "status": 204})
dmod.url_ping_single_node("JP-Active-01", conf_dir=tmp_conf, mock_result={"ok": True, "delay_ms": 95, "status": 204})
dmod.url_ping_single_node("US-07", conf_dir=tmp_conf, mock_result={"ok": True, "delay_ms": 138, "status": 204})

res_hy09 = dmod.probe_node_service_l7(
    "VIP1-HY09-日本",
    "gemini",
    conf_dir=tmp_conf,
    mock_http={"status": 301, "headers": {"Location": "https://www.google.com.hk/?gws_rd=cr"}},
)
res_jp01 = dmod.probe_node_service_l7(
    "JP-Active-01",
    "gemini",
    conf_dir=tmp_conf,
    mock_http={"status": 302, "headers": {"Location": "https://www.google.co.jp/"}},
)
res_us07 = dmod.probe_node_service_l7(
    "US-07",
    "gemini",
    conf_dir=tmp_conf,
    mock_http={"status": 200, "body": "Google US"},
)

check(
    "BUG-006-1: 标日节点 VIP1-HY09-日本 经 Google 301 (.com.hk) 准确判定为 HK 且 Gemini 不可用",
    res_hy09["ok"] is False and res_hy09["google_region"] == "HK" and res_hy09["region_blocked"] is True,
    f"ok={res_hy09['ok']} google_region={res_hy09['google_region']} reason={res_hy09['reason']}",
)

nodes_api = dmod.build_nodes_api_response(tmp_conf, include_full=True)
hy09_node = next((n for n in nodes_api["nodes"] if n["tag"] == "VIP1-HY09-日本"), {})
check(
    "BUG-006-2: /api/nodes 暴露 google_region='HK' 与完整文案「Google 地区：HK（不支持 Gemini）」",
    hy09_node.get("google_region") == "HK" and hy09_node.get("google_region_label") == "Google 地区：HK（不支持 Gemini）",
    f"label={hy09_node.get('google_region_label')}",
)

an_cfg = dmod.load_auto_nodes_config(tmp_conf)
an_cfg["auto_nodes"] = [
    {
        "id": "auto_ai",
        "tag": "Auto_AI",
        "name": "AI 专线自动池",
        "mode": "full",
        "service_check_enabled": True,
        "service_checks": ["gemini"],
        "service_logic": "all",
        "smart_switch_enabled": True,
        "filters": {"enabled": True, "region_any": ["US", "JP", "SG"], "require_services": ["gemini"], "exclude_quarantine": True},
        "groups": [
            {"index": 1, "name": "主力组 G1", "node_tags": ["VIP1-HY09-日本", "JP-Active-01", "US-07"]}
        ],
    }
]
dmod.save_auto_nodes_config(an_cfg, tmp_conf)
dmod.evaluate_all_auto_nodes(tmp_conf, target_id="auto_ai", force_service_probe=False)
an_after = dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"][0]

check(
    "BUG-006-3: AI 自动池选点自动排除 65ms 的 Google:HK 节点，选中支持 Gemini 的 JP-Active-01",
    an_after.get("current_node") == "JP-Active-01" and an_after.get("current_node") != "VIP1-HY09-日本",
    f"selected={an_after.get('current_node')}",
)

an_cfg_rem = dmod.load_auto_nodes_config(tmp_conf)
an_cfg_rem["auto_nodes"][0]["groups"][0]["node_tags"] = ["VIP1-HY09-日本", "US-07"]
an_cfg_rem["auto_nodes"][0]["groups"][0]["node_ids"] = []
an_cfg_rem["auto_nodes"][0]["current_node"] = ""
dmod.save_auto_nodes_config(an_cfg_rem, tmp_conf)
dmod.evaluate_all_auto_nodes(tmp_conf, target_id="auto_ai", force_service_probe=False)
an_after_rem = dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"][0]
g1_tags_after_rem = an_after_rem["groups"][0]["node_tags"]

check(
    "BUG-007: 移除池内正在使用的当前出口节点 (JP-Active-01) 后彻底从池中消失，且自动切换至下一合格节点 US-07",
    "JP-Active-01" not in g1_tags_after_rem and an_after_rem.get("current_node") == "US-07",
    f"g1_tags={g1_tags_after_rem} new_current={an_after_rem.get('current_node')}",
)

an_cfg_sticky = dmod.load_auto_nodes_config(tmp_conf)
an_cfg_sticky["auto_nodes"][0]["groups"][0]["node_tags"] = ["JP-Active-01", "US-07"]
an_cfg_sticky["auto_nodes"][0]["current_node"] = "US-07"
an_cfg_sticky["auto_nodes"][0]["last_smart_switch_ts"] = int(time.time())
dmod.save_auto_nodes_config(an_cfg_sticky, tmp_conf)

unnecessary_switches = 0
for i in range(10):
    dmod.url_ping_single_node("JP-Active-01", conf_dir=tmp_conf, mock_result={"ok": True, "delay_ms": 118 + (i % 3) * 4, "status": 204})
    dmod.url_ping_single_node("US-07", conf_dir=tmp_conf, mock_result={"ok": True, "delay_ms": 135 - (i % 3) * 3, "status": 204})
    ev_an = dmod.evaluate_single_auto_node(dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"][0], conf_dir=tmp_conf)
    if ev_an.get("current_node") != "US-07":
        unnecessary_switches += 1

check(
    "AutoPool-v2 (粘性防抖): 10 分钟粘性期内小幅延迟波动下非必要切换次数 = 0 (≤ 2 次)",
    unnecessary_switches == 0,
    f"unnecessary_switches={unnecessary_switches}",
)

for _ in range(3):
    dmod.url_ping_single_node("US-07", conf_dir=tmp_conf, mock_result={"ok": False, "delay_ms": -1, "status": 502, "error": "TIMEOUT"})
dmod.evaluate_all_auto_nodes(tmp_conf, target_id="auto_ai", force_service_probe=False)
an_after_q = dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"][0]
store_q = dmod.load_node_probe_store(tmp_conf)
us07_nid = next(n["node_id"] for n in dmod.load_saved_nodes(tmp_conf) if n["tag"] == "US-07")
check(
    "AutoPool-v2 (3败降级与10分钟隔离区): US-07 连续 3 次失败后进入 quarantine 隔离区并自动切换至 JP-Active-01",
    int(store_q[us07_nid].get("quarantine_until") or 0) > int(time.time()) and an_after_q.get("current_node") == "JP-Active-01",
    f"quarantine_until={store_q[us07_nid].get('quarantine_until')} current={an_after_q.get('current_node')}",
)

res_429 = dmod.probe_node_service_l7("JP-Active-01", "chatgpt", conf_dir=tmp_conf, mock_http={"status": 429, "body": "Rate limit reached"})
store_429 = dmod.load_node_probe_store(tmp_conf)
jp01_nid = next(n["node_id"] for n in dmod.load_saved_nodes(tmp_conf) if n["tag"] == "JP-Active-01")
check(
    "AutoPool-v2 (L3 风控冷却): HTTP 429 识别为 rate_limited 并设置 60 分钟冷却，节点本身不判死 (state=='ok')",
    res_429.get("rate_limited") is True and int(store_429[jp01_nid].get("cooldown_until") or 0) > int(time.time()) and store_429[jp01_nid].get("state") == "ok",
)

store_429[jp01_nid]["cooldown_until"] = 0
dmod.save_node_probe_store(store_429, tmp_conf)

incoming_sub_nodes = [
    {
        "tag": "JP-Active-01 [IEPL新名]",
        "name": "JP-Active-01 [IEPL新名]",
        "type": "vless",
        "server": "203.0.113.50",
        "server_port": 443,
        "uuid": "22222222-3333-4444-5555-666666666666",
        "sni": "www.apple.com",
        "_sub_id": "sub_main",
    },
    {
        "tag": "SG-New-08",
        "name": "SG-New-08",
        "type": "vless",
        "server": "198.51.100.88",
        "server_port": 443,
        "uuid": "99999999-aaaa-bbbb-cccc-dddddddddddd",
        "sni": "www.cloudflare.com",
        "_sub_id": "sub_main",
    },
]
preview = dmod.preview_subscription_sync_impact("sub_main", incoming_sub_nodes, conf_dir=tmp_conf)
check(
    "AutoPool-v2 (订阅更新前影响预览): 准确计算新增(1)、移除(2)、改名保留(1) 及受影响自动池",
    preview.get("added_count") == 1 and preview.get("removed_count") == 2 and preview.get("renamed_count") == 1 and len(preview.get("affected_pools") or []) == 1,
    preview.get("summary_text", ""),
)

dmod.merge_nodes("sub_main", incoming_sub_nodes, replace_sub=True, conf_dir=tmp_conf)
an_after_sync = dmod.load_auto_nodes_config(tmp_conf)["auto_nodes"][0]
g1_tags_sync = an_after_sync["groups"][0]["node_tags"]
missing_tags = [m["tag"] for m in (an_after_sync.get("missing_members") or [])]

check(
    "AutoPool-v2 (node_key 无损改名迁移 + 7天 missing 占位 + filters 自动补位): 改名节点平滑更新 tag，消失节点进入 missing_members，新节点 SG-New-08 自动补位",
    "JP-Active-01 [IEPL新名]" in g1_tags_sync
    and "SG-New-08" in g1_tags_sync
    and "US-07" in missing_tags,
    f"g1_tags={g1_tags_sync} missing={missing_tags}",
)

# ---------------------------------------------------------------------------
# v2.2.0 New Requirements E2E Verification:
# 1. Unlimited Kernel Outbounds (get_max_outbounds_limit == 0, all enabled nodes in_kernel)
# 2. Two-State Node Management (state strictly in {"ok", "dead"})
# 3. Goal-Driven Auto Node Pool Screening (ping_only vs service_check, fastest-10 by URL Ping, partial admission if <10, auto_maintain self-healing)
# 4. Manual/Custom Nodes Category Summary (custom_nodes_summary in build_nodes_api_response)
# 5. Subscription Sync Timestamp & Failure Suffix (YYYY-MM-DD HH:MM and YYYY-MM-DD HH:MM 失败)
# ---------------------------------------------------------------------------
check(
    "v2.2.0 (取消节点入核数量限制): get_max_outbounds_limit 返回 0，260 个启用节点 100% 全部进入内核 outbounds",
    dmod.get_max_outbounds_limit(tmp_conf) == 0
    and len(dmod.select_top_n_outbounds([{"tag": f"N-{i}", "type": "vless", "server": "1.1.1.1", "server_port": 443} for i in range(260)], conf_dir=tmp_conf)) == 260,
)

# Add a custom manual node and test 12 nodes with varying latencies
extra_12 = []
for idx_e in range(1, 13):
    extra_12.append({
        "tag": f"SG-Fast-{idx_e:02d}",
        "name": f"SG-Fast-{idx_e:02d}",
        "type": "vless",
        "server": f"198.51.100.{100 + idx_e}",
        "server_port": 443,
        "uuid": f"11111111-2222-3333-4444-{idx_e:012d}",
        "_manual": (idx_e <= 3),
        "_sub_id": "" if idx_e <= 3 else "sub_main",
    })
cur_saved = dmod.load_saved_nodes(tmp_conf) + extra_12
dmod.save_nodes_list(cur_saved, tmp_conf)
store_now = dmod.load_node_probe_store(tmp_conf)
now_v22 = int(time.time())
for idx_e in range(1, 13):
    nd_e = next(x for x in dmod.load_saved_nodes(tmp_conf) if x["tag"] == f"SG-Fast-{idx_e:02d}")
    nid_e = nd_e["node_id"]
    if idx_e <= 11:
        store_now[nid_e] = {
            "state": "ok",
            "delay_ms": 50 + idx_e * 10,
            "probe_ts": now_v22,
            "svc": {"chatgpt": {"ok": (idx_e % 2 == 1), "delay_ms": 60 + idx_e * 10, "status_code": 200 if (idx_e % 2 == 1) else 403}},
        }
    else:
        store_now[nid_e] = {"state": "dead", "delay_ms": -1, "probe_ts": now_v22}
dmod.save_node_probe_store(store_now, tmp_conf)
dmod._sync_global_url_ping_state(tmp_conf, trigger_auto_eval=False)

nodes_api_v22 = dmod.build_nodes_api_response(tmp_conf)
all_states_v22 = {n["state"] for n in nodes_api_v22["nodes"]}
check(
    "v2.2.0 (节点管理三态模型 P2-1): 所有节点状态严格区分 ok(可用)、dead(不可达)、untested(未测速)，未测速不误判为 dead，且包含 custom_nodes_summary",
    all_states_v22 <= {"ok", "dead", "untested"} and "untested" in all_states_v22
    and nodes_api_v22.get("custom_nodes_summary", {}).get("count", 0) >= 3,
    f"states={all_states_v22}, custom_count={nodes_api_v22.get('custom_nodes_summary', {}).get('count')}",
)

# Mode 1: ping_only screening across SG -> should pick top 10 fastest by delay_ms ascending!
screen_ping = dmod.auto_screen_and_fill_pool({
    "pool_mode": "ping_only",
    "scope_source": "ALL",
    "scope_countries": ["SG"],
    "target_size": 10,
}, conf_dir=tmp_conf, run_live_probe=False)
g1_ping = screen_ping.get("admitted_g1") or []
reserve_ping = screen_ping.get("reserve_candidates") or []
check(
    "v2.4.1 (目标驱动单组节点池 Mode 1 仅检测连通性): 超过 10 个可用时按 URL Ping 最快优先选满 10 个入单组池，其余保留为 reserve_candidates 零 G2 双组生成",
    len(g1_ping) == 10 and g1_ping[0] == "SG-Fast-01" and g1_ping[1] == "SG-Fast-02" and len(reserve_ping) >= 1 and "admitted_g2" not in screen_ping,
    f"g1[:3]={g1_ping[:3]}, len(g1)={len(g1_ping)}, len(reserve)={len(reserve_ping)}",
)

# Mode 2: service_check screening for Custom nodes only (<10 available) -> admits as many as qualify
screen_svc_custom = dmod.auto_screen_and_fill_pool({
    "pool_mode": "service_check",
    "service_checks": ["chatgpt"],
    "scope_source": "custom",
    "scope_countries": ["SG"],
    "target_size": 10,
}, conf_dir=tmp_conf, run_live_probe=False)
g1_svc_cust = screen_svc_custom.get("admitted_g1") or []
check(
    "v2.2.0 (目标驱动节点池 Mode 2 加服务可用性检测 + 手动节点范围 + 不足10个有几个加几个): 仅选出通过 ChatGPT 检测的手动节点 (SG-Fast-01, SG-Fast-03)",
    g1_svc_cust == ["SG-Fast-01", "SG-Fast-03"],
    f"admitted_g1={g1_svc_cust}",
)

# Continuous Self-Healing & Auto-Replenishment (maintain_auto_node_pool_health)
pool_maint = {
    "id": "auto_goal_test",
    "name": "目标驱动自愈池",
    "pool_mode": "ping_only",
    "scope_source": "ALL",
    "scope_countries": ["SG"],
    "target_size": 10,
    "auto_maintain": True,
    "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["SG-Fast-01", "SG-Fast-12"]}],
}
changed_m = dmod.maintain_auto_node_pool_health(pool_maint, conf_dir=tmp_conf)
g1_after_maint = pool_maint["groups"][0]["node_tags"]
check(
    "v2.2.0 (节点池失效自动剔除与持续补满10个): 自动剔除不可达节点 SG-Fast-12 并按最快 Ping 补齐至 10 个健康节点",
    changed_m is True and "SG-Fast-12" not in g1_after_maint and len(g1_after_maint) == 10 and g1_after_maint[0] == "SG-Fast-01",
    f"g1_after_maint={g1_after_maint}",
)


# =====================================================================
# BUG-006 真网 HTTP 302 Location 头部解析 (_probe_real_node_http_region)
# =====================================================================
import os, socket, threading
srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv_sock.bind(("127.0.0.1", 0))
mock_port = srv_sock.getsockname()[1]
srv_sock.listen(5)
def _mock_proxy_server():
    for _ in range(2):
        try:
            conn, _ = srv_sock.accept()
            req_bytes = conn.recv(4096)
            if b"cdn-cgi/trace" in req_bytes:
                body = b"fl=21f\nh=www.google.com\nip=203.0.113.8\nloc=HK\n"
                resp = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
            else:
                resp = b"HTTP/1.1 302 Found\r\nLocation: https://www.google.com.hk/?gws_rd=cr\r\nContent-Length: 0\r\n\r\n"
            conn.sendall(resp)
            conn.close()
        except Exception:
            pass
    srv_sock.close()
t_srv = threading.Thread(target=_mock_proxy_server, daemon=True)
t_srv.start()
os.environ["AI_LINK_GOOGLE_PROBE_URL"] = f"http://127.0.0.1:{mock_port}/"
try:
    real_probe = dmod._probe_real_node_http_region("VIP1-HY09-日本", timeout_sec=3.0)
finally:
    os.environ.pop("AI_LINK_GOOGLE_PROBE_URL", None)
check(
    "BUG-006 (真网 Google 302 Location 落地探测): 真实 socket 捕获 Location: https://www.google.com.hk 准确识别 google_region=HK 且附带 location_raw 与 ts",
    real_probe.get("google_region") == "HK" and "google.com.hk" in str(real_probe.get("location_raw", "")) and real_probe.get("ts", 0) > 0,
    f"region={real_probe.get('google_region')} loc={real_probe.get('location_raw')} evidence={real_probe.get('evidence')}",
)

# =====================================================================
# BUG-008: 手动锁定节点不可达时的漂移告警 (manual_drifted) 与严格锁定 (strict_lock)
# =====================================================================
sh_cfg = dmod.load_shunt_config(tmp_conf)
target_gid = sh_cfg["groups"][0]["id"]
sh_cfg["groups"][0]["enabled"] = True
sh_cfg["groups"][0]["shunt_mode"] = "manual"
sh_cfg["groups"][0]["manual_node"] = "Dead-Manual-JP-99"
sh_cfg["groups"][0]["strict_lock"] = False
dmod.save_shunt_config(sh_cfg, tmp_conf)
dmod._SHUNT_API_MEMO.clear()
shunt_view = dmod.build_shunt_api_response(tmp_conf)
ai_view = next((g for g in shunt_view.get("groups", []) if g.get("id") == target_gid), {})
check(
    "BUG-008-1 / P1-05 (手动固定模式不自动漂移): 当分流组设为 manual 且指定节点不可达时保持 Dead-Manual-JP-99 固定不漂移 (manual_drifted=False)",
    bool(ai_view.get("manual_drifted")) is False and ai_view.get("resolved_node") == "Dead-Manual-JP-99" and bool(ai_view.get("strict_locked_dead")) is True,
    f"resolved={ai_view.get('resolved_node')} drifted={ai_view.get('manual_drifted')} warning={ai_view.get('drift_warning')}",
)
sh_cfg["groups"][0]["strict_lock"] = True
dmod.save_shunt_config(sh_cfg, tmp_conf)
dmod._SHUNT_API_MEMO.clear()
shunt_view_strict = dmod.build_shunt_api_response(tmp_conf)
ai_view_strict = next((g for g in shunt_view_strict.get("groups", []) if g.get("id") == target_gid), {})
check(
    "BUG-008-2 (严格锁定宁可失败不漂移): 开启 strict_lock=True 后 resolved_node 严格保持手动指定节点不漂移",
    bool(ai_view_strict.get("strict_lock")) is True and ai_view_strict.get("resolved_node") == "Dead-Manual-JP-99" and not ai_view_strict.get("manual_drifted"),
    f"strict_lock={ai_view_strict.get('strict_lock')} resolved={ai_view_strict.get('resolved_node')}",
)

# =====================================================================
# DESIGN-auto-node-pool-v2 (A-1 ~ A-4): 非 null 结构化字段完整性校验
# =====================================================================
dmod._AUTO_NODES_API_MEMO.clear()
an_payload = dmod.build_auto_nodes_api_response(tmp_conf)
p0 = (an_payload.get("auto_nodes") or [{}])[0]
check(
    "AutoPool-v2 (A-1~A-4 非 null 字段校验): current_google_region / selection_explain / filters / missing_members 均非 null",
    p0.get("current_google_region") is not None
    and bool(p0.get("selection_explain"))
    and isinstance(p0.get("filters"), dict)
    and isinstance(p0.get("missing_members"), list),
    f"region={p0.get('current_google_region')} explain={str(p0.get('selection_explain'))[:60]}",
)


# =====================================================================
# v2.3.5 Clean-Slate Auto Node Pool: Multi-Sub + Replenish Threshold + Non-Shunt Manual Pinning
# =====================================================================
res_multi_src = dmod.auto_screen_and_fill_pool({
    "pool_mode": "service_check",
    "service_check_enabled": True,
    "service_checks": ["chatgpt"],
    "scope_sources": ["custom", "sub_main"],
    "scope_countries": ["SG", "JP"],
    "target_size": 2,
    "replenish_threshold": 1,
    "run_live_probe": False
}, conf_dir=tmp_conf, run_live_probe=False, task_id="task_v235_demo")

st_task = dmod._AUTO_SCREEN_TASKS.get("task_v235_demo", {})
check(
    "v2.3.5 (多选订阅源 + 多选国家 + 1~10数量 + 实时进度条状态): 支持同时勾选 custom+sub_main 与多国家，返回 percent=100 且选入 target_size=2 个节点",
    res_multi_src.get("target_size") == 2
    and res_multi_src.get("replenish_threshold") == 1
    and len(res_multi_src.get("admitted_g1", [])) == 2
    and st_task.get("percent") == 100
    and st_task.get("done") is True,
    f"admitted={res_multi_src.get('admitted_g1')} pct={st_task.get('percent')}",
)

pool_th_test = {
    "id": "auto_thresh_test",
    "name": "阈值复选测试池",
    "pool_mode": "ping_only",
    "service_check_enabled": False,
    "scope_sources": ["ALL"],
    "scope_countries": ["SG"],
    "target_size": 4,
    "replenish_threshold": 2,
    "auto_maintain": True,
    "groups": [{"index": 1, "name": "节点池成员", "node_tags": ["SG-Fast-01", "SG-Fast-02", "SG-Fast-03", "SG-Fast-04"]}],
}
store_th = dmod.load_node_probe_store(tmp_conf)
for _k, _v in list(store_th.items()):
    if isinstance(_v, dict) and _v.get("tag") == "SG-Fast-04" or _k == "SG-Fast-04":
        _v["state"] = "dead"
        _v["delay_ms"] = -1
if "SG-Fast-04" in store_th:
    store_th["SG-Fast-04"]["state"] = "dead"
    store_th["SG-Fast-04"]["delay_ms"] = -1
for _n in dmod.load_saved_nodes(tmp_conf):
    if _n.get("tag") == "SG-Fast-04":
        _nid = _n.get("node_id") or dmod.compute_node_id(_n)
        if _nid in store_th:
            store_th[_nid]["state"] = "dead"
            store_th[_nid]["delay_ms"] = -1
dmod.save_node_probe_store(store_th, tmp_conf)
dmod.maintain_auto_node_pool_health(pool_th_test, conf_dir=tmp_conf)
tags_at_3 = list(pool_th_test["groups"][0]["node_tags"])

for _n in dmod.load_saved_nodes(tmp_conf):
    if _n.get("tag") in ("SG-Fast-02", "SG-Fast-03"):
        _nid = _n.get("node_id") or dmod.compute_node_id(_n)
        for _k in (_nid, _n.get("tag")):
            if _k in store_th:
                store_th[_k]["state"] = "dead"
                store_th[_k]["delay_ms"] = -1
dmod.save_node_probe_store(store_th, tmp_conf)
dmod.maintain_auto_node_pool_health(pool_th_test, conf_dir=tmp_conf)
tags_after_replenish = list(pool_th_test["groups"][0]["node_tags"])

check(
    "v2.3.5 (低健康度自动复选阈值 replenish_threshold): 健康数(3)>=阈值(2)时不触发外部重选，健康数(1)<阈值(2)时自动触发外部复选补满至 4 个节点",
    len(tags_at_3) == 3 and len(tags_after_replenish) == 4 and "SG-Fast-05" in tags_after_replenish,
    f"at_3={tags_at_3} after_replenish={tags_after_replenish}",
)

sh_cfg_ns = dmod.load_shunt_config(tmp_conf)
sh_cfg_ns["routing_mode"] = "gfw_list"
sh_cfg_ns["global_mode"] = "manual"
sh_cfg_ns["global_country"] = "JP"
sh_cfg_ns["global_manual_node"] = "Dead-Manual-JP-99"
dmod.save_shunt_config(sh_cfg_ns, tmp_conf)
dmod._SHUNT_API_MEMO.clear()
sh_resp_ns = dmod.build_shunt_api_response(tmp_conf)
check(
    "v2.3.5 (非分流模式手动单一节点零自动切换): gfw_list/cn_whitelist/global_proxy 手动指定节点不可达时严格保持原节点不自动切换",
    sh_resp_ns.get("global_mode") == "manual" and sh_resp_ns.get("global_resolved_node") == "Dead-Manual-JP-99",
    f"global_resolved={sh_resp_ns.get('global_resolved_node')}",
)

print("\n" + "=" * 78)
fails = [r for r in results if not r[1]]
print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
print("=" * 78)
sys.exit(1 if fails else 0)
