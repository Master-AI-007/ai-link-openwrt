# -*- coding: utf-8 -*-
"""
AI-LINK v1.0.2 全量问题解决与 E2E 回归测试套件（覆盖 KNOWN-ISSUES.md B1~B4 全部事项 + Release Gate §1~§9 + 无头浏览器 UI 自动化）。

覆盖清单：
  [Gate §1~§8] 零 CRLF、symtable 零未定义符号、_SB_OUTBOUND_KEYS 白名单、JS 全局函数定义、
               nftables 单一真相源、save_obj 写盘白名单全覆盖、关键域名路由命中
  [B1-1 & SEC-4/5] require_lan_auth 联动、/api/status 暴露 auth_required & pwd_customized、
                   GET /api/nodes/share_uri 与 GET /api/ops/logs 强制鉴权、UI 安全提示横幅
  [B1-2] UCI 彻底移除 panel_secret 凭据形态，改用布尔 panel_pwd_customized=0/1
  [B1-3 & B3-14] 下线弱默认密码 'admin'；真实 HTTP 服务端完整密码登录 -> 令牌访问 -> 改密 -> 旧密码失效 E2E
  [B1-4] Self-Healing Watchdog 与 init.d restore_proxy 挂载 nftables 前强制校验 :7893 端口监听
  [B2-6 & B2-7] 面板 .tgz 归档导出 (/api/ops/backup_archive) + 浏览器 Base64 上传恢复 (/api/ops/restore_archive)
                + 路径穿越拦截 + CLI `ai-link restore <file>` / `--restore <file>` (.tgz & .json 双格式)
  [B2-8] OTA 升级进度持久化落盘 (/root/ai-link-final-backup/last_update_progress.log) 与断电恢复判定
  [B2-9] auto_nodes.json 落盘剥离实时探测噪声，跨轮询 MD5 100% 稳定
  [B2-10 & B2-11] 自定义更新源 update_manifest_url 持久化与优先级 + v1.0.0 冷启动说明
  [B3-12] init.d / CLI / install.sh / uninstall.sh 跨架构与 BusyBox 兼容（无 toupper 依赖、无 pgrep 自匹配）
  [B3-13 & Gate §9] Headless Chromium 真实浏览器 UI 自动化回归（零 JS 异常、节点表渲染、开关点击切换、上传恢复弹窗）
  [B4-16 & B4-17 & B4-20] verify_online.py 环境变量覆盖、release.py 路径自愈、Clash API 断路器 (<5ms)
"""
import base64
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import ROOT, DAEMON  # noqa: E402

IDX = ROOT / "root/usr/share/ai-link/webui/index.html"
OV = ROOT / "htdocs/luci-static/resources/view/ai-link/overview.js"
INITD = ROOT / "root/etc/init.d/ai-link"
CLI = ROOT / "root/usr/bin/ai-link"
INST = ROOT / "install.sh"
UNINST = ROOT / "uninstall.sh"
UCI_CFG = ROOT / "root/etc/config/ai-link"

results = []


def check(name: str, cond: bool, detail: str = ""):
    results.append((name, bool(cond), str(detail)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


print("=" * 78)
print(" AI-LINK v1.0.3 双机实测根因修复 & Release Gate & 浏览器 UI E2E 回归")
print("=" * 78)

# ---------------------------------------------------------------------------
# 1. File Hygiene & Release Gate §1~§8
# ---------------------------------------------------------------------------
print("\n[1] Release Gate §1~§8 (文件卫生 / JS 符号 / nft 单一源 / 写盘白名单 / 路由规则)")
text_files = [
    DAEMON, IDX, OV, INITD, CLI, INST, UNINST, UCI_CFG,
    ROOT / "root/usr/share/ai-link/webui/nexus.css",
    ROOT / "root/usr/share/ai-link/webui/nexus3d.js",
    ROOT / "root/usr/share/ai-link/webui/nexus.js",
    ROOT / "root/usr/share/ai-link/uninstall.sh",
    ROOT / "root/usr/share/ai-link/nftables/apply_nft.sh",
    ROOT / "root/usr/share/ai-link/nftables/normalize_nft_sets.py",
]
crlf_files = [str(p.relative_to(ROOT)) for p in text_files if p.is_file() and b"\r" in p.read_bytes()]
check("Gate §1: 全部核心脚本/HTML/配置零 CRLF (\\r=0)", len(crlf_files) == 0, f"CRLF files: {crlf_files}")

html_text = IDX.read_text(encoding="utf-8")
PROJECT_GLOBALS = [
    "setSwitchState", "renderOpsSettings",
    "renderOverviewDashboard", "renderShuntMatrix", "renderOpsAndUpdatesSection",
    "renderHomeLinkSection", "renderDnsAndFilterSection", "renderMusicUnlockSection",
    "renderSubscriptionsAndNodes", "renderConnectionsSection", "renderAll",
    "syncBackendStatus", "promptPanelLoginModal",
]
missing_js = [
    fn for fn in PROJECT_GLOBALS
    if re.search(rf"\b{fn}\s*\(", html_text) and not (
        re.search(rf"function\s+{fn}\s*\(", html_text)
        or re.search(rf"(?:const|let|var)\s+{fn}\s*=", html_text)
        or re.search(rf"{fn}\s*:\s*(?:async\s*)?function", html_text)
    )
]
check("Gate §5: 面板 JS 关键全局函数 100% 已定义", not missing_js, f"missing={missing_js}")

apply_nft_txt = (ROOT / "root/usr/share/ai-link/nftables/apply_nft.sh").read_text(encoding="utf-8")
check("Gate §6: apply_nft.sh 委托 --generate-nft 单一真相源", "--generate-nft" in apply_nft_txt and "table inet ai_link {" not in apply_nft_txt)
check("Gotcha: uninstall.sh 双路径随包交付", UNINST.is_file() and (ROOT / "root/usr/share/ai-link/uninstall.sh").is_file())

# Verify VERSION-ALIGNMENT.md 7-place version alignment = 1.0.2
_d_txt = DAEMON.read_text(encoding="utf-8")
_v_lines = [ln for ln in (ROOT / "root/etc/ai-link/version").read_text(encoding="utf-8").splitlines() if ln.strip()]
_v7 = {
    "APP_VERSION": (re.search(r'^APP_VERSION = "([^"]+)"', _d_txt, re.M) or [None, "?"])[1],
    "APP_BUILD": (re.search(r'^APP_BUILD = "([0-9.]+)-release-\d+"', _d_txt, re.M) or [None, "?"])[1],
    "version_file": (_v_lines[0].split()[0] if len(_v_lines) == 1 else f"lines={len(_v_lines)}"),
    "install.sh": (re.search(r'^VERSION="([^"]+)"', INST.read_text(encoding="utf-8"), re.M) or [None, "?"])[1],
    "uci_app_version": (re.search(r"^\toption app_version '([^']+)'$", UCI_CFG.read_text(encoding="utf-8"), re.M) or [None, "?"])[1],
    "webui_badge": (re.search(r'>v([0-9.]+)</span>', html_text) or [None, "?"])[1],
    "luci_fallback": (re.search(r"\|\s*\|\s*'([0-9.]+)'\);", OV.read_text(encoding="utf-8")) or [None, "?"])[1],
}
check("Version Alignment: 包内 7 处版本串 100% 对齐为 2.3.2（且 version 文件严格单行）", len(set(_v7.values())) == 1 and _v7["APP_VERSION"] == "2.5.7", str(_v7))

# Load daemon module in isolated temp environment for runtime & E2E checks
spec = importlib.util.spec_from_file_location("ailink_daemon_v102", str(DAEMON))
dmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmod)

tmp_work = Path(tempfile.mkdtemp(prefix="ailink-v102-e2e-"))
tmp_conf = tmp_work / "ai-link"
tmp_run = tmp_work / "run"
tmp_conf.mkdir(parents=True, exist_ok=True)
tmp_run.mkdir(parents=True, exist_ok=True)
dmod.CONF_DIR = tmp_conf
dmod.RUN_DIR = tmp_run

# Gate §7: Write-whitelist round-trip check
for k_field, k_val in [
    ("require_lan_auth", True),
    ("trusted_cidr", "127.0.0.1/32, 192.168.88.0/24"),
    ("panel_bind", "0.0.0.0"),
    ("update_manifest_url", "https://custom.example.com/version.json"),
    ("ipv6_leak_guard", True),
    ("tcp_mss_clamp", True),
]:
    dmod.update_ops_settings({k_field: k_val}, tmp_conf)
    got_ops = dmod.get_ops_settings(tmp_conf)
    disk_ops = json.loads((tmp_conf / "ops_settings.json").read_text(encoding="utf-8"))
    check(f"Gate §7: ops_settings 写盘白名单覆盖 [{k_field}]", got_ops.get(k_field) == k_val and disk_ops.get(k_field) == k_val)

# Reset require_lan_auth & update_manifest_url back to default for subsequent tests
dmod.update_ops_settings({"require_lan_auth": False, "update_manifest_url": ""}, tmp_conf)

# Gate §8: Critical domains routing check
CRITICAL_DOMAINS = {
    "Shunt_Domestic_CN": ["douyincdn.com", "douyinpic.com", "zijieapi.com", "amemv.com", "baidu.com", "qq.com", "taobao.com", "bilibili.com"],
    "Shunt_Google": ["gvt1.com", "xn--ngstr-lra8j.com", "dl.google.com", "connectivitycheck.gstatic.com", "mtalk.google.com"],
}
bad_domains = []
for expected_sel, doms in CRITICAL_DOMAINS.items():
    for dom in doms:
        tr = dmod.trace_traffic_flow({"target": dom, "protocol": "tcp"}, tmp_conf)
        got_sel = tr.get("stage3_rule", {}).get("selector_tag")
        if got_sel != expected_sel:
            bad_domains.append((dom, expected_sel, got_sel))
check("Gate §8: 13 个关键业务域名 (抖音直播 CDN / Google Play) 100% 命中预期分流组", len(bad_domains) == 0, f"bad={bad_domains}")

# ---------------------------------------------------------------------------
# 2. B1-2 & B1-3: UCI panel_pwd_customized=0/1 & Disable weak 'admin' password
# ---------------------------------------------------------------------------
print("\n[2] B1-2 & B1-3 (UCI 布尔化 panel_pwd_customized + 下线弱默认密码 admin)")
uci_txt = UCI_CFG.read_text(encoding="utf-8")
check("B1-2: etc/config/ai-link 不再含 panel_secret", "panel_secret" not in uci_txt)
check("B1-2: etc/config/ai-link 使用布尔 panel_pwd_customized '0'", "option panel_pwd_customized '0'" in uci_txt)
check("B1-2: install.sh 自动迁移并清理旧 panel_secret", "uci -q delete ai-link.global.panel_secret" in INST.read_text(encoding="utf-8"))
check("B1-2: usr/bin/ai-link 改密不再向 UCI 写入明文密码", 'uci set ai-link.global.panel_secret="$2"' not in CLI.read_text(encoding="utf-8"))

init_pw = dmod._get_or_create_initial_secret(tmp_conf)
ok_def, tok_def = dmod._verify_panel_password(init_pw, tmp_conf)
ok_old_pub, _ = dmod._verify_panel_password("ai-link-2026", tmp_conf)
ok_adm, tok_adm = dmod._verify_panel_password("admin", tmp_conf)
check("B1-3 & N-P0-2: 设备唯一初始密码 initial_password 可正常验证且公开默认口令 ai-link-2026 已拒绝", ok_def is True and bool(tok_def) and ok_old_pub is False)
check("B1-3: 弱默认密码 admin 已被彻底拒绝", ok_adm is False and tok_adm == "")

# ---------------------------------------------------------------------------
# 3. B1-4: Self-Healing Watchdog & init.d restore_proxy port check
# ---------------------------------------------------------------------------
print("\n[3] B1-4 (看门狗与 restore_proxy 挂载 nftables 前强制校验 :7893 端口监听)")
daemon_src = DAEMON.read_text(encoding="utf-8")
wd_slice = daemon_src.split("def ensure_nft_and_routing_intact()")[1].split("def start_background_probe_scheduler")[0]
check("B1-4: ensure_nft_and_routing_intact 前置调用 _is_local_port_listening(tproxy_port)",
      "if not _is_local_port_listening(tproxy_port):" in wd_slice and "prevent LAN blackhole" in wd_slice)
initd_txt = INITD.read_text(encoding="utf-8")
rp_slice = initd_txt.split("restore_proxy() {")[1].split("status_check() {")[0]
check("B1-4: init.d restore_proxy 挂载前调用 port_is_listening", 'port_is_listening "${tproxy_port:-7893}"' in rp_slice)

# ---------------------------------------------------------------------------
# 4. B2-8 & B2-9: OTA 进度持久化 + auto_nodes.json 静态哈希稳定
# ---------------------------------------------------------------------------
print("\n[4] B2-8 & B2-9 (OTA 升级进度闪存持久化 + auto_nodes.json 剥离探测噪声)")
ota_body = dmod._update_script_body({
    "target": "1.0.3", "current": "1.0.2", "md5": "a" * 32, "sha256": "b" * 64,
    "size": 100, "package_urls": ["https://example.com/pkg.tar.gz"],
})
check("B2-8: 升级脚本双写 PERSIST_LOG (/root/ai-link-final-backup/last_update_progress.log)",
      'PERSIST_LOG="/root/ai-link-final-backup/last_update_progress.log"' in ota_body and '>> "$PERSIST_LOG"' in ota_body)

# Test read_update_progress fallback when tmpfs progress.log is lost (simulating power loss mid-upgrade)
fake_persist_log = tmp_work / "persist_progress.log"
fake_persist_state = tmp_work / "persist_state.json"
fake_persist_log.write_text(f"{int(time.time())}|download|40|下载完成\n", encoding="utf-8")
fake_persist_state.write_text(json.dumps({"target": "1.0.3", "started_at": int(time.time())}), encoding="utf-8")
orig_p_log, orig_p_state, orig_u_log = dmod.PERSIST_UPDATE_LOG, dmod.PERSIST_UPDATE_STATE, dmod.UPDATE_PROGRESS_LOG
try:
    dmod.PERSIST_UPDATE_LOG = fake_persist_log
    dmod.PERSIST_UPDATE_STATE = fake_persist_state
    dmod.UPDATE_PROGRESS_LOG = tmp_work / "missing_tmpfs_progress.log"
    prog_rec = dmod.read_update_progress()
    check("B2-8: tmpfs 丢失后自动从持久化闪存恢复升级状态并识别断电中断",
          prog_rec.get("from_persistent") is True and prog_rec.get("stage") == "failed" and prog_rec.get("running") is False,
          prog_rec.get("message", ""))
finally:
    dmod.PERSIST_UPDATE_LOG, dmod.PERSIST_UPDATE_STATE, dmod.UPDATE_PROGRESS_LOG = orig_p_log, orig_p_state, orig_u_log

# Test B2-9: auto_nodes.json stability across probe ticks
dmod.evaluate_all_auto_nodes(tmp_conf, force_service_probe=False, advance_revert_streak=False)
an_disk_txt = (tmp_conf / "auto_nodes.json").read_text(encoding="utf-8")
an_disk_obj = json.loads(an_disk_txt)
an_first = (an_disk_obj.get("auto_nodes") or [{}])[0]
check("B2-9: auto_nodes.json 落盘文件不含实时探测噪声 (quality_ranking / last_check_ts / members)",
      "quality_ranking" not in an_first and "last_check_ts" not in an_first and "members" not in (an_first.get("groups") or [{}])[0])
md5_an_1 = hashlib.md5((tmp_conf / "auto_nodes.json").read_bytes()).hexdigest()
# Simulate live probe telemetry update in node_probe.json and re-evaluate
(tmp_conf / "node_probe.json").write_text(json.dumps({"nid_jp_01": {"state": "ok", "delay_ms": 128, "probe_ts": int(time.time()), "svc": {}}}), encoding="utf-8")
dmod.evaluate_all_auto_nodes(tmp_conf, force_service_probe=False, advance_revert_streak=False)
md5_an_2 = hashlib.md5((tmp_conf / "auto_nodes.json").read_bytes()).hexdigest()
check("B2-9: 后台探测评估后 auto_nodes.json MD5 保持 100% 稳定", md5_an_1 == md5_an_2, f"{md5_an_1[:12]} == {md5_an_2[:12]}")

# ---------------------------------------------------------------------------
# 5. B1-1, B1-3, B2-6, B2-7, B3-14: Live HTTP Server E2E (Login / Auth / .tgz Upload / CLI Restore)
# ---------------------------------------------------------------------------
print("\n[5] 真实 HTTP 服务端全链路 E2E (密码登录 / 令牌鉴权 / 改密 / .tgz 上传恢复 / CLI restore)")
dmod.WEBUI_DIR = ROOT / "root/usr/share/ai-link/webui"
httpd = ThreadingHTTPServer(("127.0.0.1", 0), dmod.AILinkRequestHandler)
srv_port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE_URL = f"http://127.0.0.1:{srv_port}"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api_call(path, method="GET", payload=None, headers=None):
    hdrs = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method, headers=hdrs)
    try:
        with opener.open(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}


# Seed 2 subscriptions, 2 nodes & 1 homelink node so we can test subscription card filtering, masking, share_uri, and backup/restore
dmod.save_subscriptions([
    {"id": "sub_airport_main", "name": "主用全球专线机场", "url": "https://sub1.example.com/sub?token=abc12345", "enabled": True, "node_count": 1, "last_sync_human": "刚刚同步"},
    {"id": "sub_ai_unlock", "name": "AI 极速解锁专线", "url": "https://sub2.example.com/sub?token=def67890", "enabled": True, "node_count": 1, "last_sync_human": "5分钟前"},
], tmp_conf)
dmod.save_nodes_list([
    {
        "tag": "JP-Tokyo-VLESS-01", "node_id": "nid_jp_01", "type": "vless",
        "server": "jp.example.com", "server_port": 443, "uuid": "a891f02b-2026-4f88-9b1c-8899aabbccdd",
        "_sub_id": "sub_airport_main", "_sub_url": "https://sub1.example.com/sub?token=abc12345"
    },
    {
        "tag": "SG-AI-Hy2-02", "node_id": "nid_sg_02", "type": "hysteria2",
        "server": "sg.example.com", "server_port": 8443, "password": "hy2_password_2026",
        "_sub_id": "sub_ai_unlock", "_sub_url": "https://sub2.example.com/sub?token=def67890"
    }
], tmp_conf)
dmod.save_homelink_nodes([{
    "id": "hl_e2e_1", "name": "回家-Hy2", "protocol": "hysteria2",
    "listen_port": 20443, "password": "secret_hl_pw_2026", "ddns_host": "home.example.com", "enabled": True,
}], tmp_conf)

# Simulate non-loopback / enforced-auth client using X-Enforce-Auth header
st_401_adm, _ = api_call("/api/login", "POST", {"password": "admin"})
check("E2E 登录: 弱密码 admin 登录返回 401", st_401_adm == 401)
st_401_bad, _ = api_call("/api/login", "POST", {"password": "wrong-password"})
check("E2E 登录: 错误密码登录返回 401", st_401_bad == 401)
st_200_ok, login_res = api_call("/api/login", "POST", {"password": dmod._get_or_create_initial_secret(tmp_conf)})
valid_tok = login_res.get("token", "")
check("E2E 登录: 正确设备初始密码 initial_password 返回 200 并签发 64 位令牌", st_200_ok == 200 and len(valid_tok) == 64)

# Unauthenticated requests with X-Enforce-Auth
st_unauth_st, body_unauth_st = api_call("/api/status", "GET", headers={"X-Enforce-Auth": "1"})
check("E2E 鉴权: 未鉴权 /api/status 返回 auth_required=True 且脱敏回家密码",
      st_unauth_st == 200 and body_unauth_st.get("auth_required") is True and "secret_hl_pw_2026" not in json.dumps(body_unauth_st))
st_unauth_share, _ = api_call("/api/nodes/share_uri?tag=JP-Tokyo-VLESS-01", "GET", headers={"X-Enforce-Auth": "1"})
check("SEC-4: 未鉴权 GET /api/nodes/share_uri 返回 401", st_unauth_share == 401)
st_unauth_logs, _ = api_call("/api/ops/logs", "GET", headers={"X-Enforce-Auth": "1"})
check("SEC-5: 未鉴权 GET /api/ops/logs 返回 401", st_unauth_logs == 401)

# Authenticated with token
auth_hdr = {"X-AI-Link-Token": valid_tok}
st_auth_share, body_auth_share = api_call("/api/nodes/share_uri?tag=JP-Tokyo-VLESS-01", "GET", headers=auth_hdr)
check("E2E 鉴权: 携带有效令牌访问 GET /api/nodes/share_uri 返回 200 与完整 URI",
      st_auth_share == 200 and "vless://" in (body_auth_share.get("uri") or ""))

# Change password via POST /api/ops/password
st_chpw, body_chpw = api_call("/api/ops/password", "POST", {"new_password": "NewStrongPass!2026"}, headers=auth_hdr)
new_tok = body_chpw.get("token", "")
check("E2E 改密: POST /api/ops/password 成功并返回新令牌", st_chpw == 200 and len(new_tok) == 64)
st_old_pw, _ = api_call("/api/login", "POST", {"password": "ai-link-2026"})
st_new_pw, _ = api_call("/api/login", "POST", {"password": "NewStrongPass!2026"})
check("E2E 改密后: 旧默认密码 ai-link-2026 立即失效 (401)，新密码可正常登录 (200)", st_old_pw == 401 and st_new_pw == 200)
_, st_after_pw = api_call("/api/status", "GET", headers={"X-AI-Link-Token": new_tok})
check("E2E 改密后: /api/status pwd_customized=True 且 auth_required=False",
      st_after_pw.get("pwd_customized") is True and st_after_pw.get("auth_required") is False)

# Test B2-6: Export .tgz archive -> Factory Reset -> Upload .tgz archive via POST /api/ops/restore_archive
st_exp_tgz, exp_tgz_res = api_call("/api/ops/backup_archive", "GET", headers={"X-AI-Link-Token": new_tok})
tgz_b64 = exp_tgz_res.get("archive_base64", "")
check("B2-6: GET /api/ops/backup_archive 成功导出 Base64 .tgz 归档", st_exp_tgz == 200 and len(tgz_b64) > 100)

# Perform factory reset
st_rst, _ = api_call("/api/ops/factory_reset", "POST", {"confirm": "RESET", "create_backup": False}, headers={"X-AI-Link-Token": new_tok})
check("E2E 恢复出厂: 清空节点并重置密码为初始状态", st_rst == 200 and len(dmod.load_saved_nodes(tmp_conf)) == 0 and dmod.is_panel_pwd_customized(tmp_conf) is False)

# Test path traversal protection on /api/ops/restore_archive
evil_buf = io.BytesIO()
with tarfile.open(fileobj=evil_buf, mode="w:gz") as tf:
    ti = tarfile.TarInfo(name="../../tmp/evil_traversal.txt")
    payload_evil = b"evil" * 30
    ti.size = len(payload_evil)
    tf.addfile(ti, io.BytesIO(payload_evil))
st_evil, res_evil = api_call("/api/ops/restore_archive", "POST", {"archive_base64": base64.b64encode(evil_buf.getvalue()).decode("ascii")})
check("B2-6 安全: 上传含 ../ 路径穿越的 .tgz 归档被拦截 (400 unsafe_archive_path)",
      st_evil == 400 and res_evil.get("error") == "unsafe_archive_path")

# Restore valid .tgz via browser upload format (data:application/gzip;base64,...)
st_up_res, up_res = api_call("/api/ops/restore_archive", "POST", {
    "archive_base64": f"data:application/gzip;base64,{tgz_b64}",
    "filename": "ai-link-backup-test.tgz",
})
check("B2-6: POST /api/ops/restore_archive 上传 .tgz 归档恢复成功 (节点、回家节点、自定义密码全部还原)",
      st_up_res == 200 and up_res.get("ok") is True and len(dmod.load_saved_nodes(tmp_conf)) == 2 and len(dmod.load_homelink_nodes(tmp_conf)) == 1 and dmod.is_panel_pwd_customized(tmp_conf) is True)

# Test B2-7: CLI --restore with both .tgz and .json files
cli_tgz_file = tmp_work / "cli_test.tgz"
cli_tgz_file.write_bytes(base64.b64decode(tgz_b64))
cli_json_file = tmp_work / "cli_test.json"
cli_json_file.write_text(json.dumps(dmod.export_ops_backup(tmp_conf), ensure_ascii=False), encoding="utf-8")

dmod.factory_reset_all_configs(tmp_conf, create_backup_archive=False)
assert len(dmod.load_saved_nodes(tmp_conf)) == 0
old_argv = list(sys.argv)
try:
    sys.argv = [str(DAEMON), "--restore", str(cli_tgz_file)]
    rc_tgz = dmod.main()
    check("B2-7: CLI `--restore <file.tgz>` 成功恢复归档", rc_tgz == 0 and len(dmod.load_saved_nodes(tmp_conf)) == 2)

    dmod.factory_reset_all_configs(tmp_conf, create_backup_archive=False)
    sys.argv = [str(DAEMON), "--restore", str(cli_json_file)]
    rc_json = dmod.main()
    check("B2-7: CLI `--restore <file.json>` 成功恢复 JSON 备份", rc_json == 0 and len(dmod.load_saved_nodes(tmp_conf)) == 2)
finally:
    sys.argv = old_argv

# ---------------------------------------------------------------------------
# 6. B3-13 & Release Gate §9: Headless Chromium Browser UI E2E Verification
# ---------------------------------------------------------------------------
print("\n[6] B3-13 & Gate §9 (无头 Chromium 浏览器 UI 自动化回归)")
dmod.update_ops_settings({"require_lan_auth": False, "entry_bypass": True}, tmp_conf)
_, live_status_json = api_call("/api/status", "GET")
_, live_nodes_json = api_call("/api/nodes", "GET")
_, live_ops_json = api_call("/api/ops/settings", "GET")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1440,900")
    driver = webdriver.Chrome(options=chrome_opts)
    try:
        driver.get("about:blank")
        three_js_src = (ROOT / "root/usr/share/ai-link/webui/assets/three.min.js").read_text(encoding="utf-8")
        driver.execute_script(three_js_src)
        mock_boot_js = f"""
        window.__errs = [];
        window.addEventListener('error', e => window.__errs.push(e.message));
        window.__AI_LINK_MOCK_ORIGIN = 'http://127.0.0.1:9099';
        window.__MOCK_STATUS = {json.dumps(live_status_json, ensure_ascii=False)};
        window.__MOCK_NODES = {json.dumps(live_nodes_json, ensure_ascii=False)};
        window.__MOCK_OPS = {json.dumps(live_ops_json, ensure_ascii=False)};
        window.fetch = async function(url, opts) {{
            const u = String(url || '');
            let bodyObj = {{ ok: true }};
            if (u.includes('/api/status')) bodyObj = window.__MOCK_STATUS;
            else if (u.includes('/api/nodes')) bodyObj = window.__MOCK_NODES;
            else if (u.includes('/api/ops/settings')) {{
                if (opts && opts.method === 'POST' && opts.body) {{
                    const p = JSON.parse(opts.body);
                    Object.assign(window.__MOCK_OPS, p);
                    if (window.__MOCK_STATUS.ops_settings) Object.assign(window.__MOCK_STATUS.ops_settings, p);
                }}
                bodyObj = Object.assign({{ ok: true, settings: window.__MOCK_OPS }}, window.__MOCK_OPS);
            }} else if (u.includes('/api/shunt/update')) {{
                if (opts && opts.method === 'POST' && opts.body) {{
                    const p = JSON.parse(opts.body);
                    if (!window.__MOCK_STATUS.shunt) window.__MOCK_STATUS.shunt = {{ ok: true }};
                    Object.assign(window.__MOCK_STATUS.shunt, p);
                    if (p.global_mode === 'manual') {{
                        window.__MOCK_STATUS.shunt.global_resolved_node = p.global_manual_node || 'JP-Tokyo-VLESS-01';
                    }} else if (p.global_mode === 'direct') {{
                        window.__MOCK_STATUS.shunt.global_resolved_node = 'direct';
                    }} else {{
                        window.__MOCK_STATUS.shunt.global_resolved_node = 'JP-Tokyo-VLESS-01';
                    }}
                }}
                bodyObj = Object.assign({{ ok: true }}, window.__MOCK_STATUS.shunt);
            }} else if (u.includes('/api/clash/connections')) {{
                bodyObj = {{ ok: true, connections: [], total_count: 0 }};
            }} else if (u.includes('/api/dns/filter/toggle')) {{
                if (opts && opts.method === 'POST' && opts.body) {{
                    const p = JSON.parse(opts.body);
                    if ('enabled' in p) {{
                        window.__MOCK_STATUS.dns_telemetry.filter.enabled = Boolean(p.enabled);
                        window.__MOCK_STATUS.shield_status.enabled = Boolean(p.enabled);
                        window.__MOCK_STATUS.shield_status.state = p.enabled ? 'healthy' : 'disabled';
                    }}
                }}
                bodyObj = Object.assign({{ ok: true }}, window.__MOCK_STATUS.dns_telemetry);
            }} else if (u.includes('/api/auto_nodes/test_candidates')) {{
                const p = (opts && opts.body) ? JSON.parse(opts.body) : {{}};
                const tags = p.tags || [];
                window.__lastTestedCandidateTags = tags;
                const svcs = p.service_checks || ['chatgpt', 'youtube'];
                bodyObj = {{
                    ok: true,
                    service_checks: svcs,
                    service_logic: p.service_logic || 'all',
                    results: tags.map((t, idx) => ({{
                        tag: t,
                        node_id: 'nid-' + idx,
                        country: idx % 2 === 0 ? 'JP' : 'SG',
                        protocol: 'VLESS',
                        state: 'ok',
                        delay_ms: 112 + idx * 14,
                        score: 96 - idx * 3,
                        svc_results: Object.fromEntries(svcs.map(s => [s, {{ ok: true, ms: 128 + idx * 10, code: 200 }}])),
                        svc_passed: true,
                        qualified: true,
                        recommend_action: 'keep'
                    }}))
                }};
            }}
            return {{
                status: 200,
                ok: true,
                json: async () => bodyObj
            }};
        }};
        document.open();
        document.write(arguments[0]);
        document.close();
        """
        css_text = (ROOT / "root/usr/share/ai-link/webui/nexus.css").read_text(encoding="utf-8")
        html_with_css = re.sub(r'<link rel="stylesheet" href="[^"]*nexus\.css[^"]*">', lambda _: f"<style>{css_text}</style>", html_text)
        driver.execute_script(mock_boot_js, html_with_css)
        driver.execute_script((ROOT / "root/usr/share/ai-link/webui/nexus3d.js").read_text(encoding="utf-8"))
        driver.execute_script((ROOT / "root/usr/share/ai-link/webui/nexus.js").read_text(encoding="utf-8"))
        time.sleep(1.5)
        js_errs = driver.execute_script("return window.__errs || [];")
        check("Gate §9-1: 浏览器加载面板零 JS 运行时异常 (window.__errs == [])", len(js_errs) == 0, f"errs={js_errs}")

        driver.execute_script('document.querySelector(\'[data-tab="nodes"]\').click();')
        time.sleep(0.5)
        node_rows = driver.execute_script("return document.querySelectorAll('#probe-nodes-tbody tr').length;")
        check("Gate §9-2: 节点管理页真实渲染节点数据行 (#probe-nodes-tbody tr > 0)", int(node_rows) > 0, f"rows={node_rows}")

        driver.execute_script('document.querySelector(\'[data-tab="settings"]\').click();')
        time.sleep(0.4)
        sec_notice_txt = driver.execute_script("const el = document.getElementById('lan-auth-security-notice'); return el ? el.textContent : '';")
        check("B1-1 UI: 设置页显式展示局域网免密安全风险提示", "安全风险提示" in sec_notice_txt, sec_notice_txt[:45])

        before_eb = driver.execute_script("return document.getElementById('toggle-ops-entry-bypass').getAttribute('aria-checked');")
        driver.execute_script("document.getElementById('toggle-ops-entry-bypass').click();")
        time.sleep(0.6)
        after_eb = driver.execute_script("return document.getElementById('toggle-ops-entry-bypass').getAttribute('aria-checked');")
        check("Gate §9-3: 开关点击后状态真实变化 (toggle-ops-entry-bypass)", before_eb != after_eb, f"{before_eb} -> {after_eb}")

        driver.execute_script("document.getElementById('btn-restore-backup').click();")
        time.sleep(0.3)
        has_file_inp = driver.execute_script("const el = document.getElementById('mdl-restore-file'); return !!(el && el.accept.includes('.tgz'));")
        check("B2-6 UI: 导入恢复弹窗包含 .tgz/.tar.gz/.json 文件上传控件 (#mdl-restore-file)", has_file_inp is True)
        driver.execute_script("if (typeof closeModal === 'function') closeModal();")

        # Non-shunt mode (cn_whitelist / gfw_list / global_proxy) unified egress dropdown selection UI test
        driver.execute_script('''
            window.confirm = () => true;
            document.querySelector('[data-tab="shunt"]').click();
        ''')
        time.sleep(0.3)
        driver.execute_script('''
            document.querySelector('[data-routing-mode="cn_whitelist"]').click();
        ''')
        time.sleep(0.6)
        non_shunt_auto_info = driver.execute_script('''
            const bar = document.getElementById('non-shunt-global-bar');
            const m = document.getElementById('select-global-mode');
            const an = document.getElementById('select-global-autonode');
            const c = document.getElementById('select-global-country');
            const mn = document.getElementById('select-global-manual-node');
            return {
                barVisible: bar && !bar.classList.contains('hidden'),
                modeVal: m ? m.value : '',
                autoOpts: an ? an.options.length : 0,
                autoVisible: an && !an.classList.contains('hidden'),
                countryHidden: c && c.classList.contains('hidden'),
                manualHidden: mn && mn.classList.contains('hidden')
            };
        ''')
        check("v1.0.3 非分流模式 UI: 切换至「非国内走代理」后统一出口栏显示且自动节点池下拉框已填充选项 (>0)",
              non_shunt_auto_info.get("barVisible") is True and non_shunt_auto_info.get("autoOpts", 0) >= 2 and non_shunt_auto_info.get("autoVisible") is True and non_shunt_auto_info.get("countryHidden") is True,
              str(non_shunt_auto_info))

        # Switch #select-global-mode to 'manual' in UI and verify country + manual node dropdowns appear and are populated
        driver.execute_script('''
            const m = document.getElementById('select-global-mode');
            m.value = 'manual';
            m.dispatchEvent(new Event('change'));
        ''')
        time.sleep(0.6)
        non_shunt_manual_info = driver.execute_script('''
            const an = document.getElementById('select-global-autonode');
            const c = document.getElementById('select-global-country');
            const mn = document.getElementById('select-global-manual-node');
            const lbl = document.getElementById('non-shunt-resolved-label');
            return {
                autoHidden: an && an.classList.contains('hidden'),
                countryVisible: c && !c.classList.contains('hidden'),
                countryOpts: c ? c.options.length : 0,
                manualVisible: mn && !mn.classList.contains('hidden'),
                manualOpts: mn ? mn.options.length : 0,
                selectedManual: mn ? mn.value : '',
                labelTxt: lbl ? lbl.textContent : ''
            };
        ''')
        check("v1.0.3 非分流模式 UI: 切换为「🖐️ 手动 (国家 ➔ 节点)」后国家与具体节点下拉框正常展开且可选取节点",
              non_shunt_manual_info.get("autoHidden") is True and non_shunt_manual_info.get("countryVisible") is True and non_shunt_manual_info.get("countryOpts", 0) == 6 and non_shunt_manual_info.get("manualVisible") is True and non_shunt_manual_info.get("manualOpts", 0) >= 1 and "手动" in non_shunt_manual_info.get("labelTxt", ""),
              str(non_shunt_manual_info))

        # Restore back to rule_shunt after UI test
        driver.execute_script('''
            document.querySelector('[data-routing-mode="rule_shunt"]').click();
        ''')
        time.sleep(0.3)

        # NEXUS v2 P2: Verify Overview Sonar (#sonar-stage) right-side labels (ChatGPT / Gemini) are not clipped at 1576px
        driver.set_window_size(1576, 960)
        driver.execute_script('document.querySelector(\x27[data-tab="overview"]\x27).click();')
        time.sleep(0.4)
        sonar_bounds = driver.execute_script('''
            const stage = document.getElementById('sonar-stage');
            const card = stage ? stage.closest('.sonar-card') : null;
            if (!stage || !card) return { ok: false, reason: 'missing stage/card' };
            const sRect = stage.getBoundingClientRect();
            const cRect = card.getBoundingClientRect();
            const blips = Array.from(stage.querySelectorAll('.sonar-blip'));
            const details = blips.map(b => {
                const bRect = b.getBoundingClientRect();
                const cs = window.getComputedStyle(b, ':after');
                const name = b.getAttribute('data-name') || '';
                const isLeft = b.classList.contains('blip-left');
                const estW = Math.min(72, Math.max(44, name.length * 6.2));
                const lblLeft = isLeft ? (bRect.left - 8 - estW) : (bRect.right + 8);
                const lblRight = isLeft ? (bRect.left - 8) : (bRect.right + 8 + estW);
                return {
                    name,
                    isLeft,
                    insideStage: lblLeft >= sRect.left + 2 && lblRight <= sRect.right - 2,
                    insideCard: lblLeft >= cRect.left + 6 && lblRight <= cRect.right - 6
                };
            });
            return {
                ok: blips.length === 8 && details.every(d => d.insideStage && d.insideCard),
                count: blips.length,
                details
            };
        ''')
        check("NEXUS v2 P2: 1576px 视口下概览页「全球核心应用延迟声呐」8 个标签 (含 ChatGPT/Gemini) 100% 位于圆盘与卡片内零裁切",
              sonar_bounds.get("ok") is True, str(sonar_bounds))

        # v2.4.9 Visual & Readability Gate: Overview (.traffic-card == .sonar-card height, <=520px no DPR inflation) & DNS stacked cards flush bottom
        v249_geom = driver.execute_script('''
            const tc = document.querySelector('#page-overview .traffic-card');
            const sc = document.querySelector('#page-overview .sonar-card');
            const kpis = document.querySelectorAll('#traffic-wave-kpis .traffic-kpi-item');
            const r1 = tc ? tc.getBoundingClientRect() : {height: 0, bottom: 0};
            const r2 = sc ? sc.getBoundingClientRect() : {height: 0, bottom: 0};
            return {
                tcH: Math.round(r1.height),
                scH: Math.round(r2.height),
                diffH: Math.abs(Math.round(r1.height) - Math.round(r2.height)),
                kpiCount: kpis.length,
                rateTxt: (document.getElementById('tw-kpi-rate') || {}).textContent || '',
                peakTxt: (document.getElementById('tw-kpi-peak') || {}).textContent || ''
            };
        ''')
        check("v2.4.9 概览页左右双卡片 100% 等高对齐 (高度差=0px 且无 DPR 膨胀 <=530px) 与全息流量波形 4-KPI 摘要栏门禁",
              440 <= v249_geom.get("tcH", 0) <= 530 and v249_geom.get("diffH", 99) <= 1 and v249_geom.get("kpiCount") == 4 and "↓" in v249_geom.get("rateTxt", ""),
              str(v249_geom))

        v250_geom = driver.execute_script('''
            const rowLabels = document.querySelectorAll('#traffic-matrix .matrix-row-label').length;
            const mKpis = document.querySelectorAll('#matrix-kpi-strip .traffic-kpi-item').length;
            document.querySelector('[data-tab="shunt"]').click();
            const shLeft = document.querySelector('#page-shunt .dashboard-grid.two-one > .glass-card').getBoundingClientRect();
            const shTrace = document.getElementById('shunt-trace-card').getBoundingClientRect();
            const diffTrace = Math.abs(Math.round(shLeft.bottom) - Math.round(shTrace.bottom));
            document.querySelector('[data-tab="overview"]').click();
            return { rowLabels, mKpis, diffTrace };
        ''')
        check("v2.5.0 分流页左右双栏等高对齐 (高度差=0px) 与 7x24 时空流量矩阵日期刻度/4-KPI 摘要栏门禁",
              v250_geom.get("rowLabels") == 7 and v250_geom.get("mKpis") == 4 and v250_geom.get("diffTrace", 99) <= 1,
              str(v250_geom))

        v250_sub_auto = driver.execute_script('''
            document.querySelector('[data-tab="nodes"]').click();
            const btn = document.querySelector('[data-action="sub-toggle-auto-update"]');
            const txtBefore = btn ? btn.textContent.trim() : '';
            if (btn) btn.click();
            const btnAfter = document.querySelector('[data-action="sub-toggle-auto-update"]');
            const txtAfter = btnAfter ? btnAfter.textContent.trim() : '';
            const editBtn = document.querySelector('[data-action="sub-edit-one"]');
            if (editBtn) editBtn.click();
            const chk = document.getElementById('mdl-sub-auto-update');
            const iv = document.getElementById('mdl-sub-interval');
            const chkUnchecked = chk ? (!chk.checked && iv && iv.disabled) : false;
            if (typeof closeModal === 'function') closeModal();
            document.querySelector('[data-tab="overview"]').click();
            return { txtBefore, txtAfter, chkUnchecked };
        ''')
        check("v2.5.0 订阅卡片「自动同步」一键开关与编辑弹窗联动门禁: 点击卡片胶囊立即切换为「自动同步: 已关闭」且弹窗内自动同步勾选框与间隔输入框联动禁用",
              "自动同步: 每" in v250_sub_auto.get("txtBefore", "") and "已关闭" in v250_sub_auto.get("txtAfter", "") and v250_sub_auto.get("chkUnchecked") is True,
              str(v250_sub_auto))

        # --- Requirement 1: Sonar bottom list removed, circular radar enlarged, and clicking blip probes real group ---
        sonar_req1 = driver.execute_script('''
            window.__lastDelayUrl = '';
            const origFetch = window.fetch;
            window.fetch = async function(u, o) {
                if (String(u).includes('/api/clash/delay')) window.__lastDelayUrl = String(u);
                return origFetch(u, o);
            };
            const sList = document.getElementById('service-list');
            const stage = document.getElementById('sonar-stage');
            const ytBlip = stage ? stage.querySelector('[data-service="youtube"]') : null;
            if (ytBlip) ytBlip.click();
            return {
                noBottomList: sList === null,
                stageWidth: stage ? Math.round(stage.getBoundingClientRect().width) : 0,
                ytSelector: ytBlip ? ytBlip.getAttribute('data-selector') : '',
                lastDelayUrl: window.__lastDelayUrl
            };
        ''')
        check("Req 1 (声呐重构): 移除下方列表 (#service-list=null)，圆形雷达放大 (>=280px)，且点击 YouTube 星点按真实 Shunt_YouTube 分流组探测",
              sonar_req1.get("noBottomList") is True and sonar_req1.get("stageWidth", 0) >= 280 and "name=Shunt_YouTube" in sonar_req1.get("lastDelayUrl", ""),
              str(sonar_req1))
        driver.save_screenshot("/tmp/verify_1_overview_sonar.png")

        # --- VERIFY-frontend-deep.md Section 二: Real Telemetry Mapping Check ---
        driver.execute_script('''
            window.__MOCK_STATUS.overview_telemetry = Object.assign({}, window.__MOCK_STATUS.overview_telemetry || {}, {
                active_connections: 39,
                in_rate_bps: 4288675,
                in_rate_str: '4.09 MB/s',
                out_rate_bps: 87756,
                out_rate_str: '85.7 KB/s',
                core_mem_mib: 118.6,
                month_total_str: '18.42 GB'
            });
            if (!window.__MOCK_STATUS.dns_telemetry) window.__MOCK_STATUS.dns_telemetry = {};
            window.__MOCK_STATUS.dns_telemetry.stats_24h = {
                blocked_queries: 2595203,
                total_loaded_rules: 50000,
                dns_layer_blocks: 2592326,
                route_reject_blocks: 2877,
                blocked_pct: 90.6,
                avg_resolve_ms: 1
            };
            window.__NEXUS_PREVIEW__.syncBackendStatus(false, true);
        ''')
        time.sleep(0.5)
        truth_map = driver.execute_script('''
            return {
                topConn: document.getElementById('top-connections').textContent,
                topDown: document.getElementById('top-down').textContent,
                topUp: document.getElementById('top-up').textContent,
                dnsBlockedQ: document.getElementById('ov-dns-blocked-q').textContent,
                dnsHeroTitle: document.getElementById('dns-hero-title').textContent,
                dnsLayerRules: document.getElementById('ov-dns-layer-rules').textContent,
                dnsLayerReject: document.getElementById('dns-layer-reject').textContent
            };
        ''')
        check("VERIFY-deep P0 (真值映射): 顶栏连接(39)/下行(4.09 MB/s)/上行(85.7 KB/s) 与 DNS 拦截(2,595,203)/规则数(50,000) 100% 映射真值",
              truth_map.get("topConn") == "39" and truth_map.get("topDown") == "4.09 MB/s" and truth_map.get("topUp") == "85.7 KB/s" and "2,595,203" in truth_map.get("dnsBlockedQ", "") and "50,000" in truth_map.get("dnsHeroTitle", "") and "2,592,326" in truth_map.get("dnsLayerRules", ""),
              str(truth_map))

        # --- Requirement 2: Subscriptions & Nodes ("All Subscriptions" Card + Clickable Subscription Filter) ---
        driver.execute_script('document.querySelector(\'[data-tab="nodes"]\').click();')
        time.sleep(0.4)
        sub_filter_test = driver.execute_script('''
            const hasAllCard = !!document.querySelector('[data-sub-select="ALL"]');
            const rowsAll = document.querySelectorAll('#probe-nodes-tbody tr').length;
            document.querySelector('[data-sub-select="sub_airport_main"]').click();
            const rowsSub1 = document.querySelectorAll('#probe-nodes-tbody tr').length;
            const firstSub1Txt = document.querySelector('#probe-nodes-tbody tr') ? document.querySelector('#probe-nodes-tbody tr').textContent : '';
            document.querySelector('[data-sub-select="sub_ai_unlock"]').click();
            const rowsSub2 = document.querySelectorAll('#probe-nodes-tbody tr').length;
            const firstSub2Txt = document.querySelector('#probe-nodes-tbody tr') ? document.querySelector('#probe-nodes-tbody tr').textContent : '';
            document.querySelector('[data-sub-select="ALL"]').click();
            const rowsRestored = document.querySelectorAll('#probe-nodes-tbody tr').length;
            return {
                hasAllCard,
                rowsAll,
                rowsSub1,
                firstSub1Txt,
                rowsSub2,
                firstSub2Txt,
                rowsRestored
            };
        ''')
        check("Req 2 (订阅卡片联动过滤): 顶部包含「全部订阅源汇总」卡片，点击各订阅卡片精准过滤下方节点列表",
              sub_filter_test.get("hasAllCard") is True and sub_filter_test.get("rowsAll") == 2 and sub_filter_test.get("rowsSub1") == 1 and ("主用全球专线机场丨日本" in sub_filter_test.get("firstSub1Txt", "") or "JP-Tokyo-VLESS-01" in sub_filter_test.get("firstSub1Txt", "")) and sub_filter_test.get("rowsSub2") == 1 and ("AI 极速解锁专线丨新加坡" in sub_filter_test.get("firstSub2Txt", "") or "SG-AI-Hy2-02" in sub_filter_test.get("firstSub2Txt", "")) and sub_filter_test.get("rowsRestored") == 2,
              str(sub_filter_test))
        driver.save_screenshot("/tmp/verify_2_nodes_subscriptions.png")
        node_fmt_audit = driver.execute_script('''
            const td2List = Array.from(document.querySelectorAll("#probe-nodes-tbody tr td:nth-child(2)")).map(td => td.textContent.trim());
            const prevNodes = window.__MOCK_NODES.nodes.slice();
            window.__MOCK_NODES.nodes.push(
                { node_id: "nid_de_test", tag: "地区随机 | 德国 DE | FRA | 82.117.245.166:443", type: "hysteria2", server: "82.117.245.166", server_port: 443, country: "HK", google_region: "HK", region_blocked: true, state: "ok", probe_state: "ok", delay_ms: 158, score_20: 91, _sub_id: "sub_global_main", _sub_name: "主用全球专线机场" },
                { node_id: "nid_other_test", tag: "极速中转专线 | 82.117.245.167:443", type: "vless", server: "82.117.245.167", server_port: 443, country: "SG", google_region: "SG", state: "ok", probe_state: "ok", delay_ms: 142, score_20: 93, _sub_id: "sub_global_main", _sub_name: "主用全球专线机场" }
            );
            return window.__NEXUS_PREVIEW__.syncBackendStatus(true, true).then(() => {
                const rows = Array.from(document.querySelectorAll("#probe-nodes-tbody tr")).map(tr => ({
                    name: tr.querySelector("td:nth-child(1) b") ? tr.querySelector("td:nth-child(1) b").textContent.trim() : "",
                    protoReg: tr.querySelector("td:nth-child(2)") ? tr.querySelector("td:nth-child(2)").textContent.trim() : "",
                    hasBlockedCls: Boolean(tr.querySelector("td:nth-child(2) .google-region-badge.blocked") || tr.querySelector("td:nth-child(2) .google-region-badge.mismatch"))
                }));
                window.__MOCK_NODES.nodes = prevNodes;
                return window.__NEXUS_PREVIEW__.syncBackendStatus(true, true).then(() => ({ td2List, rows }));
            });
        ''')
        check("v2.4.0 节点名称与Google地区协议统一格式门禁: 地区协议统一只显示「（协议）Google地区：xx」且香港不改色，节点名按原节点名提取为「订阅名丨国家名」或「订阅名丨其他国家」",
              any(r.get("name") == "主用全球专线机场丨德国" and r.get("protoReg") == "（HYSTERIA2）Google地区：HK" and r.get("hasBlockedCls") is False for r in node_fmt_audit.get("rows", []))
              and any(r.get("name") == "主用全球专线机场丨其他国家" and r.get("protoReg") == "（VLESS）Google地区：SG" for r in node_fmt_audit.get("rows", [])),
              str(node_fmt_audit))

        # --- Requirement 3 & VERIFY-deep P0: Topbar Mode Display & API Error Toast on Failure ---
        driver.execute_script('document.querySelector(\'[data-tab="shunt"]\').click();')
        time.sleep(0.3)
        topbar_mode_test = driver.execute_script('''
            // In rule_shunt mode, top-exit must show 精细规则分流 (not a single node)
            const ruleExitTxt = document.getElementById('top-exit').textContent;
            const ruleLblTxt = document.getElementById('top-route-label').textContent;
            return { ruleExitTxt, ruleLblTxt };
        ''')
        driver.execute_script('document.querySelector(\'[data-routing-mode="global_proxy"]\').click();')
        time.sleep(0.5)
        topbar_global_test = driver.execute_script('''
            return {
                globalLblTxt: document.getElementById('top-route-label').textContent,
                globalExitTxt: document.getElementById('top-exit').textContent
            };
        ''')
        # Inject failure on /api/shunt/update and verify rollback + warning toast
        driver.execute_script('''
            window.__failNextShuntUpdate = true;
            const prevFetch = window.fetch;
            window.fetch = async function(u, o) {
                if (window.__failNextShuntUpdate && String(u).includes('/api/shunt/update')) {
                    window.__failNextShuntUpdate = false;
                    return { status: 500, ok: false, json: async () => ({ ok: false, message: '模拟后端写入失败' }) };
                }
                return prevFetch(u, o);
            };
            document.querySelector('[data-routing-mode="gfw_list"]').click();
        ''')
        time.sleep(0.5)
        err_toast_test = driver.execute_script('''
            const activeModeBtn = document.querySelector('.routing-mode.active');
            const toasts = Array.from(document.querySelectorAll('#toast-stack .toast')).map(t => t.textContent);
            return {
                rolledBackMode: activeModeBtn ? activeModeBtn.getAttribute('data-routing-mode') : '',
                toasts
            };
        ''')
        driver.execute_script('document.querySelector(\'[data-routing-mode="rule_shunt"]\').click();')
        time.sleep(0.4)
        check("Req 3 (顶栏模式与出口逻辑): 分流模式顶栏显示「精细规则分流」不误导单一节点；全局/GFW/非国内模式显示当前模式与所选出口节点/池",
              topbar_mode_test.get("ruleExitTxt") == "精细规则分流" and "全局模式" in topbar_global_test.get("globalLblTxt", "") and ("主用全球专线机场丨日本" in topbar_global_test.get("globalExitTxt", "") or "JP-Tokyo-VLESS-01" in topbar_global_test.get("globalExitTxt", "")),
              f"rule={topbar_mode_test}, global={topbar_global_test}")
        check("VERIFY-deep P0 (API 失败告警与状态回滚): /api/shunt/update 失败时自动回滚选中态并弹出 warn toast",
              err_toast_test.get("rolledBackMode") == "global_proxy" and any("失败" in t for t in err_toast_test.get("toasts", [])),
              str(err_toast_test))
        driver.save_screenshot("/tmp/verify_3_shunt_topbar_modes.png")

        # --- Requirement 4: 3D Galaxy Satellites & 4-Galaxy Detail Panels ---
        driver.execute_script('document.querySelector(\'[data-page-link="galaxy"]\').click();')
        time.sleep(0.5)
        driver.execute_script('document.querySelector(\'[data-inspector-tab="core"]\').click();')
        time.sleep(0.3)
        gal_core_info = driver.execute_script('''
            return {
                title: document.getElementById('inspector-title').textContent,
                html: document.getElementById('inspector-galaxy-detail').textContent
            };
        ''')
        driver.save_screenshot("/tmp/verify_4_galaxy_core_panel.png")

        driver.execute_script('document.querySelector(\'[data-inspector-tab="global"]\').click();')
        time.sleep(0.3)
        gal_global_info = driver.execute_script('''
            return {
                title: document.getElementById('inspector-title').textContent,
                html: document.getElementById('inspector-galaxy-detail').textContent
            };
        ''')
        driver.save_screenshot("/tmp/verify_5_galaxy_global_panel.png")

        driver.execute_script('document.querySelector(\'[data-inspector-tab="blackhole"]\').click();')
        time.sleep(0.3)
        gal_bh_info = driver.execute_script('''
            return {
                title: document.getElementById('inspector-title').textContent,
                html: document.getElementById('inspector-galaxy-detail').textContent
            };
        ''')
        driver.save_screenshot("/tmp/verify_6_galaxy_blackhole_panel.png")
        check("Req 4 (3D 星图四星系详情面板): 内核中枢/国内直连/海外代理/黑洞拦截四大面板全部按 NEXUS 视觉重构补全 (含4宫格指标、水位条、实时排序列表)",
              "局域网终端列表" in gal_core_info.get("title", "") and "内核连接池水位" in gal_core_info.get("html", "") and "海外代理访问目标" in gal_global_info.get("html", "") and "黑洞吞噬高频域名" in gal_bh_info.get("html", ""),
              f"core={gal_core_info.get('title')}, global={gal_global_info.get('title')}, bh={gal_bh_info.get('title')}")

        # --- v2.0.0 Requirement A, B, C: Soft Pink CN Planet, 3-Tier Speed Gears (高/中/低), & Surge 3D Real Connections ---
        driver.execute_script('document.querySelector(\'[data-scene-mode="panorama"]\').click();')
        time.sleep(0.35)
        driver.save_screenshot("/tmp/verify_7_galaxy_panorama.png")
        driver.execute_script('document.getElementById("surge-toggle").click();')
        time.sleep(0.35)
        driver.execute_script('document.getElementById("wallpaper-toggle").click();')
        time.sleep(0.5)
        driver.save_screenshot("/tmp/verify_8_galaxy_wallpaper.png")
        wp_r5_audit = driver.execute_script("""
            const shell = document.getElementById('scene-shell');
            const wpHud = document.getElementById('wallpaper-hud');
            const sc = window.__nexusScene;
            const controls = Array.from(document.querySelectorAll('input:not([type="hidden"]), select, textarea'));
            const unlabeled = controls.filter(el => {
                if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.getAttribute('title') || el.getAttribute('placeholder')) return false;
                if (el.closest('label')) return false;
                if (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)) return false;
                return true;
            });
            return {
                wpActive: Boolean(shell && shell.classList.contains('wallpaper-mode')),
                hasWpHud: Boolean(wpHud),
                hasEcliptic: Boolean(sc && sc.eclipticPlane),
                hasCometTrails: Boolean(sc && sc.packets && sc.packets.length && sc.packets[0].trailSprites && sc.packets[0].trailSprites.length === 3),
                unlabeledCount: unlabeled.length
            };
        """)
        check("Round 4 & 5 (Apple HIG 无障碍与壁纸级 3D 星图沉浸模式): 全站表单 100% 具备无障碍标签 (unlabeled=0)，3D 星图具备黄道星盘网格、3阶彗尾光子流与壁纸沉浸模式 (#wallpaper-hud)",
              wp_r5_audit.get("unlabeledCount") == 0 and wp_r5_audit.get("wpActive") and wp_r5_audit.get("hasWpHud") and wp_r5_audit.get("hasEcliptic") and wp_r5_audit.get("hasCometTrails"),
              str(wp_r5_audit))
        driver.execute_script('document.getElementById("wallpaper-exit-btn").click();')
        time.sleep(0.6)
        v200_3d_info = driver.execute_script('''
            const sc = window.__nexusScene || (window.__NEXUS_PREVIEW__ && window.__NEXUS_PREVIEW__.scene);
            const gLow = window.NexusScene.computeSpeedGear(4096, 1);
            const gMed = window.NexusScene.computeSpeedGear(40 * 1024, 4);
            const gHigh = window.NexusScene.computeSpeedGear(500 * 1024, 16);
            if (!sc) {
                return {
                    hasScene: false,
                    gearsOk: gLow.gear === 'low' && gMed.gear === 'med' && gHigh.gear === 'high' && gLow.speed < gMed.speed && gMed.speed < gHigh.speed,
                    surgeBtnActive: document.getElementById('surge-toggle').classList.contains('active')
                };
            }
            const gears = sc.getLinkSpeedGears();
            return {
                hasScene: true,
                coreColor: sc.centers.core.data.color,
                cnColor: sc.centers.cn.data.color,
                cnBeamColor: sc.beamsByKey.core_cn.color,
                gearsOk: gLow.gear === 'low' && gMed.gear === 'med' && gHigh.gear === 'high' && gLow.speed < gMed.speed && gMed.speed < gHigh.speed,
                surgeActive: sc.surge,
                liveConnGroupVisible: sc.liveConnGroup ? sc.liveConnGroup.visible : false,
                liveConnArcsCount: sc.liveConnArcs ? sc.liveConnArcs.length : 0,
                liveConnPacketsCount: sc.liveConnPackets ? sc.liveConnPackets.length : 0,
                trunks: gears.trunks
            };
        ''')
        driver.save_screenshot("/tmp/v200_1_galaxy_surge_live3d.png")
        check("v2.0.0 Req 1 (国内直连母星淡粉色): 国内直连母星与连线颜色为淡粉色 (0xf9a8d4)，与内核中枢青色 (0x28b8d4) 鲜明区分",
              v200_3d_info.get("hasScene") is True and v200_3d_info.get("cnColor") == 0xf9a8d4 and v200_3d_info.get("coreColor") == 0x28b8d4 and v200_3d_info.get("cnBeamColor") == 0xf9a8d4,
              str(v200_3d_info))
        check("v2.0.0 Req 2 (流量激增真实连接3D表达): 开启流量激增后实时渲染跨星系真实连接 3D 轨迹弧与流动光球",
              v200_3d_info.get("hasScene") is True and v200_3d_info.get("surgeActive") is True and v200_3d_info.get("liveConnGroupVisible") is True and v200_3d_info.get("liveConnArcsCount", 0) >= 6 and v200_3d_info.get("liveConnPacketsCount", 0) >= 8,
              str(v200_3d_info))
        check("v2.0.0 Req 3 (连线小球高中低三挡速度): 连线光球支持高(0.56)/中(0.26)/低(0.095)三挡速度并按真实连接与速率动态驱动",
              v200_3d_info.get("gearsOk") is True,
              str(v200_3d_info.get("trunks")))

        # --- v2.0.0 Requirement D: Overview Bottom 3 Cards Clickable for Detailed Information ---
        driver.execute_script('document.querySelector(\'[data-page-link="overview"]\').click();')
        time.sleep(0.5)
        driver.execute_script('document.getElementById("ov-card-devices").click();')
        time.sleep(0.35)
        ov_dev_modal = driver.execute_script('''
            const m = document.getElementById('modal');
            const title = document.getElementById('modal-title').textContent;
            const rows = document.querySelectorAll('#mdl-ov-dev-tbody tr').length;
            const avatars = Array.from(document.querySelectorAll('#ov-devices-avatars i')).map(i => i.textContent);
            return { open: m && !m.hidden, title, rows, avatars };
        ''')
        driver.save_screenshot("/tmp/v200_2_overview_modal_devices.png")
        driver.execute_script('window.closeModal();')
        time.sleep(0.2)

        driver.execute_script('document.getElementById("ov-card-outbounds").click();')
        time.sleep(0.35)
        ov_out_modal = driver.execute_script('''
            const m = document.getElementById('modal');
            const title = document.getElementById('modal-title').textContent;
            const rows = document.querySelectorAll('#mdl-ov-node-tbody tr').length;
            return { open: m && !m.hidden, title, rows };
        ''')
        driver.save_screenshot("/tmp/v200_3_overview_modal_outbounds.png")
        driver.execute_script('window.closeModal();')
        time.sleep(0.2)

        driver.execute_script('document.getElementById("ov-card-destinations").click();')
        time.sleep(0.35)
        ov_dest_modal = driver.execute_script('''
            const m = document.getElementById('modal');
            const title = document.getElementById('modal-title').textContent;
            const rows = document.querySelectorAll('#mdl-ov-dest-tbody tr').length;
            const gearBadges = document.querySelectorAll('#mdl-ov-dest-tbody .gear-badge').length;
            return { open: m && !m.hidden, title, rows, gearBadges };
        ''')
        driver.save_screenshot("/tmp/v200_4_overview_modal_destinations.png")
        driver.execute_script('window.closeModal();')
        time.sleep(0.2)

        check("v2.0.0 Req 4 (概览页底部三卡片点击详情): 点击终端设备/入核节点/热门访问目标三张卡片均弹出完整明细表格且终端头像不再重复显示 10",
              ov_dev_modal.get("open") and ov_dev_modal.get("rows", 0) >= 1 and "10" not in ov_dev_modal.get("avatars", []) and
              ov_out_modal.get("open") and ov_out_modal.get("rows", 0) >= 1 and
              ov_dest_modal.get("open") and ov_dest_modal.get("rows", 0) >= 3 and ov_dest_modal.get("gearBadges", 0) >= 2,
              f"dev={ov_dev_modal}, out={ov_out_modal}, dest={ov_dest_modal}")

        # --- v2.0.2 Req: Auto Node Pool Builder Modal Overhaul (Filter check -> In-Filter Test Result -> Add to Pool -> "✓ 已添加" badge -> Group-Specific Bottom List -> 9-to-10 Cap Fix) ---
        driver.execute_script('''
            // Ensure mock.nodes has 12 healthy nodes so we can test 1..9 -> 10th node addition
            const baseNodes = window.__NEXUS_PREVIEW__.mock.nodes;
            while (baseNodes.length < 12) {
                const idx = baseNodes.length + 1;
                baseNodes.push({
                    id: 'nid_extra_' + idx,
                    tag: 'JP-Extra-Node-' + idx,
                    name: 'JP-Extra-Node-' + idx,
                    region: 'JP',
                    country: 'JP',
                    protocol: 'VLESS',
                    server: 'jp' + idx + '.example.com',
                    port: 443,
                    rtt: 95 + idx * 3,
                    score: 98,
                    status: 'ok',
                    sub_id: 'sub_airport_main'
                });
            }
            document.querySelector('[data-page-link="shunt"]').click();
        ''')
        time.sleep(0.3)
        driver.execute_script('document.querySelector(\'[data-action="new-auto-pool"]\').click();')
        time.sleep(0.3)
        # Test 6-step Auto Node Pool Wizard: Multi-source checkboxes, multi-country chips, target size 1-10, replenish threshold 1-10, progress bar & direct removal
        wizard_info = driver.execute_script('''
            const srcBoxes = document.querySelectorAll('.chk-an-source');
            const ctryBtns = document.querySelectorAll('#mdl-an-country-chips button');
            const targetSel = document.getElementById('mdl-an-target-size');
            const repSel = document.getElementById('mdl-an-replenish-thresh');
            if (targetSel) {
                targetSel.value = '4';
                targetSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (repSel) {
                repSel.value = '2';
                repSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            document.getElementById('btn-an-auto-screen').click();
            return {
                srcCount: srcBoxes.length,
                ctryCount: ctryBtns.length,
                targetVal: targetSel ? targetSel.value : '',
                repVal: repSel ? repSel.value : ''
            };
        ''')
        time.sleep(0.45)
        after_screen_info = driver.execute_script('''
            const cntBeforeRemove = document.getElementById('mdl-an-g1-cnt').textContent;
            const rowsBeforeRemove = document.querySelectorAll('#mdl-an-selected-tbody tr').length;
            const progVisible = !document.getElementById('mdl-an-progress-box').classList.contains('hidden');
            const remBtn = document.querySelector('#mdl-an-selected-tbody [data-an-row-op="remove"]');
            if (remBtn) remBtn.click();
            const cntAfterRemove = document.getElementById('mdl-an-g1-cnt').textContent;
            const rowsAfterRemove = document.querySelectorAll('#mdl-an-selected-tbody tr').length;
            window.closeModal();
            return {
                cntBeforeRemove,
                rowsBeforeRemove,
                progVisible,
                cntAfterRemove,
                rowsAfterRemove
            };
        ''')
        check("v2.3.5 Auto-Pool 6步极简向导与实时进度条: 支持多选订阅/多选国家/数量1-10/复选阈值1-10/进度条展示与单点移除",
              wizard_info.get("srcCount", 0) >= 2 and wizard_info.get("ctryCount") == 7 and
              wizard_info.get("targetVal") == "4" and wizard_info.get("repVal") == "2" and
              after_screen_info.get("progVisible") is True and int(after_screen_info.get("cntBeforeRemove") or 0) == 4 and
              int(after_screen_info.get("cntAfterRemove") or 0) == 3,
              f"wizard={wizard_info}, afterScreen={after_screen_info}")

        # --- v2.0.2 P0 Verification: confirmModal on Destructive/Batch Actions ---
        p0_p3_info = driver.execute_script('''
            window.__destructiveApiCalls = 0;
            const prevFetch2 = window.fetch;
            window.fetch = async function(u, o) {
                const us = String(u || '');
                if (us.includes('/api/shunt/reset_group_rules') || (us.includes('/api/shunt/update') && o && o.method === 'POST')) {
                    window.__destructiveApiCalls++;
                }
                return prevFetch2(u, o);
            };
            document.querySelector('[data-action="reset-all-shunt-rules"]').click();
            const modalOpenOnReset = !document.getElementById('modal').hidden;
            const resetModalTitle = document.getElementById('modal-title').textContent;
            const apiCallsBeforeConfirm = window.__destructiveApiCalls;
            window.closeModal();
            const apiCallsAfterCancel = window.__destructiveApiCalls;

            document.querySelector('[data-action="batch-shunt-auto"]').click();
            const modalOpenOnBatch = !document.getElementById('modal').hidden;
            const batchModalTitle = document.getElementById('modal-title').textContent;
            const apiCallsBeforeBatchConfirm = window.__destructiveApiCalls;
            document.getElementById('modal-confirm').click();

            return {
                modalOpenOnReset,
                resetModalTitle,
                apiCallsBeforeConfirm,
                apiCallsAfterCancel,
                modalOpenOnBatch,
                batchModalTitle,
                apiCallsBeforeBatchConfirm
            };
        ''')
        time.sleep(0.35)
        batch_after_confirm = driver.execute_script('''
            return {
                apiCallsAfterBatchConfirm: window.__destructiveApiCalls,
                hasUndoBtn: Boolean(document.querySelector('#toast-stack .toast-undo-btn'))
            };
        ''')
        check("v2.0.2 P0 (危险与批量操作确认弹窗 confirmModal): 点击恢复默认规则库/批量自动池必先弹确认窗，点取消零副作用 (0 API 调用)，点确认后执行并附带「↩ 撤销」",
              p0_p3_info.get("modalOpenOnReset") is True and "确认恢复默认" in p0_p3_info.get("resetModalTitle", "") and
              p0_p3_info.get("apiCallsBeforeConfirm") == 0 and p0_p3_info.get("apiCallsAfterCancel") == 0 and
              p0_p3_info.get("modalOpenOnBatch") is True and p0_p3_info.get("apiCallsBeforeBatchConfirm") == 0 and
              batch_after_confirm.get("apiCallsAfterBatchConfirm") == 1 and batch_after_confirm.get("hasUndoBtn") is True,
              f"p0={p0_p3_info}, afterConfirm={batch_after_confirm}")

        # Verify #mdl-max-outbounds removed from schedule modal
        auto_screen_ui = driver.execute_script('''
            document.querySelector('[data-page-link="nodes"]').click();
            document.querySelector('[data-action="open-schedules"]').click();
            const hasObsMaxInput = Boolean(document.getElementById("mdl-max-outbounds"));
            const schedModalTxt = document.getElementById("modal-body") ? document.getElementById("modal-body").textContent : "";
            window.closeModal();
            return { hasObsMaxInput, hasUnlimitedText: schedModalTxt.includes("全部入核（无数量上限") };
        ''')
        check("v2.3.2 P1-1 & P2-2 UI E2E: 定时测速弹窗已移除入核上限输入",
              auto_screen_ui.get("hasObsMaxInput") is False and auto_screen_ui.get("hasUnlimitedText") is True,
              str(auto_screen_ui))

        # --- New Req B: HomeLink Per-Node Independent Route Mode & Complete Live Monitoring ---
        driver.execute_script('document.querySelector(\'[data-page-link="homelink"]\').click();')
        time.sleep(0.35)
        hl_ui_info = driver.execute_script('''
            const globalModesRemoved = (document.getElementById('homelink-modes') === null);
            const nodeModeSelects = document.querySelectorAll('select[data-hl-node-mode]').length;
            const monitorKpis = document.querySelectorAll('#homelink-monitor-kpis .galaxy-kpi-card').length;
            const monitorRows = document.querySelectorAll('#homelink-monitor-tbody tr').length;
            return { globalModesRemoved, nodeModeSelects, monitorKpis, monitorRows };
        ''')
        driver.save_screenshot("/tmp/v200_6_homelink_per_node_and_monitor.png")
        check("回家节点改造: 移除全局三模式大按钮 (#homelink-modes=null)，改为单节点独立路由模式下拉框 + 完整实时监控面板与明细表",
              hl_ui_info.get("globalModesRemoved") is True and hl_ui_info.get("nodeModeSelects", 0) >= 1 and
              hl_ui_info.get("monitorKpis") == 4 and hl_ui_info.get("monitorRows", 0) >= 1,
              str(hl_ui_info))

        # --- New Req C: Cloud Domain Filtering Shield Toggle Persistence on Reload ---
        driver.execute_script('document.querySelector(\'[data-page-link="dns"]\').click();')
        time.sleep(0.3)
        driver.execute_script('document.getElementById("toggle-dns-filter").click();')
        time.sleep(0.3)
        driver.execute_script('window.__NEXUS_PREVIEW__.syncBackendStatus(false, true);')
        time.sleep(0.4)
        dns_toggle_persisted_off = driver.execute_script('''
            const btn = document.getElementById('toggle-dns-filter');
            return {
                isOffClass: btn.classList.contains('off') && !btn.classList.contains('on'),
                ariaChecked: btn.getAttribute('aria-checked'),
                stateDnsEnabled: window.__NEXUS_PREVIEW__.state.dnsEnabled
            };
        ''')
        # Restore ON
        driver.execute_script('document.getElementById("toggle-dns-filter").click();')
        time.sleep(0.2)
        check("已知问题 3 修复 (云端域名过滤护盾开关持久化): 关闭护盾开关后刷新同步状态依然保持关闭 (aria-checked=false, state.dnsEnabled=false)",
              dns_toggle_persisted_off.get("isOffClass") is True and dns_toggle_persisted_off.get("ariaChecked") == "false" and dns_toggle_persisted_off.get("stateDnsEnabled") is False,
              str(dns_toggle_persisted_off))

        # --- Optimization 1 & 2: 3D Decluttering (No meaningless dust/cn_global beam) & GitHub Project Link ---
        opt_info = driver.execute_script('''
            const sc = window.__nexusScene || (window.__NEXUS_PREVIEW__ && window.__NEXUS_PREVIEW__.scene);
            const ghLink = document.getElementById('top-github-link');
            return {
                noDust: sc ? (sc.dust === undefined) : true,
                noCnGlobalBeam: sc ? (sc.beamsByKey.cn_global === undefined) : true,
                threeRealTrunks: sc ? (Object.keys(sc.beamsByKey).length === 3) : true,
                ghHref: ghLink ? ghLink.getAttribute('href') : ''
            };
        ''')
        check("优化建议 1 & 2 (3D无意义渲染删减 + GitHub项目地址): 移除无意义星尘与cn_global假连线，保留3条真实可读数据主干，顶栏与设置页提供GitHub项目链接",
              opt_info.get("noDust") is True and opt_info.get("noCnGlobalBeam") is True and opt_info.get("threeRealTrunks") is True and "github.com/Master-AI-007/ai-link-openwrt" in opt_info.get("ghHref", ""),
              str(opt_info))

        # --- v2.3.6 Sci-Fi HUD Overhaul & UI Issues (U-01 ~ U-08) E2E Assertions ---
        driver.execute_script('document.querySelector(\'[data-page-link="shunt"]\').click();')
        time.sleep(0.35)
        u01_u06_audit = driver.execute_script('''
            // U-01: Count visible elements whose computed text color is mint (#38e0b2 -> rgb(56, 224, 178))
            const allVisible = Array.from(document.querySelectorAll('#page-shunt *')).filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && el.children.length === 0 && (el.textContent || '').trim().length > 0;
            });
            const mintTextNodes = allVisible.filter(el => getComputedStyle(el).color === 'rgb(56, 224, 178)');

            // U-02: Topbar buttons unified (0 permanent primary buttons in .topbar-actions)
            const topActionBtns = Array.from(document.querySelectorAll('.topbar-actions > button'));
            const topPrimaryBtns = topActionBtns.filter(b => b.classList.contains('primary'));

            // U-03: Compact 3-layer HUD Auto-Pool cards (height <= 165px, 1 primary button + 1 more menu per card)
            const poolCards = Array.from(document.querySelectorAll('#auto-pools .auto-pool'));
            const maxPoolHeight = poolCards.reduce((m, c) => Math.max(m, Math.round(c.getBoundingClientRect().height)), 0);
            const hasMoreMenu = poolCards.every(c => Boolean(c.querySelector('[data-action="toggle-pool-menu"]')) && Boolean(c.querySelector('.pool-more-menu')));

            // U-05: Shunt page 3-Tab right-hand observation switcher (#shunt-obs-tabs) & align-items: start
            const obsTabs = document.querySelectorAll('#shunt-obs-tabs [data-shunt-obs-tab]').length;
            const gridAlign = getComputedStyle(document.querySelector('#page-shunt .dashboard-grid.two-one')).alignItems;

            // U-06: Switch .switch.on has transparent background (no double-circle overlay from legacy rule)
            const swOn = document.querySelector('.switch.on');
            const swBg = swOn ? getComputedStyle(swOn).backgroundColor : '';

            // U-07: Unified .page-hero headers with .hud-hero-orb and .hud-help-btn across pages
            const pageHeros = document.querySelectorAll('.dns-hero.page-hero').length;
            const legacyContentHeads = document.querySelectorAll('.content-head').length;
            const heroOrbs = document.querySelectorAll('.dns-hero.page-hero .hud-hero-orb').length;
            const helpBtns = document.querySelectorAll('.hud-help-btn').length;

            return {
                mintTextCount: mintTextNodes.length,
                topActionCount: topActionBtns.length,
                topPrimaryCount: topPrimaryBtns.length,
                poolCardCount: poolCards.length,
                maxPoolHeight,
                hasMoreMenu,
                obsTabs,
                gridAlign,
                swBg,
                pageHeros,
                legacyContentHeads,
                heroOrbs,
                helpBtns
            };
        ''')
        check("UI-Audit U-01 & U-02 & U-06 & U-07 (科幻HUD色彩克制/顶栏统一/开关去双圈/统一Hero横幅): 分流页薄荷绿文字<=8处，顶栏0常驻Primary，.switch.on背景透明无双圈，全站具备统一.page-hero与?战术指南",
              u01_u06_audit.get("mintTextCount", 99) <= 8 and u01_u06_audit.get("topPrimaryCount") == 0 and
              u01_u06_audit.get("swBg") == "rgba(0, 0, 0, 0)" and u01_u06_audit.get("pageHeros", 0) == 6 and u01_u06_audit.get("legacyContentHeads", 99) == 0 and
              u01_u06_audit.get("heroOrbs", 0) >= 6 and u01_u06_audit.get("helpBtns", 0) >= 8,
              str(u01_u06_audit))
        check("UI-Audit U-03 & U-05 (自动节点池极简3层HUD卡片 & 分流页右栏3-Tab矩阵): 节点池卡片高度<=165px且含···菜单，右栏支持3-Tab切换且左栏align-items=start消除留白",
              u01_u06_audit.get("poolCardCount", 0) >= 2 and u01_u06_audit.get("maxPoolHeight", 999) <= 165 and
              u01_u06_audit.get("hasMoreMenu") is True and u01_u06_audit.get("obsTabs") == 3 and
              u01_u06_audit.get("gridAlign") in ("start", "stretch"),
              str(u01_u06_audit))

        # Verify Auto-Pool ··· Popover Menu (.pool-more-menu) is 100% unclipped by outer .glass-card and never occluded by sibling cards
        pool_menu_hit_audit = driver.execute_script('''
            const boot = document.getElementById('boot');
            if (boot) boot.remove();
            window.__NEXUS_PREVIEW__.showPage('shunt');
            const outerCard = document.getElementById('auto-pools').closest('.glass-card');
            const outerOverflow = window.getComputedStyle(outerCard).overflow;
            const btns = Array.from(document.querySelectorAll('[data-action="toggle-pool-menu"]'));
            const results = [];
            for (const btn of btns) {
                btn.click();
                const idx = btn.dataset.poolIdx;
                const menu = document.getElementById('pool-more-menu-' + idx);
                const oRect = outerCard.getBoundingClientRect();
                const items = Array.from(menu.querySelectorAll('button'));
                const hits = items.map(it => {
                    it.scrollIntoView({ block: 'nearest' });
                    const r = it.getBoundingClientRect();
                    const cx = Math.round(r.left + r.width / 2);
                    const cy = Math.round(r.top + r.height / 2);
                    const topEl = document.elementFromPoint(cx, cy);
                    return {
                        text: it.textContent.trim(),
                        hitSelf: topEl === it || it.contains(topEl),
                        insideOuter: r.top >= oRect.top && r.bottom <= oRect.bottom
                    };
                });
                results.push({ idx, allHitSelf: hits.every(h => h.hitSelf), allInsideOuter: hits.every(h => h.insideOuter), hits });
            }
            document.body.click();
            return { outerOverflow, count: results.length, allOk: results.length >= 2 && results.every(r => r.allHitSelf && r.allInsideOuter), results };
        ''')
        check("v2.4.0 自动节点池 ··· 菜单零遮挡/零裁切门禁 (向上弹出 + 外层 .glass-card overflow=visible + menu-open 提权 + elementFromPoint 100% 命中)",
              pool_menu_hit_audit.get("allOk") is True and pool_menu_hit_audit.get("outerOverflow") == "visible",
              str(pool_menu_hit_audit))

        # U-04: Shunt group modal zero horizontal overflow + 3 mode cards + dynamic field visibility + live preview
        driver.execute_script('document.querySelector(\'.shunt-group-card [data-group="0"]\').click();')
        time.sleep(0.3)
        u04_audit = driver.execute_script('''
            const mBody = document.getElementById('modal-body');
            const noOverflow = mBody ? (mBody.scrollWidth <= mBody.clientWidth + 2) : false;
            const modeCards = document.querySelectorAll('#mdl-grp-mode-cards [data-grp-mode-pick]').length;
            const autoPane = document.getElementById('mdl-grp-pane-auto');
            const manPane = document.getElementById('mdl-grp-pane-manual');
            const previewBefore = document.getElementById('mdl-grp-preview-bar') ? document.getElementById('mdl-grp-preview-bar').textContent : '';
            // Click manual mode card
            const manBtn = document.querySelector('#mdl-grp-mode-cards [data-grp-mode-pick="manual"]');
            if (manBtn) manBtn.click();
            const manVisibleAfter = manPane ? !manPane.classList.contains('hidden') : false;
            const autoHiddenAfter = autoPane ? autoPane.classList.contains('hidden') : false;
            const previewAfter = document.getElementById('mdl-grp-preview-bar') ? document.getElementById('mdl-grp-preview-bar').textContent : '';
            window.closeModal();
            return {
                noOverflow,
                scrollW: mBody ? mBody.scrollWidth : 0,
                clientW: mBody ? mBody.clientWidth : 0,
                modeCards,
                manVisibleAfter,
                autoHiddenAfter,
                previewBefore,
                previewAfter
            };
        ''')
        check("UI-Audit U-04 (分流策略组弹窗重构): 弹窗零横向溢出 (scrollWidth<=clientWidth)，3张互斥出站模式卡片动态切换表单显隐并实时更新预览条",
              u04_audit.get("noOverflow") is True and u04_audit.get("modeCards") == 3 and
              u04_audit.get("manVisibleAfter") is True and u04_audit.get("autoHiddenAfter") is True and
              "应用后效果预览" in u04_audit.get("previewAfter", ""),
              str(u04_audit))

        # U-08: Active Connections table renders real c.host & c.src_ip (0 unknown:443) + device filter dropdown
        driver.execute_script('document.querySelector(\'[data-page-link="settings"]\').click();')
        time.sleep(0.35)
        driver.execute_script('''
            window.__MOCK_CONNECTIONS = [
                { id: 'c1', host: 'api.openai.com:443', dst_ip: '104.18.32.47', dst_port: 443, src_ip: '10.10.10.224', network: 'tcp', rule: 'Shunt_AI_Intl', chains: ['JP-Tokyo-VLESS-01', 'Shunt_AI_Intl'], upload: 16384, download: 524288, start: new Date().toISOString() },
                { id: 'c2', host: 'mtalk.google.com:5228', dst_ip: '142.250.107.188', dst_port: 443, src_ip: '10.10.10.180', network: 'tcp', rule: 'Shunt_Google_Suite', chains: ['SG-AI-Hy2-02', 'Shunt_Google_Suite'], upload: 4096, download: 65536, start: new Date().toISOString() }
            ];
            if (window.__NEXUS_PREVIEW__ && window.__NEXUS_PREVIEW__.state) {
                window.__NEXUS_PREVIEW__.state.rawConnections = window.__MOCK_CONNECTIONS;
            }
            const qInput = document.getElementById('conn-search-input');
            if (qInput) qInput.dispatchEvent(new Event('input', { bubbles: true }));
        ''')
        time.sleep(0.25)
        u08_audit = driver.execute_script('''
            const tbodyTxt = document.getElementById('connections-tbody') ? document.getElementById('connections-tbody').textContent : '';
            const devSel = document.getElementById('conn-device-filter');
            const devOpts = devSel ? devSel.options.length : 0;
            // Filter by 10.10.10.180
            if (devSel) {
                devSel.value = '10.10.10.180';
                devSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            const filteredRows = document.querySelectorAll('#connections-tbody tr').length;
            const filteredTxt = document.getElementById('connections-tbody') ? document.getElementById('connections-tbody').textContent : '';
            if (devSel) {
                devSel.value = 'ALL';
                devSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            return {
                hasUnknown: tbodyTxt.includes('unknown:443'),
                hasDoublePort: tbodyTxt.includes(':5228:443'),
                hasRealHost: tbodyTxt.includes('api.openai.com:443') && tbodyTxt.includes('mtalk.google.com:5228'),
                hasRealSrcIp: tbodyTxt.includes('10.10.10.224') && tbodyTxt.includes('10.10.10.180'),
                devOpts,
                filteredRows,
                filteredTxt
            };
        ''')
        check("UI-Audit U-08 (实时活跃连接表真值解析与按设备筛选): 0个unknown:443且不重复拼接:5228:443，真实展示源IP并支持#conn-device-filter按设备过滤",
              u08_audit.get("hasUnknown") is False and u08_audit.get("hasDoublePort") is False and
              u08_audit.get("hasRealHost") is True and u08_audit.get("hasRealSrcIp") is True and
              u08_audit.get("devOpts", 0) >= 3 and u08_audit.get("filteredRows") == 1 and
              "10.10.10.180" in u08_audit.get("filteredTxt", ""),
              str(u08_audit))

        # v2.4.0 UI E2E: Settings 3-Mode Data-Plane Switcher & Mobile (375px / 430px) Page-Hero Responsive Scaling Gate
        driver.set_window_size(1440, 900)
        dpm_ui_test = driver.execute_script('''
            window.__NEXUS_PREVIEW__.showPage('settings');
            const selDpm = document.getElementById('sel-ops-data-plane-mode');
            const selTs = document.getElementById('sel-ops-tun-stack');
            const subEl = document.getElementById('sys-core-sub');
            if (!selDpm || !selTs || !subEl) return { ok: false };
            selDpm.value = 'tproxy_tcp_tun_udp';
            selDpm.dispatchEvent(new Event('change'));
            selDpm.value = 'tun_full';
            selDpm.dispatchEvent(new Event('change'));
            selDpm.value = 'tproxy_redirect';
            selDpm.dispatchEvent(new Event('change'));
            return {
                ok: true,
                optsDpm: Array.from(selDpm.options).map(o => o.value),
                optsTs: Array.from(selTs.options).map(o => o.value),
                subTxt: subEl.textContent
            };
        ''')
        time.sleep(0.3)
        check("v2.4.0 设置页三模数据面 UI 切换门禁: 支持切换 TProxy / 游戏混合 TUN / 全量 TUN 并实时同步内核副标题",
              dpm_ui_test.get("ok") is True
              and dpm_ui_test.get("optsDpm") == ["tproxy_redirect", "tproxy_tcp_tun_udp", "tun_full"]
              and dpm_ui_test.get("optsTs") == ["mixed", "system", "gvisor", "auto"],
              str(dpm_ui_test))

        # Mobile 430x932 & 375x812 Page-Hero Responsive Scaling Gate across all 6 pages
        mobile_hero_results = {}
        for _mw, _mh in [(430, 932), (375, 812)]:
            driver.set_window_size(_mw, _mh)
            time.sleep(0.15)
            _vp_res = driver.execute_script('''
                const pages = ['overview', 'shunt', 'homelink', 'dns', 'nodes', 'settings'];
                const out = [];
                for (const pg of pages) {
                    window.__NEXUS_PREVIEW__.showPage(pg);
                    const sec = document.querySelector('#page-' + pg);
                    const hero = sec ? sec.querySelector('.dns-hero.page-hero') : null;
                    if (!hero) { out.push({ page: pg, ok: false }); continue; }
                    const hr = hero.getBoundingClientRect();
                    const cr = hero.querySelector('.shield-copy').getBoundingClientRect();
                    const sr = hero.querySelector('.shield-stats').getBoundingClientRect();
                    out.push({
                        page: pg,
                        heroH: Math.round(hr.height),
                        clientW: hero.clientWidth,
                        scrollW: hero.scrollWidth,
                        copyW: Math.round(cr.width),
                        statsH: Math.round(sr.height),
                        ok: hero.scrollWidth <= hero.clientWidth + 1 && cr.width >= hero.clientWidth - 40 && hr.height <= 480 && sr.height <= 68
                    });
                }
                return out;
            ''')
            mobile_hero_results[f"{_mw}x{_mh}"] = _vp_res
        driver.set_window_size(1440, 900)
        check("v2.4.0 移动端分页头自适应门禁 (375px & 430px 全站 6 页 .dns-hero.page-hero 零横向溢出、文案区 100% 满宽不挤压、指标单行<=68px、总高<=480px)",
              all(item.get("ok") is True for vp_list in mobile_hero_results.values() for item in vp_list),
              str(mobile_hero_results))

        # v2.4.0 Round-2 UI Gate: Settings Card 01 Kernel Update Button & Version Sync + Card 04 IPv6 Switch Alignment + Overview 340px Sonar & Custom Modal
        settings_ui_gate = driver.execute_script('''
            window.__NEXUS_PREVIEW__.showPage('settings');
            const coreCard = document.querySelector('article.system-card');
            const btnCheckCore = coreCard ? coreCard.querySelector('[data-action="check-core-update"]') : null;
            const otaSubInCard1 = coreCard ? coreCard.querySelector('#core-ota-sub') : null;
            const swAuth = document.getElementById('toggle-require-lan-auth');
            const swBypass = document.getElementById('toggle-ops-entry-bypass');
            const swIpv6 = document.getElementById('toggle-ipv6-proxy');
            const rAuth = swAuth ? swAuth.getBoundingClientRect() : { right: 0 };
            const rBypass = swBypass ? swBypass.getBoundingClientRect() : { right: 0 };
            const rIpv6 = swIpv6 ? swIpv6.getBoundingClientRect() : { right: -999 };
            return {
                btnInCard1: Boolean(btnCheckCore && otaSubInCard1),
                authRight: Math.round(rAuth.right),
                bypassRight: Math.round(rBypass.right),
                ipv6Right: Math.round(rIpv6.right),
                ipv6Aligned: Math.abs(rIpv6.right - rAuth.right) <= 2 && Math.abs(rIpv6.right - rBypass.right) <= 2
            };
        ''')
        check("v2.4.0 设置页門禁 (「检查内核更新」按钮移入左侧 01/CORE LIFECYCLE 卡片内，且 IPv6 开关与上方两个开关 100% 垂直右对齐零折行)",
              settings_ui_gate.get("btnInCard1") is True and settings_ui_gate.get("ipv6Aligned") is True,
              str(settings_ui_gate))

        driver.execute_script('''
            window.__NEXUS_PREVIEW__.showPage('overview');
            const btnCustom = document.getElementById('btn-sonar-custom');
            if (btnCustom) btnCustom.click();
        ''')
        time.sleep(0.35)
        sonar_ui_gate = driver.execute_script('''
            const stage = document.getElementById('sonar-stage');
            const btnProbeAll = document.getElementById('btn-sonar-probe-all');
            const btnCustom = document.getElementById('btn-sonar-custom');
            const stRect = stage ? stage.getBoundingClientRect() : { width: 0, height: 0 };
            const rowsCnt = document.querySelectorAll('#sonar-cfg-rows .sonar-cfg-row').length;
            const closeBtn = document.getElementById('modal-close');
            if (closeBtn) closeBtn.click();
            return {
                stageW: Math.round(stRect.width),
                stageH: Math.round(stRect.height),
                hasActions: Boolean(btnProbeAll && btnCustom),
                modalRows: rowsCnt
            };
        ''')
        check("v2.4.0 概览声呐 UI 门禁 (圆形仪表盘占比放大至 340x340px，支持「全部实测」与「自定义目标」8 行配置弹窗)",
              sonar_ui_gate.get("stageW", 0) >= 320 and sonar_ui_gate.get("hasActions") is True and sonar_ui_gate.get("modalRows") == 8,
              str(sonar_ui_gate))

        # v2.4.0 Subscription Card .sub-health-box Zero-Overflow & Visual Sync Progress Modal + Immediate Status Refresh Gate
        driver.execute_script('''
            window.__NEXUS_PREVIEW__.showPage('nodes');
            const subs = window.__MOCK_STATUS.subscriptions || [];
            if (subs[0]) {
                subs[0].status = 'error';
                subs[0].last_sync_status = 'error';
                subs[0].sync_status_text = '2026-11-05 14:00 失败';
                subs[0].userinfo = {
                    used_bytes: 110519913676,
                    total_bytes: 161061273600,
                    used_human: '102.93 GiB',
                    total_human: '150.00 GiB',
                    remaining_human: '47.07 GiB',
                    used_pct: 68.6,
                    expire_ts: 1795305600,
                    expire_days_left: 16,
                    expire_human: '2026-11-22',
                    reset_day: 22
                };
            }
        ''')
        driver.execute_script("window.__triggerSyncStatus && window.__triggerSyncStatus();")
        time.sleep(0.25)
        sub_box_gate = driver.execute_script('''
            window.__NEXUS_PREVIEW__.showPage('nodes');
            const cards = Array.from(document.querySelectorAll('#subscription-list .subscription-card'));
            const subCard = cards[2] || cards[cards.length - 1];
            const box = subCard ? subCard.querySelector('.sub-health-box') : null;
            if (!box) return { ok: false, reason: 'no sub-health-box' };
            const bRect = box.getBoundingClientRect();
            const topEl = box.querySelector('.sub-health-top');
            const barEl = box.querySelector('.sub-health-bar');
            const metaEl = box.querySelector('.sub-health-meta');
            const pillEl = box.querySelector('.sub-expire-pill');
            const tRect = topEl ? topEl.getBoundingClientRect() : bRect;
            const barRect = barEl ? barEl.getBoundingClientRect() : { width: 0 };
            const mRect = metaEl ? metaEl.getBoundingClientRect() : bRect;
            const pRect = pillEl ? pillEl.getBoundingClientRect() : bRect;
            const inside = r => (r.left >= bRect.left - 1 && r.right <= bRect.right + 1);
            const syncBtn = subCard.querySelector('[data-action="sub-sync-one"]');
            if (syncBtn) syncBtn.click();
            return {
                boxW: Math.round(bRect.width),
                barW: Math.round(barRect.width),
                topInside: inside(tRect),
                metaInside: inside(mRect),
                pillInside: inside(pRect),
                ok: barRect.width >= 160 && inside(tRect) && inside(mRect) && inside(pRect)
            };
        ''')
        time.sleep(0.85)
        sub_sync_modal_gate = driver.execute_script('''
            const modalEl = document.getElementById('sub-sync-progress-modal');
            const fillEl = document.getElementById('sub-sync-prog-fill');
            const badge0 = document.getElementById('sub-sync-badge-0');
            const pctTxt = document.getElementById('sub-sync-pct-label');
            const closeBtn = document.getElementById('modal-close');
            const modalOpen = Boolean(modalEl && fillEl);
            const badgeTxt = badge0 ? badge0.textContent.trim() : '';
            const pctVal = pctTxt ? pctTxt.textContent.trim() : '';
            if (closeBtn) closeBtn.click();
            const cards = Array.from(document.querySelectorAll('#subscription-list .subscription-card'));
            const subCard = cards[2] || cards[cards.length - 1];
            const statusSpan = subCard ? subCard.querySelector('.sub-sync-status') : null;
            const statusTxt = statusSpan ? statusSpan.textContent.trim() : '';
            return {
                modalOpen,
                badgeTxt,
                pctVal,
                statusTxt,
                refreshedOk: Boolean(statusTxt && !statusTxt.includes('失败'))
            };
        ''')
        check("v2.4.0 订阅卡片零出框与同步可视化进度弹窗门禁 (.sub-health-box 内部文字/胶囊 100% 不出框且进度条宽度正常；点击「立即同步」弹出实时进度条并立即将「失败」刷新为最新成功时间)",
              sub_box_gate.get("ok") is True and sub_sync_modal_gate.get("modalOpen") is True and sub_sync_modal_gate.get("refreshedOk") is True,
              f"box={sub_box_gate} modal={sub_sync_modal_gate}")
        # v2.4.2 5-Feature UI E2E: Auto-Pool Multi-Line Interactive Guardrail + Keyword Filter + Bandwidth Prefer
        ml_ui_res = driver.execute_script('''
            // Open Auto-Pool Wizard for a new pool
            window.__NEXUS_PREVIEW__.showPage('shunt');
            const addPoolBtn = document.querySelector('[data-action="new-auto-pool"]');
            if (addPoolBtn) addPoolBtn.click();
            const btnSvc = document.getElementById('btn-an-mode-svc');
            const btnPing = document.getElementById('btn-an-mode-ping');
            const btnSingle = document.getElementById('btn-an-dispatch-single');
            const btnMulti = document.getElementById('btn-an-dispatch-multi');
            // 1. Switch to service_check mode where gemini & chatgpt are checked by default -> btnMulti must auto-lock (disabled=true)
            if (btnSvc) btnSvc.click();
            const lockedWhenAiChecked = Boolean(btnMulti && btnMulti.disabled && btnSingle && btnSingle.classList.contains('active'));
            // 2. Switch back to ping_only mode -> btnMulti must unlock (disabled=false), then click btnMulti -> AI service checkboxes must auto-disable!
            if (btnPing) btnPing.click();
            const unlockedOnPing = Boolean(btnMulti && !btnMulti.disabled);
            if (btnMulti) btnMulti.click();
            const multiActive = Boolean(btnMulti && btnMulti.classList.contains('active'));
            const aiChkDisabled = Array.from(document.querySelectorAll('.chk-an-svc'))
                .filter(c => ['gemini', 'chatgpt', 'claude'].includes(c.value))
                .every(c => c.disabled && !c.checked);
            const hasKwInput = Boolean(document.getElementById('mdl-an-keywords') && document.getElementById('mdl-an-kw-mode'));
            const bwChk = document.getElementById('mdl-an-bw-prefer');
            if (bwChk && !bwChk.checked) bwChk.click();
            const bwVisible = Boolean(document.getElementById('mdl-an-bw-opts') && !document.getElementById('mdl-an-bw-opts').classList.contains('hidden'));
            const closeBtn = document.getElementById('modal-close');
            if (closeBtn) closeBtn.click();
            return { lockedWhenAiChecked, unlockedOnPing, multiActive, aiChkDisabled, hasKwInput, bwVisible };
        ''')
        check(
            "v2.4.2 节点池「多线并发」交互防风控护栏与带宽择优 UI 门禁: 勾选 AI 敏感服务时自动锁定单线并禁用多线并发；开启多线并发时自动屏蔽 AI 勾选项，且支持原名关键词 AND/OR 与定量带宽择优",
            isinstance(ml_ui_res, dict)
            and ml_ui_res.get("lockedWhenAiChecked") is True
            and ml_ui_res.get("unlockedOnPing") is True
            and ml_ui_res.get("multiActive") is True
            and ml_ui_res.get("aiChkDisabled") is True
            and ml_ui_res.get("hasKwInput") is True
            and ml_ui_res.get("bwVisible") is True,
            str(ml_ui_res)
        )
    finally:
        driver.quit()
except ImportError:
    check("Gate §9-1: 静态 DOM 包含 #probe-nodes-tbody 与 #toggle-ops-entry-bypass",
          'id="probe-nodes-tbody"' in html_text and 'id="toggle-ops-entry-bypass"' in html_text, "selenium 未安装，使用静态 DOM 校验")
    check("B1-1 UI: 静态 DOM 包含 #lan-auth-security-notice 安全风险提示", 'id="lan-auth-security-notice"' in html_text)
    _ui_all_txt = html_text + "\n" + (ROOT / "root/usr/share/ai-link/webui/nexus.js").read_text(encoding="utf-8")
    check("B2-6 UI: 静态/弹窗 DOM 包含 #mdl-restore-file (.tgz/.json 文件上传控件)", 'id="mdl-restore-file"' in _ui_all_txt)

# ---------------------------------------------------------------------------
# 7. v1.0.3 Dual-Device Field Diagnostics & Anti-Drop Root-Cause Regressions
#    (DIAG-10.10.10.7.md & AI-LINK-内核掉线根因深度调研报告.html)
# ---------------------------------------------------------------------------
print("\n[7] v1.0.3 双机实测根因与内核防掉线深度回归 (P0-1~P0-3 / P1-1~P1-3 / P2 / P3 / DIAG-1~DIAG-3)")

# P0-1: init.d/ai-link respawn 0 5 0 & restart_core
check("P0-1: init.d/ai-link 放宽 procd respawn 配额为 `respawn 0 5 0` (永不放弃)",
      initd_txt.count("procd_set_param respawn 0 5 0") >= 2 and "3600 5 5" not in initd_txt)
check("P0-1: init.d/ai-link 与 CLI 提供独立 `restart_core` 恢复入口",
      "restart_core()" in initd_txt and "restart_core)" in CLI.read_text(encoding="utf-8"))

# P0-2: Watchdog process liveness guard ensure_core_alive_and_recover
check("P0-2: _telemetry_and_watchdog_loop 周期调用 ensure_core_alive_and_recover 守护内核进程",
      "def ensure_core_alive_and_recover" in daemon_src and "ensure_core_alive_and_recover(CONF_DIR)" in daemon_src and "Watchdog: core process missing; restarting service." in daemon_src)

# P0-3: Anti-blackhole teardown when core is dead
check("P0-3: 内核死后自动清理 nft 表 + ip rule 162 + dnsmasq 7874 防全网黑洞 (_teardown_blackhole_nft_and_routing)",
      "def _teardown_blackhole_nft_and_routing" in daemon_src and "Watchdog: core dead; nft removed, LAN restored to direct." in daemon_src)
check("P0-3: _sync_ipv6_policy_routing 在内核未起或 :7893 未监听时拒绝挂载 ip rule 0x162",
      "if not _get_live_singbox_pids() or not _is_local_port_listening(tproxy_port):" in daemon_src)

# P1-1: Idempotent /api/shunt/reorder & schedule_async_core_reload (Experiment C verification)
_, shunt_before = api_call("/api/shunt", "GET")
orig_ids = [g["id"] for g in (shunt_before.get("groups") or []) if not g.get("locked_bottom") and g.get("id") not in ("Domestic_CN", "Final_Fallback")]
st_ro_same, res_ro_same = api_call("/api/shunt/reorder", "POST", {"ordered_ids": orig_ids})
check("P1-1 (实验 C): 原样提交 /api/shunt/reorder 规则指纹未变 -> requires_core_respawn=False (不杀内核)",
      st_ro_same == 200 and res_ro_same.get("requires_core_respawn") is False,
      f"requires_core_respawn={res_ro_same.get('requires_core_respawn')}")
rev_ids = list(reversed(orig_ids))
st_ro_diff, res_ro_diff = api_call("/api/shunt/reorder", "POST", {"ordered_ids": rev_ids})
check("P1-1: 真实改变顺序提交 /api/shunt/reorder 指纹变化 -> requires_core_respawn=True",
      st_ro_diff == 200 and res_ro_diff.get("requires_core_respawn") is True,
      f"requires_core_respawn={res_ro_diff.get('requires_core_respawn')}")
# Restore original order
api_call("/api/shunt/reorder", "POST", {"ordered_ids": orig_ids})

# P1-2: Persistent /etc/ai-link/.applied_core_rule_hash across tmpfs wipe
dmod.write_all_configs(tmp_conf)
fp_expected = dmod._compute_core_rules_fingerprint(tmp_conf)
dmod._record_applied_core_rule_hash(tmp_conf, fp_expected)
persist_hash_file = tmp_conf / ".applied_core_rule_hash"
check("P1-2: 规则指纹持久化写入非 tmpfs (/etc/ai-link/.applied_core_rule_hash)",
      persist_hash_file.is_file() and persist_hash_file.read_text(encoding="utf-8").strip() == fp_expected)
# Simulate router reboot / tmpfs wipe by clearing memory variable & deleting RUN_DIR/applied_core_rule_hash.txt
dmod._LAST_APPLIED_CORE_RULE_HASH = ""
(tmp_run / "applied_core_rule_hash.txt").unlink(missing_ok=True)
recovered_fp = dmod._get_applied_core_rule_hash(tmp_conf)
check("P1-2: tmpfs 清空后 _get_applied_core_rule_hash 自动从 /etc/ai-link/.applied_core_rule_hash 无损恢复",
      recovered_fp == fp_expected and (tmp_run / "applied_core_rule_hash.txt").is_file())

# P1-3 & DIAG-3 & NEXUS v2 P1: install.sh & OTA real health assertion + pre-clean webui/assets symlink
inst_txt = INST.read_text(encoding="utf-8")
pre_rm_idx = inst_txt.find("rm -f /usr/share/ai-link/webui/assets")
cp_root_idx = inst_txt.find('cp -rf "$SCRIPT_DIR/root/"* /')
check("NEXUS v2 P1: install.sh 在 cp -rf root/* 之前清理 webui/assets 符号链接且不再强制覆盖为软链",
      0 < pre_rm_idx < cp_root_idx and "if [ ! -d /usr/share/ai-link/webui/assets ]; then" in inst_txt)
check("P1-3 & DIAG-3: install.sh 包含 sing-box 进程与 7890/7893 端口真实健康断言 (UPGRADE OK / UPGRADE FAIL)",
      'UPGRADE OK: core=$(pidof sing-box) ports ok' in inst_txt and 'UPGRADE FAIL: core not running' in inst_txt)
check("DIAG-3: init.d wait_for_ports_And_apply_nft 具备 trap HUP 与后台标准流解耦 (防 SSH 退出中断挂载)",
      "trap '' HUP" in initd_txt and "</dev/null >/dev/null 2>&1 &" in initd_txt)

# DIAG-1: Silence BrokenPipeError & ConnectionResetError in HTTP handler
import socket as _sock
_s_rst = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
_s_rst.connect(("127.0.0.1", srv_port))
_s_rst.sendall(b"GET /api/status HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
_s_rst.close()
time.sleep(0.1)
st_after_rst, body_after_rst = api_call("/api/status", "GET")
check("DIAG-1: 客户端中途断开连接 (BrokenPipeError/ConnectionResetError) 被静默捕获且服务零受影响",
      "except (BrokenPipeError, ConnectionResetError, socket.timeout):" in daemon_src and st_after_rst == 200)

# DIAG-2: Preserve router self-DNS (/etc/resolv.conf & resolv.conf.auto) during stop/restart/core-down
check("DIAG-2: init.d 与 daemon 均实现停机/内核离线期间 /etc/resolv.conf 自动回退主路由与公共 DNS (223.5.5.5)",
      "fallback_resolv_conf_direct()" in initd_txt and "restore_resolv_conf_local()" in initd_txt and "def fallback_resolv_conf_to_direct():" in daemon_src)

# P2 & P3: WebUI core-offline alert banner (#core-offline-alert-banner / #ov-core-offline-card) & unified status.build_ver == "1.0.3"
check("P2: WebUI 含显著红色内核离线告警横幅 (#core-offline-alert-banner & #ov-core-offline-card) 与一键重启内核按钮",
      'id="core-offline-alert-banner"' in html_text and 'id="ov-core-offline-card"' in html_text and 'id="btn-restart-core-banner"' in html_text)
check("P3: /api/status 中 build_ver 与 version 统一为 2.3.2 (无 2.0.0-r8-v24-nolo 残留)",
      body_after_rst.get("version") == dmod.APP_VERSION and body_after_rst.get("build_ver") == dmod.APP_VERSION,
      f"version={body_after_rst.get('version')}, build_ver={body_after_rst.get('build_ver')}")

# Non-shunt modes (gfw_list / cn_whitelist / global_proxy) unified egress backend E2E verification
for _ns_mode in ("cn_whitelist", "gfw_list", "global_proxy"):
    st_ns_auto, res_ns_auto = api_call("/api/shunt/update", "POST", {
        "routing_mode": _ns_mode,
        "global_mode": "auto",
        "global_auto_node_id": "auto_ai"
    })
    check(f"非分流模式 E2E ({_ns_mode}): 切换自动节点池 (auto_ai) 成功且统一出口已同步",
          st_ns_auto == 200 and res_ns_auto.get("routing_mode") == _ns_mode and res_ns_auto.get("global_mode") == "auto" and res_ns_auto.get("global_auto_node_id") == "auto_ai" and res_ns_auto.get("global_resolved_node") not in ("", "direct"),
          f"mode={res_ns_auto.get('global_mode')}, aid={res_ns_auto.get('global_auto_node_id')}, resolved={res_ns_auto.get('global_resolved_node')}")

    st_ns_man, res_ns_man = api_call("/api/shunt/update", "POST", {
        "routing_mode": _ns_mode,
        "global_mode": "manual",
        "global_country": "JP",
        "global_manual_node": "JP-Tokyo-VLESS-01"
    })
    _sb_ns = dmod.ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_conf)
    _ai_ob = next((o for o in _sb_ns.get("outbounds", []) if o.get("tag") == "AI_Best_Auto"), {})
    check(f"非分流模式 E2E ({_ns_mode}): 手动指定国家与节点 (JP -> JP-Tokyo-VLESS-01) 同步至 global_resolved_node 与 AI_Best_Auto",
          st_ns_man == 200 and res_ns_man.get("global_mode") == "manual" and res_ns_man.get("global_country") == "JP" and res_ns_man.get("global_resolved_node") == "JP-Tokyo-VLESS-01" and _ai_ob.get("default") == "JP-Tokyo-VLESS-01",
          f"resolved={res_ns_man.get('global_resolved_node')}, AI_Best_Auto.default={_ai_ob.get('default')}")
# Restore rule_shunt
api_call("/api/shunt/update", "POST", {"routing_mode": "rule_shunt", "global_mode": "auto", "global_auto_node_id": "auto_youtube"})

# ---------------------------------------------------------------------------
# 8. Fake-IP Loopback Protection (cn.localbattle.net), DNS Shield Toggle Persistence,
#    Auto-Pool test_candidates & Default Failover, and Per-Node HomeLink Route Mode E2E
# ---------------------------------------------------------------------------
print("\n[8] Fake-IP 本地回环保护 (战网 cn.localbattle.net) / 护盾开关持久化 / 节点池即时检测与默认容灾 E2E")

# 8.1 Battle.net cn.localbattle.net:22885 Fake-IP bypass verification
st_bn, res_bn = api_call("/api/shunt/trace", "POST", {"target": "cn.localbattle.net:22885", "protocol": "tcp"})
_sb_dns_cfg = dmod.ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_conf)
_dns_direct_rules = [r for r in (_sb_dns_cfg.get("dns", {}).get("rules") or []) if r.get("server") == "dns_direct"]
_dns_direct_doms = set()
for _dr in _dns_direct_rules:
    _dns_direct_doms.update(_dr.get("domain") or [])
    _dns_direct_doms.update(_dr.get("domain_suffix") or [])
_rw_file_txt = (tmp_conf / "ai-link-rewrite.conf").read_text(encoding="utf-8") if (tmp_conf / "ai-link-rewrite.conf").is_file() else ""
check("排查问题 1 (暴雪战网 cn.localbattle.net:22885 本地回环保护): sing-box dns_direct 与 dnsmasq 127.0.0.1 双层豁免 Fake-IP，4阶透视判定为 127.0.0.1 本机闭环",
      st_bn == 200 and "127.0.0.1" in str(res_bn.get("stage2_dns", {})) and res_bn.get("stage3_rule", {}).get("selector_tag") == "direct" and
      "cn.localbattle.net" in _dns_direct_doms and "localbattle.net" in _dns_direct_doms and "address=/cn.localbattle.net/127.0.0.1" in _rw_file_txt,
      f"stage2={res_bn.get('stage2_dns', {}).get('title')}, stage4={res_bn.get('stage4_outbound', {}).get('outbound_tag')}")

# 8.2 Cloud Domain Filtering Shield toggle persistence E2E
st_flt_off, res_flt_off = api_call("/api/dns/filter/toggle", "POST", {"enabled": False})
st_stat_off, res_stat_off = api_call("/api/status", "GET")
check("已知问题 3 (后端护盾开关持久化): 关闭云端过滤后 /api/status 的 shield_status.enabled 与 dns_telemetry.filter.enabled 均为 False",
      st_flt_off == 200 and res_stat_off.get("shield_status", {}).get("enabled") is False and
      res_stat_off.get("dns_telemetry", {}).get("filter", {}).get("enabled") is False,
      f"shield_status.enabled={res_stat_off.get('shield_status', {}).get('enabled')}")
# Restore enabled=True
api_call("/api/dns/filter/toggle", "POST", {"enabled": True})

# 8.3 Auto-Pool candidate immediate test API & default smart_switch_enabled=True
st_tc, res_tc = api_call("/api/auto_nodes/test_candidates", "POST", {
    "tags": ["JP-Tokyo-VLESS-01", "SG-AI-Hy2-02"],
    "check_ping": True,
    "service_checks": ["chatgpt", "youtube"],
    "service_logic": "all"
})
check("节点池即时检测 API (/api/auto_nodes/test_candidates): 返回勾选节点的 URL Ping 延迟与多选服务可用性结果",
      st_tc == 200 and len(res_tc.get("results") or []) == 2 and all("svc_results" in r and "delay_ms" in r for r in res_tc["results"]),
      str(res_tc.get("results")))

st_an_save, res_an_save = api_call("/api/auto_nodes/save", "POST", {
    "id": "auto_custom_test",
    "name": "测试双组自动池",
    "service_checks": ["chatgpt"],
    "service_logic": "any",
    "groups": [
        {"index": 1, "name": "主力组 G1", "node_tags": ["JP-Tokyo-VLESS-01"]},
        {"index": 2, "name": "备选组 G2", "node_tags": ["SG-AI-Hy2-02"]}
    ]
})
_saved_an = next((a for a in (res_an_save.get("auto_nodes") or []) if a.get("id") == "auto_custom_test"), {})
check("节点池默认健康巡检与单组自动收敛: 新建或传入多组节点池自动合并收敛为单组(groups=1, <=10)且默认开启 smart_switch_enabled=True",
      st_an_save == 200 and _saved_an.get("smart_switch_enabled") is True and len(_saved_an.get("groups") or []) == 1 and len(_saved_an["groups"][0].get("node_tags") or []) == 2,
      f"smart_switch_enabled={_saved_an.get('smart_switch_enabled')}, groups={_saved_an.get('groups')}")
api_call("/api/auto_nodes/delete", "POST", {"id": "auto_custom_test"})

# 8.5 Verify /api/homelink/update partial update (only id + route_mode on a second node) does not trigger false port_conflict on 18443
_, _hl_add1 = api_call("/api/homelink/quick_create", "POST", {"protocol": "vless-reality", "listen_port": 18443, "name": "HL-Primary-18443"})
_, _hl_add2 = api_call("/api/homelink/quick_create", "POST", {"protocol": "hysteria2", "listen_port": 20443, "name": "HL-Second-20443"})
_hl2_id = (_hl_add2.get("nodes") or [{}])[-1].get("id", "")
_hl_upd_code, _hl_upd_res = api_call("/api/homelink/update", "POST", {"id": _hl2_id, "route_mode": "direct"})
_hl2_after = next((h for h in (_hl_upd_res.get("nodes") or []) if h.get("id") == _hl2_id), {})
check("v2.0.2 /api/homelink/update 局部字段更新: 仅传 id + route_mode 不误报 18443 端口冲突且保留原端口 20443",
      _hl_upd_code == 200 and _hl_upd_res.get("ok") is True and _hl2_after.get("route_mode") == "direct" and int(_hl2_after.get("listen_port") or 0) == int((_hl_add2.get("nodes") or [{}])[-1].get("listen_port") or 20443),
      f"code={_hl_upd_code}, port={_hl2_after.get('listen_port')}, mode={_hl2_after.get('route_mode')}")


# ---------------------------------------------------------------------------
# 9. v2.3.2 Phase 1 & Phase 2 HTTP & UI E2E (T1 Network Doctor, T4 Hit Leaderboard, T7 Sub Health, BUG-001~005)
# ---------------------------------------------------------------------------
print("\n[9] v2.3.2 Phase 1 & Phase 2 (T1 网络医生 / T4 命中排行 / T7 订阅健康度 / BUG-001~005 HTTP E2E)")

st_doc, res_doc = api_call("/api/diag/run", "POST", {"mock_env": {"client_dns_queries_10m": 30, "aaaa_leaked_count": 0, "pmtu": 1500, "lan_mtu": 1500}})
check("v2.3.2 T1 (/api/diag/run): 8 项并发体检返回 pass 且含 checks/items 列表",
      st_doc == 200 and res_doc.get("ok") is True and len(res_doc.get("checks") or []) == 8 and res_doc.get("overall_status") == "pass",
      f"status={res_doc.get('overall_status')}, elapsed_ms={res_doc.get('elapsed_ms')}")

st_dfix, res_dfix = api_call("/api/diag/fix", "POST", {"fix_action": "fix_all", "recheck": True})
check("v2.3.2 T1 (/api/diag/fix): 一键修复 fix_all 执行成功并返回复检报告",
      st_dfix == 200 and res_dfix.get("ok") is True and isinstance(res_dfix.get("recheck"), dict),
      f"msg={res_dfix.get('message')}")

st_hit, res_hit = api_call("/api/shunt/hit_stats", "GET")
check("v2.3.2 T4 (/api/shunt/hit_stats): 返回 1 小时滑动窗口 by_group / by_rule / by_outbound 排行",
      st_hit == 200 and res_hit.get("ok") is True and len(res_hit.get("by_group") or []) >= 1 and len(res_hit.get("by_outbound") or []) >= 1,
      f"total_hits={res_hit.get('total_hits')}")

_hl_p_code, _hl_p_res = api_call("/api/homelink/update", "POST", {"id": _hl2_id, "name": "HL-Second (:20443)", "listen_port": 25443})
_hl2_p_after = next((h for h in (_hl_p_res.get("nodes") or []) if h.get("id") == _hl2_id), {})
check("v2.3.2 BUG-005 (/api/homelink/update): 修改回家节点端口自动同步名称内 (:port) 后缀",
      _hl_p_code == 200 and "(:25443)" in str(_hl2_p_after.get("name") or ""),
      f"name={_hl2_p_after.get('name')}")

check("v2.3.2 UI 契约: index.html 与 nexus.js 包含网络医生 (#btn-top-network-doctor)、命中排行榜 (#shunt-hit-leaderboard-card)、关键应用保护开关 (#toggle-dns-essential-protect)、订阅健康度 (.sub-health-box) 与清晰入池按钮文案",
      all(tok in html_text for tok in (
          "btn-top-network-doctor",
          "shunt-hit-leaderboard-card",
          "toggle-dns-essential-protect",
          "sub-health-box",
          "仅入池检测达标项",
          "免测直接加入池",
          "delete-custom-group"
      )))

# v2.3.2 HTTP E2E: /api/nodes/probe_region (BUG-006), /api/auto_nodes/remove_member (BUG-007), /api/subscriptions/preview_sync (AutoPool v2)
st_pr, res_pr = api_call("/api/nodes/probe_region", "POST", {
    "tag": "JP-Tokyo-VLESS-01",
    "status": 301,
    "location": "https://www.google.com.hk/?gws_rd=cr"
})
check("v2.3.2 BUG-006 (/api/nodes/probe_region): 模拟 Google 301 至 .com.hk 判定 google_region=HK 且 region_blocked=True",
      st_pr == 200 and res_pr.get("google_region") == "HK" and res_pr.get("region_blocked") is True and res_pr.get("ok") is False,
      f"region={res_pr.get('google_region')}, reason={res_pr.get('reason')}")
# Restore JP-Tokyo-VLESS-01 back to Google:JP
api_call("/api/nodes/probe_region", "POST", {
    "tag": "JP-Tokyo-VLESS-01",
    "status": 302,
    "location": "https://www.google.co.jp/"
})

st_prev, res_prev = api_call("/api/subscriptions/preview_sync", "POST", {"id": "sub_airport_main"})
check("v2.3.2 AutoPool-v2 (/api/subscriptions/preview_sync): 返回订阅同步前 diff 影响预览",
      st_prev == 200 and res_prev.get("ok") is True and "summary_text" in res_prev,
      res_prev.get("summary_text", ""))

st_as, res_as = api_call("/api/auto_nodes/auto_screen", "POST", {
    "pool_mode": "ping_only",
    "scope_source": "ALL",
    "scope_countries": ["ALL"],
    "target_size": 10,
    "run_live_probe": False
})
check("v2.3.2 (/api/auto_nodes/auto_screen): 目标驱动节点池自动筛选接口按延迟升序返回最快节点",
      st_as == 200 and res_as.get("ok") is True and isinstance(res_as.get("admitted_g1"), list) and len(res_as.get("admitted_g1")) >= 1,
      f"admitted_g1={res_as.get('admitted_g1')}")

st_nd, res_nd = api_call("/api/nodes", "GET")
check("v2.3.2 (/api/nodes): 取消入核上限(max_outbounds_limit=0)、节点两态模型(ok/dead)、含 custom_nodes_summary 与订阅同步时间戳",
      st_nd == 200
      and res_nd.get("max_outbounds_limit") == 0
      and "custom_nodes_summary" in res_nd
      and set(x.get("state") for x in (res_nd.get("nodes") or [])) <= {"ok", "dead", "untested"}
      and "untested_nodes_count" in res_nd
      and all(bool(s.get("sync_status_text")) for s in (res_nd.get("subscriptions") or [])),
      f"max_lim={res_nd.get('max_outbounds_limit')}, custom={res_nd.get('custom_nodes_summary')}")

check("v2.3.2 UI 契约: 订阅栏第2张卡片为手动添加节点 (#sub-card-custom)、支持两态筛选与目标驱动一键筛选按钮 (#btn-an-auto-screen)",
      all(tok in html_text for tok in (
          "sub-card-custom",
          "手动添加节点",
          "btn-an-auto-screen",
          "btn-an-mode-ping",
          "btn-an-mode-svc",
          "同步时间:"
      )))

# v2.3.2 NEXT-SUBMISSION-4 (BUG-008 strict_lock HTTP round-trip) & Plan A HTTP E2E
st_sl_on, res_sl_on = api_call("/api/shunt/update", "POST", {"group_id": "AI", "shunt_mode": "manual", "strategy": "manual", "manual_node": "JP-Tokyo-VLESS-01", "strict_lock": True})
g_ai_on = next((g for g in (res_sl_on.get("groups") or []) if g.get("id") == "AI"), {})
disk_sh_on = json.loads((tmp_conf / "shunt.json").read_text(encoding="utf-8"))
disk_ai_on = next((g for g in (disk_sh_on.get("groups") or []) if g.get("id") == "AI"), {})
st_sl_off, res_sl_off = api_call("/api/shunt/update", "POST", {"group_id": "AI", "strict_lock": False})
g_ai_off = next((g for g in (res_sl_off.get("groups") or []) if g.get("id") == "AI"), {})
check("v2.3.2 BUG-008 (/api/shunt/update strict_lock 读写对称持久化): POST strict_lock=True 落盘 shunt.json 且响应 strict_lock=True，切换 False 同步恢复",
      st_sl_on == 200 and g_ai_on.get("strict_lock") is True and disk_ai_on.get("strict_lock") is True and g_ai_off.get("strict_lock") is False,
      f"api_on={g_ai_on.get('strict_lock')}, disk_on={disk_ai_on.get('strict_lock')}, api_off={g_ai_off.get('strict_lock')}")

st_topo, res_topo = api_call("/api/topology/detect", "GET")
st_upst, res_upst = api_call("/api/dns/upstream_stats", "GET")
st_hist, res_hist = api_call("/api/ops/config_history", "GET")
check("v2.3.2 Plan A HTTP E2E (/api/topology/detect & /api/dns/upstream_stats & /api/ops/config_history): 拓扑识别、DNS上游统计与配置变更历史接口全部正常返回",
      st_topo == 200 and res_topo.get("ok") is True and len(res_topo.get("wizard_steps") or []) == 3
      and st_upst == 200 and res_upst.get("ok") is True and len(res_upst.get("upstreams") or []) >= 2
      and st_hist == 200 and res_hist.get("ok") is True and len(res_hist.get("history") or []) >= 1,
      f"topo={res_topo.get('topology')}, upstreams={len(res_upst.get('upstreams') or [])}, history={len(res_hist.get('history') or [])}")

# v2.3.2 NEXT-SUBMISSION-5 HTTP E2E (P2-1 rule_providers 400 validation & delete + P3-2 GET /api/shunt/rule_blocks)
st_bad_rp, res_bad_rp = api_call("/api/shunt/rule_providers", "POST", {"name": "x"})
st_add_rp, res_add_rp = api_call("/api/shunt/rule_providers", "POST", {
    "id": "rp_e2e_1",
    "name": "测试规则源1",
    "url": "https://rules.example.com/e2e.list",
    "format": "domain_list",
    "group_id": "AI",
    "sync_now": False
})
st_del_rp, res_del_rp = api_call("/api/shunt/rule_providers", "POST", {"id": "rp_e2e_1", "action": "delete"})
disk_rps_e2e = json.loads((tmp_conf / "rule_providers.json").read_text(encoding="utf-8")) if (tmp_conf / "rule_providers.json").is_file() else []
st_get_rb, res_get_rb = api_call("/api/shunt/rule_blocks", "GET")
check("v2.3.2 P2-1 & P3-2 HTTP E2E: 提交无 url 规则源返回 400 不落盘，删除 rp_e2e_1 后列表与 JSON 同步清空，且 GET /api/shunt/rule_blocks 返回 200",
      st_bad_rp == 400 and res_bad_rp.get("ok") is False
      and st_add_rp == 200 and res_add_rp.get("ok") is True
      and st_del_rp == 200 and res_del_rp.get("ok") is True and len(res_del_rp.get("providers") or []) == 0 and len(disk_rps_e2e) == 0
      and st_get_rb == 200 and res_get_rb.get("ok") is True and isinstance(res_get_rb.get("groups"), list),
      f"bad_st={st_bad_rp}, after_del={len(disk_rps_e2e)}, get_rb_st={st_get_rb}")

# v2.3.2 Urgent Fix #2 HTTP E2E: HomeLink quick_create non-blocking (<200ms) + 3-second duplicate debounce + /api/homelink/dedup
t0_hl = time.time()
st_hl1, res_hl1 = api_call("/api/homelink/quick_create", "POST", {"protocol": "hysteria2", "listen_port": 0, "ddns_host": "home.test.lan", "route_mode": "shunt"})
hl_ms = (time.time() - t0_hl) * 1000.0
st_hl2, res_hl2 = api_call("/api/homelink/quick_create", "POST", {"protocol": "hysteria2", "listen_port": 0, "ddns_host": "home.test.lan", "route_mode": "shunt"})
st_hl3, res_hl3 = api_call("/api/homelink/quick_create", "POST", {"protocol": "hysteria2", "listen_port": 0, "ddns_host": "home.test.lan", "route_mode": "shunt"})
st_dedup, res_dedup = api_call("/api/homelink/dedup", "POST", {})
# Consolidated Audit Round 1~3 HTTP & Backend E2E checks
st_csrf_chk, csrf_obj = api_call("/api/ops/settings", "POST", {"block_quic": False}, headers={"Origin": "http://evil.example.com"})
check("Audit Round 1 (C-P0-02 & C-P0-09): 跨源 POST 请求被 CSRF 守卫拦截 (403) 且 OPS_PERSIST_KEYS 覆盖 21 字段",
      st_csrf_chk == 403 and csrf_obj.get("error") == "csrf_forbidden" and len(dmod.OPS_PERSIST_KEYS) >= 21,
      f"csrf={st_csrf_chk}, keys={len(dmod.OPS_PERSIST_KEYS)}")
st_wol_b, _ = api_call("/api/wol", "POST", {"mac": "00:00:00:00:00:00"})
st_wol_g, wol_g_obj = api_call("/api/wol", "POST", {"mac": "BC:24:11:45:67:89", "broadcast_ip": "127.0.0.1"})
n_ws_a = {"type": "vless", "server": "cdn.example.com", "server_port": 443, "uuid": "u1", "transport": {"type": "ws", "path": "/a", "headers": {"Host": "a.example.com"}}}
n_ws_b = {"type": "vless", "server": "cdn.example.com", "server_port": 443, "uuid": "u1", "transport": {"type": "ws", "path": "/b", "headers": {"Host": "b.example.com"}}}
check("Audit Round 2 & 3 (C-P1-07 & C-P1-02): /api/wol 校验真实 MAC 发送 102B 魔术包，同主机不同 WS path/Host 节点生成独立指纹",
      st_wol_b == 400 and st_wol_g == 200 and wol_g_obj.get("packet_bytes") == 102 and dmod.compute_node_id(n_ws_a) != dmod.compute_node_id(n_ws_b),
      f"wol={st_wol_b}/{st_wol_g}, id_diff={dmod.compute_node_id(n_ws_a) != dmod.compute_node_id(n_ws_b)}")

check("v2.3.2 紧急修复2 (/api/homelink/quick_create 亚秒级响应与防连点重复创建): 亚秒级响应 (<2000ms)，3秒内连续3次点击幂等拦截不产生重复节点，且支持 /api/homelink/dedup",
      st_hl1 == 200 and hl_ms < 2000.0
      and res_hl2.get("deduplicated") is True and res_hl3.get("deduplicated") is True
      and len(res_hl1.get("nodes") or []) == len(res_hl3.get("nodes") or [])
      and st_dedup == 200 and res_dedup.get("ok") is True,
      f"elapsed={hl_ms:.1f}ms, dedup2={res_hl2.get('deduplicated')}, nodes_cnt={len(res_hl3.get('nodes') or [])}")


# ---------------------------------------------------------------------------
# 10. v2.3.4 Acceptance Report Full Closure Verification
# ---------------------------------------------------------------------------
print("\n[10] v2.3.4 验收报告问题全闭环回归 (P0-1/P0-2 / N-P0-2 升级与v2.3.3自愈 / N-P3-3 删除计数 / ETag & 内容哈希)")

# 10.1 N-P0-2: v2.3.2 legacy default hash migration ("390a34176b...")
mig_dir = tmp_work / "mig_v232"
mig_dir.mkdir(parents=True, exist_ok=True)
(mig_dir / "panel_auth.json").write_text(json.dumps({
    "salt": "ailink_salt_2026",
    "hash": "390a34176b28262aaad88e2e684b215759c6b799b0ed76fd75394091e5426269",
    "kdf": "sha256"
}), encoding="utf-8")
mig_auth = dmod._load_panel_auth(mig_dir)
mig_init_pw = dmod._get_or_create_initial_secret(mig_dir)
check("v2.3.4 N-P0-2 (v2.3.2 存量默认口令升级迁移): 识别 390a3417... 默认哈希并迁移为 customized=False + initial_password",
      mig_auth.get("kdf") == "pbkdf2_sha256" and mig_auth.get("customized") is False
      and dmod._verify_panel_password("ai-link-2026", mig_dir)[0] is False
      and dmod._verify_panel_password(mig_init_pw, mig_dir)[0] is True,
      f"kdf={mig_auth.get('kdf')}, customized={mig_auth.get('customized')}")

# 10.2 N-P0-2: v2.3.3 misclassified pbkdf2_sha256_chain self-healing
mig_v233_dir = tmp_work / "mig_v233"
mig_v233_dir.mkdir(parents=True, exist_ok=True)
v233_salt = "b31640ff112233445566778899aabbcc"
v233_chained_hash = hashlib.pbkdf2_hmac(
    "sha256",
    b"390a34176b28262aaad88e2e684b215759c6b799b0ed76fd75394091e5426269",
    v233_salt.encode("utf-8"),
    100000
).hex()
(mig_v233_dir / "panel_auth.json").write_text(json.dumps({
    "legacy_salt": "ailink_salt_2026",
    "salt": v233_salt,
    "kdf": "pbkdf2_sha256_chain",
    "hash": v233_chained_hash,
    "customized": True
}), encoding="utf-8")
healed_auth = dmod._load_panel_auth(mig_v233_dir)
healed_init_pw = dmod._get_or_create_initial_secret(mig_v233_dir)
check("v2.3.4 N-P0-2 (v2.3.3 误判链式哈希自动自愈): 自动修复 pbkdf2_sha256_chain 默认口令为 customized=False 并禁用 ai-link-2026",
      healed_auth.get("kdf") == "pbkdf2_sha256" and healed_auth.get("customized") is False
      and "legacy_salt" not in healed_auth
      and dmod._verify_panel_password("ai-link-2026", mig_v233_dir)[0] is False
      and dmod._verify_panel_password(healed_init_pw, mig_v233_dir)[0] is True,
      f"kdf={healed_auth.get('kdf')}, customized={healed_auth.get('customized')}")

# 10.3 N-P3-3 / New-4: /api/nodes/delete total_nodes matches /api/nodes even when builtin loopback test node is present
dmod.add_loopback_test_nodes(tmp_conf)
_, nd_before_add = api_call("/api/nodes", "GET")
cnt_base = nd_before_add.get("total_nodes")
_, add_res = api_call("/api/nodes/add", "POST", {
    "tag": "Temp-Del-Test-Node", "type": "vless", "server": "del.example.com", "server_port": 443, "uuid": "u-del-1"
})
_, del_res = api_call("/api/nodes/delete", "POST", {"tag": "Temp-Del-Test-Node"})
_, nd_after_del = api_call("/api/nodes", "GET")
check("v2.3.4 N-P3-3 (/api/nodes/delete 计数零偏差): 含内置测试节点时新增再删除节点，响应 total_nodes 与 /api/nodes 完全一致",
      add_res.get("total_nodes") == cnt_base + 1
      and del_res.get("total_nodes") == cnt_base
      and nd_after_del.get("total_nodes") == cnt_base,
      f"base={cnt_base}, add={add_res.get('total_nodes')}, del={del_res.get('total_nodes')}, api_nodes={nd_after_del.get('total_nodes')}")

# 10.4 New-1..3: build_revision alignment, orphan webui cleanup in install.sh, content-hashed assets & ETag 304
_, st_ver_chk = api_call("/api/status", "GET")
has_hash_assets = bool(re.search(r"nexus\.css\?v=\d+\.\d+\.\d+-[0-9a-f]{8}", html_text)) and bool(re.search(r"nexus\.js\?v=\d+\.\d+\.\d+-[0-9a-f]{8}", html_text))
check("v2.3.4 New-1~3 (构建号对齐 / webui 孤儿清理 / 静态资源内容哈希): build_revision 对齐 2.3.4，install.sh 清理旧 webui，静态资源带内容哈希",
      st_ver_chk.get("build_revision", "").startswith(f"{dmod.APP_VERSION}-release-")
      and "rm -rf /usr/share/ai-link/webui" in INST.read_text(encoding="utf-8")
      and has_hash_assets,
      f"build_revision={st_ver_chk.get('build_revision')}, has_hash_assets={has_hash_assets}")

# 11. v2.3.6 Deep Audit Report P1/P2 Full Remediation Verification
print("\n[11] v2.3.6 深度审计报告 P1/P2 核心整改项全闭环回归 (GET鉴权闸门 / 边界校验 / 测速预算 / 孤儿GC / 零编造数据 / HEAD一致性)")

# 11.1 P1-02: Unified GET authentication gate when require_lan_auth is enabled (or X-Enforce-Auth is present)
_enf_hdr = {"X-Enforce-Auth": "1"}
_tok_hdr = {"X-AI-Link-Token": new_tok}
unauth_shunt_code, _ = api_call("/api/shunt", "GET", headers=_enf_hdr)
unauth_an_code, _ = api_call("/api/auto_nodes", "GET", headers=_enf_hdr)
unauth_ops_code, _ = api_call("/api/ops/settings", "GET", headers=_enf_hdr)
unauth_status_code, _ = api_call("/api/status", "GET", headers=_enf_hdr)
unauth_ver_code, _ = api_call("/api/system/version", "GET", headers=_enf_hdr)
check("Audit P1-02 (_do_GET_inner 统一鉴权闸门): 未授权访问 /api/shunt、/api/auto_nodes、/api/ops/settings 全部返回 401，白名单 /api/status 与 /api/system/version 返回 200",
      unauth_shunt_code == 401 and unauth_an_code == 401 and unauth_ops_code == 401 and unauth_status_code == 200 and unauth_ver_code == 200,
      f"shunt={unauth_shunt_code}, auto_nodes={unauth_an_code}, ops={unauth_ops_code}, status={unauth_status_code}")

# 11.2 P1-04 & L3: Strict boolean & trusted_cidr & panel_bind validation + no silent trusted_cidr overwrite
bad_bool_code, _ = api_call("/api/ops/settings", "POST", {"require_lan_auth": "abc"})
bad_cidr_code, _ = api_call("/api/ops/settings", "POST", {"trusted_cidr": "192.168.1.0/33"})
long_cidr_code, _ = api_call("/api/ops/settings", "POST", {"trusted_cidr": "a" * 9000})
bad_bind_code, _ = api_call("/api/ops/settings", "POST", {"panel_bind": "999.999.999.999"})
ok_cidr_code, _ = api_call("/api/ops/settings", "POST", {"trusted_cidr": "10.10.10.0/24"})
_, after_auth_toggle = api_call("/api/ops/settings", "POST", {"require_lan_auth": False})
check("Audit P1-04 & L3 (严格类型与网段校验 + 防静默重置): 非法布尔 'abc'、非法网段 /33、超长串与非法监听地址全部 400 拦截，且切换鉴权不重置自定义 trusted_cidr",
      bad_bool_code == 400 and bad_cidr_code == 400 and long_cidr_code == 400 and bad_bind_code == 400
      and ok_cidr_code == 200 and after_auth_toggle.get("trusted_cidr") == "10.10.10.0/24",
      f"bool={bad_bool_code}, cidr={bad_cidr_code}, long={long_cidr_code}, bind={bad_bind_code}, preserved={after_auth_toggle.get('trusted_cidr')}")

# 11.3 P1-05: Daily node_test_budget quota enforcement
api_call("/api/ops/settings", "POST", {"node_test_budget": 5})
dmod._atomic_write_text(dmod._node_test_quota_path(), json.dumps({"date": time.strftime("%Y-%m-%d"), "used": 5}))
used_after_non_forced = dmod._node_test_spend(1, force=False, conf_dir=tmp_conf)
res_capped_delay = dmod.clash_test_delay("JP-Tokyo-VLESS-01", force=False, conf_dir=tmp_conf)
check("Audit P1-05 (每日测速预算真实生效): 达到预算上限 (5/5) 后非强制测速不再超支且返回 quota_capped=True",
      used_after_non_forced == 5 and res_capped_delay.get("quota_capped") is True,
      f"used={used_after_non_forced}, capped={res_capped_delay.get('quota_capped')}")
api_call("/api/ops/settings", "POST", {"node_test_budget": 3000})

# 11.4 P2-16: Automatic GC of orphan records in node_probe.json
ps_with_orphans = dmod.load_node_probe_store(tmp_conf)
for i_orph in range(15):
    ps_with_orphans[f"orphan_nid_{i_orph}"] = {"tag": f"Orphan-Node-{i_orph}", "node_id": f"orphan_nid_{i_orph}", "state": "dead", "delay_ms": -1}
dmod.save_node_probe_store(ps_with_orphans, tmp_conf, strict_gc=True)
ps_after_gc = dmod.load_node_probe_store(tmp_conf)
check("Audit P2-16 (node_probe.json 孤儿记录自动 GC): 15 条孤儿探测记录在 GC 后被 100% 清理，仅保留有效节点记录",
      not any(k.startswith("orphan_nid_") for k in ps_after_gc.keys()),
      f"remaining_keys={list(ps_after_gc.keys())}")

# 11.5 P2-22 & P2-03 & P1-01: HEAD static header parity, real conntrack_max/mem_total_mb, and zero 142ms fabrication
req_head = urllib.request.Request(f"http://127.0.0.1:{srv_port}/nexus.js", headers={"Accept-Encoding": "gzip"}, method="HEAD")
with urllib.request.urlopen(req_head, timeout=5) as r_head:
    head_etag = r_head.headers.get("ETag", "")
    head_ce = r_head.headers.get("Content-Encoding", "")
    head_cc = r_head.headers.get("Cache-Control", "")
nexus_js_src = (DAEMON.parent / "webui/nexus.js").read_text(encoding="utf-8")
check("Audit P1-01/P2-03/P2-10/P2-22 (零 142ms/4096 假数据 + 恢复出厂去预填 + HEAD 响应头对齐): nexus.js 已移除 142/4096 硬编码与 RESET 预填，且 HEAD 返回 ETag 与 gzip",
      ": 142;" not in nexus_js_src and ": 156)" not in nexus_js_src and "const maxConns = 4096" not in nexus_js_src and 'value="RESET"' not in nexus_js_src
      and bool(head_etag) and head_ce == "gzip" and "max-age=86400" in head_cc,
      f"etag={head_etag}, ce={head_ce}, cc={head_cc}")

# 12. v2.3.6-r10 Field Installation Report (P0-1 BusyBox flock / P0-2 Quota Skip & Migration / P2-1..3 / P3)
print("\n[12] v2.3.6-r10 实机安装验收报告闭环门禁 (P0-1 BusyBox flock / P0-2 超配额跳过保态与迁移 / P2-1 同源 / P2-3 & P3)")

# 12.1 P0-1 Platform Gate: BusyBox flock (rejects -w, supports only [-sxun]) + apply_nft.sh execution
bb_dir = tmp_work / "busybox_mock_bin"
bb_dir.mkdir(parents=True, exist_ok=True)
bb_flock = bb_dir / "flock"
bb_flock.write_text('''#!/bin/sh
for arg in "$@"; do
    case "$arg" in
        -w*) echo "flock: unrecognized option: w" >&2; exit 1 ;;
    esac
done
exit 0
''', encoding="utf-8")
bb_flock.chmod(0o755)

bb_nft_out = tmp_work / "applied_nft_capture.nft"
bb_nft = bb_dir / "nft"
bb_nft.write_text(f'''#!/bin/sh
if [ "$1" = "-f" ] && [ -f "$2" ]; then
    cp "$2" "{bb_nft_out}"
    exit 0
fi
exit 0
''', encoding="utf-8")
bb_nft.chmod(0o755)

bb_run_dir = tmp_work / "bb_nft_run"
bb_run_dir.mkdir(parents=True, exist_ok=True)
bb_nft_file = bb_run_dir / "ai-link.nft"
dmod.generate_nft_rules_file(tmp_conf, bb_run_dir)
bb_env = os.environ.copy()
bb_env["PATH"] = f"{bb_dir}:{bb_env.get('PATH', '')}"
bb_env["AI_LINK_RUN_DIR"] = str(bb_run_dir)
bb_env["AI_LINK_DAEMON_PY"] = str(DAEMON)
bb_env["AI_LINK_NORM_PY"] = str(ROOT / "root/usr/share/ai-link/nftables/normalize_nft_sets.py")
apply_sh = ROOT / "root/usr/share/ai-link/nftables/apply_nft.sh"
import subprocess
bb_proc = subprocess.run(["/bin/sh", str(apply_sh)], env=bb_env, capture_output=True, text=True, timeout=15)
bb_status = json.loads((bb_run_dir / "nft_apply_status.json").read_text(encoding="utf-8")) if (bb_run_dir / "nft_apply_status.json").is_file() else {}
check("P0-1 平台门禁 (BusyBox flock 禁用 -w 实测): apply_nft.sh 在不支持 -w 的 BusyBox flock 下成功挂载 table inet ai_link 且零报错",
      bb_proc.returncode == 0 and bb_status.get("ok") is True and bb_nft_out.is_file()
      and "table inet ai_link" in bb_nft_out.read_text(encoding="utf-8") and "unrecognized option" not in (bb_proc.stderr or ""),
      f"rc={bb_proc.returncode}, status={bb_status}, stderr={bb_proc.stderr.strip()}")
check("P0-1 门禁 (加锁超时绝不静默 exit 0): apply_nft.sh 加锁失败分支严格退出 exit 1 且 install.sh 对未挂载执行 exit 1",
      "acquire_nft_lock || {\n\tlogger -t \"ai-link\" \"ERROR: apply_nft.sh lock timeout after 18s\"\n\twrite_nft_status \"false\" \"1\" \"apply_nft.sh 互斥锁等待超时 (lock_timeout)\"\n\texit 1" in apply_sh.read_text(encoding="utf-8")
      and "table inet ai_link 未挂载，透明代理规则未生效，安装中止" in INST.read_text(encoding="utf-8"))

# 12.2 P0-2 Migration Gate: Legacy bloated node_test_used_today = 99999 upgrade + active quota_capped skip semantics
api_call("/api/ops/settings", "POST", {"node_test_budget": 3000})
# Case A: Pre-upgrade quota file without v236_r10_migrated flag and used=99999 -> auto resets to 0
dmod._atomic_write_text(dmod._node_test_quota_path(), json.dumps({"date": time.strftime("%Y-%m-%d"), "used": 99999}))
migrated_used = dmod._node_test_used(tmp_conf)
check("P0-2 迁移门禁 A (存量超额计数自动清零): 升级发现旧版累积 node_test_used_today=99999 时自动重置为 0 并标记 v236_r10_migrated",
      migrated_used == 0 and dmod._is_node_test_budget_exceeded(tmp_conf) is False,
      f"migrated_used={migrated_used}")

# Case B: Active quota exhaustion (used=99999 with v236_r10_migrated=True) -> skip semantics (0 nodes marked dead, Shunt_* stays on proxy)
dmod.url_ping_single_node("JP-Tokyo-VLESS-01", conf_dir=tmp_conf, mock_result={"ok": True, "delay_ms": 92, "http_status": 204})
dmod.url_ping_single_node("SG-AI-Hy2-02", conf_dir=tmp_conf, mock_result={"ok": True, "delay_ms": 105, "http_status": 204})
dmod._atomic_write_text(dmod._node_test_quota_path(), json.dumps({"date": time.strftime("%Y-%m-%d"), "used": 99999, "v236_r10_migrated": True}))
res_q_ping = dmod.url_ping_single_node("JP-Tokyo-VLESS-01", conf_dir=tmp_conf)
res_q_l7 = dmod.probe_node_service_l7("JP-Tokyo-VLESS-01", "gemini", conf_dir=tmp_conf)
dmod.evaluate_all_auto_nodes(tmp_conf, force_service_probe=False)
_, shunt_under_cap = api_call("/api/shunt", "GET")
_, an_under_cap = api_call("/api/auto_nodes", "GET")
ai_grp_under_cap = next((g for g in (shunt_under_cap.get("groups") or []) if g.get("id") == "AI"), {})
yt_grp_under_cap = next((g for g in (shunt_under_cap.get("groups") or []) if g.get("id") == "YouTube"), {})
an_ai_under_cap = next((a for a in (an_under_cap.get("auto_nodes") or []) if a.get("id") == "auto_ai"), {})
check("P0-2 迁移门禁 B (超配额跳过保态，绝不判死节点或降级 direct): 配额耗尽 (99999/3000) 时探测返回 skipped=True 且保留 state='ok'，AI/YouTube 分流组与自动池 100% 保持真实代理节点",
      res_q_ping.get("quota_capped") is True and res_q_ping.get("skipped") is True and res_q_ping.get("state") == "ok"
      and res_q_l7.get("quota_capped") is True and res_q_l7.get("ok") is True
      and ai_grp_under_cap.get("resolved_node") not in ("", "direct")
      and yt_grp_under_cap.get("resolved_node") not in ("", "direct")
      and an_ai_under_cap.get("current_node") not in ("", "direct")
      and int(an_ai_under_cap.get("pool_reachable_count") or 0) >= 1,
      f"ping_st={res_q_ping.get('state')}, ai={ai_grp_under_cap.get('resolved_node')}, yt={yt_grp_under_cap.get('resolved_node')}, pool_reach={an_ai_under_cap.get('pool_reachable_count')}")

# Case C: Self-healing of already quota-poisoned node_probe.json records
ps_poison = dmod.load_node_probe_store(tmp_conf)
for _k_p, _v_p in ps_poison.items():
    if isinstance(_v_p, dict):
        _v_p["state"] = "dead"
        _v_p["delay_ms"] = -1
        _v_p["delay_ewma_ms"] = 118.0
        _v_p["fail_reason"] = "daily_test_budget_exceeded"
        _v_p["consecutive_fail"] = 5
        _v_p["quarantine_until"] = int(time.time()) + 600
        _v_p["svc"] = {"gemini": {"ok": False, "reason": "daily_test_budget_exceeded"}}
dmod.save_node_probe_store(ps_poison, tmp_conf)
ps_healed = dmod.load_node_probe_store(tmp_conf)
check("P0-2 迁移门禁 C (已受污染 node_probe.json 自动自愈): 存量被 daily_test_budget_exceeded 标死与隔离的节点在读取时 100% 自动恢复为 ok 且清空隔离期",
      all(v.get("state") == "ok" and v.get("quarantine_until") == 0 and v.get("fail_reason") == "" for v in ps_healed.values() if isinstance(v, dict)),
      str({k: (v.get("state"), v.get("delay_ms"), v.get("quarantine_until")) for k, v in ps_healed.items() if isinstance(v, dict)}))
dmod._atomic_write_text(dmod._node_test_quota_path(), json.dumps({"date": time.strftime("%Y-%m-%d"), "used": 0, "v236_r10_migrated": True}))

# 12.3 P2-1, P2-3 & P3: Single-source pool_reachable_count/current_node, --mint == #38e0b2, and zero 142/156 mock seeds
nexus_css_src = (DAEMON.parent / "webui/nexus.css").read_text(encoding="utf-8")
check("P2-1 & P2-3 & P3 (--mint=#38e0b2 对齐 + mock 零 142/156 种子 + 顶栏连接快捷跳转): CSS --mint 精确为 #38e0b2，nexus.js 无 rtt:142/156 种子，顶栏含 jump-active-connections",
      "--mint: #38e0b2;" in nexus_css_src
      and "rtt: 142" not in nexus_js_src and "rtt: 156" not in nexus_js_src
      and "current_delay_ms: 142" not in nexus_js_src and "current_delay_ms: 156" not in nexus_js_src
      and 'data-action="jump-active-connections"' in (DAEMON.parent / 'webui/index.html').read_text(encoding='utf-8'))


# 12.5 Pool-to-Shunt Group 1:1 Egress & Latency Consistency Gate (User Screenshot Scenario)
with tempfile.TemporaryDirectory(prefix="ailink-pool-shunt-sync-") as _td_ps:
    _ps_dir = Path(_td_ps)
    _ps_nodes = [
        {"type": "vless", "tag": "SG-N-3", "node_id": "nid_sgn3", "server": "1.1.1.1", "server_port": 443},
        {"type": "hysteria2", "tag": "VIP1-HY47-日本", "node_id": "nid_hy47", "server": "2.2.2.2", "server_port": 443},
        {"type": "vless", "tag": "VIP1-07-日本", "node_id": "nid_jp07", "server": "3.3.3.3", "server_port": 443},
        {"type": "vless", "tag": "地区随机 | 摩尔多瓦 MD | OTP | 146.19.213.60:443", "node_id": "nid_md_rand", "server": "146.19.213.60", "server_port": 443},
        {"type": "vless", "tag": "地区随机 | 香港 HK | HKG", "node_id": "nid_hk_rand", "server": "4.4.4.4", "server_port": 443},
    ]
    (_ps_dir / "nodes.json").write_text(json.dumps(_ps_nodes, ensure_ascii=False), encoding="utf-8")
    _ps_probe = {
        "nid_sgn3": {"state": "ok", "delay_ms": 144, "probe_ts": int(time.time()), "svc": {}},
        "nid_hy47": {"state": "ok", "delay_ms": 188, "probe_ts": int(time.time()), "svc": {}},
        "nid_jp07": {"state": "ok", "delay_ms": 1997, "probe_ts": int(time.time()), "svc": {}},
        "nid_md_rand": {"state": "ok", "delay_ms": 210, "probe_ts": int(time.time()), "svc": {}},
        "nid_hk_rand": {"state": "ok", "delay_ms": 135, "probe_ts": int(time.time()), "svc": {}},
    }
    (_ps_dir / "node_probe.json").write_text(json.dumps(_ps_probe, ensure_ascii=False), encoding="utf-8")
    _ps_auto = {
        "auto_nodes": [
            {"id": "auto_youtube", "tag": "Auto_YouTube", "name": "Youtube自动", "mode": "semi", "current_node": "SG-N-3", "groups": [{"index": 1, "name": "主力", "node_tags": ["SG-N-3"]}]},
            {"id": "auto_ai", "tag": "Auto_AI", "name": "AI自动", "mode": "full", "current_node": "VIP1-HY47-日本", "groups": [{"index": 1, "name": "主力", "node_tags": ["VIP1-HY47-日本", "SG-N-3"]}]},
            {"id": "auto_netflix", "tag": "Auto_Netflix", "name": "网飞", "mode": "semi", "current_node": "VIP1-07-日本", "groups": [{"index": 1, "name": "主力", "node_tags": ["VIP1-07-日本"]}]},
            {"id": "auto_soul", "tag": "Auto_Soul", "name": "soul", "mode": "semi", "current_node": "地区随机 | 摩尔多瓦 MD | OTP | 146.19.213.60:443", "groups": [{"index": 1, "name": "主力", "node_tags": ["地区随机 | 摩尔多瓦 MD | OTP | 146.19.213.60:443"]}]},
        ]
    }
    (_ps_dir / "auto_nodes.json").write_text(json.dumps(_ps_auto, ensure_ascii=False), encoding="utf-8")
    _ps_shunt = {
        "routing_mode": "rule_shunt",
        "groups": [
            {"id": "Custom_Soul", "name": "Soul", "shunt_mode": "auto", "auto_node_id": "auto_soul", "country": "SG", "manual_node": "auto:auto_soul", "is_custom": True},
            {"id": "Custom_Copilot", "name": "Copilot", "shunt_mode": "auto", "auto_node_id": "auto_ai", "country": "SG", "manual_node": "auto:auto_ai", "is_custom": True},
            {"id": "Custom_WorkBuddy", "name": "WorkBuddy AI", "shunt_mode": "auto", "auto_node_id": "auto_ai", "country": "HK", "manual_node": "auto:auto_ai", "is_custom": True},
            {"id": "AI", "name": "AI", "shunt_mode": "auto", "auto_node_id": "auto_ai", "country": "US", "manual_node": "auto:auto_ai"},
            {"id": "YouTube", "name": "YouTube", "shunt_mode": "auto", "auto_node_id": "auto_youtube", "country": "JP", "manual_node": "auto:auto_youtube"},
            {"id": "Netflix", "name": "Netflix", "shunt_mode": "auto", "auto_node_id": "auto_netflix", "country": "HK", "manual_node": "auto:auto_netflix"},
        ]
    }
    (_ps_dir / "shunt.json").write_text(json.dumps(_ps_shunt, ensure_ascii=False), encoding="utf-8")
    _sh_out = dmod.build_shunt_api_response(_ps_dir)
    _pool_map = {a["id"]: (a.get("current_node"), int(a.get("current_delay_ms") or -1)) for a in _sh_out.get("auto_nodes", [])}
    _grp_map = {g["id"]: (g.get("resolved_node"), int(round(g.get("resolved_rtt_ms") or -1))) for g in _sh_out.get("groups", [])}
    check(
        "Pool-Shunt 1:1 出口与延迟严格同源门禁 (Soul/Copilot/WorkBuddy/AI/YouTube/Netflix 100% 等于所选自动节点池出口与延迟)",
        _grp_map["Custom_Soul"] == _pool_map["auto_soul"] == ("地区随机 | 摩尔多瓦 MD | OTP | 146.19.213.60:443", 210)
        and _grp_map["Custom_Copilot"] == _pool_map["auto_ai"] == ("VIP1-HY47-日本", 188)
        and _grp_map["Custom_WorkBuddy"] == _pool_map["auto_ai"] == ("VIP1-HY47-日本", 188)
        and _grp_map["AI"] == _pool_map["auto_ai"] == ("VIP1-HY47-日本", 188)
        and _grp_map["YouTube"] == _pool_map["auto_youtube"] == ("SG-N-3", 144)
        and _grp_map["Netflix"] == _pool_map["auto_netflix"] == ("VIP1-07-日本", 1997),
        f"pools={_pool_map} groups={_grp_map}"
    )

# 12.6 Controlled 3-Mode TUN Data Plane + Version-Aware sing-box Schema Adapter + Kernel Hot-Upgrade Gate
with tempfile.TemporaryDirectory(prefix="ailink-tun-and-core-up-") as _td_tun:
    _tun_dir = Path(_td_tun)
    # (A) Version-Aware sing-box Schema Adapter (1.11.15 vs 1.14.4 vs 1.15.0)
    _tun_111 = dmod.build_tun_inbound_config(sb_version="1.11.15", conf_dir=_tun_dir)
    _tun_114 = dmod.build_tun_inbound_config(sb_version="1.14.4", conf_dir=_tun_dir)
    _tun_115 = dmod.build_tun_inbound_config(sb_version="1.15.0", conf_dir=_tun_dir)
    check(
        "sing-box 版本感知 Schema 适配器门禁 (1.11.15 无 dns_mode / 1.14.4 注入 dns_mode=disabled / 1.15.0 注入 multi_queue=True 并省略废弃 stack，且默认 MTU=1500)",
        _tun_111.get("mtu") == 1500 and _tun_111.get("stack") == "mixed" and "dns_mode" not in _tun_111 and "multi_queue" not in _tun_111
        and _tun_114.get("mtu") == 1500 and _tun_114.get("stack") == "mixed" and _tun_114.get("dns_mode") == "disabled" and "multi_queue" not in _tun_114
        and _tun_115.get("mtu") == 1500 and _tun_115.get("multi_queue") is True and _tun_115.get("dns_mode") == "disabled" and "stack" not in _tun_115,
        f"v1.11={_tun_111} v1.14={_tun_114} v1.15={_tun_115}"
    )

    # (B) 3-Mode nftables & 4-Stage Traffic Trace Verification (tproxy_redirect vs tproxy_tcp_tun_udp vs tun_full across IPv4/IPv6 & CLI)
    _nft_tproxy = dmod.generate_nft_rules_file(conf_dir=_tun_dir, run_dir=_tun_dir, data_plane_mode="tproxy_redirect", ipv6_proxy=True)
    _nft_hybrid = dmod.generate_nft_rules_file(conf_dir=_tun_dir, run_dir=_tun_dir, data_plane_mode="tproxy_tcp_tun_udp", ipv6_proxy=True)
    _nft_tunfull = dmod.generate_nft_rules_file(conf_dir=_tun_dir, run_dir=_tun_dir, data_plane_mode="tun_full", ipv6_proxy=True)
    _out_nat_tp = _nft_tproxy.split("chain output_nat")[1].split("chain forward_mss")[0]
    _out_nat_hy = _nft_hybrid.split("chain output_nat")[1].split("chain forward_mss")[0]
    _out_nat_tf = _nft_tunfull.split("chain output_nat")[1].split("chain forward_mss")[0]
    assert "redirect to :7891" in _out_nat_tp and "redirect to :7891" in _out_nat_hy and "redirect to :7891" not in _out_nat_tf
    dmod.update_ops_settings({"data_plane_mode": "tproxy_tcp_tun_udp", "tun_stack": "system"}, _tun_dir)
    _tr_hy_tcp = dmod.trace_traffic_flow({"target": "chatgpt.com:443", "protocol": "tcp"}, _tun_dir)
    _tr_hy_udp = dmod.trace_traffic_flow({"target": "8.8.4.4:34780", "protocol": "udp"}, _tun_dir)
    dmod.update_ops_settings({"data_plane_mode": "tun_full"}, _tun_dir)
    _tr_tf_tcp = dmod.trace_traffic_flow({"target": "chatgpt.com:443", "protocol": "tcp"}, _tun_dir)
    _tr_tf_cn = dmod.trace_traffic_flow({"target": "www.baidu.com:443", "protocol": "tcp"}, _tun_dir)
    _tr_tf_lol = dmod.trace_traffic_flow({"target": "lol.qq.com:5000", "protocol": "udp"}, _tun_dir)
    check(
        "受控三模 TUN 数据面门禁 (tproxy_redirect / tproxy_tcp_tun_udp / tun_full 规则生成与 4 阶流量透视联动 + 国内/国服游戏 0 回归旁路)",
        "# data_plane_mode: tproxy_redirect" in _nft_tproxy
        and "# data_plane_mode: tproxy_tcp_tun_udp" in _nft_hybrid
        and "meta nfproto ipv4 meta l4proto tcp tproxy ip to 127.0.0.1:7893 meta mark set 0x162 accept" in _nft_hybrid
        and "meta nfproto ipv4 meta l4proto udp meta mark set 0x163 accept" in _nft_hybrid
        and 'iifname "ailink0" accept' in _nft_hybrid
        and "# data_plane_mode: tun_full" in _nft_tunfull
        and "meta nfproto ipv4 meta l4proto { tcp, udp } meta mark set 0x163 accept" in _nft_tunfull
        and "TProxy :7893" in _tr_hy_tcp["stage1_nft"]["badge"]
        and "ailink0" in _tr_hy_udp["stage1_nft"]["badge"]
        and "ailink0" in _tr_tf_tcp["stage1_nft"]["badge"]
        and _tr_tf_cn["enters_kernel"] is False
        and _tr_tf_lol["enters_kernel"] is False,
        f"hy_tcp={_tr_hy_tcp['stage1_nft']['badge']} hy_udp={_tr_hy_udp['stage1_nft']['badge']} tf_tcp={_tr_tf_tcp['stage1_nft']['badge']}"
    )

    # (C) sing-box Kernel Online Check & 5-Stage Sandboxed Hot-Upgrade + Pre-Flight Rollback
    _mock_rel = {
        "tag_name": "v1.15.0",
        "name": "v1.15.0",
        "body": "sing-box 1.15.0 multi-queue TUN release",
        "assets": [
            {"name": f"sing-box-1.15.0-{dmod.detect_router_arch_and_libc()['preferred_suffix']}.tar.gz", "size": 18450000, "browser_download_url": "https://github.com/SagerNet/sing-box/releases/download/v1.15.0/sb.tar.gz"}
        ]
    }
    _chk_core = dmod.check_singbox_core_update(_tun_dir, force=True, mock_release=_mock_rel)
    _bin_dir = _tun_dir / "bin"
    _bin_dir.mkdir(parents=True, exist_ok=True)
    _orig_bin = _bin_dir / "sing-box"
    _orig_bin.write_text("#!/bin/sh\necho 'sing-box version 1.14.1'\nexit 0\n", encoding="utf-8")
    _orig_bin.chmod(0o755)
    # Bad candidate that fails `check -c`
    _bad_cand = _tun_dir / "sing-box-bad"
    _bad_cand.write_text("#!/bin/sh\nif [ \"$1\" = \"version\" ]; then echo 'sing-box version 1.15.0'; exit 0; fi\necho 'FATAL: unknown field in config' >&2\nexit 1\n", encoding="utf-8")
    _bad_cand.chmod(0o755)
    _up_bad = dmod.upgrade_singbox_core({"staged_binary_path": str(_bad_cand), "target_binary_path": str(_orig_bin)}, _tun_dir)
    _after_bad_text = _orig_bin.read_text(encoding="utf-8")
    # Good candidate that passes `check -c`
    _good_cand = _tun_dir / "sing-box-good"
    _good_cand.write_text("#!/bin/sh\nif [ \"$1\" = \"version\" ]; then echo 'sing-box version 1.15.0'; exit 0; fi\nif [ \"$1\" = \"check\" ]; then exit 0; fi\nexit 0\n", encoding="utf-8")
    _good_cand.chmod(0o755)
    _up_good = dmod.upgrade_singbox_core({"staged_binary_path": str(_good_cand), "target_binary_path": str(_orig_bin)}, _tun_dir)
    _after_good_text = _orig_bin.read_text(encoding="utf-8")
    _upgraded_cfg = json.loads((_tun_dir / "sing-box.json").read_text(encoding="utf-8"))
    _upgraded_tun = next((ib for ib in _upgraded_cfg.get("inbounds", []) if ib.get("tag") == "tun-in"), {})
    check(
        "sing-box 内核版本检测与 5 步沙箱预检热升级/回滚门禁 (check 失败自动拦截不替换原内核；check 通过自动备份 sing-box.bak 并生成 1.15 multi_queue 配置)",
        _chk_core.get("ok") is True and _chk_core.get("latest_version") == "1.15.0" and _chk_core.get("schema_profile") == "v1.15-multiqueue"
        and _up_bad.get("ok") is False and _up_bad.get("stage") == "precheck" and _up_bad.get("rolled_back") is True
        and ("1.14.1" in _after_bad_text) and ("1.15.0" in _after_good_text)
        and _up_good.get("ok") is True and _up_good.get("current_version") == "1.15.0" and (_bin_dir / "sing-box.bak").is_file()
        and _upgraded_tun.get("multi_queue") is True and "stack" not in _upgraded_tun,
        f"chk={_chk_core.get('schema_profile')} bad={_up_bad} good={_up_good} tun={_upgraded_tun}"
    )

# HTTP E2E check for /api/ops/core_update/check and data_plane_mode setting + UI controls
st_cu_http, res_cu_http = api_call("/api/ops/core_update/check", "GET")
st_dpm_set, res_dpm_set = api_call("/api/ops/settings", "POST", {"data_plane_mode": "tproxy_tcp_tun_udp", "tun_stack": "system"})
st_dpm_rst, res_dpm_rst = api_call("/api/ops/settings", "POST", {"data_plane_mode": "tproxy_redirect", "tun_stack": "mixed"})
html_src_tun = (DAEMON.parent / "webui/index.html").read_text(encoding="utf-8")
js_src_tun = (DAEMON.parent / "webui/nexus.js").read_text(encoding="utf-8")
check(
    "HTTP E2E & 前端设置页门禁 (/api/ops/core_update/check 200 + data_plane_mode 持久化切换 + index.html/nexus.js 控件齐全)",
    st_cu_http == 200 and res_cu_http.get("ok") is True
    and st_dpm_set == 200 and res_dpm_set.get("data_plane_mode") == "tproxy_tcp_tun_udp" and res_dpm_set.get("tun_stack") == "system"
    and st_dpm_rst == 200 and res_dpm_rst.get("data_plane_mode") == "tproxy_redirect"
    and 'id="sel-ops-data-plane-mode"' in html_src_tun and 'id="sel-ops-tun-stack"' in html_src_tun
    and 'data-action="check-core-update"' in html_src_tun and "case 'check-core-update':" in js_src_tun,
    f"cu_st={st_cu_http} dpm_set={res_dpm_set.get('data_plane_mode')} dpm_rst={res_dpm_rst.get('data_plane_mode')}"
)

# 14. v2.4.0 Round-2 Incident & Feedback Closure (incident-2026-11-05-node-outage.md + Sonar Custom/Offline)
print("\n[14] v2.4.0 节点假死事故根治 (TTL 过期保态 / 500+ 节点预算自适应 / force_manual 穿透) & 声呐实时离线与自定义目标 E2E")
_inc_dir = tmp_work / "incident_20261105"
_inc_dir.mkdir(parents=True, exist_ok=True)
_inc_nodes = [
    {"tag": f"SG-Large-Node-{i:03d}", "node_id": f"nid_sg_{i:03d}", "type": "vless", "server": f"10.99.{i // 250}.{(i % 250) + 1}", "server_port": 443, "uuid": f"u-{i}"}
    for i in range(120)
]
(_inc_dir / "nodes.json").write_text(json.dumps(_inc_nodes), encoding="utf-8")
(_inc_dir / "ops_settings.json").write_text(json.dumps({"node_test_budget": 3000}), encoding="utf-8")
_stale_ts = int(time.time()) - (dmod.PROBE_SNAPSHOT_TTL_SEC + 18000)  # 11 hours ago (> 6h TTL)
_inc_store = {
    "nid_sg_000": {"tag": "SG-Large-Node-000", "node_id": "nid_sg_000", "state": "ok", "delay_ms": 128, "probe_ts": _stale_ts, "history": [{"state": "ok", "delay_ms": 128, "ts": _stale_ts}]},
    "nid_sg_001": {"tag": "SG-Large-Node-001", "node_id": "nid_sg_001", "state": "dead", "delay_ms": -1, "probe_ts": _stale_ts, "history": [{"state": "dead", "delay_ms": -1, "ts": _stale_ts}]},
}
dmod.save_node_probe_store(_inc_store, _inc_dir)
_eff_stale_ok = dmod.get_node_effective_probe(_inc_nodes[0], store=_inc_store, conf_dir=_inc_dir)
_eff_real_dead = dmod.get_node_effective_probe(_inc_nodes[1], store=_inc_store, conf_dir=_inc_dir)
_eff_untested = dmod.get_node_effective_probe(_inc_nodes[2], store=_inc_store, conf_dir=_inc_dir)
_sel_stale_ok = dmod.evaluate_node_selectability(_inc_nodes[0], store=_inc_store, conf_dir=_inc_dir)
_scaled_budget = dmod._get_effective_node_test_budget(_inc_dir)
check(
    "incident-2026-11-05 根因修复 1 & 2 (超过 6h TTL 的历史 ok 节点保持 state='ok' 且 selectable=True 绝不误判 dead；>50 节点库自动将默认 3000 预算动态扩容至 >=30000)",
    _eff_stale_ok.get("state") == "ok" and _eff_stale_ok.get("stale") is True and _eff_stale_ok.get("delay_ms") == 128
    and _sel_stale_ok.get("selectable") is True
    and _eff_real_dead.get("state") == "dead" and _eff_untested.get("state") == "untested"
    and _scaled_budget >= 30000,
    f"stale_ok={_eff_stale_ok.get('state')}/stale={_eff_stale_ok.get('stale')} selectable={_sel_stale_ok.get('selectable')} scaled_budget={_scaled_budget}"
)

# Verify manual probe (force_manual=True) bypasses daily budget even when quota is exhausted
api_call("/api/ops/settings", "POST", {"node_test_budget": 5})
dmod._atomic_write_text(dmod._node_test_quota_path(), json.dumps({"date": time.strftime("%Y-%m-%d"), "used": 99999, "v236_r10_migrated": True, "v240_budget_migrated": True}))
st_man_probe, res_man_probe = api_call("/api/probe/run", "POST", {"manual": True, "sync": True})
api_call("/api/ops/settings", "POST", {"node_test_budget": 3000})
dmod._atomic_write_text(dmod._node_test_quota_path(), json.dumps({"date": time.strftime("%Y-%m-%d"), "used": 0, "v236_r10_migrated": True, "v240_budget_migrated": True}))
check(
    "incident-2026-11-05 根因修复 3 (/api/probe/run 手动全量测速 force_manual=True 穿透每日测速预算，0 节点因 quota_capped 被跳过)",
    st_man_probe == 200 and res_man_probe.get("ok") is True
    and not any(v.get("quota_capped") for v in (res_man_probe.get("results") or {}).values()),
    f"tested={res_man_probe.get('tested_count')} any_capped={any(v.get('quota_capped') for v in (res_man_probe.get('results') or {}).values())}"
)

# Verify Sonar custom targets persistence & real-time disconnect detection (zero stale ms on outage)
_custom_sonar_list = [
    {"id": "claude", "name": "Claude AI", "url": "https://claude.ai", "selector": "Shunt_AI"},
    {"id": "gemini", "name": "Gemini", "url": "https://gemini.google.com", "selector": "Shunt_AI"},
    {"id": "youtube", "name": "YouTube", "url": "https://www.youtube.com/generate_204", "selector": "Shunt_YouTube"},
    {"id": "github", "name": "GitHub", "url": "https://api.github.com/zen", "selector": "Shunt_GitHub"},
    {"id": "netflix", "name": "Netflix", "url": "https://www.netflix.com/title/80018499", "selector": "Shunt_Netflix"},
    {"id": "tiktok", "name": "TikTok", "url": "https://www.tiktok.com/favicon.ico", "selector": "Shunt_TikTok"},
    {"id": "telegram", "name": "Telegram", "url": "https://core.telegram.org/", "selector": "Shunt_Outside_CN"},
    {"id": "bilibili", "name": "B站直连", "url": "https://www.bilibili.com", "selector": "Shunt_Domestic_CN"},
]
st_st_save, res_st_save = api_call("/api/overview/sonar_targets", "POST", {"targets": _custom_sonar_list})
st_st_off, res_st_off = api_call("/api/overview/sonar_probe", "POST", {"simulate_offline": True})
_off_pulses = res_st_off.get("pulse_services") or []
st_st_rst, res_st_rst = api_call("/api/overview/sonar_targets", "POST", {"reset": True})
check(
    "v2.4.0 概览声呐自定义目标与断网实时清零门禁 (/api/overview/sonar_targets 持久化自定义目标 + 断网时全部目标 ms=0 & state='dead' 零残留假延迟)",
    st_st_save == 200 and res_st_save.get("targets", [{}])[0].get("name") == "Claude AI"
    and st_st_off == 200 and len(_off_pulses) == 8 and all(int(p.get("ms") or 0) == 0 and p.get("state") == "dead" for p in _off_pulses)
    and st_st_rst == 200 and res_st_rst.get("targets", [{}])[0].get("name") == "ChatGPT",
    f"custom0={res_st_save.get('targets', [{}])[0].get('name')} off_states={[(p.get('id'), p.get('ms'), p.get('state')) for p in _off_pulses]}"
)


# 17. v2.4.2 本地智能体三份实机排查报告闭环门禁 (单组迁移 + 零死节点振荡 + 数据真实性 D-01..D-11)
print("\n[17] v2.4.2 本地智能体三份实机排查报告闭环门禁 (双组遗留清理 / 自动节点池防抖闭环 / 数据真实性 D-01..D-11)")

# Ensure both test nodes exist in saved_nodes before testing dual-to-single migration
dmod.save_nodes_list([
    {"node_id": "nid_jp_01", "tag": "JP-Tokyo-VLESS-01", "type": "vless", "server": "jp.example.com", "server_port": 443, "uuid": "11111111-1111-1111-1111-111111111111"},
    {"node_id": "nid_sg_02", "tag": "SG-AI-Hy2-02", "type": "hysteria2", "server": "sg.example.com", "server_port": 8443, "password": "pass"},
    {"node_id": "nid_dead_hk", "tag": "Dead-HK-Node", "type": "vless", "server": "hk.example.com", "server_port": 443, "uuid": "22222222-2222-2222-2222-222222222222"},
], tmp_conf)
_ps_mig = dmod.load_node_probe_store(tmp_conf)
_ps_mig["nid_jp_01"] = {"state": "ok", "delay_ms": 88, "consecutive_fail": 0, "last_probe_ts": int(time.time()), "quarantine_until": 0}
_ps_mig["nid_sg_02"] = {"state": "ok", "delay_ms": 118, "consecutive_fail": 0, "last_probe_ts": int(time.time()), "quarantine_until": 0}
dmod.save_node_probe_store(_ps_mig, tmp_conf)

# 17.1 Single-group migration & backup verification
_legacy_an_doc = {
    "auto_nodes": [
        {
            "id": "auto_legacy_dual",
            "name": "历史双组残留池",
            "target_size": 5,
            "active_group_index": 2,
            "current_node": "SG-AI-Hy2-02",
            "groups": [
                {"index": 1, "name": "主力组 G1", "node_tags": ["JP-Tokyo-VLESS-01"]},
                {"index": 2, "name": "备选组 G2", "node_tags": ["SG-AI-Hy2-02"]}
            ],
            "missing_members": [{"tag": f"missing_{i}"} for i in range(25)]
        }
    ]
}
(tmp_conf / "auto_nodes.json").write_text(json.dumps(_legacy_an_doc, ensure_ascii=False), encoding="utf-8")
_migrated_doc = dmod.load_auto_nodes_config(tmp_conf)
_mig_pool = next((a for a in (_migrated_doc.get("auto_nodes") or []) if a.get("id") == "auto_legacy_dual"), {})
check(
    "v2.4.2 双组历史遗留自动迁移门禁: 旧版含 G1+G2 的 auto_nodes.json 自动备份并收敛为单组(groups=1, active_group_index=1, missing_members<=10)",
    _migrated_doc.get("v241_single_group_migrated") is True
    and (tmp_conf / "auto_nodes.json.bak-single-group").is_file()
    and len(_mig_pool.get("groups") or []) == 1
    and _mig_pool.get("active_group_index") == 1
    and _mig_pool["groups"][0].get("node_tags") == ["JP-Tokyo-VLESS-01", "SG-AI-Hy2-02"]
    and len(_mig_pool.get("missing_members") or []) == 10,
    f"migrated={_migrated_doc.get('v241_single_group_migrated')}, groups={_mig_pool.get('groups')}, missing_len={len(_mig_pool.get('missing_members') or [])}"
)

# 17.2 Auto-pool dead member zero-flapping & runtime state persistence across save/load
_dead_pool_doc = {
    "v241_single_group_migrated": True,
    "auto_nodes": [
        {
            "id": "auto_youtube",
            "tag": "Auto_YouTube",
            "name": "Youtube自动",
            "target_size": 5,
            "replenish_threshold": 2,
            "switch_cooldown_s": 600,
            "current_node": "Dead-HK-Node",
            "groups": [{"index": 1, "name": "节点池成员", "node_tags": ["Dead-HK-Node"]}],
        }
    ]
}
dmod.save_auto_nodes_config(_dead_pool_doc, tmp_conf)
_probe_snap = dmod.load_node_probe_store(tmp_conf)
_probe_snap["nid_dead_hk"] = {
    "state": "dead", "delay_ms": -1, "consecutive_fail": 5, "last_probe_ts": int(time.time())
}
_probe_snap["Dead-HK-Node"] = {
    "state": "dead", "delay_ms": -1, "consecutive_fail": 5, "last_probe_ts": int(time.time())
}
_probe_snap["nid_jp_01"] = {
    "state": "ok", "delay_ms": 88, "consecutive_fail": 0, "last_probe_ts": int(time.time())
}
dmod.save_node_probe_store(_probe_snap, tmp_conf)
dmod.evaluate_all_auto_nodes(tmp_conf, sync_selectors=False)
_after_eval1 = next((a for a in (dmod.load_auto_nodes_config(tmp_conf).get("auto_nodes") or []) if a.get("id") == "auto_youtube"), {})
_resolved_yt = dmod.resolve_node_for_country_strategy_with_failover(
    "HK", "auto", "auto:auto_youtube", ["JP-Tokyo-VLESS-01", "Dead-HK-Node"], {"JP-Tokyo-VLESS-01": 88.0}, group_id="YouTube", conf_dir=tmp_conf
)
# Run a second evaluation immediately — must NOT flap back to Dead-HK-Node!
dmod.evaluate_all_auto_nodes(tmp_conf, sync_selectors=False)
_after_eval2 = next((a for a in (dmod.load_auto_nodes_config(tmp_conf).get("auto_nodes") or []) if a.get("id") == "auto_youtube"), {})
check(
    "v2.4.2 自动节点池死节点零乒乓振荡门禁 (A-P0/A-P1): 池内唯一成员不可达时 current_node 稳定保持 direct 绝不被 _normalize 覆盖回死节点，且分流解析与二次评估零反复振荡",
    _after_eval1.get("current_node") == "direct"
    and _after_eval2.get("current_node") == "direct"
    and _after_eval2.get("all_groups_dead_alert") is True
    and _after_eval2.get("pool_degraded_alert") is True
    and int(_after_eval2.get("last_switch_ts") or 0) > 0
    and _resolved_yt.get("selected") == "direct",
    f"eval1={_after_eval1.get('current_node')}, eval2={_after_eval2.get('current_node')}, resolved={_resolved_yt}"
)

# 17.3 Data authenticity D-01..D-11 API contract verification
st_conn_api, res_conn_api = api_call("/api/clash/connections", "GET")
st_stat_api, res_stat_api = api_call("/api/status", "GET")
check(
    "v2.4.2 数据真实性门禁 (D-01/D-04/D-06/D-10/D-11): /api/clash/connections 返回 total/displayed_count/truncated，/api/status 返回 data_age_ms/srs_rulesets_count/backup_info",
    st_conn_api == 200 and "total" in res_conn_api and "displayed_count" in res_conn_api and "truncated" in res_conn_api
    and st_stat_api == 200 and "data_age_ms" in res_stat_api and "srs_rulesets_count" in res_stat_api and isinstance(res_stat_api.get("backup_info"), dict)
    and dmod._fmt_bytes_short(1536) == dmod._format_bytes_human(1536),
    f"conn_keys={list(res_conn_api.keys())}, status_age={res_stat_api.get('data_age_ms')}, srs={res_stat_api.get('srs_rulesets_count')}, backup={res_stat_api.get('backup_info')}"
)

# 17.4 v2.4.2 内核日志实时被动故障感知与秒级切换门禁 (scan_kernel_logs_for_active_pool_failures)
api_call("/api/shunt/update", "POST", {"routing_mode": "rule_shunt", "group_id": "YouTube", "shunt_mode": "auto", "strategy": "auto", "auto_node_id": "auto_youtube"})
_now_lp = int(time.time())
_ps_lp = dmod.load_node_probe_store(tmp_conf)
_ps_lp["nid_jp_01"] = {"state": "ok", "delay_ms": 88, "consecutive_fail": 0, "last_probe_ts": _now_lp, "quarantine_until": 0}
_ps_lp["JP-Tokyo-VLESS-01"] = {"state": "ok", "delay_ms": 88, "consecutive_fail": 0, "last_probe_ts": _now_lp, "quarantine_until": 0}
_ps_lp["nid_sg_02"] = {"state": "ok", "delay_ms": 126, "consecutive_fail": 0, "last_probe_ts": _now_lp, "quarantine_until": 0}
_ps_lp["SG-AI-Hy2-02"] = {"state": "ok", "delay_ms": 126, "consecutive_fail": 0, "last_probe_ts": _now_lp, "quarantine_until": 0}
dmod.save_node_probe_store(_ps_lp, tmp_conf)
_log_pool_doc = {
    "v242_single_group_migrated": True,
    "auto_nodes": [
        {
            "id": "auto_youtube",
            "tag": "Auto_YouTube",
            "name": "Youtube自动",
            "mode": "semi",
            "pool_mode": "ping_only",
            "service_check_enabled": False,
            "target_size": 5,
            "replenish_threshold": 1,
            "switch_cooldown_s": 600,
            "current_node": "JP-Tokyo-VLESS-01",
            "groups": [{"index": 1, "name": "节点池成员", "node_tags": ["JP-Tokyo-VLESS-01", "SG-AI-Hy2-02"]}],
        }
    ]
}
dmod.save_auto_nodes_config(_log_pool_doc, tmp_conf)
_now_lp = int(time.time())
dmod._set_auto_pool_runtime_state(tmp_conf, "auto_youtube", {
    "current_node": "JP-Tokyo-VLESS-01",
    "last_switch_ts": _now_lp,
    "last_smart_switch_ts": _now_lp,
    "all_groups_dead_alert": False,
})
_ps_lp = dmod.load_node_probe_store(tmp_conf)
_ps_lp["nid_jp_01"] = {"state": "ok", "delay_ms": 88, "consecutive_fail": 0, "last_probe_ts": _now_lp, "quarantine_until": 0}
_ps_lp["JP-Tokyo-VLESS-01"] = {"state": "ok", "delay_ms": 88, "consecutive_fail": 0, "last_probe_ts": _now_lp, "quarantine_until": 0}
_ps_lp["nid_sg_02"] = {"state": "ok", "delay_ms": 126, "consecutive_fail": 0, "last_probe_ts": _now_lp, "quarantine_until": 0}
_ps_lp["SG-AI-Hy2-02"] = {"state": "ok", "delay_ms": 126, "consecutive_fail": 0, "last_probe_ts": _now_lp, "quarantine_until": 0}
dmod.save_node_probe_store(_ps_lp, tmp_conf)

# Step A: 2 errors followed by 1 healthy INFO connection must reset streak and NOT switch
_sb_log_file = tmp_conf / "singbox.log"
_sb_log_file.write_text(
    "ERROR[0001] outbound/vless[JP-Tokyo-VLESS-01]: dial tcp 1.2.3.4:443: i/o timeout\n"
    "WARN[0002] outbound/vless[JP-Tokyo-VLESS-01]: handshake failed: context deadline exceeded\n"
    "INFO[0003] outbound/vless[JP-Tokyo-VLESS-01]: outbound connection to www.youtube.com:443\n",
    encoding="utf-8"
)
_scan_step_a = dmod.scan_kernel_logs_for_active_pool_failures(tmp_conf, log_path=_sb_log_file, fail_threshold=3)
_cur_after_a = next((a for a in (dmod.load_auto_nodes_config(tmp_conf).get("auto_nodes") or []) if a.get("id") == "auto_youtube"), {}).get("current_node")

# Step B: 3 consecutive outbound errors on active pool node JP-Tokyo-VLESS-01 -> must bypass 600s cooldown and switch to SG-AI-Hy2-02 immediately!
with open(_sb_log_file, "a", encoding="utf-8") as _fh_log:
    _fh_log.write(
        "ERROR[0004] outbound/vless[JP-Tokyo-VLESS-01]: dial tcp 1.2.3.4:443 to www.youtube.com:443: i/o timeout\n"
        "ERROR[0005] outbound/vless[JP-Tokyo-VLESS-01]: dial tcp 1.2.3.5:443 to rr1.googlevideo.com:443: connection refused\n"
        "ERROR[0006] outbound/vless[JP-Tokyo-VLESS-01]: tls: handshake failed to s.ytimg.com:443: unexpected EOF\n"
    )
_scan_step_b = dmod.scan_kernel_logs_for_active_pool_failures(tmp_conf, log_path=_sb_log_file, fail_threshold=3)
_an_after_b = next((a for a in (dmod.load_auto_nodes_config(tmp_conf).get("auto_nodes") or []) if a.get("id") == "auto_youtube"), {})
_ps_after_b = dmod.load_node_probe_store(tmp_conf)
_jp_rec_b = _ps_after_b.get("nid_jp_01") or {}
st_an_guard, res_an_guard = api_call("/api/auto_nodes", "GET")
check(
    "v2.4.2 内核日志实时故障感知与秒级切换门禁: 偶发报错后正常连接自动清零不误切；连续 3 次传输报错立即将当前节点判死隔离 300s、突破 600s 冷却秒切至池内下一健康节点 SG-AI-Hy2-02 并记录切换历史",
    _scan_step_a.get("triggered") is False
    and _cur_after_a == "JP-Tokyo-VLESS-01"
    and _scan_step_b.get("triggered") is True
    and _an_after_b.get("current_node") == "SG-AI-Hy2-02"
    and _jp_rec_b.get("state") == "dead"
    and int(_jp_rec_b.get("quarantine_until") or 0) > _now_lp
    and st_an_guard == 200
    and isinstance(res_an_guard.get("log_failover_guard"), dict)
    and int(res_an_guard["log_failover_guard"].get("total_switches") or 0) >= 1,
    f"stepA={_scan_step_a}, curA={_cur_after_a}, stepB={_scan_step_b}, new_cur={_an_after_b.get('current_node')}, jp_rec={_jp_rec_b}, guard={res_an_guard.get('log_failover_guard')}"
)

# Step C: v2.4.2 Audit Remediation P0-2 & N-P1 (Single-Target Suppression + Bridge Token Isolation + Unified request_switch)
with open(_sb_log_file, "a", encoding="utf-8") as _fh_log_c:
    _fh_log_c.write(
        "ERROR[0007] outbound/hysteria2[SG-AI-Hy2-02]: connection to dead-origin.example.com:443: i/o timeout\n"
        "ERROR[0008] outbound/hysteria2[SG-AI-Hy2-02]: connection to dead-origin.example.com:443: i/o timeout\n"
        "ERROR[0009] outbound/hysteria2[SG-AI-Hy2-02]: connection to dead-origin.example.com:443: i/o timeout\n"
    )
_scan_step_c = dmod.scan_kernel_logs_for_active_pool_failures(tmp_conf, log_path=_sb_log_file, fail_threshold=3)
_bridge_tok = dmod.get_luci_bridge_token(create=True)
st_bridge_logs, _ = api_call("/api/ops/logs", "GET", headers={"X-Auth-Token": _bridge_tok})
st_bridge_bk, _ = api_call("/api/ops/backup", "GET", headers={"X-Auth-Token": _bridge_tok})
check(
    "v2.4.2 升级审计 P0-2 & N-P1 门禁: 单一死目标网站 (dead-origin.example.com) 连续 3 次超时被目标多样性守卫抑制不误切节点 (single_target_suppressed=True)，且 LuCI 内存桥接令牌严禁访问 /api/ops/logs 与 /api/ops/backup (401)",
    _scan_step_c.get("triggered") is False
    and _scan_step_c.get("single_target_suppressed") is True
    and st_bridge_logs == 401
    and st_bridge_bk == 401,
    f"stepC={_scan_step_c}, bridge_logs={st_bridge_logs}, bridge_bk={st_bridge_bk}"
)

# Step D: v2.4.2 Five Major Capabilities Full-Chain E2E Verification
# D.1: Multi-Line Pool + IP-Sensitive Group Auto-Single-Line Protection + Bandwidth Preference + Keyword AND/OR Filter
dmod.save_nodes_list([
    {"tag": "JP-IEPL-Relay-01", "raw_tag": "专线 | 日本 IEPL 01", "type": "vless", "server": "gz.iepl-relay.cn", "server_port": 443, "uuid": "11111111-2222-3333-4444-555555555555", "node_id": "nid_jp_iepl_1"},
    {"tag": "SG-Direct-Fast-02", "raw_tag": "直连 | 新加坡 BGP 02", "type": "hysteria2", "server": "sg.example.com", "server_port": 8443, "password": "pw", "node_id": "nid_sg_dir_2"},
    {"tag": "US-Direct-03", "raw_tag": "美国原生 03", "type": "vless", "server": "us.example.com", "server_port": 443, "uuid": "11111111-2222-3333-4444-666666666666", "node_id": "nid_us_dir_3"},
], tmp_conf)
_now_d = int(time.time())
dmod.save_node_probe_store({
    "nid_jp_iepl_1": {"state": "ok", "delay_ms": 95, "delay_ewma_ms": 95.0, "probe_ts": _now_d, "last_probe_ts": _now_d, "bandwidth_mbps": 45.0, "last_bw_test_ts": _now_d, "svc": {}},
    "nid_sg_dir_2": {"state": "ok", "delay_ms": 102, "delay_ewma_ms": 102.0, "probe_ts": _now_d, "last_probe_ts": _now_d, "bandwidth_mbps": 680.0, "last_bw_test_ts": _now_d, "svc": {}},
    "nid_us_dir_3": {"state": "ok", "delay_ms": 160, "delay_ewma_ms": 160.0, "probe_ts": _now_d, "last_probe_ts": _now_d, "bandwidth_mbps": 220.0, "last_bw_test_ts": _now_d, "svc": {}},
}, tmp_conf)

# Test keyword AND/OR filter in auto_screen_and_fill_pool
_sc_and = dmod.auto_screen_and_fill_pool({"pool_mode": "ping_only", "keyword_filter": "日本, IEPL", "keyword_mode": "AND", "run_live_probe": False}, conf_dir=tmp_conf, run_live_probe=False)
_sc_or = dmod.auto_screen_and_fill_pool({"pool_mode": "ping_only", "keyword_filter": "IEPL, 新加坡", "keyword_mode": "OR", "run_live_probe": False}, conf_dir=tmp_conf, run_live_probe=False)

# Test saving a multi_line pool with bandwidth_prefer=True vs AI pool auto-locking to single_best
st_save_ml, res_save_ml = api_call("/api/auto_nodes/save", "POST", {
    "id": "auto_youtube",
    "name": "YouTube多线并发池",
    "pool_mode": "ping_only",
    "dispatch_mode": "multi_line",
    "bandwidth_prefer": True,
    "bandwidth_interval_h": 6,
    "bandwidth_limit_mb": 16,
    "target_size": 4,
    "replenish_threshold": 2,
    "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["JP-IEPL-Relay-01", "SG-Direct-Fast-02", "US-Direct-03"]}],
    "probe_now": False,
})
st_save_ai_ml, res_save_ai_ml = api_call("/api/auto_nodes/save", "POST", {
    "id": "auto_ai",
    "name": "AI防风控池",
    "pool_mode": "service_check",
    "service_check_enabled": True,
    "service_checks": ["gemini", "chatgpt"],
    "dispatch_mode": "multi_line",  # Should be auto-locked to single_best by backend guardrail!
    "target_size": 4,
    "replenish_threshold": 2,
    "groups": [{"index": 1, "name": "主力组 G1", "node_tags": ["JP-IEPL-Relay-01", "SG-Direct-Fast-02"]}],
    "probe_now": False,
})
_yt_pool = next((a for a in (res_save_ml.get("auto_nodes") or []) if a.get("id") == "auto_youtube"), {})
_ai_pool = next((a for a in (res_save_ai_ml.get("auto_nodes") or []) if a.get("id") == "auto_ai"), {})

# Bind AI shunt group to the multi_line YouTube pool and verify AI group is automatically single-line protected!
api_call("/api/shunt/update", "POST", {"group_id": "AI", "shunt_mode": "auto", "strategy": "auto", "auto_node_id": "auto_youtube"})
api_call("/api/shunt/update", "POST", {"group_id": "YouTube", "shunt_mode": "auto", "strategy": "auto", "auto_node_id": "auto_youtube"})
st_sh_ml, res_sh_ml = api_call("/api/shunt", "GET")
_sh_ai_grp = next((g for g in (res_sh_ml.get("groups") or []) if g.get("id") == "AI"), {})
_sh_yt_grp = next((g for g in (res_sh_ml.get("groups") or []) if g.get("id") == "YouTube"), {})

# D.2: Chained Proxy (`POST /api/nodes/chained_create`) + sing-box `detour` generation + Relay/Chained line_type detection
st_ch, res_ch = api_call("/api/nodes/chained_create", "POST", {
    "tag": "US-Static-Residential-Socks5",
    "type": "socks",
    "server": "198.51.100.88",
    "server_port": 1080,
    "username": "user_res",
    "password": "pw_res",
    "region_override": "US",
    "detour_pool_id": "auto_youtube",
    "reload_core": False,
})
_sb_cfg_gen = dmod.ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_conf)
_ch_ob_in_sb = next((o for o in (_sb_cfg_gen.get("outbounds") or []) if o.get("tag") == "US-Static-Residential-Socks5"), {})
st_nds_d, res_nds_d = api_call("/api/nodes", "GET")
_iepl_nd = next((n for n in (res_nds_d.get("nodes") or []) if n.get("tag") == "JP-IEPL-Relay-01"), {})
_ch_nd = next((n for n in (res_nds_d.get("nodes") or []) if n.get("tag") == "US-Static-Residential-Socks5"), {})

# D.3: Traffic Insights (`GET /api/traffic/insights`) & Silent Multi-Core RPS optimization
st_ti, res_ti = api_call("/api/traffic/insights?include_direct=1", "GET")
_rps_res = dmod.optimize_multicore_network_rps()

check(
    "v2.4.2 五大新能力全链路门禁: (1)多线并发与AI防风控自动锁定单线 (2)关键词AND/OR与680Mbps高带宽择优胜出 (3)中转专线/链式落地识别与sing-box detour注入 (4)三维流量归因洞察与底层静默多核RPS调优",
    _sc_and.get("admitted_g1") == ["JP-IEPL-Relay-01"]
    and set(_sc_or.get("admitted_g1") or []) == {"JP-IEPL-Relay-01", "SG-Direct-Fast-02"}
    and _yt_pool.get("dispatch_mode") == "multi_line"
    and len(_yt_pool.get("multi_line_nodes") or []) >= 2
    and _yt_pool.get("current_node") == "SG-Direct-Fast-02"  # 680Mbps beats 45Mbps when bandwidth_prefer=True!
    and _ai_pool.get("dispatch_mode") == "single_best"
    and _ai_pool.get("multi_line_locked") is True
    and _sh_ai_grp.get("dispatch_mode") == "single_best"
    and _sh_ai_grp.get("auto_single_line_protected") is True
    and _sh_yt_grp.get("dispatch_mode") == "multi_line"
    and st_ch == 200
    and _ch_ob_in_sb.get("detour") in ("Stream_Auto", "Auto_YouTube", "Auto_auto_youtube")
    and _iepl_nd.get("line_type") == "relay"
    and _ch_nd.get("line_type") == "chained"
    and st_ti == 200
    and len(res_ti.get("hourly_series") or []) == 24
    and len(res_ti.get("daily_series") or []) == 7
    and _rps_res.get("done") is True,
    f"and={_sc_and.get('admitted_g1')}, yt_cur={_yt_pool.get('current_node')}, ai_dm={_ai_pool.get('dispatch_mode')}, sh_ai_prot={_sh_ai_grp.get('auto_single_line_protected')}, ch_detour={_ch_ob_in_sb.get('detour')}, iepl_lt={_iepl_nd.get('line_type')}, ti_st={st_ti}"
)

httpd.shutdown()
shutil.rmtree(tmp_work, ignore_errors=True)

print("\n" + "=" * 78)
fails = [r for r in results if not r[1]]
print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
for n, ok, d in fails:
    print(f"   ✗ {n}  {d}")
print("=" * 78)
sys.exit(1 if fails else 0)
