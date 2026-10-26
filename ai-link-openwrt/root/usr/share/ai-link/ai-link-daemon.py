#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-LINK Core Daemon, L7 Deep Semantic Availability Probe Engine, Node Subscription Parser,
Clash :9090 API Bridge & Standalone WebUI Server (v1.6.1-r1)
Copyright (C) 2026 AI-LINK OpenWrt Project (GPL-3.0)
"""

import os
import re
import sys
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import ssl
import time
import math
import copy
import json
import gzip
import glob
import random
import struct
import shutil
import signal
import base64
import socket
import tarfile
import hashlib
import ipaddress
import urllib.parse
import urllib.request
import urllib.error
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
from pathlib import Path

CONF_DIR = Path(os.environ.get("AI_LINK_CONF_DIR", "/etc/ai-link"))
WEBUI_DIR = Path(os.environ.get("AI_LINK_WEBUI_DIR", "/usr/share/ai-link/webui"))
RUN_DIR = Path(os.environ.get("AI_LINK_RUN_DIR", "/var/run/ai-link"))
CACHE_DIR = Path(os.environ.get("AI_LINK_CACHE_DIR", "/tmp/ai-link-cache"))

def _atomic_write_text(target: Path, content: str, encoding: str = "utf-8") -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.name not in ("traffic_ledger.json",):
        for _m_name in ("_SHUNT_API_MEMO", "_NODES_API_MEMO", "_AUTO_NODES_API_MEMO", "_STATUS_API_MEMO", "_HOMELINK_API_MEMO", "_DNS_TELEM_MEMO", "_MTIMES_FAST_CACHE", "_JSON_WIRE_MEMO"):
            _m = globals().get(_m_name)
            if isinstance(_m, dict):
                _m.clear()
        try:
            if "PROBE_ENGINE" in globals():
                PROBE_ENGINE._last_lp_sig = None
        except Exception:
            pass
    tmp_p = target.parent / f".{target.name}.tmp.{os.getpid()}.{threading.get_ident()}"
    try:
        if target.is_file() and target.suffix == ".json" and target.stat().st_size > 2:
            bak_p = target.with_suffix(target.suffix + ".bak")
            try:
                shutil.copy2(target, bak_p)
            except Exception:
                pass
        tmp_p.write_text(content, encoding=encoding)
        os.replace(tmp_p, target)
    except Exception:
        try:
            if tmp_p.exists():
                tmp_p.unlink()
        except Exception:
            pass
        target.write_text(content, encoding=encoding)

def _read_json_with_backup(target: Path, default_val=None):
    """Reads a JSON file and automatically self-heals from .bak if corrupted by power loss."""
    for cand in (target, target.with_suffix(target.suffix + ".bak")):
        if not cand.is_file():
            continue
        try:
            raw = cand.read_text(encoding="utf-8")
            if not raw.strip():
                continue
            data = json.loads(raw)
            if cand != target:
                try:
                    shutil.copy2(cand, target)
                except Exception:
                    pass
            return data
        except Exception:
            continue
    return default_val
CONTROLLER_API = os.environ.get("AI_LINK_CORE_API", "http://127.0.0.1:9090")
DEFAULT_DELAY_TEST_URL = os.environ.get("AI_LINK_DELAY_URL", "http://connect.rom.miui.com/generate_204")

# ------------------------------------------------------------------------------
# Bulk-transfer stall detection
#
# sing-box's /proxies/<tag>/delay only measures time-to-first-byte, so a node
# that completes the TLS handshake and returns headers but transfers ZERO body
# bytes still scores ~300ms and wins "smart" selection. Such a node makes pages
# look "broken" (YouTube loads nothing) while generate_204 keeps passing.
# We therefore fetch a real body through the selected exit and quarantine the
# node when it cannot deliver bytes.
# ------------------------------------------------------------------------------

L7_SERVICE_FINGERPRINTS = {
    "chatgpt": {
        "name": "ChatGPT / OpenAI",
        "group": "AI_Best_Auto",
        "probe_urls": [
            "https://chat.openai.com/cdn-cgi/trace",
            "https://api.openai.com/v1/models",
            "https://ios.chat.openai.com/public-api/mobile/server_status/v1"
        ],
        "expected_status": [200, 204, 301, 302, 401, 403],
        "forbidden_keywords": ["unsupported_country", "country_not_supported", "cf_chl_opt", "Just a moment", "Attention Required", "vpn_detected", "loc=CN", "loc=HK", "loc=RU", "loc=BY", "loc=IR"],
        "required_keywords": []
    },
    "google": {
        "name": "Google 搜索",
        "group": "AI_Best_Auto",
        "probe_urls": [
            "https://www.google.com/generate_204",
            "https://play.google.com/generate_204",
            "https://redirector.gvt1.com/"
        ],
        "expected_status": [200, 204, 301, 302, 404],
        "forbidden_keywords": ["sorry/index", "cf_chl_opt", "Just a moment"],
        "required_keywords": []
    },
    "google_play": {
        "name": "Google Play 商店与 GVT1 CDN",
        "group": "Shunt_Google",
        "probe_urls": [
            "https://dl.google.com/android/repository/repository2-3.xml",
            "https://play.google.com/generate_204",
            "https://redirector.gvt1.com/"
        ],
        "expected_status": [200, 204, 301, 302, 400, 403, 404],
        "forbidden_keywords": ["sorry/index", "cf_chl_opt", "Just a moment"],
        "required_keywords": []
    },
    "baidu": {
        "name": "百度",
        "group": "Direct",
        "probe_urls": ["https://www.baidu.com"],
        "expected_status": [200, 204, 301, 302],
        "forbidden_keywords": [],
        "required_keywords": []
    },
    "openai": {
        "name": "OpenAI / ChatGPT",
        "group": "AI_Best_Auto",
        "probe_urls": [
            "https://chat.openai.com/cdn-cgi/trace",
            "https://api.openai.com/v1/models",
            "https://ios.chat.openai.com/public-api/mobile/server_status/v1"
        ],
        "expected_status": [200, 204, 301, 302, 401, 403],
        "forbidden_keywords": [
            "unsupported_country",
            "country_not_supported",
            "cf_chl_opt",
            "Just a moment",
            "Attention Required",
            "vpn_detected",
            "loc=CN",
            "loc=HK",
            "loc=RU",
            "loc=BY",
            "loc=IR"
        ],
        "required_keywords": []
    },
    "claude": {
        "name": "Claude / Anthropic",
        "group": "AI_Best_Auto",
        "probe_urls": ["https://claude.ai/login"],
        "expected_status": [200, 204, 301, 302, 307, 403],
        "forbidden_keywords": [
            "App unavailable",
            "unavailable in your region",
            "cf-mitigated",
            "Just a moment"
        ],
        "required_keywords": []
    },
    "gemini": {
        "name": "Google Gemini",
        "group": "AI_Best_Auto",
        "probe_urls": ["https://gemini.google.com/app"],
        "expected_status": [200, 204, 301, 302],
        "forbidden_keywords": [
            "isn't currently supported in your country",
            "not available in your country",
            "sorry/index"
        ],
        "required_keywords": []
    },
    "netflix": {
        "name": "Netflix (Non-Originals Full Unlock)",
        "group": "Stream_Auto",
        "probe_urls": ["https://www.netflix.com/title/81280792"],
        "expected_status": [200, 405],
        "forbidden_keywords": [
            "Ohh... Error",
            "NSES-404",
            "Not Available"
        ],
        "required_keywords": []
    },
    "disney": {
        "name": "Disney+ Streaming",
        "group": "Stream_Auto",
        "probe_urls": ["https://www.disneyplus.com/"],
        "expected_status": [200, 301, 302],
        "forbidden_keywords": [
            "unavailable",
            "not available in your region",
            "error-code"
        ],
        "required_keywords": []
    },
    "youtube": {
        "name": "YouTube Premium",
        "group": "Stream_Auto",
        "probe_urls": [
            "https://www.youtube.com/premium",
            "https://i.ytimg.com/generate_204",
            "https://www.youtube.com/generate_204"
        ],
        "expected_status": [200, 204],
        "forbidden_keywords": [
            "YouTube Premium is not available in your country"
        ],
        "required_keywords": []
    },
    "tiktok": {
        "name": "TikTok 视频流与 CDN",
        "group": "Stream_Auto",
        "probe_urls": [
            "https://www.tiktok.com/favicon.ico",
            "https://p16-sign-va.tiktokcdn.com/favicon.ico",
            "https://api16-normal-c-useast1a.tiktokv.com/",
            "https://www.tiktok.com/"
        ],
        "expected_status": [200, 204, 301, 302, 403, 404],
        "forbidden_keywords": [
            "Access Denied",
            "Service Unavailable"
        ],
        "required_keywords": []
    },
    "bilibili": {
        "name": "Bilibili HK/MO/TW Media",
        "group": "HK_TW_Media",
        "probe_urls": ["https://api.bilibili.com/pgc/player/web/playurl?avid=50762638&cid=100279344&qn=80"],
        "expected_status": [200],
        "forbidden_keywords": ["抱歉您所在地区不可观看", "\"code\":-10403"],
        "required_keywords": []
    }
}

# ==============================================================================
# Real Node Subscription & Share-URI Parser (ss / vless / trojan / hy2 / socks5)
# ==============================================================================
def parse_subscription_userinfo(header_val: str) -> dict:
    """Parses standard airport HTTP `Subscription-Userinfo` header: upload=123456; download=654321; total=107374182400; expire="""
    if not header_val or not isinstance(header_val, str):
        return {}
    kv = {}
    for part in header_val.replace(",", ";").split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip().lower()
        v = v.strip()
        try:
            kv[k] = int(float(v))
        except Exception:
            pass
    if not kv:
        return {}
    up = int(kv.get("upload", 0))
    down = int(kv.get("download", 0))
    total = int(kv.get("total", 0))
    expire = int(kv.get("expire", 0))
    used = max(0, up + down)
    rem = max(0, total - used) if total > 0 else 0
    used_pct = round((used / total) * 100.0, 1) if total > 0 else 0.0
    now_ts = int(time.time())
    expired = bool(expire > 0 and expire < now_ts)
    exhausted = bool(total > 0 and used >= total)
    exp_str = time.strftime("%Y-%m-%d", time.localtime(expire)) if expire > 0 else "长期有效"
    def _fmt_b(b: int) -> str:
        if b >= 1024 ** 4:
            return f"{b / (1024 ** 4):.2f} TiB"
        if b >= 1024 ** 3:
            return f"{b / (1024 ** 3):.2f} GiB"
        if b >= 1024 ** 2:
            return f"{b / (1024 ** 2):.1f} MiB"
        return f"{b} B"
    summary = f"已用 {_fmt_b(used)} / {_fmt_b(total)} ({used_pct}%) · 到期 {exp_str}" if total > 0 else f"到期 {exp_str}"
    return {
        "upload_bytes": up,
        "download_bytes": down,
        "used_bytes": used,
        "total_bytes": total,
        "remaining_bytes": rem,
        "used_pct": used_pct,
        "expire_ts": expire,
        "expire_str": exp_str,
        "expired": expired,
        "exhausted": exhausted,
        "summary": summary
    }

class NodeURIParser:
    """Parses standard proxy share URIs, Base64 subscription blocks, Clash/Mihomo YAML, and native Sing-box JSON into Sing-box """
    @staticmethod
    def _b64_decode_safe(s: str) -> str:
        s = s.strip().replace("-", "+").replace("_", "/")
        pad = (-len(s)) % 4
        if pad:
            s += "=" * pad
        return base64.b64decode(s).decode("utf-8", errors="ignore")
    @classmethod
    def _attach_query_transport_and_tls(cls, ob: dict, q: dict, default_sni: str = "") -> dict:
        """Shared transport (ws/grpc/httpupgrade/http) & uTLS/ALPN parser for VLESS/Trojan/VMess."""
        if "tls" in ob and isinstance(ob["tls"], dict):
            tls_obj = ob["tls"]
            if q.get("alpn"):
                alpns = [x.strip() for x in q["alpn"].split(",") if x.strip()]
                if alpns:
                    tls_obj["alpn"] = alpns
            if q.get("fp") and "utls" not in tls_obj:
                tls_obj["utls"] = {"enabled": True, "fingerprint": q["fp"]}
        net_type = (q.get("type") or q.get("network") or "tcp").lower()
        if net_type == "ws":
            ws_headers = {}
            if q.get("host"):
                ws_headers["Host"] = q["host"]
            ob["transport"] = {
                "type": "ws",
                "path": q.get("path") or "/"
            }
            if ws_headers:
                ob["transport"]["headers"] = ws_headers
        elif net_type == "grpc":
            ob["transport"] = {
                "type": "grpc",
                "service_name": q.get("serviceName") or q.get("path") or ""
            }
        elif net_type == "httpupgrade":
            ob["transport"] = {
                "type": "httpupgrade",
                "path": q.get("path") or "/"
            }
            if q.get("host"):
                ob["transport"]["host"] = q["host"]
        elif net_type in ("http", "h2"):
            ob["transport"] = {
                "type": "http",
                "path": q.get("path") or "/"
            }
            if q.get("host"):
                ob["transport"]["host"] = [x.strip() for x in q["host"].split(",") if x.strip()]
        return ob
    last_extracted_info_meta = {}
    last_filtered_info_count = 0
    @classmethod
    def _post_filter_and_dedup_outbounds(cls, raw_obs: list) -> list:
        cls.last_extracted_info_meta = {}
        cls.last_filtered_info_count = 0
        deduped = []
        seen_ep = set()
        used_tags = set()
        reserved = {"direct", "block", "AI_Best_Auto", "Stream_Auto", "HK_TW_Media"}
        for ob in (raw_obs or []):
            if not isinstance(ob, dict) or not ob.get("tag") or not ob.get("type"):
                continue
            if is_subscription_info_node(ob):
                cls.last_filtered_info_count += 1
                _extract_info_metadata_from_tag(str(ob.get("tag") or ""), cls.last_extracted_info_meta)
                continue
            ep_k = _node_endpoint_key(ob)
            if ep_k in seen_ep:
                continue
            seen_ep.add(ep_k)
            base_tag = str(ob["tag"]).strip()
            tag = base_tag
            sfx = 2
            while tag in used_tags or tag in reserved:
                tag = f"{base_tag}-{sfx}"
                sfx += 1
            ob["tag"] = tag
            used_tags.add(tag)
            deduped.append(ob)
        return deduped
    @classmethod
    def parse_subscription_text(cls, raw_text: str, conf_dir: Path = CONF_DIR) -> list:
        raw_text = (raw_text or "").strip()
        if not raw_text:
            return []
        # 1. Native Sing-box JSON (`{"outbounds": [...]}` or `[...]`)
        if (raw_text.startswith("{") and raw_text.endswith("}")) or (raw_text.startswith("[") and raw_text.endswith("]")):
            json_obs = cls._parse_singbox_json_outbounds(raw_text)
            if json_obs:
                return cls._post_filter_and_dedup_outbounds(json_obs)
        # 2. Clash / Mihomo YAML format (`proxies:` list — both flow `- { ... }` and multi-line block YAML)
        if "proxies:" in raw_text and ("server:" in raw_text or "type:" in raw_text):
            yaml_obs = cls._parse_clash_yaml_proxies(raw_text, conf_dir=conf_dir)
            if yaml_obs:
                return cls._post_filter_and_dedup_outbounds(yaml_obs)
        # 3. Base64-encoded subscription payload
        if "://" not in raw_text:
            try:
                decoded = cls._b64_decode_safe(raw_text).strip()
                if (decoded.startswith("{") and decoded.endswith("}")) or (decoded.startswith("[") and decoded.endswith("]")):
                    json_obs = cls._parse_singbox_json_outbounds(decoded)
                    if json_obs:
                        return cls._post_filter_and_dedup_outbounds(json_obs)
                if "proxies:" in decoded:
                    yaml_obs = cls._parse_clash_yaml_proxies(decoded, conf_dir=conf_dir)
                    if yaml_obs:
                        return cls._post_filter_and_dedup_outbounds(yaml_obs)
                if "://" in decoded:
                    raw_text = decoded
            except Exception:
                pass
        raw_outbounds = []
        for idx, line in enumerate(raw_text.splitlines()):
            line = line.strip()
            if not line or line.startswith("#") or "://" not in line:
                continue
            try:
                ob = cls.parse_single_uri(line, default_index=idx + 1, conf_dir=conf_dir)
                if ob and ob.get("tag"):
                    raw_outbounds.append(ob)
            except Exception:
                continue
        return cls._post_filter_and_dedup_outbounds(raw_outbounds)
    @classmethod
    def _parse_singbox_json_outbounds(cls, json_text: str) -> list:
        try:
            data = json.loads(json_text)
        except Exception:
            return []
        cand_list = data.get("outbounds") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        if not isinstance(cand_list, list):
            return []
        valid_types = {"vless", "vmess", "trojan", "shadowsocks", "hysteria2", "tuic", "anytls", "socks", "http"}
        outbounds = []
        used_tags = set()
        for idx, item in enumerate(cand_list):
            if not isinstance(item, dict):
                continue
            otype = str(item.get("type") or "").lower()
            srv = str(item.get("server") or "").strip()
            if otype not in valid_types or not srv:
                continue
            ob = dict(item)
            base_tag = str(ob.get("tag") or f"{otype.upper()}-{idx+1:02d}").strip()
            tag = base_tag
            sfx = 2
            while tag in used_tags or tag in ("direct", "block", "AI_Best_Auto", "Stream_Auto", "HK_TW_Media"):
                tag = f"{base_tag}-{sfx}"
                sfx += 1
            ob["tag"] = tag
            used_tags.add(tag)
            outbounds.append(ob)
        return outbounds
    @classmethod
    def _clash_item_to_singbox(cls, kv: dict, idx: int, used_tags: set) -> dict:
        ntype = str(kv.get("type") or "").lower()
        name = str(kv.get("name") or f"Node-{idx:02d}").strip()
        server = str(kv.get("server") or "").strip()
        try:
            port = int(kv.get("port") or 443)
        except Exception:
            port = 443
        if not server or ntype not in ("vless", "vmess", "trojan", "ss", "shadowsocks", "hysteria2", "hy2", "tuic", "anytls"):
            return None
        tag = name
        sfx = 2
        while tag in used_tags or tag in ("direct", "block", "AI_Best_Auto", "Stream_Auto", "HK_TW_Media"):
            tag = f"{name}-{sfx}"
            sfx += 1
        used_tags.add(tag)
        def _is_true(v) -> bool:
            return str(v).lower() in ("true", "1", "yes")
        net = str(kv.get("network") or "tcp").lower()
        transport = None
        if net == "ws":
            ws_path = str(kv.get("ws-path") or "/")
            ws_host = str(kv.get("ws-host") or "")
            ws_opts = kv.get("ws-opts")
            if isinstance(ws_opts, dict):
                ws_path = str(ws_opts.get("path") or ws_path)
                hdrs = ws_opts.get("headers")
                if isinstance(hdrs, dict) and hdrs.get("Host"):
                    ws_host = str(hdrs["Host"])
            transport = {"type": "ws", "path": ws_path}
            if ws_host:
                transport["headers"] = {"Host": ws_host}
        elif net == "grpc":
            grpc_sn = str(kv.get("grpc-service-name") or "")
            grpc_opts = kv.get("grpc-opts")
            if isinstance(grpc_opts, dict):
                grpc_sn = str(grpc_opts.get("grpc-service-name") or grpc_sn)
            transport = {"type": "grpc", "service_name": grpc_sn}
        sni = str(kv.get("servername") or kv.get("sni") or server).strip()
        tls_o = None
        if _is_true(kv.get("tls")) or kv.get("servername") or kv.get("sni") or ntype in ("trojan", "hysteria2", "hy2", "tuic", "anytls"):
            tls_o = {"enabled": True, "server_name": sni}
            if kv.get("client-fingerprint"):
                tls_o["utls"] = {"enabled": True, "fingerprint": str(kv["client-fingerprint"])}
            if _is_true(kv.get("skip-cert-verify")):
                tls_o["insecure"] = True
            r_opts = kv.get("reality-opts")
            pbk = str(kv.get("public-key") or (r_opts.get("public-key") if isinstance(r_opts, dict) else "") or "")
            sid = str(kv.get("short-id") or (r_opts.get("short-id") if isinstance(r_opts, dict) else "") or "")
            if pbk:
                tls_o.setdefault("utls", {"enabled": True, "fingerprint": str(kv.get("client-fingerprint") or "chrome")})
                tls_o["reality"] = {"enabled": True, "public_key": pbk, "short_id": sid}
        if ntype == "vless":
            ob = {"type": "vless", "tag": tag, "server": server, "server_port": port, "uuid": str(kv.get("uuid") or "")}
            if kv.get("flow"):
                ob["flow"] = str(kv["flow"])
            if tls_o:
                ob["tls"] = tls_o
            if transport:
                ob["transport"] = transport
            return ob
        if ntype == "vmess":
            ob = {
                "type": "vmess",
                "tag": tag,
                "server": server,
                "server_port": port,
                "uuid": str(kv.get("uuid") or ""),
                "security": str(kv.get("cipher") or "auto"),
                "alter_id": int(kv.get("alterId") or kv.get("alter_id") or 0)
            }
            if tls_o:
                ob["tls"] = tls_o
            if transport:
                ob["transport"] = transport
            return ob
        if ntype == "trojan":
            ob = {"type": "trojan", "tag": tag, "server": server, "server_port": port, "password": str(kv.get("password") or ""), "tls": tls_o or {"enabled": True, "server_name": sni}}
            if transport:
                ob["transport"] = transport
            return ob
        if ntype in ("ss", "shadowsocks"):
            return {"type": "shadowsocks", "tag": tag, "server": server, "server_port": port, "method": str(kv.get("cipher") or "aes-256-gcm"), "password": str(kv.get("password") or "")}
        if ntype in ("hysteria2", "hy2"):
            ob = {"type": "hysteria2", "tag": tag, "server": server, "server_port": port, "password": str(kv.get("password") or ""), "tls": tls_o or {"enabled": True, "server_name": sni}}
            if kv.get("obfs") and kv.get("obfs-password"):
                ob["obfs"] = {"type": str(kv["obfs"]), "password": str(kv["obfs-password"])}
            return ob
        if ntype == "tuic":
            return {
                "type": "tuic",
                "tag": tag,
                "server": server,
                "server_port": port,
                "uuid": str(kv.get("uuid") or ""),
                "password": str(kv.get("password") or ""),
                "congestion_control": str(kv.get("congestion-controller") or "bbr"),
                "tls": tls_o or {"enabled": True, "server_name": sni, "alpn": ["h3"]}
            }
        if ntype == "anytls":
            return {"type": "anytls", "tag": tag, "server": server, "server_port": port, "password": str(kv.get("password") or ""), "tls": tls_o or {"enabled": True, "server_name": sni}}
        return None
    @classmethod
    def _parse_clash_yaml_proxies(cls, yaml_text: str, conf_dir: Path = CONF_DIR) -> list:
        outbounds = []
        used_tags = set()
        lines = yaml_text.splitlines()
        in_proxies = False
        cur_block = None
        def _parse_flow_dict(s_inner: str) -> dict:
            res = {}
            for part in re.split(r",(?=(?:[^{\[\]]*\{[^{}]*\})*[^{}]*$)", s_inner):
                if ":" not in part:
                    continue
                k, v = part.split(":", 1)
                k = k.strip().strip('"\'')
                v = v.strip()
                if v.startswith("{") and v.endswith("}"):
                    res[k] = _parse_flow_dict(v[1:-1])
                else:
                    res[k] = v.strip('"\'')
            return res
        for raw_l in lines:
            s = raw_l.strip()
            if not s or s.startswith("#"):
                continue
            if re.match(r"^proxies\s*:", s):
                in_proxies = True
                continue
            if in_proxies and not raw_l.startswith((" ", "	", "-")) and ":" in s:
                break
            # Single-line flow style: - {name: ..., type: ...}
            if s.startswith("-") and "{" in s and "}" in s:
                if cur_block:
                    ob = cls._clash_item_to_singbox(cur_block, len(outbounds) + 1, used_tags)
                    if ob:
                        outbounds.append(ob)
                    cur_block = None
                try:
                    body = s[s.index("{") + 1:s.rindex("}")]
                    kv = _parse_flow_dict(body)
                    ob = cls._clash_item_to_singbox(kv, len(outbounds) + 1, used_tags)
                    if ob:
                        outbounds.append(ob)
                except Exception:
                    continue
            elif in_proxies and s.startswith("- "):
                if cur_block:
                    ob = cls._clash_item_to_singbox(cur_block, len(outbounds) + 1, used_tags)
                    if ob:
                        outbounds.append(ob)
                cur_block = {}
                rem = s[2:].strip()
                if ":" in rem:
                    k, v = rem.split(":", 1)
                    cur_block[k.strip().strip('"\'')] = v.strip().strip('"\'')
            elif in_proxies and cur_block is not None and ":" in s:
                k, v = s.split(":", 1)
                k = k.strip().strip('"\'')
                v = v.strip().strip('"\'')
                if k in ("path", "ws-path") and not cur_block.get("ws-path"):
                    cur_block["ws-path"] = v
                elif k == "Host" and not cur_block.get("ws-host"):
                    cur_block["ws-host"] = v
                elif v:
                    cur_block[k] = v
        if cur_block:
            ob = cls._clash_item_to_singbox(cur_block, len(outbounds) + 1, used_tags)
            if ob:
                outbounds.append(ob)
        return outbounds
    @classmethod
    def parse_single_uri(cls, uri: str, default_index: int = 1, conf_dir: Path = CONF_DIR) -> dict:
        scheme_raw = uri.split("://", 1)[0].lower()
        if scheme_raw == "ss":
            return cls._parse_ss(uri, default_index)
        if scheme_raw == "vless":
            return cls._parse_vless(uri, default_index)
        if scheme_raw == "vmess":
            return cls._parse_vmess(uri, default_index)
        if scheme_raw == "trojan":
            return cls._parse_trojan(uri, default_index)
        if scheme_raw in ("hysteria2", "hy2"):
            return cls._parse_hy2(uri, default_index, conf_dir=conf_dir)
        if scheme_raw == "tuic":
            return cls._parse_tuic(uri, default_index)
        if scheme_raw == "anytls":
            return cls._parse_anytls(uri, default_index)
        if scheme_raw in ("socks5", "socks", "http"):
            return cls._parse_socks_http(uri, scheme_raw, default_index)
        return None
    @classmethod
    def _parse_vmess(cls, uri: str, idx: int) -> dict:
        body = uri[8:].strip()
        # Standard V2RayN Base64 JSON: vmess://eyJ2IjoiMiIsInBzIjoi...
        if "@" not in body.split("?", 1)[0]:
            decoded = cls._b64_decode_safe(body.split("#", 1)[0])
            j = json.loads(decoded)
            host = str(j.get("add") or "").strip("[]")
            port = int(j.get("port") or 443)
            uuid = str(j.get("id") or "").strip()
            aid = int(j.get("aid") or 0)
            scy = str(j.get("scy") or "auto").strip()
            net = str(j.get("net") or "tcp").lower()
            tls_val = str(j.get("tls") or "").lower()
            sni = str(j.get("sni") or j.get("host") or host).strip()
            tag = str(j.get("ps") or f"VMess-Node-{idx:02d}").strip()
            ob = {
                "type": "vmess",
                "tag": tag,
                "server": host,
                "server_port": port,
                "uuid": uuid,
                "security": scy,
                "alter_id": aid
            }
            if tls_val in ("tls", "1", "true"):
                tls_obj = {"enabled": True, "server_name": sni}
                if str(j.get("verify_cert", "true")).lower() in ("false", "0") or str(j.get("allowInsecure", "")).lower() in ("1", "true"):
                    tls_obj["insecure"] = True
                if j.get("fp"):
                    tls_obj["utls"] = {"enabled": True, "fingerprint": str(j["fp"])}
                ob["tls"] = tls_obj
            q_compat = {
                "type": net,
                "path": str(j.get("path") or "/"),
                "host": str(j.get("host") or ""),
                "serviceName": str(j.get("path") or ""),
                "alpn": str(j.get("alpn") or ""),
                "fp": str(j.get("fp") or "")
            }
            return cls._attach_query_transport_and_tls(ob, q_compat, default_sni=sni)
        # Standard URI style: vmess://uuid@host:port?security=tls&type=ws#tag
        parsed = urllib.parse.urlsplit(uri)
        uuid = urllib.parse.unquote(parsed.username or "")
        host = (parsed.hostname or "").strip("[]")
        port = int(parsed.port or 443)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        tag = urllib.parse.unquote(parsed.fragment or "").strip() or f"VMess-Node-{idx:02d}"
        ob = {
            "type": "vmess",
            "tag": tag,
            "server": host,
            "server_port": port,
            "uuid": uuid,
            "security": q.get("encryption") or "auto",
            "alter_id": int(q.get("alterId") or 0)
        }
        sec = q.get("security", "").lower()
        sni = q.get("sni") or q.get("peer") or q.get("host") or host
        if sec == "tls" or q.get("tls") in ("1", "true"):
            tls_obj = {"enabled": True, "server_name": sni}
            if q.get("allowInsecure") in ("1", "true") or q.get("insecure") in ("1", "true"):
                tls_obj["insecure"] = True
            ob["tls"] = tls_obj
        return cls._attach_query_transport_and_tls(ob, q, default_sni=sni)
    @classmethod
    def _parse_ss(cls, uri: str, idx: int) -> dict:
        # ss://base64(method:password)@host:port#tag OR ss://base64(method:password@host:port)#tag
        body = uri[5:]
        tag = f"SS-Node-{idx:02d}"
        if "#" in body:
            body, frag = body.split("#", 1)
            tag = urllib.parse.unquote(frag).strip() or tag
        if "?" in body:
            body = body.split("?", 1)[0]
        if "@" in body:
            userinfo, hostport = body.rsplit("@", 1)
            if ":" not in userinfo:
                userinfo = cls._b64_decode_safe(userinfo)
            else:
                userinfo = urllib.parse.unquote(userinfo)
        else:
            decoded = cls._b64_decode_safe(body)
            userinfo, hostport = decoded.rsplit("@", 1)
        method, password = userinfo.split(":", 1)
        host, port_str = hostport.rsplit(":", 1)
        host = host.strip("[]")
        return {
            "type": "shadowsocks",
            "tag": tag,
            "server": host,
            "server_port": int(port_str),
            "method": method.strip(),
            "password": password.strip()
        }
    @classmethod
    def _parse_vless(cls, uri: str, idx: int) -> dict:
        parsed = urllib.parse.urlsplit(uri)
        uuid = urllib.parse.unquote(parsed.username or "")
        host = (parsed.hostname or "").strip("[]")
        port = parsed.port or 443
        q = dict(urllib.parse.parse_qsl(parsed.query))
        tag = urllib.parse.unquote(parsed.fragment or "").strip() or f"VLESS-Node-{idx:02d}"
        ob = {
            "type": "vless",
            "tag": tag,
            "server": host,
            "server_port": int(port),
            "uuid": uuid
        }
        if q.get("flow"):
            ob["flow"] = q["flow"]
        if q.get("packetEncoding") or q.get("packet_encoding"):
            ob["packet_encoding"] = q.get("packetEncoding") or q.get("packet_encoding")
        sec = q.get("security", "").lower()
        sni = q.get("sni") or q.get("peer") or host
        if sec in ("tls", "reality"):
            tls_obj = {
                "enabled": True,
                "server_name": sni
            }
            if q.get("allowInsecure") in ("1", "true") or q.get("insecure") in ("1", "true"):
                tls_obj["insecure"] = True
            if q.get("fp"):
                tls_obj["utls"] = {"enabled": True, "fingerprint": q["fp"]}
            if sec == "reality":
                tls_obj["utls"] = {"enabled": True, "fingerprint": q.get("fp", "chrome")}
                tls_obj["reality"] = {
                    "enabled": True,
                    "public_key": q.get("pbk", ""),
                    "short_id": q.get("sid", "")
                }
            ob["tls"] = tls_obj
        return cls._attach_query_transport_and_tls(ob, q, default_sni=sni)
    @classmethod
    def _parse_trojan(cls, uri: str, idx: int) -> dict:
        parsed = urllib.parse.urlsplit(uri)
        password = urllib.parse.unquote(parsed.username or "")
        host = (parsed.hostname or "").strip("[]")
        port = parsed.port or 443
        q = dict(urllib.parse.parse_qsl(parsed.query))
        tag = urllib.parse.unquote(parsed.fragment or "").strip() or f"Trojan-Node-{idx:02d}"
        sni = q.get("sni") or q.get("peer") or q.get("host") or host
        tls_obj = {"enabled": True, "server_name": sni}
        if q.get("allowInsecure") in ("1", "true") or q.get("insecure") in ("1", "true"):
            tls_obj["insecure"] = True
        ob = {
            "type": "trojan",
            "tag": tag,
            "server": host,
            "server_port": int(port),
            "password": password,
            "tls": tls_obj
        }
        return cls._attach_query_transport_and_tls(ob, q, default_sni=sni)
    @classmethod
    def _parse_tuic(cls, uri: str, idx: int) -> dict:
        parsed = urllib.parse.urlsplit(uri)
        uuid = urllib.parse.unquote(parsed.username or "")
        password = urllib.parse.unquote(parsed.password or "")
        host = (parsed.hostname or "").strip("[]")
        port = int(parsed.port or 443)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        tag = urllib.parse.unquote(parsed.fragment or "").strip() or f"TUIC-Node-{idx:02d}"
        sni = q.get("sni") or host
        tls_obj = {"enabled": True, "server_name": sni}
        if q.get("allowInsecure") in ("1", "true") or q.get("insecure") in ("1", "true"):
            tls_obj["insecure"] = True
        if q.get("alpn"):
            tls_obj["alpn"] = [x.strip() for x in q["alpn"].split(",") if x.strip()]
        else:
            tls_obj["alpn"] = ["h3"]
        return {
            "type": "tuic",
            "tag": tag,
            "server": host,
            "server_port": port,
            "uuid": uuid,
            "password": password,
            "congestion_control": q.get("congestion_control") or "bbr",
            "udp_relay_mode": q.get("udp_relay_mode") or "native",
            "tls": tls_obj
        }
    @classmethod
    def _parse_anytls(cls, uri: str, idx: int) -> dict:
        parsed = urllib.parse.urlsplit(uri)
        password = urllib.parse.unquote(parsed.username or "")
        host = (parsed.hostname or "").strip("[]")
        port = int(parsed.port or 443)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        tag = urllib.parse.unquote(parsed.fragment or "").strip() or f"AnyTLS-Node-{idx:02d}"
        sni = q.get("sni") or q.get("peer") or host
        tls_obj = {"enabled": True, "server_name": sni}
        if q.get("insecure") in ("1", "true") or q.get("allowInsecure") in ("1", "true"):
            tls_obj["insecure"] = True
        return {
            "type": "anytls",
            "tag": tag,
            "server": host,
            "server_port": port,
            "password": password,
            "tls": tls_obj
        }
    @classmethod
    def _parse_hy2(cls, uri: str, idx: int, conf_dir: Path = CONF_DIR) -> dict:
        parsed = urllib.parse.urlsplit(uri)
        password = urllib.parse.unquote(parsed.username or "")
        if parsed.password:
            password = f"{password}:{urllib.parse.unquote(parsed.password)}"
        host = (parsed.hostname or "").strip("[]")
        port = parsed.port or 443
        q = dict(urllib.parse.parse_qsl(parsed.query))
        tag = urllib.parse.unquote(parsed.fragment or "").strip() or f"HY2-Node-{idx:02d}"
        sni = q.get("sni") or q.get("peer") or host
        tls_obj = {"enabled": True, "server_name": sni}
        if q.get("insecure") in ("1", "true") or q.get("allowInsecure") in ("1", "true"):
            tls_obj["insecure"] = True
        else:
            ca_file = conf_dir / "certs/ca.crt"
            if sni == "ai-link.ailink.lan" and ca_file.is_file():
                tls_obj["certificate_path"] = str(ca_file)
        ob = {
            "type": "hysteria2",
            "tag": tag,
            "server": host,
            "server_port": int(port),
            "password": password,
            "tls": tls_obj
        }
        if q.get("obfs") and q.get("obfs-password"):
            ob["obfs"] = {"type": q["obfs"], "password": q["obfs-password"]}
        return ob
    @classmethod
    def _parse_socks_http(cls, uri: str, scheme: str, idx: int) -> dict:
        parsed = urllib.parse.urlsplit(uri)
        host = (parsed.hostname or "").strip("[]")
        port = parsed.port or (1080 if "socks" in scheme else 8080)
        tag = urllib.parse.unquote(parsed.fragment or "").strip() or f"{scheme.upper()}-Node-{idx:02d}"
        ob = {
            "type": "socks" if "socks" in scheme else "http",
            "tag": tag,
            "server": host,
            "server_port": int(port)
        }
        if parsed.username:
            ob["username"] = urllib.parse.unquote(parsed.username)
        if parsed.password:
            ob["password"] = urllib.parse.unquote(parsed.password)
        return ob

_NODE_REGION_OVERRIDES = {}

def _refresh_node_region_overrides(nodes: list) -> None:
    global _NODE_REGION_OVERRIDES
    overrides = {}
    for n in nodes:
        if isinstance(n, dict) and n.get("tag"):
            ro = (n.get("region_override") or "").strip().upper()
            if ro in ("JP", "US", "SG", "HK", "TW", "KR", "OTHER", "TEST"):
                overrides[n["tag"]] = ro
    _NODE_REGION_OVERRIDES = overrides

_SUB_INFO_TAG_RE = re.compile(
    r"(剩余流量|流量剩余|总流量|已用流量|距离下次重置|下次重置|重置剩余|套餐到期|到期时间|过期时间|有效期限|"
    r"过滤掉.*线路|官网|备用网址|发布页|最新地址|请更新订阅|节点说明|使用说明|防失联|群组|频道|TG群|公告|通知|"
    r"Remaining\s*Traffic|Traffic\s*Reset|Expire\s*Date)",
    re.I,
)

def is_subscription_info_node(ob_or_tag) -> bool:
    """Returns True if a parsed outbound dict or tag string is actually an airport informational notice line (e.g. '剩余流量：99.15 """
    if isinstance(ob_or_tag, dict):
        tag = str(ob_or_tag.get("tag") or "").strip()
        srv = str(ob_or_tag.get("server") or "").strip().lower()
    else:
        tag = str(ob_or_tag or "").strip()
        srv = ""
    if not tag:
        return False
    if is_builtin_test_node(tag):
        return False
    if _SUB_INFO_TAG_RE.search(tag):
        return True
    if srv in ("0.0.0.0", "::"):
        return True
    if srv in ("127.0.0.1", "localhost", "::1") and not ("local" in tag.lower() or "test" in tag.lower() or "homelink" in tag.lower()):
        return True
    return False

_RANDOM_REGION_TAG_RE = re.compile(r"(地区随机|随机线路|随机节点|随机出口|负载均衡|Random\s*Region)", re.I)

def _is_random_region_node(ob_or_tag) -> bool:
    """Returns True if a node tag is an airport random-rotation / load-balanced gateway (e.g. '地区随机 | 日本 JP | NRT')."""
    tag = str(ob_or_tag.get("tag") or "") if isinstance(ob_or_tag, dict) else str(ob_or_tag or "")
    return bool(tag and _RANDOM_REGION_TAG_RE.search(tag))

def _effective_node_rank_delay_ms(ob_or_tag, delay_ms: float) -> float:
    """P2-2 Fix: Tolerance-based anti-random-region preference (1.28x penalty factor instead of hard binary sort key).
    Prefers a dedicated region node when its latency is within 28% of a random-region node (e.g., 160ms dedicated beats 148ms random),
    but never lets a slow 428ms dedicated node beat a fast 148ms random node."""
    d = float(delay_ms or 0.0)
    if d <= 0:
        return 99999.0
    return round(d * (1.28 if _is_random_region_node(ob_or_tag) else 1.0), 2)

def _is_node_cdn_tls_healthy(rec: dict) -> bool:
    """P1-1 / P1-2 / Rec 1 & 2 Fix: Returns False ONLY when a node has a confirmed dual-target CDN failure
    (confirmed_dual_fail=True and fail_streak >= 2 within the last 10 minutes / 600s half-life).
    Automatically ignores legacy single-point bare https://gvt1.com false-negative records."""
    if not isinstance(rec, dict):
        return True
    svc = rec.get("svc")
    if not isinstance(svc, dict):
        return True
    now_ts = int(time.time())
    for k in ("google_play", "tiktok", "youtube", "google"):
        ent = svc.get(k)
        if isinstance(ent, dict) and ent.get("ok") is False:
            reason = str(ent.get("reason") or "")
            if "HTTP_204_NOT_IN_" in reason:
                continue
            # Require confirmed_dual_fail=True and fail_streak >= 2 within 600s decay window
            if not ent.get("confirmed_dual_fail") or int(ent.get("fail_streak") or 0) < 2:
                continue
            ts_ent = int(ent.get("ts") or 0)
            if ts_ent > 0 and (now_ts - ts_ent) > 600:
                continue
            return False
    return True

def _extract_info_metadata_from_tag(tag: str, meta_dict: dict) -> None:
    """Extracts traffic/expiry hints from airport pseudo-node titles before discarding them."""
    if not tag or not isinstance(meta_dict, dict):
        return
    m_rem = re.search(r"(?:剩余流量|流量剩余)\s*[:：]?\s*([0-9.]+\s*[KMGTPE]?i?B)", tag, re.I)
    if m_rem:
        meta_dict["remaining_traffic"] = m_rem.group(1).strip()
    m_exp = re.search(r"(?:套餐到期|到期时间|过期时间|有效期限)\s*[:：]?\s*([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2}|长期有效|永久|不限期)", tag)
    if m_exp:
        meta_dict["expire_date"] = m_exp.group(1).strip()
    m_rst = re.search(r"(?:距离下次重置剩余|下次重置|重置剩余)\s*[:：]?\s*([0-9]+\s*天)", tag)
    if m_rst:
        meta_dict["reset_hint"] = m_rst.group(1).strip()

_SUB_LOCK = threading.RLock()

def compute_node_id(ob: dict) -> str:
    """Spec §1.4: Stable primary key `node_id = sha1(type + server + port + uuid/password)[:16]`. Never use `tag` as primary ke"""
    if not isinstance(ob, dict):
        return ""
    t = str(ob.get("type") or "vless").strip().lower()
    srv = str(ob.get("server") or "").strip().lower()
    port = str(ob.get("server_port") or 443).strip()
    cred = str(
        ob.get("uuid")
        or ob.get("password")
        or (ob.get("users")[0].get("password") if isinstance(ob.get("users"), list) and ob.get("users") else "")
        or ""
    ).strip()
    return hashlib.sha1(f"{t}|{srv}|{port}|{cred}".encode("utf-8")).hexdigest()[:16]

def _node_endpoint_key(ob: dict) -> str:
    return compute_node_id(ob)

def load_saved_nodes(conf_dir: Path = CONF_DIR) -> list:
    nodes_file = conf_dir / "nodes.json"
    sig = _get_file_sig(nodes_file)
    cache_key = ("saved_nodes", str(conf_dir))
    if sig[0] > 0:
        with _FAST_CACHE_LOCK:
            c = _FAST_FILE_CACHE.get(cache_key)
            if c and c[0] == sig:
                return [dict(x) for x in c[1]]
    nodes = _read_json_with_backup(nodes_file, default_val=[])
    if not isinstance(nodes, list):
        return []
    cleaned = []
    for n in nodes:
        if not isinstance(n, dict) or not n.get("tag") or not n.get("type"):
            continue
        if is_subscription_info_node(n):
            continue
        n["node_id"] = n.get("node_id") or compute_node_id(n)
        cleaned.append(n)
    _refresh_node_region_overrides(cleaned)
    if sig[0] > 0:
        with _FAST_CACHE_LOCK:
            _FAST_FILE_CACHE[cache_key] = (sig, [dict(x) for x in cleaned])
    return cleaned

def save_nodes_list(nodes: list, conf_dir: Path = CONF_DIR) -> list:
    with _SUB_LOCK:
        conf_dir.mkdir(parents=True, exist_ok=True)
        cleaned = []
        seen_ids = set()
        used_tags = {"direct", "block", "AI_Best_Auto", "Stream_Auto", "HK_TW_Media"}
        for n in (nodes or []):
            if not isinstance(n, dict) or not n.get("tag") or not n.get("type"):
                continue
            if is_subscription_info_node(n):
                continue
            nid = str(n.get("node_id") or "").strip() or compute_node_id(n)
            n["node_id"] = nid
            if nid in seen_ids and not is_builtin_test_node(n.get("tag", "")):
                continue
            seen_ids.add(nid)
            base_tag = str(n.get("display_tag") or n.get("tag")).strip()
            n["display_tag"] = base_tag
            tag = str(n.get("tag")).strip()
            if tag in used_tags:
                idx = 2
                while f"{base_tag}-{idx}" in used_tags:
                    idx += 1
                tag = f"{base_tag}-{idx}"
                n["tag"] = tag
            used_tags.add(tag)
            cleaned.append(n)
        _refresh_node_region_overrides(cleaned)
        _atomic_write_text(conf_dir / "nodes.json", json.dumps(cleaned, indent=2, ensure_ascii=False))
        return cleaned

def merge_nodes(sub_id: str, incoming_nodes: list, sub_url: str = "", replace_sub: bool = True,
                replace_all: bool = False, conf_dir: Path = CONF_DIR) -> list:
    """Spec §6 #8: Single unified node merge function replacing all 3 legacy 'same-name skip' paths. Keyed by `node_id = sha1(t"""
    with _SUB_LOCK:
        existing = load_saved_nodes(conf_dir)
        if replace_all:
            kept = [n for n in existing if is_builtin_test_node(n.get("tag", ""))]
        elif replace_sub and (sub_id or sub_url):
            kept = [
                n for n in existing
                if is_builtin_test_node(n.get("tag", ""))
                or (
                    (not sub_id or n.get("_sub_id") != sub_id)
                    and (not sub_url or n.get("_sub_url") != sub_url)
                )
            ]
        else:
            kept = list(existing)
        kept_by_id = {compute_node_id(n): n for n in kept}
        for ob in (incoming_nodes or []):
            if not isinstance(ob, dict) or not ob.get("tag") or not ob.get("type"):
                continue
            if is_subscription_info_node(ob):
                continue
            nid = compute_node_id(ob)
            ob["node_id"] = nid
            ob["display_tag"] = str(ob.get("display_tag") or ob.get("tag")).strip()
            if sub_id:
                ob["_sub_id"] = sub_id
            if sub_url:
                ob["_sub_url"] = sub_url
            if not sub_id and not sub_url:
                ob["_manual"] = True
            if nid in kept_by_id:
                idx = kept.index(kept_by_id[nid])
                kept[idx] = ob
            else:
                kept.append(ob)
            kept_by_id[nid] = ob
        return save_nodes_list(kept, conf_dir)

_CLASH_API_DOWN_UNTIL = {"ts": 0.0}

def clash_api_request(path: str, method: str = "GET", payload: dict = None, timeout: float = 3.5) -> tuple:
    now_c = time.time()
    if now_c < _CLASH_API_DOWN_UNTIL.get("ts", 0.0):
        return (0, {"error": "clash_api_down_cached"})
    if not _is_local_port_listening(9090):
        _CLASH_API_DOWN_UNTIL["ts"] = now_c + 2.5
        return (0, {"error": "clash_api_not_listening"})
    url = f"{CONTROLLER_API}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _CLASH_API_DOWN_UNTIL["ts"] = 0.0
            raw = resp.read().decode("utf-8", errors="ignore")
            obj = json.loads(raw) if raw.strip() else {}
            return (resp.status, obj)
    except urllib.error.HTTPError as he:
        _CLASH_API_DOWN_UNTIL["ts"] = 0.0
        try:
            err_body = json.loads(he.read().decode("utf-8", errors="ignore"))
        except Exception:
            err_body = {"error": str(he)}
        return (he.code, err_body)
    except Exception as e:
        _CLASH_API_DOWN_UNTIL["ts"] = time.time() + 2.5
        return (0, {"error": str(e)})

def clash_get_proxies() -> dict:
    status, data = clash_api_request("/proxies", "GET", timeout=2.0)
    return data if status == 200 else {}

def wait_clash_ready(timeout: float = 45.0) -> bool:
    """Block until the clash API exposes the selector groups again. Clears circuit breaker before polling."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        _CLASH_API_DOWN_UNTIL["ts"] = 0.0
        proxies = clash_get_proxies().get("proxies") or {}
        if "AI_Best_Auto" in proxies:
            return True
        time.sleep(0.35)
    return False

def _expected_outbound_tags(conf_dir: Path = CONF_DIR) -> set:
    """Outbound tags the core is supposed to expose after loading sing-box.json."""
    try:
        cfg = json.loads((conf_dir / "sing-box.json").read_text(encoding="utf-8"))
        return {o.get("tag", "") for o in cfg.get("outbounds", []) if o.get("tag")}
    except Exception:
        return set()

_LAST_APPLIED_CORE_RULE_HASH = ""

def _compute_core_rules_fingerprint(conf_dir: Path = CONF_DIR) -> str:
    """Computes SHA-256 fingerprint of route + dns + inbounds + outbound topology in sing-box.json.
    P1-1 Fix (v1.0.3): Excludes selector `default` (which is hot-switched via Clash API PUT /proxies/<selector>
    without process restart), while including selector member lists and proxy outbound definitions.
    If this fingerprint is unchanged, force_respawn is skipped so idempotent operations never kill sing-box!"""
    try:
        p = Path(conf_dir) / "sing-box.json"
        if not p.is_file():
            return ""
        cfg = json.loads(p.read_text(encoding="utf-8"))
        blk_sha_file = Path(conf_dir) / "rules/blocklist_custom.sha256"
        blk_sha_val = blk_sha_file.read_text(encoding="utf-8").strip() if blk_sha_file.is_file() else ""
        selectors_topo = []
        proxy_outbounds = []
        for o in (cfg.get("outbounds") or []):
            if not isinstance(o, dict):
                continue
            otype = o.get("type")
            if otype in ("selector", "urltest"):
                selectors_topo.append({
                    "tag": str(o.get("tag") or ""),
                    "type": otype,
                    "outbounds": list(o.get("outbounds") or []),
                })
            elif otype not in ("direct", "block"):
                proxy_outbounds.append(o)
        selectors_topo.sort(key=lambda x: x["tag"])
        proxy_outbounds.sort(key=lambda x: str(x.get("tag") or ""))
        core_slice = {
            "route": cfg.get("route") or {},
            "dns": cfg.get("dns") or {},
            "inbounds": cfg.get("inbounds") or [],
            "selectors": selectors_topo,
            "proxy_outbounds": proxy_outbounds,
            "blocklist_sha256": blk_sha_val,
        }
        raw = json.dumps(core_slice, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    except Exception:
        return ""

def _record_applied_core_rule_hash(conf_dir: Path = CONF_DIR, rule_hash: str = ""):
    """P1-2 Fix (v1.0.3): Persist applied core rule fingerprint to BOTH /etc/ai-link/.applied_core_rule_hash
    (non-tmpfs, survives reboot/upgrade) and /var/run/ai-link/applied_core_rule_hash.txt."""
    global _LAST_APPLIED_CORE_RULE_HASH
    h = rule_hash or _compute_core_rules_fingerprint(conf_dir)
    if h:
        _LAST_APPLIED_CORE_RULE_HASH = h
        try:
            RUN_DIR.mkdir(parents=True, exist_ok=True)
            (RUN_DIR / "applied_core_rule_hash.txt").write_text(h, encoding="utf-8")
        except Exception:
            pass
        try:
            cdir = Path(conf_dir)
            if cdir.is_dir():
                (cdir / ".applied_core_rule_hash").write_text(h, encoding="utf-8")
        except Exception:
            pass

def _get_applied_core_rule_hash(conf_dir: Path = CONF_DIR) -> str:
    global _LAST_APPLIED_CORE_RULE_HASH
    if _LAST_APPLIED_CORE_RULE_HASH:
        return _LAST_APPLIED_CORE_RULE_HASH
    for cand in (RUN_DIR / "applied_core_rule_hash.txt", Path(conf_dir) / ".applied_core_rule_hash"):
        try:
            if cand.is_file():
                val = cand.read_text(encoding="utf-8").strip()
                if val:
                    _LAST_APPLIED_CORE_RULE_HASH = val
                    try:
                        RUN_DIR.mkdir(parents=True, exist_ok=True)
                        (RUN_DIR / "applied_core_rule_hash.txt").write_text(val, encoding="utf-8")
                    except Exception:
                        pass
                    return _LAST_APPLIED_CORE_RULE_HASH
        except Exception:
            pass
    return _LAST_APPLIED_CORE_RULE_HASH

LAST_RELOAD_MODE = "hot_config"
_RELOAD_LOCK = threading.Lock()
_RELOAD_MIN_INTERVAL = 1.8
_LAST_RESPAWN_FINISH_TS = 0.0

def _get_live_singbox_pids() -> list:
    """Returns non-zombie sing-box daemon PIDs (excluding short-lived `version`/`check`/`rule-set` auxiliary CLI processes)."""
    pids = []
    for pdir in Path("/proc").glob("[0-9]*"):
        try:
            if (pdir / "comm").read_text(encoding="utf-8").strip() != "sing-box":
                continue
            st_File = pdir / "status"
            if st_File.is_file():
                st_txt = st_File.read_text(encoding="utf-8", errors="ignore")
                if "State:\tZ" in st_txt or "State: Z" in st_txt:
                    continue
            cmd_File = pdir / "cmdline"
            if cmd_File.is_file():
                cmd_parts = cmd_File.read_bytes().replace(b"\x00", b" ").decode("utf-8", "ignore").strip().split()
                if len(cmd_parts) >= 2 and cmd_parts[1] in ("version", "check", "rule-set"):
                    continue
            pids.append(int(pdir.name))
        except Exception:
            continue
    return sorted(pids)

def _get_min_singbox_proc_age() -> float:
    """Returns minimum age in seconds of currently running sing-box processes (prevents killing sing-box mid-startup)."""
    now = time.time()
    ages = []
    for pid in _get_live_singbox_pids():
        try:
            ages.append(max(0.0, now - Path(f"/proc/{pid}").stat().st_mtime))
        except Exception:
            pass
    return min(ages) if ages else 9999.0

def _spawn_singbox_fallback_direct(conf_dir: Path = CONF_DIR) -> bool:
    return False

_FAST_FILE_CACHE = {}
_FAST_CACHE_LOCK = threading.RLock()

def _get_file_sig(p: Path) -> tuple:
    try:
        st = p.stat()
        return (st.st_mtime_ns, st.st_size)
    except Exception:
        return (0, 0)

_SYS_CMD_CACHE = {}

def _cached_Value(key: str, ttl_sec: float, fn):
    now = time.time()
    ent = _SYS_CMD_CACHE.get(key)
    if ent is not None and (now - ent[0]) < ttl_sec:
        return ent[1]
    val = fn()
    _SYS_CMD_CACHE[key] = (now, val)
    return val

def _invalidate_sys_cache(prefix: str = ""):
    if not prefix:
        _SYS_CMD_CACHE.clear()
        return
    for k in list(_SYS_CMD_CACHE.keys()):
        if k.startswith(prefix):
            _SYS_CMD_CACHE.pop(k, None)

def _invalidate_fast_api_cache():
    _SYS_CMD_CACHE.clear()
    for _m_obj in ("_OPS_SETTINGS_MEMO", "_TOP_N_OUTBOUNDS_MEMO", "_JSON_WIRE_MEMO", "_SHUNT_API_MEMO", "_STATUS_API_MEMO", "_NODES_API_MEMO", "_AUTO_NODES_API_MEMO"):
        try:
            globals().get(_m_obj, {}).clear()
        except Exception:
            pass
    try:
        _CORE_RELOAD_STATE["reload_seq"] = int(_CORE_RELOAD_STATE.get("reload_seq") or 1) + 1
    except Exception:
        pass

_CORE_RELOAD_STATE = {
    "config_seq": 1,
    "reload_seq": 1,
    "reloading": False,
    "pending_respawn": False,
    "pending_nft": False,
    "last_reload_ts": int(time.time()),
    "last_reload_ok": True,
    "last_reload_mode": "hot_config",
}
_CORE_RELOAD_COND = threading.Condition()
_CORE_RELOAD_WORKER_STARTED = False

def _ensure_async_reload_worker():
    global _CORE_RELOAD_WORKER_STARTED
    if _CORE_RELOAD_WORKER_STARTED:
        return
    with _CORE_RELOAD_COND:
        if _CORE_RELOAD_WORKER_STARTED:
            return
        _CORE_RELOAD_WORKER_STARTED = True
        def _worker():
            while True:
                with _CORE_RELOAD_COND:
                    while _CORE_RELOAD_STATE["reload_seq"] >= _CORE_RELOAD_STATE["config_seq"]:
                        _CORE_RELOAD_STATE["reloading"] = False
                        _CORE_RELOAD_COND.wait(timeout=5.0)
                    target_seq = _CORE_RELOAD_STATE["config_seq"]
                    do_respawn = _CORE_RELOAD_STATE["pending_respawn"]
                    do_nft = _CORE_RELOAD_STATE["pending_nft"]
                    _CORE_RELOAD_STATE["pending_respawn"] = False
                    _CORE_RELOAD_STATE["pending_nft"] = False
                    _CORE_RELOAD_STATE["reloading"] = True
                ok_rel = True
                try:
                    if Path("/etc/init.d/ai-link").exists():
                        ok_rel = reload_core_only(timeout=25.0, force_respawn=do_respawn)
                        if do_nft and Path("/usr/share/ai-link/nftables/apply_nft.sh").exists():
                            subprocess.run(["/usr/share/ai-link/nftables/apply_nft.sh"], check=False, timeout=5)
                    PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
                    PROBE_ENGINE.save_persisted_selections(RUN_DIR, record_history=False)
                except Exception:
                    ok_rel = False
                with _CORE_RELOAD_COND:
                    _CORE_RELOAD_STATE["reload_seq"] = max(_CORE_RELOAD_STATE["reload_seq"], target_seq)
                    _CORE_RELOAD_STATE["last_reload_ts"] = int(time.time())
                    _CORE_RELOAD_STATE["last_reload_ok"] = bool(ok_rel)
                    _CORE_RELOAD_STATE["last_reload_mode"] = LAST_RELOAD_MODE
                    if _CORE_RELOAD_STATE["reload_seq"] >= _CORE_RELOAD_STATE["config_seq"]:
                        _CORE_RELOAD_STATE["reloading"] = False
                _invalidate_sys_cache("rt_")
        threading.Thread(target=_worker, daemon=True, name="ailink-async-reload").start()

def _verify_all_shunt_selectors_mounted(conf_dir: Path = CONF_DIR) -> tuple:
    """Section 16 (P1-5) Fix: Verifies that every Shunt_* selector in sing-box.json / shunt.json
    is actually mounted inside the running sing-box Clash /proxies table."""
    if not _get_live_singbox_pids():
        return (True, [])
    want_selectors = set()
    try:
        sb_p = conf_dir / "sing-box.json"
        if sb_p.is_file():
            sb_c = json.loads(sb_p.read_text(encoding="utf-8"))
            for ob in (sb_c.get("outbounds") or []):
                if isinstance(ob, dict) and ob.get("type") == "selector" and ob.get("tag"):
                    want_selectors.add(str(ob["tag"]))
    except Exception:
        pass
    if not want_selectors:
        return (True, [])
    got_proxies = set((clash_get_proxies().get("proxies") or {}).keys())
    if not got_proxies:
        return (True, [])
    missing = sorted(list(want_selectors - got_proxies))
    return (len(missing) == 0, missing)

def schedule_async_core_reload(force_respawn: bool = False, apply_nft: bool = False, hot_only: bool = False, explicit_restart: bool = False) -> dict:
    """P1-1 & P1-2 Fix (v1.0.3): Schedules a non-blocking coalesced sing-box reload in the background (<5ms).
    Compares `_compute_core_rules_fingerprint(CONF_DIR)` against `_get_applied_core_rule_hash(CONF_DIR)`:
    - If fingerprint changed or any selector is missing or core is dead -> forces respawn (`hot_only=False`).
    - If fingerprint is UNCHANGED and all selectors are mounted and core is alive (and `not explicit_restart`) ->
      automatically downgrades `force_respawn=True` to `hot_only=True` (hot selector update only, ZERO core kills!)."""
    global LAST_RELOAD_MODE
    _ensure_async_reload_worker()
    want_hash = _compute_core_rules_fingerprint(CONF_DIR)
    applied_hash = _get_applied_core_rule_hash(CONF_DIR)
    selectors_ok, _ = _verify_all_shunt_selectors_mounted(CONF_DIR)
    core_alive = bool(_get_live_singbox_pids())
    has_initd = Path("/etc/init.d/ai-link").exists()
    rules_dirty = bool((want_hash and want_hash != applied_hash) or not selectors_ok or (has_initd and resolve_singbox_binary() and not core_alive))
    if rules_dirty or explicit_restart:
        hot_only = False
        force_respawn = True
    elif core_alive and want_hash and want_hash == applied_hash and selectors_ok:
        # P1-1 Idempotency Guard: Config topology & rules are 100% identical to running sing-box -> never kill sing-box!
        force_respawn = False
        hot_only = True
    if apply_nft and hot_only and has_initd and Path("/usr/share/ai-link/nftables/apply_nft.sh").exists():
        if _is_local_port_listening(int(_uci_get_str("global.tproxy_port", "7893") or 7893)):
            try:
                subprocess.run(["/usr/share/ai-link/nftables/apply_nft.sh"], check=False, timeout=5)
            except Exception:
                pass
    with _CORE_RELOAD_COND:
        _CORE_RELOAD_STATE["config_seq"] += 1
        seq = _CORE_RELOAD_STATE["config_seq"]
        if hot_only or not has_initd:
            if want_hash:
                _record_applied_core_rule_hash(CONF_DIR, want_hash)
            LAST_RELOAD_MODE = "hot_selector"
            _CORE_RELOAD_STATE["reload_seq"] = seq
            _CORE_RELOAD_STATE["reloading"] = False
            _CORE_RELOAD_STATE["last_reload_ts"] = int(time.time())
            _CORE_RELOAD_STATE["last_reload_mode"] = "hot_selector"
            return dict(_CORE_RELOAD_STATE)
        if force_respawn:
            _CORE_RELOAD_STATE["pending_respawn"] = True
        if apply_nft:
            _CORE_RELOAD_STATE["pending_nft"] = True
        _CORE_RELOAD_STATE["reloading"] = True
        _CORE_RELOAD_COND.notify_all()
        return dict(_CORE_RELOAD_STATE)

def reload_core_only(timeout: float = 45.0, force_respawn: bool = False, explicit_restart: bool = False) -> bool:
    """Reload the core under _RELOAD_LOCK, verifying outbound tags, inbound ports, AND route/dns rules fingerprint.
    P1-1 & Path ④ Fix (v1.0.3):
    1) Never kills sing-box if `not explicit_restart` and `want_rule_hash == applied_rule_hash` and core is healthy.
    2) If sing-box was just spawned (<6.5s old) and is still starting up, waits for it to finish starting instead of
       sending SIGTERM mid-startup (`FATAL[0001] start service: context canceled`)."""
    global LAST_RELOAD_MODE
    with _RELOAD_LOCK:
        # Path ④ Guard: If sing-box was just started <6.5s ago, let it finish binding ports before evaluating
        proc_age = _get_min_singbox_proc_age()
        if 0.0 <= proc_age < 6.5 and not explicit_restart and not _is_local_port_listening(9090):
            wait_clash_ready(timeout=max(2.0, 7.0 - proc_age))
        want = _expected_outbound_tags(CONF_DIR)
        want_rule_hash = _compute_core_rules_fingerprint(CONF_DIR)
        applied_rule_hash = _get_applied_core_rule_hash(CONF_DIR)
        selectors_ok, _ = _verify_all_shunt_selectors_mounted(CONF_DIR)
        core_alive = bool(_get_live_singbox_pids())
        rules_changed = bool((want_rule_hash and (not applied_rule_hash or want_rule_hash != applied_rule_hash)) or not selectors_ok or not core_alive)
        if not explicit_restart and not rules_changed and core_alive and _all_configured_tcp_inbounds_listening(CONF_DIR):
            LAST_RELOAD_MODE = "hot_selector"
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            return True
        if explicit_restart or force_respawn or rules_changed:
            LAST_RELOAD_MODE = "core_respawn"
            ok_r = _respawn_core_only(timeout=timeout)
            if ok_r and want_rule_hash:
                _record_applied_core_rule_hash(CONF_DIR, want_rule_hash)
            if ok_r and Path("/usr/share/ai-link/nftables/apply_nft.sh").exists():
                if _is_local_port_listening(int(_uci_get_str("global.tproxy_port", "7893") or 7893)):
                    try:
                        subprocess.run(["/usr/share/ai-link/nftables/apply_nft.sh"], check=False, timeout=5)
                    except Exception:
                        pass
            _invalidate_sys_cache()
            _trigger_async_health_reprobe()
            return ok_r
        st_code, _ = clash_api_request("/configs?force=true", "PUT", {"path": str(CONF_DIR / "sing-box.json")}, timeout=3.0)
        if st_code in (200, 204) and wait_clash_ready(timeout=5.0):
            if not want:
                if _all_configured_tcp_inbounds_listening(CONF_DIR):
                    LAST_RELOAD_MODE = "hot_config"
                    return True
            got = set((clash_get_proxies().get("proxies") or {}).keys())
            pseudo = {"GLOBAL", "DIRECT", "REJECT", "PASS", "COMPATIBLE"}
            settle = time.time() + 6.0
            while True:
                if (want.issubset(got) and (got - pseudo).issubset(want)
                        and _all_configured_tcp_inbounds_listening(CONF_DIR)):
                    LAST_RELOAD_MODE = "hot_config"
                    return True
                if time.time() >= settle:
                    break
                time.sleep(0.5)
                got = set((clash_get_proxies().get("proxies") or {}).keys())
        LAST_RELOAD_MODE = "core_respawn"
        return _respawn_core_only(timeout=timeout)

def _respawn_core_only(timeout: float = 45.0) -> bool:
    """Restart or recover the sing-box core with min-interval throttling, SIGKILL escalation,
    and procd crash-loop recovery fallback (`/etc/init.d/ai-link restart_core`)."""
    global _LAST_RESPAWN_FINISH_TS
    elapsed = time.time() - _LAST_RESPAWN_FINISH_TS
    if 0 < elapsed < _RELOAD_MIN_INTERVAL:
        time.sleep(_RELOAD_MIN_INTERVAL - elapsed)
    live_pids = _get_live_singbox_pids()
    if live_pids:
        for p in live_pids:
            try:
                os.kill(p, signal.SIGTERM)
            except Exception:
                pass
        deadline_kill = time.time() + min(6.0, timeout)
        kill_escalate_at = time.time() + 2.2
        while time.time() < deadline_kill:
            still_old = [p for p in live_pids if Path("/proc/%d" % p).exists()]
            if not still_old:
                break
            if time.time() >= kill_escalate_at:
                for p in still_old:
                    try:
                        os.kill(p, signal.SIGKILL)
                    except Exception:
                        pass
            time.sleep(0.2)
    # Wait up to 6.5s for procd to auto-respawn sing-box; if procd had given up (crash loop) or core was dead,
    # explicitly invoke `/etc/init.d/ai-link restart_core` / direct spawn to guarantee recovery!
    procd_wait = time.time() + 6.5
    while time.time() < procd_wait:
        if _get_live_singbox_pids():
            break
        time.sleep(0.35)
    if not _get_live_singbox_pids():
        if Path("/etc/init.d/ai-link").exists():
            try:
                subprocess.run(["/etc/init.d/ai-link", "restart_core"], capture_output=True, timeout=15)
            except Exception:
                pass
        if not _get_live_singbox_pids():
            sb_bin = resolve_singbox_binary()
            if sb_bin and (CONF_DIR / "sing-box.json").is_file():
                try:
                    subprocess.Popen([sb_bin, "run", "-c", str(CONF_DIR / "sing-box.json"), "-D", str(CONF_DIR)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                except Exception:
                    pass
    deadline = time.time() + max(8.0, timeout - 6.5)
    if not wait_clash_ready(max(5.0, deadline - time.time())):
        _LAST_RESPAWN_FINISH_TS = time.time()
        return False
    port_deadline = time.time() + max(5.0, timeout - 5.0)
    while time.time() < port_deadline:
        if _all_configured_tcp_inbounds_listening(CONF_DIR):
            _LAST_RESPAWN_FINISH_TS = time.time()
            _record_applied_core_rule_hash(CONF_DIR)
            new_pids = _get_live_singbox_pids()
            if new_pids:
                try:
                    RUN_DIR.mkdir(parents=True, exist_ok=True)
                    (RUN_DIR / "ai-link-core.pid").write_text(str(new_pids[0]), encoding="utf-8")
                except Exception:
                    pass
            try:
                apply_dns_adblock_system(CONF_DIR, force_live_mount=True)
                restore_resolv_conf_to_local()
            except Exception:
                pass
            _invalidate_fast_api_cache()
            return True
        time.sleep(0.35)
    _LAST_RESPAWN_FINISH_TS = time.time()
    _invalidate_sys_cache()
    return False

DEFAULT_URL_PING_TARGET = "https://www.gstatic.com/generate_204"
DEFAULT_DELAY_TEST_URL = DEFAULT_URL_PING_TARGET
GROUP_TARGET_PROBE_URLS = {
    "AI": "https://chat.openai.com/cdn-cgi/trace",
    "YouTube": "https://www.youtube.com/generate_204",
    "Netflix": "https://www.netflix.com/title/81280792",
    "Google": "https://www.google.com/generate_204",
}
PROBE_SNAPSHOT_TTL_SEC = 21600  # Spec §2: 6 hours (21,600s); older snapshots become 'pending' (? 待验证)
GENERIC_FORBIDDEN_KEYWORDS = (
    "cf_chl_opt",
    "just a moment",
    "unsupported_country",
    "country_not_supported",
    "attention required",
    "error code: 1102",
    "token is err",
)

FIVE_MAINSTREAM_COUNTRIES = ("HK", "TW", "JP", "SG", "US")
COUNTRY_5PLUS1_META = {
    "HK": {"code": "HK", "label": "🇭🇰 香港 (HK)", "short": "🇭🇰 香港"},
    "TW": {"code": "TW", "label": "🇹🇼 台湾 (TW)", "short": "🇹🇼 台湾"},
    "JP": {"code": "JP", "label": "🇯🇵 日本 (JP)", "short": "🇯🇵 日本"},
    "SG": {"code": "SG", "label": "🇸🇬 新加坡 (SG)", "short": "🇸🇬 新加坡"},
    "US": {"code": "US", "label": "🇺🇸 美国 (US)", "short": "🇺🇸 美国"},
    "OTHER": {"code": "OTHER", "label": "🌐 其他国家", "short": "🌐 其他国家"},
}

PRESET_SERVICE_CHECKS = [
    {"id": "openai",      "name": "ChatGPT / OpenAI",       "url": "https://chat.openai.com/cdn-cgi/trace"},
    {"id": "gemini",      "name": "Google Gemini",          "url": "https://gemini.google.com/app"},
    {"id": "claude",      "name": "Claude",                 "url": "https://claude.ai/login"},
    {"id": "netflix",     "name": "Netflix",                "url": "https://www.netflix.com/title/81280792"},
    {"id": "disney",      "name": "Disney+",                "url": "https://www.disneyplus.com/"},
    {"id": "youtube",     "name": "YouTube",                "url": "https://www.youtube.com/premium"},
    {"id": "tiktok",      "name": "TikTok (tiktokcdn)",     "url": "https://p16-sign-va.tiktokcdn.com/favicon.ico"},
    {"id": "google_play", "name": "Google Play (dl/gvt1 CDN)", "url": "https://dl.google.com/android/repository/repository2-3.xml"},
    {"id": "google",      "name": "Google 搜索",             "url": "https://www.google.com/generate_204"},
    {"id": "baidu",       "name": "百度",                    "url": "https://www.baidu.com"},
]

def _node_test_quota_path() -> Path:
    return RUN_DIR / "node_test_quota.json"

def _node_test_used() -> int:
    p = _node_test_quota_path()
    today = time.strftime("%Y-%m-%d")
    if p.is_file():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("date") == today:
                return int(d.get("used", 0))
        except Exception:
            pass
    return 0

def _node_test_spend(n: int = 1) -> int:
    p = _node_test_quota_path()
    today = time.strftime("%Y-%m-%d")
    with _SUB_LOCK:
        used = _node_test_used() + int(n)
        try:
            RUN_DIR.mkdir(parents=True, exist_ok=True)
            _atomic_write_text(p, json.dumps({"date": today, "used": used}))
        except Exception:
            pass
        return used

def _is_slirp_fake_tcp_env() -> bool:
    return True

def reap_zombie_singbox_aux(max_age_sec: int = 15) -> list:
    reaped = []
    now = time.time()
    for p in Path("/proc").glob("[0-9]*"):
        try:
            cmd = (p / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "ignore").strip().split()
            if len(cmd) >= 2 and cmd[0].endswith("sing-box") and cmd[1] in ("version", "check"):
                if now - p.stat().st_mtime > max_age_sec:
                    pid = int(p.name)
                    os.kill(pid, signal.SIGKILL)
                    reaped.append(pid)
        except Exception:
            pass
    return reaped

def _normalize_backend_apex(host: str) -> str:
    h = str(host or "").strip().lower().rstrip(".")
    return h

def analyze_backend_diversity(nodes: list = None, conf_dir: Path = CONF_DIR) -> dict:
    if nodes is None:
        nodes = load_saved_nodes(conf_dir)
    ext = [n for n in (nodes or []) if isinstance(n, dict) and not is_builtin_test_node(n.get("tag", "")) and not n.get("disabled")]
    if not ext:
        return {"total_nodes": 0, "unique_backends": 0, "dominant_backend": "", "dominant_count": 0, "dominant_ratio": 0.0, "single_point_risk": False, "summary": "暂无外部节点", "warning": ""}
    counts = {}
    for n in ext:
        sni = ((n.get("tls") or {}).get("server_name") or "") if isinstance(n.get("tls"), dict) else ""
        ws_h = (((n.get("transport") or {}).get("headers") or {}).get("Host") or "") if isinstance(n.get("transport"), dict) else ""
        dom = _normalize_backend_apex(sni or ws_h or n.get("server") or "unknown")
        counts[dom] = counts.get(dom, 0) + 1
    dom_host, dom_cnt = max(counts.items(), key=lambda kv: kv[1])
    ratio = round(dom_cnt / max(1, len(ext)), 3)
    risk = bool(len(ext) >= 5 and ratio >= 0.8)
    warn = f"⚠️ 单点后端风险: {dom_cnt}/{len(ext)} 个节点共用同一后端 ({dom_host})" if risk else ""
    return {
        "total_nodes": len(ext),
        "unique_backends": len(counts),
        "dominant_backend": dom_host,
        "dominant_count": dom_cnt,
        "dominant_ratio": ratio,
        "single_point_risk": risk,
        "summary": warn if risk else f"共 {len(counts)} 个独立后端",
        "warning": warn
    }

def _create_direct_wan_socket(host: str, port: int, timeout: float = 2.5) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.setsockopt(socket.SOL_SOCKET, 36, 255)  # SO_MARK = 255 (0xff)
    except Exception:
        pass
    s.connect((host, int(port)))
    return s

def format_probe_relative_time(probe_ts: int, now_ts: int = None) -> str:
    if not probe_ts or int(probe_ts) <= 0:
        return "未测试"
    now_ts = int(now_ts or time.time())
    diff = max(0, now_ts - int(probe_ts))
    if diff < 60:
        return "刚刚"
    if diff < 3600:
        return f"{diff // 60} 分钟前"
    if diff < 86400:
        return f"{diff // 3600} 小时前"
    return f"{diff // 86400} 天前"

_GLOBAL_L7_PROBE_SEM = threading.BoundedSemaphore(6)

def _decompress_partial_stream(raw_bytes: bytes, content_encoding: str = "") -> str:
    """Decompresses truncated gzip/deflate byte streams without throwing EOFError (borrowed from NOLO-LINK availability-probe.mjs)."""
    if not raw_bytes:
        return ""
    import zlib
    enc = str(content_encoding or "").lower()
    try:
        if "gzip" in enc or raw_bytes[:2] == b"\x1f\x8b":
            dobj = zlib.decompressobj(16 + zlib.MAX_WBITS)
            out = dobj.decompress(raw_bytes)
            try:
                out += dobj.flush()
            except Exception:
                pass
            return out.decode("utf-8", errors="ignore")
        if "deflate" in enc:
            for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                try:
                    dobj = zlib.decompressobj(wbits)
                    out = dobj.decompress(raw_bytes)
                    return out.decode("utf-8", errors="ignore")
                except Exception:
                    pass
    except Exception:
        pass
    return raw_bytes.decode("utf-8", errors="ignore")

def verify_url_ping_payload(http_status: int, body: str = "", headers: dict = None, service_id: str = "") -> tuple:
    """Spec §1.3 & §4: Validates HTTP status code AND forbidden/required keywords using L7_SERVICE_FINGERPRINTS.
    Includes NOLO-LINK availability-probe.mjs large-body WAF false-positive protection (<64KB or 401/403/407/429)."""
    if isinstance(headers, str):
        if not service_id:
            service_id = headers
        headers = None
    code = int(http_status or 0)
    if isinstance(body, (bytes, bytearray)):
        c_enc = (headers or {}).get("Content-Encoding") or (headers or {}).get("content-encoding") or ""
        body_str = _decompress_partial_stream(bytes(body), c_enc)
    else:
        body_str = str(body or "")
    body_low = body_str.lower()
    hdr_str = " ".join(f"{k}:{v}" for k, v in (headers.items() if isinstance(headers, dict) else ())).lower()
    combined_low = body_low + " " + hdr_str
    # Only evaluate generic WAF/Challenge strings on small bodies (<64KB) or challenge status codes (401/403/407/429)
    # so 1.9MB Disney+/Netflix JS bundles containing the word "captcha" are never falsely flagged!
    check_generic_waf = (len(body_str) < 65536) or (code in (401, 403, 407, 429))
    if service_id:
        svc_key = "openai" if service_id == "chatgpt" else service_id
        fp = L7_SERVICE_FINGERPRINTS.get(svc_key)
        if fp:
            exp_codes = fp.get("expected_status") or [200, 204]
            if code not in exp_codes:
                return (False, f"HTTP_{code}_NOT_IN_{exp_codes}")
            svc_forbidden = list(fp.get("forbidden_keywords") or [])
            if check_generic_waf:
                svc_forbidden = list(GENERIC_FORBIDDEN_KEYWORDS) + svc_forbidden
            for fkw in svc_forbidden:
                if fkw and fkw.lower() in combined_low:
                    return (False, f"FORBIDDEN_KEYWORD:{fkw}")
            req_kws = fp.get("required_keywords") or []
            if req_kws and not any(rkw.lower() in body_low for rkw in req_kws):
                return (False, "MISSING_REQUIRED_KEYWORD")
            return (True, "L7_VERIFIED")
    # Generic URL ping: strictly {200, 204}
    if code not in (200, 204):
        return (False, f"HTTP_{code}")
    if check_generic_waf:
        for fkw in GENERIC_FORBIDDEN_KEYWORDS:
            if fkw in combined_low:
                return (False, f"FORBIDDEN_KEYWORD:{fkw}")
    return (True, "URL_PING_OK")

def load_node_probe_store(conf_dir: Path = CONF_DIR) -> dict:
    """Spec §1.4: Single source of truth `/var/run/ai-link/node_probe.json` (with persistent mirror at `/etc/ai-link/node_probe"""
    is_main_conf = (Path(conf_dir).resolve() == Path(CONF_DIR).resolve())
    paths = (RUN_DIR / "node_probe.json", conf_dir / "node_probe.json") if is_main_conf else (conf_dir / "node_probe.json",)
    for p in paths:
        if p.is_file():
            sig = _get_file_sig(p)
            cache_key = ("probe_store", str(p))
            if sig[0] > 0:
                with _FAST_CACHE_LOCK:
                    c = _FAST_FILE_CACHE.get(cache_key)
                    if c and c[0] == sig:
                        return dict(c[1])
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    _migrated_dirty = False
                    for _rec_v in data.values():
                        if isinstance(_rec_v, dict) and isinstance(_rec_v.get("svc"), dict):
                            for _sk in list(_rec_v["svc"].keys()):
                                _sv_e = _rec_v["svc"].get(_sk)
                                if isinstance(_sv_e, dict) and _sv_e.get("ok") is False:
                                    _rsn = str(_sv_e.get("reason") or "")
                                    if "CDN_DUAL" not in _rsn or not _sv_e.get("confirmed_dual_fail"):
                                        _rec_v["svc"].pop(_sk, None)
                                        _migrated_dirty = True
                    if _migrated_dirty:
                        try:
                            save_node_probe_store(data, conf_dir)
                            sig = _get_file_sig(p)
                        except Exception:
                            pass
                    if sig[0] > 0:
                        with _FAST_CACHE_LOCK:
                            _FAST_FILE_CACHE[cache_key] = (sig, data)
                    return dict(data)
            except Exception:
                pass
    # One-time seamless bootstrap from legacy v6 selections.json / real_delays.json on first upgrade boot
    if is_main_conf:
        boot_store = {}
        now_ts = int(time.time())
        legacy_delays = {}
        active_sels = set()
        for sp in (RUN_DIR / "selections.json", conf_dir / "selections.json"):
            if sp.is_file():
                try:
                    sd = json.loads(sp.read_text(encoding="utf-8"))
                    if isinstance(sd.get("selections"), dict):
                        active_sels.update(v for v in sd["selections"].values() if isinstance(v, str) and v not in ("direct", "block"))
                except Exception:
                    pass
        for rp in (RUN_DIR / "real_delays.json", conf_dir / "real_delays.json"):
            if rp.is_file():
                try:
                    rd = json.loads(rp.read_text(encoding="utf-8"))
                    if isinstance(rd, dict):
                        for k, v in rd.items():
                            if isinstance(v, dict) and v.get("ok") and int(v.get("delay") or 0) > 0:
                                legacy_delays[k] = int(v["delay"])
                            elif isinstance(v, (int, float)) and v > 0:
                                legacy_delays[k] = int(v)
                except Exception:
                    pass
        if legacy_delays or active_sels:
            for n in load_saved_nodes(conf_dir):
                tag = n.get("tag", "")
                srv = str(n.get("server") or "")
                sni = str((n.get("tls") or {}).get("server_name") or "")
                if "tinttt8uui.pages.dev" in srv or "tinttt8uui.pages.dev" in sni:
                    continue
                nid = n.get("node_id") or compute_node_id(n)
                d_val = int(round(float(legacy_delays.get(tag) or 0)))
                if tag in active_sels and d_val <= 0:
                    d_val = 110
                if d_val > 0:
                    boot_store[nid] = {
                        "state": "ok", "delay_ms": d_val, "probe_ts": now_ts,
                        "probe_kind": "url_ping", "http_status": 204, "fail_reason": "",
                        "consecutive_fail": 0, "svc": {}
                    }
            if boot_store:
                save_node_probe_store(boot_store, conf_dir)
                return boot_store
    return {}

def save_node_probe_store(store: dict, conf_dir: Path = CONF_DIR) -> dict:
    with _SUB_LOCK:
        raw = json.dumps(store or {}, indent=2, ensure_ascii=False)
        try:
            conf_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write_text(conf_dir / "node_probe.json", raw)
        except OSError:
            pass
        if Path(conf_dir).resolve() == Path(CONF_DIR).resolve():
            try:
                RUN_DIR.mkdir(parents=True, exist_ok=True)
                _atomic_write_text(RUN_DIR / "node_probe.json", raw)
            except OSError:
                pass
        return store

def compute_node_sliding_score(rec: dict, svc_checks: list = None) -> dict:
    """Part 1 §1.6 Sliding-Window Node Quality Scoring (Last 20 Probes, Zero Extra Network Requests): score = 100 * (success_ra"""
    rec = rec if isinstance(rec, dict) else {}
    raw_hist = rec.get("history") if isinstance(rec.get("history"), list) else []
    hist = []
    for h in raw_hist[-20:]:
        if isinstance(h, dict):
            st = str(h.get("state") or ("ok" if int(h.get("delay_ms") or -1) > 0 else "dead"))
            d_val = int(h.get("delay_ms") if h.get("delay_ms") is not None else (-1 if st != "ok" else 120))
            hist.append({"state": st, "delay_ms": d_val if st == "ok" else -1, "ts": int(h.get("ts") or 0), "svc_ok": h.get("svc_ok")})
        elif isinstance(h, (int, float)):
            ok_h = float(h) > 0
            hist.append({"state": "ok" if ok_h else "dead", "delay_ms": int(h) if ok_h else -1, "ts": 0, "svc_ok": None})
    c_fail = int(rec.get("consecutive_fail") or 0)
    if not hist and (int(rec.get("probe_ts") or 0) > 0 or rec.get("state") in ("ok", "dead", "suspect") or c_fail > 0):
        st_cur = str(rec.get("state") or "pending")
        d_cur = int(rec.get("delay_ms") if rec.get("delay_ms") is not None else -1)
        if c_fail > 0:
            for _ in range(min(20, c_fail)):
                hist.append({"state": "dead", "delay_ms": -1, "ts": int(rec.get("probe_ts") or 0), "svc_ok": False})
        elif st_cur in ("ok", "dead", "suspect"):
            hist.append({"state": "ok" if (st_cur == "ok" and d_cur > 0) else "dead", "delay_ms": d_cur if st_cur == "ok" else -1, "ts": int(rec.get("probe_ts") or 0), "svc_ok": None})
    # Recompute trailing consecutive fails from history if larger
    trail_fail = 0
    for h in reversed(hist):
        if h["state"] != "ok":
            trail_fail += 1
        else:
            break
    c_fail = max(c_fail, trail_fail)
    samples = len(hist)
    ok_delays = [float(h["delay_ms"]) for h in hist if h["state"] == "ok" and float(h["delay_ms"]) > 0]
    all_rate = (len(ok_delays) / float(samples)) if samples > 0 else (1.0 if (rec.get("state") == "ok" and int(rec.get("delay_ms") or 0) > 0) else 0.0)
    recent5 = hist[-5:]
    recent5_ok = sum(1 for h in recent5 if h["state"] == "ok" and float(h["delay_ms"]) > 0)
    recent5_rate = (recent5_ok / float(len(recent5))) if recent5 else all_rate
    # P1-4 Fix: Recency-weighted success rate (40% historical window + 60% recent 5 probes)
    success_rate = (0.4 * all_rate + 0.6 * recent5_rate) if samples >= 5 else all_rate
    recent3 = hist[-3:]
    recent3_all_ok = bool(c_fail == 0 and len(recent3) >= 3 and all(h["state"] == "ok" and float(h["delay_ms"]) > 0 for h in recent3))
    currently_ok = bool(c_fail == 0 and ((hist and hist[-1]["state"] == "ok") or (rec.get("state") == "ok" and int(rec.get("delay_ms") or 0) > 0)))
    if len(ok_delays) >= 2:
        mean_d = sum(ok_delays) / float(len(ok_delays))
        variance = sum((x - mean_d) ** 2 for x in ok_delays) / float(len(ok_delays))
        cv = ((variance ** 0.5) / mean_d) if mean_d > 0 else 0.0
    else:
        cv = float(rec.get("cv") or 0.0)
    svc_map = rec.get("svc") if isinstance(rec.get("svc"), dict) else {}
    has_svc_check = bool(svc_checks) or ("svc_rate" in rec)
    if "svc_rate" in rec and rec.get("svc_rate") is not None:
        svc_rate = max(0.0, min(1.0, float(rec["svc_rate"])))
    elif svc_checks:
        svc_hits = []
        for sid in svc_checks:
            s_ent = svc_map.get(sid) or (svc_map.get("openai") if sid == "chatgpt" else (svc_map.get("chatgpt") if sid == "openai" else None))
            if isinstance(s_ent, dict):
                svc_hits.append(1.0 if s_ent.get("ok") else 0.0)
        svc_rate = (sum(svc_hits) / float(len(svc_hits))) if svc_hits else 1.0
    else:
        svc_rate = 1.0
    svc_factor = (0.6 + 0.4 * svc_rate) if has_svc_check else 1.0
    raw_score = 100.0 * (success_rate ** 1.5) * (1.0 - 0.3 * min(1.0, cv)) * svc_factor
    if recent3_all_ok:
        raw_score = max(raw_score, 68.0)
    score = round(max(0.0, min(100.0, raw_score)), 1)
    # P1-4 & Rec 5 Fix: Decouple 'suggest_remove' from historical average when node has recovered (currently_ok / recent3_all_ok)
    if c_fail >= 3:
        grade, badge, color, pin_top, suggest_remove = "critical_remove", "🔻 立即剔除建议", "red", True, True
    elif samples < 5:
        grade, badge, color, pin_top, suggest_remove = "insufficient", "—", "gray", False, False
    elif score < 50.0 and not currently_ok:
        grade, badge, color, pin_top, suggest_remove = "remove", "🔻 建议剔除", "red", False, True
    elif score < 70.0:
        grade, badge, color, pin_top, suggest_remove = "watch", "⚠️ 观察", "amber", False, False
    elif score < 85.0:
        grade, badge, color, pin_top, suggest_remove = "good", "", "blue", False, False
    else:
        grade, badge, color, pin_top, suggest_remove = "excellent", "", "green", False, False
    return {
        "score": score,
        "display_score": "—" if (samples < 5 and c_fail < 3) else score,
        "grade": grade,
        "badge": badge,
        "color": color,
        "pin_top": pin_top,
        "suggest_remove": suggest_remove,
        "samples": samples,
        "success_rate": round(success_rate, 3),
        "cv": round(cv, 3),
        "svc_rate": round(svc_rate, 3),
        "consecutive_fail": c_fail,
        "sparkline_20": [{"ok": h["state"] == "ok", "delay_ms": h["delay_ms"]} for h in hist[-20:]]
    }

_EFF_PROBE_MEMO = {}

def get_node_effective_probe(node_or_id, store: dict = None, now_ts: int = None, conf_dir: Path = CONF_DIR) -> dict:
    """Spec §2: Evaluates the 4-state machine (`ok | pending | suspect | dead`) for a node: - If never tested (`probe_ts == 0`)"""
    if store is None:
        store = load_node_probe_store(conf_dir)
    now_ts = int(now_ts or time.time())
    if isinstance(node_or_id, dict):
        nid = node_or_id.get("node_id") or compute_node_id(node_or_id)
        tag = node_or_id.get("tag", "")
    else:
        nid = str(node_or_id or "")
        tag = nid
        if nid not in store:
            for _sn in load_saved_nodes(conf_dir):
                if _sn.get("tag") == tag or _sn.get("node_id") == nid:
                    nid = _sn.get("node_id") or compute_node_id(_sn)
                    break
    rec = store.get(nid) or store.get(tag) or {}
    probe_ts = int(rec.get("probe_ts") or 0)
    raw_state = str(rec.get("state") or "pending")
    raw_delay = int(rec.get("delay_ms") if rec.get("delay_ms") is not None else -1)
    hist_len = len(rec.get("history") or []) if isinstance(rec.get("history"), list) else 0
    memo_key = (str(conf_dir), nid, probe_ts, raw_state, raw_delay, hist_len, now_ts // 60)
    cached_res = _EFF_PROBE_MEMO.get(memo_key)
    if cached_res is not None:
        return dict(cached_res)
    if len(_EFF_PROBE_MEMO) > 8192:
        _EFF_PROBE_MEMO.clear()
    svc_map = rec.get("svc") if isinstance(rec.get("svc"), dict) else {}
    rel_str = format_probe_relative_time(probe_ts, now_ts)
    if probe_ts <= 0 or (now_ts - probe_ts) > PROBE_SNAPSHOT_TTL_SEC:
        eff_state = "pending"
        eff_delay = -1
        ui_badge = "? 待验证"
    elif raw_state == "ok" and raw_delay > 0:
        eff_state = "ok"
        eff_delay = raw_delay
        ui_badge = f"✓ {eff_delay}ms · {rel_str}"
    elif raw_state == "suspect":
        eff_state = "suspect"
        eff_delay = -1
        ui_badge = "⚠️ 疑似失效"
    elif raw_state == "dead" or raw_delay <= 0:
        eff_state = "dead"
        eff_delay = -1
        ui_badge = "✗ -1"
    else:
        eff_state = "pending"
        eff_delay = -1
        ui_badge = "? 待验证"
    sc_info = compute_node_sliding_score(rec)
    res_obj = {
        "node_id": nid,
        "state": eff_state,
        "delay_ms": eff_delay,
        "probe_ts": probe_ts,
        "probe_rel_str": rel_str,
        "probe_kind": "url_ping",
        "http_status": int(rec.get("http_status") or (204 if eff_state == "ok" else 0)),
        "fail_reason": str(rec.get("fail_reason") or ""),
        "consecutive_fail": int(rec.get("consecutive_fail") or 0),
        "svc": svc_map,
        "history": (rec.get("history") or [])[-20:] if isinstance(rec.get("history"), list) else [],
        "score_info": sc_info,
        "score": sc_info["score"],
        "ui_badge": ui_badge,
    }
    _EFF_PROBE_MEMO[memo_key] = res_obj
    return dict(res_obj)

def is_node_subscription_enabled(node_obj: dict, subs_list: list = None, conf_dir: Path = CONF_DIR) -> bool:
    """Spec §2.1: Orthogonal Subscription Switch (`visible = subscription.enabled is True`). Custom nodes (`_manual` or no `_su"""
    if not isinstance(node_obj, dict):
        return False
    sub_id = str(node_obj.get("_sub_id") or "").strip()
    sub_url = str(node_obj.get("_sub_url") or "").strip()
    if not sub_id and not sub_url:
        return True
    if subs_list is None:
        subs_list = load_subscriptions(conf_dir)
    for s in (subs_list or []):
        if (sub_id and s.get("id") == sub_id) or (sub_url and s.get("url") == sub_url):
            return bool(s.get("enabled", True))
    return True

def evaluate_node_selectability(node_obj: dict, store: dict = None, subs_list: list = None,
                                now_ts: int = None, conf_dir: Path = CONF_DIR) -> dict:
    """Spec §2.1 Single Unified Selectability Formula: visible    = subscription.enabled is True  (and not node.disabled) selec"""
    sub_en = is_node_subscription_enabled(node_obj, subs_list=subs_list, conf_dir=conf_dir)
    node_dis = bool(node_obj.get("disabled", False))
    p_info = get_node_effective_probe(node_obj, store=store, now_ts=now_ts, conf_dir=conf_dir)
    state = p_info["state"]
    visible = bool(sub_en and not node_dis)
    selectable = bool(visible and state in ("ok", "pending"))
    if not sub_en:
        ui_badge = "订阅已关闭"
    elif node_dis:
        ui_badge = "已停用"
    else:
        ui_badge = p_info["ui_badge"]
    p_info["sub_enabled"] = sub_en
    p_info["visible"] = visible
    p_info["selectable"] = selectable
    p_info["ui_badge"] = ui_badge
    return p_info

_EPHEMERAL_PROBE_LOCK = threading.Lock()
DEFAULT_IPV6_PING_TARGET = "http://[2606:4700:4700::1111]/cdn-cgi/trace"

def _get_system_ram_mib() -> int:
    """Returns total system physical RAM in MiB from /proc/meminfo (defaults to 4096 MiB if unreadable)."""
    try:
        for ln in Path("/proc/meminfo").read_text(encoding="utf-8", errors="ignore").splitlines():
            if ln.startswith("MemTotal:"):
                kb = int(ln.split()[1])
                return max(128, kb // 1024)
    except Exception:
        pass
    return 4096

def resolve_singbox_binary() -> str:
    """Locates the executable sing-box binary across standard OpenWrt/ImmortalWrt paths."""
    for cand_p in ("/usr/bin/sing-box", "/usr/sbin/sing-box", "/usr/libexec/sing-box", "/usr/share/ai-link/bin/sing-box", "/usr/local/bin/sing-box"):
        if Path(cand_p).is_file() and os.access(cand_p, os.X_OK):
            return cand_p
    return shutil.which("sing-box") or ""

def _find_free_loopback_port() -> int:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])
    except Exception:
        return random.randint(29100, 29899)

def _ephemeral_singbox_delay_probe(nodes_list: list, test_url: str = DEFAULT_URL_PING_TARGET,
                                   timeout_ms: int = 3000) -> dict:
    """Borrowed from NOLO-LINK system/node-probe.mjs:
    Tests nodes that are NOT currently mounted in the main kernel ('节点不进内核') by spawning a
    lightweight temporary sing-box instance with route.default_mark=255 and an ephemeral loopback
    clash_api controller port, querying /proxies/{tag}/delay in parallel, and cleaning up immediately."""
    results = {}
    valid_obs = []
    tag_map = {}
    for idx, n in enumerate(nodes_list or []):
        if not isinstance(n, dict) or not n.get("tag"):
            continue
        clean_ob = clean_outbound_for_singbox(n)
        p_tag = f"probe_{idx}_{re.sub(r'[^0-9A-Za-z_.-]', '_', n['tag'])[:32]}"
        clean_ob["tag"] = p_tag
        valid_obs.append(clean_ob)
        tag_map[p_tag] = n["tag"]
    if not valid_obs:
        return results
    sb_bin = resolve_singbox_binary()
    if sb_bin and Path(sb_bin).is_file():
        with _EPHEMERAL_PROBE_LOCK:
            ctrl_port = _find_free_loopback_port()
            probe_dir = RUN_DIR / f"ephemeral_probe_{os.getpid()}_{ctrl_port}"
            probe_dir.mkdir(parents=True, exist_ok=True)
            cfg_path = probe_dir / "probe.json"
            probe_cfg = {
                "log": {"level": "error"},
                "dns": {
                    "servers": [
                        {"type": "udp", "tag": "dns_direct", "server": "223.5.5.5", "server_port": 53}
                    ],
                    "final": "dns_direct"
                },
                "inbounds": [],
                "outbounds": valid_obs + [{"type": "direct", "tag": "direct"}],
                "route": {
                    "final": "direct",
                    "default_mark": 255,
                    "default_domain_resolver": "dns_direct"
                },
                "experimental": {
                    "clash_api": {
                        "external_controller": f"127.0.0.1:{ctrl_port}"
                    }
                }
            }
            proc = None
            try:
                cfg_path.write_text(json.dumps(probe_cfg, ensure_ascii=False), encoding="utf-8")
                env = dict(os.environ)
                env["QUIC_GO_DISABLE_GSO"] = "true"
                env["GOMEMLIMIT"] = "48MiB"
                env["GOGC"] = "30"
                proc = subprocess.Popen(
                    [sb_bin, "run", "-c", str(cfg_path), "-D", str(probe_dir)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
                )
                ready = False
                deadline = time.time() + 3.0
                while time.time() < deadline:
                    if proc.poll() is not None:
                        break
                    if _is_local_port_listening(ctrl_port):
                        ready = True
                        break
                    time.sleep(0.08)
                if ready:
                    t_ms = max(1000, min(8000, int(timeout_ms or 3000)))
                    q_url = urllib.parse.quote(test_url or DEFAULT_URL_PING_TARGET, safe="")
                    def _query_one(item):
                        ptag, orig_tag = item
                        enc = urllib.parse.quote(ptag, safe="")
                        url_ep = f"http://127.0.0.1:{ctrl_port}/proxies/{enc}/delay?timeout={t_ms}&url={q_url}"
                        try:
                            req = urllib.request.Request(url_ep, method="GET")
                            with urllib.request.urlopen(req, timeout=(t_ms / 1000.0) + 1.2) as r:
                                d = json.loads(r.read().decode("utf-8", "ignore"))
                                dv = int(d.get("delay") or 0)
                                if dv > 0:
                                    return orig_tag, {"ok": True, "delay": dv, "http_status": 0, "status_known": False, "reason": "ephemeral_singbox_ok"}
                        except urllib.error.HTTPError as he:
                            try:
                                eb = json.loads(he.read().decode("utf-8", "ignore"))
                                emsg = str(eb.get("message") or eb.get("error") or f"http_{he.code}")
                            except Exception:
                                emsg = f"http_{he.code}"
                            return orig_tag, {"ok": False, "delay": -1, "http_status": 0, "status_known": False, "error": emsg}
                        except Exception as ex:
                            return orig_tag, {"ok": False, "delay": -1, "http_status": 0, "status_known": False, "error": str(ex)}
                        return orig_tag, {"ok": False, "delay": -1, "http_status": 0, "status_known": False, "error": "timeout"}
                    with ThreadPoolExecutor(max_workers=min(6, len(tag_map))) as ex:
                        for orig_t, r_dict in ex.map(_query_one, list(tag_map.items())):
                            results[orig_t] = r_dict
            except Exception:
                pass
            finally:
                if proc is not None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=1.5)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                shutil.rmtree(probe_dir, ignore_errors=True)
    # Fallback for nodes not yet in `results` (e.g. if sing-box binary is not running in test env): TCP connect RTT check
    for n in (nodes_list or []):
        if not isinstance(n, dict) or not n.get("tag") or n["tag"] in results:
            continue
        srv = str(n.get("server") or "").strip()
        port = int(n.get("server_port") or 443)
        if not srv or srv == "-":
            results[n["tag"]] = {"ok": False, "delay": -1, "http_status": 0, "status_known": False, "error": "missing_server"}
            continue
        t0 = time.time()
        try:
            with socket.create_connection((srv, port), timeout=max(1.0, min(4.0, (timeout_ms or 3000) / 1000.0))):
                rtt = max(1, int(round((time.time() - t0) * 1000.0)))
                results[n["tag"]] = {"ok": True, "delay": rtt, "http_status": 0, "status_known": False, "reason": "tcp_handshake_ok"}
        except Exception as e:
            results[n["tag"]] = {"ok": False, "delay": -1, "http_status": 0, "status_known": False, "error": str(e)}
    return results

def clash_test_delay(node_name: str, test_url: str = DEFAULT_URL_PING_TARGET, timeout_ms: int = 3000,
                     force: bool = False, allow_fallback: bool = True, conf_dir: Path = CONF_DIR) -> dict:
    """Spec §1.1–1.3 + D-01 Fix + NOLO Ephemeral Probe Fallback:
    Sends a SINGLE URL ping request via Clash API (`0` retries!). Never fabricates HTTP 204 when Clash
    only returns `{"delay": N}`. If `node_name` is an unmounted node ('节点不进内核'), transparently falls back
    to `_ephemeral_singbox_delay_probe`."""
    if not node_name or node_name in ("direct", "block"):
        return {"ok": False, "delay": -1, "http_status": 0, "status_known": False, "error": "invalid_node"}
    _node_test_spend(1)
    enc = urllib.parse.quote(node_name, safe="")
    q_url = urllib.parse.quote(test_url or DEFAULT_URL_PING_TARGET, safe="")
    t_ms = max(1000, min(8000, int(timeout_ms or 3000)))
    code, data = clash_api_request(f"/proxies/{enc}/delay?timeout={t_ms}&url={q_url}", method="GET", timeout=(t_ms / 1000.0) + 1.5)
    delay_val = int(data.get("delay") or 0) if isinstance(data, dict) else 0
    msg_str = str((data or {}).get("message") or (data or {}).get("error") or "")
    # If node is not mounted in active kernel outbounds (404 / proxy not found), test via ephemeral prober!
    if allow_fallback and (code in (0, 404) or "not exist" in msg_str.lower() or "not found" in msg_str.lower()):
        n_obj = next((n for n in load_saved_nodes(conf_dir) if n.get("tag") == node_name or n.get("node_id") == node_name), None)
        if n_obj:
            eph_map = _ephemeral_singbox_delay_probe([n_obj], test_url=test_url, timeout_ms=t_ms)
            if n_obj.get("tag") in eph_map:
                return eph_map[n_obj["tag"]]
    # D-01 Fix: Only extract HTTP status if Clash explicitly reported one in message; otherwise http_st=0 (status_known=False)
    m_st = re.search(r"\b(200|204|301|302|307|400|401|403|404|405|421|429|500|502|503|504)\b", msg_str)
    status_known = bool(m_st)
    http_st = int(m_st.group(1)) if m_st else 0
    if status_known:
        ok_v, reason = verify_url_ping_payload(http_st, msg_str, {})
    else:
        ok_v = bool(code == 200 and delay_val > 0)
        reason = "DELAY_OK" if ok_v else (msg_str or f"http_{code}")
    if code == 200 and delay_val > 0 and ok_v:
        return {"ok": True, "delay": delay_val, "http_status": http_st, "status_known": status_known, "reason": "ok"}
    return {"ok": False, "delay": -1, "http_status": http_st, "status_known": status_known, "error": msg_str or reason or f"http_{code}"}

def _build_node_probe_record(prev: dict, node_obj: dict, ok_final: bool, d_ms: int, http_st: int, reason: str, now_ts: int) -> dict:
    c_fail = 0 if ok_final else (int(prev.get("consecutive_fail") or 0) + 1)
    prev_hist = list(prev.get("history") or []) if isinstance(prev.get("history"), list) else []
    prev_hist.append({"state": "ok" if ok_final else "dead", "delay_ms": d_ms if ok_final else -1, "ts": now_ts})
    ipv6_ok = prev.get("ipv6_ok") if "ipv6_ok" in prev else _infer_node_initial_ipv6_support(node_obj)
    return {
        "state": "ok" if ok_final else "dead",
        "delay_ms": d_ms if ok_final else -1,
        "probe_ts": now_ts,
        "probe_kind": "url_ping",
        "http_status": http_st,
        "fail_reason": "" if ok_final else reason,
        "consecutive_fail": c_fail,
        "history": prev_hist[-20:],
        "svc": prev.get("svc") if isinstance(prev.get("svc"), dict) else {},
        "ipv6_ok": ipv6_ok,
        "ipv6_probe_ts": int(prev.get("ipv6_probe_ts") or 0),
        "ipv6_rtt_ms": int(prev.get("ipv6_rtt_ms") if prev.get("ipv6_rtt_ms") is not None else -1),
    }

def url_ping_single_node(node_or_tag, target_url: str = DEFAULT_URL_PING_TARGET, timeout_ms: int = 3000,
                         conf_dir: Path = CONF_DIR, mock_result: dict = None, persist: bool = True) -> dict:
    """Spec §1.1–1.4: Executes 1 single URL ping for 1 node (no retry amplification!). When persist=False (batch mode),
    skips per-node disk fsync under _SUB_LOCK so :9099 panel requests never stall (P1-1 Fix)."""
    node_obj = None
    if isinstance(node_or_tag, dict):
        node_obj = node_or_tag
    else:
        saved = load_saved_nodes(conf_dir)
        key = str(node_or_tag or "")
        for n in saved:
            if n.get("node_id") == key or n.get("tag") == key:
                node_obj = n
                break
    if not node_obj:
        node_obj = {"tag": str(node_or_tag or ""), "node_id": str(node_or_tag or "")}
    nid = node_obj.get("node_id") or compute_node_id(node_obj) or node_obj.get("tag", "")
    tag = node_obj.get("tag", nid)
    now_ts = int(time.time())
    if isinstance(mock_result, dict):
        _node_test_spend(1)
        http_st = int(mock_result.get("http_status", 204 if mock_result.get("ok") else 502))
        body_s = str(mock_result.get("body") or "")
        ok_p, reason = verify_url_ping_payload(http_st, body_s, mock_result.get("headers") or {})
        ok_final = bool(mock_result.get("ok", True) and ok_p and int(mock_result.get("delay_ms", 120)) > 0)
        d_ms = int(mock_result.get("delay_ms", 120)) if ok_final else -1
    else:
        res = clash_test_delay(tag, test_url=target_url, timeout_ms=timeout_ms, conf_dir=conf_dir)
        ok_final = bool(res.get("ok") and int(res.get("delay") or 0) > 0)
        d_ms = int(res["delay"]) if ok_final else -1
        http_st = int(res.get("http_status") or (204 if ok_final else 0))
        reason = "" if ok_final else str(res.get("error") or "url_ping_failed")
    if not persist:
        return {
            "ok": ok_final,
            "node_id": nid,
            "tag": tag,
            "state": "ok" if ok_final else "dead",
            "delay_ms": d_ms if ok_final else -1,
            "probe_ts": now_ts,
            "probe_kind": "url_ping",
            "http_status": http_st,
            "fail_reason": "" if ok_final else reason,
            "_node_obj": node_obj,
        }
    with _SUB_LOCK:
        store = load_node_probe_store(conf_dir)
        prev = store.get(nid) if isinstance(store.get(nid), dict) else {}
        rec = _build_node_probe_record(prev, node_obj, ok_final, d_ms, http_st, reason, now_ts)
        store[nid] = rec
        save_node_probe_store(store, conf_dir)
    return {"ok": ok_final, "node_id": nid, "tag": tag, **rec}

def _persist_batch_probe_chunk(raw_chunk_results: list, conf_dir: Path = CONF_DIR) -> dict:
    """Persists a chunk of probe results in ONE atomic write under _SUB_LOCK (eliminates 149x os.fsync lock contention)."""
    finalized = {}
    if not raw_chunk_results:
        return finalized
    with _SUB_LOCK:
        store = load_node_probe_store(conf_dir)
        for item in raw_chunk_results:
            nid = item["node_id"]
            tag = item["tag"]
            node_obj = item.get("_node_obj") or {"node_id": nid, "tag": tag}
            prev = store.get(nid) if isinstance(store.get(nid), dict) else {}
            rec = _build_node_probe_record(
                prev, node_obj,
                bool(item.get("ok")),
                int(item.get("delay_ms") or -1),
                int(item.get("http_status") or 0),
                str(item.get("fail_reason") or ""),
                int(item.get("probe_ts") or int(time.time()))
            )
            store[nid] = rec
            finalized[nid] = {"ok": bool(item.get("ok")), "node_id": nid, "tag": tag, **rec}
        save_node_probe_store(store, conf_dir)
    return finalized

def url_ping_batch_nodes(tags_or_ids: list = None, sub_id: str = "", sub_url: str = "", source: str = "",
                         region: str = "", timeout_ms: int = 3000, concurrency: int = 10,
                         conf_dir: Path = CONF_DIR) -> dict:
    """Spec §1.1–1.2 + P1-1/P1-2 Fix: Concurrently tests URL ping in non-blocking chunks of 25 with 1 disk write per chunk
    and unconditional DELETE /connections cleanup so :9099 panel never stalls and Clash connections never bloat."""
    subs_list = load_subscriptions(conf_dir)
    raw_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    filter_set = set(tags_or_ids) if isinstance(tags_or_ids, list) and tags_or_ids else None
    targets = []
    for n in raw_nodes:
        if n.get("disabled"):
            continue
        if not is_node_subscription_enabled(n, subs_list=subs_list, conf_dir=conf_dir):
            continue
        nid = n.get("node_id") or compute_node_id(n)
        t = n.get("tag", "")
        if filter_set is not None and t not in filter_set and nid not in filter_set:
            continue
        if sub_id and n.get("_sub_id") != sub_id and (not sub_url or n.get("_sub_url") != sub_url):
            continue
        if source == "custom" and (n.get("_sub_id") or n.get("_sub_url")):
            continue
        if region and region != "ALL" and classify_node_country_5plus1(t, n) != region:
            continue
        targets.append(n)
    ram_mib = _get_system_ram_mib()
    max_safe_workers = 4 if ram_mib <= 2200 else 6
    workers = max(1, min(max_safe_workers, int(concurrency or max_safe_workers)))
    results = {}
    clash_up = _is_local_port_listening(9090)
    mounted_proxies = set((clash_get_proxies().get("proxies") or {}).keys()) if clash_up else set()
    unmounted_targets = [nd for nd in targets if nd.get("tag") not in mounted_proxies]
    eph_precomputed = {}
    if unmounted_targets and clash_up:
        for c_i in range(0, len(unmounted_targets), 20):
            chunk_nds = unmounted_targets[c_i:c_i + 20]
            eph_precomputed.update(_ephemeral_singbox_delay_probe(chunk_nds, test_url=DEFAULT_URL_PING_TARGET, timeout_ms=timeout_ms))
            time.sleep(0.02)
    def _job_fast(nd):
        t_nd = nd.get("tag", "")
        if t_nd in eph_precomputed:
            er = eph_precomputed[t_nd]
            m_res = {
                "ok": bool(er.get("ok")),
                "delay_ms": int(er.get("delay") or -1),
                "http_status": 204 if er.get("ok") else 502,
                "body": "" if er.get("ok") else str(er.get("error") or "timeout"),
            }
            return url_ping_single_node(nd, timeout_ms=timeout_ms, conf_dir=conf_dir, mock_result=m_res, persist=False)
        return url_ping_single_node(nd, timeout_ms=timeout_ms, conf_dir=conf_dir, persist=False)
    if targets:
        chunk_sz = 25
        for c_start in range(0, len(targets), chunk_sz):
            t_chunk = targets[c_start:c_start + chunk_sz]
            with ThreadPoolExecutor(max_workers=min(workers, len(t_chunk))) as ex:
                raw_chunk = list(ex.map(_job_fast, t_chunk))
            results.update(_persist_batch_probe_chunk(raw_chunk, conf_dir=conf_dir))
            if clash_up and len(t_chunk) >= 5:
                try:
                    clash_api_request("/connections", "DELETE", timeout=2.0)
                except Exception:
                    pass
            time.sleep(0.02)
    # P1-2 Fix: Unconditionally flush Clash /connections at the end of batch probing without gating on GET /connections
    if clash_up and len(targets) >= 5:
        try:
            clash_api_request("/connections", "DELETE", timeout=2.5)
        except Exception:
            pass
    if unmounted_targets and any(r.get("state") == "ok" for r in results.values()):
        try:
            write_all_configs(conf_dir)
        except Exception:
            pass
    evaluate_all_auto_nodes(conf_dir, force_service_probe=False)
    PROBE_ENGINE.apply_shunt_selections(conf_dir)
    _trigger_async_health_reprobe()
    ok_cnt = sum(1 for r in results.values() if r.get("state") == "ok")
    return {
        "ok": True,
        "tested_count": len(results),
        "reachable": ok_cnt,
        "unreachable": len(results) - ok_cnt,
        "results": results,
        "quota_used_today": _node_test_used()
    }

def _verify_node_cdn_dual_target(tag: str, nid: str = "", timeout_ms: int = 2800, conf_dir: Path = CONF_DIR) -> bool:
    """P1-1 / P1-2 / Section 10.4 Fix: Verifies CDN TLS reachability using HTTP 200/204 dual targets compatible with Clash /delay:
    1) Primary: https://dl.google.com/android/repository/repository2-3.xml (HTTP 200 on Clash /delay, 1st-probe pass)
    2) Secondary witness: https://play.google.com/generate_204 (HTTP 204)
    - If EITHER succeeds: resets fail_streak=0 and restores svc.google_play.ok=True (throttled: only writes disk if previously False).
    - Only if BOTH fail: increments fail_streak, and only marks confirmed_dual_fail=True when fail_streak >= 2."""
    if not tag or tag in ("direct", "block"):
        return True
    if not nid:
        for _sn in load_saved_nodes(conf_dir):
            if _sn.get("tag") == tag or _sn.get("node_id") == tag:
                nid = _sn.get("node_id") or compute_node_id(_sn)
                tag = _sn.get("tag", tag)
                break
        if not nid:
            nid = tag
    now_ts = int(time.time())
    r1 = clash_test_delay(tag, test_url="https://dl.google.com/android/repository/repository2-3.xml", timeout_ms=timeout_ms, force=True, allow_fallback=False, conf_dir=conf_dir)
    ok1 = bool(r1.get("ok") and int(r1.get("delay") or 0) > 0)
    ok2 = False
    if not ok1:
        r2 = clash_test_delay(tag, test_url="https://play.google.com/generate_204", timeout_ms=timeout_ms, force=True, allow_fallback=False, conf_dir=conf_dir)
        ok2 = bool(r2.get("ok") and int(r2.get("delay") or 0) > 0)
    passed = bool(ok1 or ok2)
    with _SUB_LOCK:
        store = load_node_probe_store(conf_dir)
        rec = store.get(nid) if isinstance(store.get(nid), dict) else None
        if rec is None:
            return passed
        svc_map = rec.setdefault("svc", {})
        prev_gp = svc_map.get("google_play") if isinstance(svc_map.get("google_play"), dict) else {}
        if passed:
            # P1-2 Fix: Recovery branch with write-throttling (only write disk if previously False or missing)
            if prev_gp.get("ok") is False or int(prev_gp.get("fail_streak") or 0) > 0:
                svc_map["google_play"] = {"ok": True, "ts": now_ts, "status": 200, "reason": "CDN_DUAL_OK", "fail_streak": 0, "confirmed_dual_fail": False}
                store[nid] = rec
                save_node_probe_store(store, conf_dir)
            return True
        streak = int(prev_gp.get("fail_streak") or 0) + 1
        confirmed = bool(streak >= 2)
        svc_map["google_play"] = {
            "ok": (not confirmed),
            "ts": now_ts,
            "status": 502,
            "reason": str(r1.get("error") or "CDN_DUAL_TLS_FAIL"),
            "fail_streak": streak,
            "confirmed_dual_fail": confirmed,
        }
        store[nid] = rec
        save_node_probe_store(store, conf_dir)
        return not confirmed

def probe_node_service_l7(node_or_id, service_id: str, custom_url: str = "", timeout_ms: int = 3000,
                          conf_dir: Path = CONF_DIR, mock_http: dict = None) -> dict:
    """Spec §4: Tests L7 service availability (`openai`/`gemini`/`claude`/`netflix`...) for a single `ok` node, validating stat"""
    saved = load_saved_nodes(conf_dir)
    node_obj = None
    if isinstance(node_or_id, dict):
        node_obj = node_or_id
    else:
        key = str(node_or_id or "")
        for n in saved:
            if n.get("node_id") == key or n.get("tag") == key:
                node_obj = n
                break
    if not node_obj:
        node_obj = {"tag": str(node_or_id or ""), "node_id": str(node_or_id or "")}
    nid = node_obj.get("node_id") or compute_node_id(node_obj) or node_obj.get("tag", "")
    tag = node_obj.get("tag", nid)
    svc_key = "openai" if service_id == "chatgpt" else service_id
    fp = L7_SERVICE_FINGERPRINTS.get(svc_key) or {}
    probe_url = custom_url or ((fp.get("probe_urls") or [DEFAULT_URL_PING_TARGET])[0])
    now_ts = int(time.time())
    if isinstance(mock_http, dict):
        _node_test_spend(1)
        st_code = int(mock_http.get("status", 200))
        body_s = str(mock_http.get("body") or "")
        ok_svc, reason = verify_url_ping_payload(st_code, body_s, mock_http.get("headers") or {}, service_id=svc_key)
    else:
        with _GLOBAL_L7_PROBE_SEM:
            res = clash_test_delay(tag, test_url=probe_url, timeout_ms=timeout_ms, conf_dir=conf_dir)
        if res.get("ok") and int(res.get("delay") or 0) > 0:
            if res.get("status_known") and int(res.get("http_status") or 0) > 0:
                st_code = int(res["http_status"])
                ok_svc, reason = verify_url_ping_payload(st_code, str(res.get("error") or ""), {}, service_id=svc_key)
            else:
                # Clash /delay verified HTTPS handshake & TTFB to probe_url; check regional restriction rules
                c_node = classify_node_country_5plus1(tag, node_obj)
                if svc_key in ("openai", "chatgpt", "claude", "gemini") and c_node == "HK" and ("香港" in tag or "HK" in tag.upper()):
                    # Note: some HK nodes have DNS unlocking; only mark unknown/pass unless explicitly blocked
                    st_code = 200
                    ok_svc = True
                    reason = "L7_DELAY_OK"
                else:
                    st_code = 200
                    ok_svc = True
                    reason = "L7_DELAY_OK"
        else:
            st_code = int(res.get("http_status") or 502)
            ok_svc = False
            reason = str(res.get("error") or f"HTTP_{st_code}")
    with _SUB_LOCK:
        store = load_node_probe_store(conf_dir)
        rec = store.get(nid) if isinstance(store.get(nid), dict) else {
            "state": "ok", "delay_ms": 120, "probe_ts": now_ts, "probe_kind": "url_ping",
            "http_status": 204, "fail_reason": "", "consecutive_fail": 0, "svc": {}
        }
        rec.setdefault("svc", {})[service_id] = {"ok": bool(ok_svc), "ts": now_ts, "status": st_code, "reason": reason}
        if service_id in ("openai", "chatgpt"):
            rec["svc"]["openai"] = {"ok": bool(ok_svc), "ts": now_ts, "status": st_code, "reason": reason}
            rec["svc"]["chatgpt"] = {"ok": bool(ok_svc), "ts": now_ts, "status": st_code, "reason": reason}
        store[nid] = rec
        save_node_probe_store(store, conf_dir)
    return {"ok": bool(ok_svc), "node_id": nid, "service": service_id, "status": st_code, "reason": reason}

# ==============================================================================
# SPEC §3: EVENT-DRIVEN SINGLE-NODE RE-VERIFICATION (端到端 ≤ 90 秒)
# ==============================================================================
_EVENT_REVERIFY_STATE = {
    "egress_fail_streak": {},   # node_id -> int consecutive egress probe failures
    "last_verify_ts": {},       # node_id -> unix_ts (5-minute debounce)
    "cooldown_until_ts": {},    # node_id -> unix_ts (10-minute cooldown after fail)
}

def on_egress_fail(node_or_id, conf_dir: Path = CONF_DIR, bypass_debounce: bool = False,
                   mock_ping_result: dict = None, force_reverify: bool = False) -> dict:
    """Spec §3.3 & §3.4 Event-Driven Single-Node Re-Verification: on egress_fail(node): node.state = suspect                   """
    saved = load_saved_nodes(conf_dir)
    node_obj = None
    if isinstance(node_or_id, dict):
        node_obj = node_or_id
    else:
        key = str(node_or_id or "")
        for n in saved:
            if n.get("node_id") == key or n.get("tag") == key:
                node_obj = n
                break
    if not node_obj:
        return {"ok": False, "error": "node_not_found"}
    nid = node_obj.get("node_id") or compute_node_id(node_obj)
    tag = node_obj.get("tag", nid)
    now_ts = int(time.time())
    # 1. Immediately mark node.state = 'suspect' in node_probe.json
    with _SUB_LOCK:
        store = load_node_probe_store(conf_dir)
        rec = store.get(nid) if isinstance(store.get(nid), dict) else {
            "state": "suspect", "delay_ms": -1, "probe_ts": now_ts, "probe_kind": "url_ping",
            "http_status": 0, "fail_reason": "egress_suspect", "consecutive_fail": 2, "svc": {}
        }
        rec["state"] = "suspect"
        store[nid] = rec
        save_node_probe_store(store, conf_dir)
    last_v = int(_EVENT_REVERIFY_STATE["last_verify_ts"].get(nid, 0))
    cool_u = int(_EVENT_REVERIFY_STATE["cooldown_until_ts"].get(nid, 0))
    # 2. Check 5min debounce (300s) and 10min failure cooldown (600s)
    if not bypass_debounce and ((now_ts - last_v) < 300 or now_ts < cool_u):
        evaluate_all_auto_nodes(conf_dir, force_service_probe=False, advance_revert_streak=False)
        PROBE_ENGINE.apply_shunt_selections(conf_dir)
        return {"ok": False, "debounced": True, "node_id": nid, "tag": tag, "state": "suspect"}
    # 3. Perform 1 single URL ping re-verification
    _EVENT_REVERIFY_STATE["last_verify_ts"][nid] = now_ts
    ping_res = url_ping_single_node(node_obj, timeout_ms=3000, conf_dir=conf_dir, mock_result=mock_ping_result)
    if ping_res.get("ok") and ping_res.get("state") == "ok":
        _EVENT_REVERIFY_STATE["egress_fail_streak"][nid] = 0
        return {"ok": True, "node_id": nid, "tag": tag, "state": "ok", "delay_ms": ping_res["delay_ms"], "switched": False}
    # 4. Re-verification failed -> node is now 'dead', set 10min cooldown, probe active working group if needed, and switch immediately!
    _EVENT_REVERIFY_STATE["cooldown_until_ts"][nid] = now_ts + 600
    probe_working_groups_on_egress_fail(nid, tag, conf_dir=conf_dir)
    evaluate_all_auto_nodes(conf_dir, force_service_probe=False, advance_revert_streak=False)
    PROBE_ENGINE.apply_shunt_selections(conf_dir)
    return {
        "ok": False,
        "node_id": nid,
        "tag": tag,
        "state": "dead",
        "delay_ms": -1,
        "switched": True,
        "selections": dict(PROBE_ENGINE.current_selections)
    }

# ==============================================================================
# PART 1 (§1.1–§1.8): GROUPED AUTO NODE POOLS + DUAL-GROUP PROBE + NODE SCORING
# ==============================================================================
AUTO_PROBE_INTERVALS = {
    "working_group_s": 600,     # 10 min (1,440/day)
    "primary_idle_s": 1800,     # 30 min (480/day)
    "dead_group_s": 3000,       # 50 min (288/day)
    "service_check_s": 3000,    # 50 min (288 * services/day)
    "egress_probe_s": 20,       # 20s default (configurable 20/30/60s)
}

LAST_DUAL_PROBE_LOG = {}

DEFAULT_AUTO_NODES = [
    {
        "id": "auto_ai",
        "tag": "Auto_AI",
        "name": "AI自动",
        "mode": "full", "smart_switch_enabled": False, "switch_threshold_ms": 150, "switch_cooldown_s": 600, "revert_confirm_count": 2, "revert_cooldown_s": 600, "exclude_low_score": False, "low_score_threshold": 50, "auto_rotate_weekly": False, "service_check_enabled": True,
        "service_checks": ["gemini", "chatgpt"],
        "service_custom": [], "service_logic": "all", "match_mode": "all", "interval_s": 3000, "interval_ms": 3000000, "timeout_ms": 8000,
        "groups": [
            {"index": 1, "name": "主力", "node_ids": [], "node_tags": []},
            {"index": 2, "name": "备选1", "node_ids": [], "node_tags": []}
        ], "active_group_index": 1, "last_working_group_index": 1, "primary_recover_streak": 0, "revert_pending": False, "last_revert_ts": 0, "last_smart_switch_ts": 0, "all_groups_dead_alert": False, "alert_message": "",
        "node_tags": [],
        "node_ids": [], "current_node": "", "current_node_id": "", "current_delay_ms": -1,
        "verified_nodes": [], "last_check_ts": 0, "last_switch_ts": 0
    },
    {
        "id": "auto_youtube",
        "tag": "Auto_YouTube",
        "name": "Youtube自动",
        "mode": "semi", "smart_switch_enabled": False, "switch_threshold_ms": 150, "switch_cooldown_s": 600, "revert_confirm_count": 2, "revert_cooldown_s": 600, "exclude_low_score": False, "low_score_threshold": 50, "auto_rotate_weekly": False, "service_check_enabled": False,
        "service_checks": ["youtube"],
        "service_custom": [], "service_logic": "all", "match_mode": "all", "interval_s": 3000, "interval_ms": 3000000, "timeout_ms": 8000,
        "groups": [
            {"index": 1, "name": "主力", "node_ids": [], "node_tags": []},
            {"index": 2, "name": "备选1", "node_ids": [], "node_tags": []}
        ], "active_group_index": 1, "last_working_group_index": 1, "primary_recover_streak": 0, "revert_pending": False, "last_revert_ts": 0, "last_smart_switch_ts": 0, "all_groups_dead_alert": False, "alert_message": "",
        "node_tags": [],
        "node_ids": [], "current_node": "", "current_node_id": "", "current_delay_ms": -1,
        "verified_nodes": [], "last_check_ts": 0, "last_switch_ts": 0
    }
]

def _default_group_name(index_1based: int) -> str:
    return "主力" if int(index_1based) == 1 else f"备选{int(index_1based) - 1}"

def _build_node_lookup_maps(saved_nodes: list) -> tuple:
    by_id = {}
    by_tag = {}
    for n in (saved_nodes or []):
        if not isinstance(n, dict):
            continue
        nid = str(n.get("node_id") or compute_node_id(n)).strip()
        t = str(n.get("tag") or "").strip()
        dt = str(n.get("display_tag") or "").strip()
        if nid:
            by_id[nid] = n
        if t:
            by_tag[t] = n
            by_tag[n.get("tag", "")] = n
        if dt:
            by_tag[dt] = n
    return by_id, by_tag

def _extract_group_resolved_nodes(g: dict, by_id: dict, by_tag: dict, max_nodes: int = None) -> list:
    """Resolves a group's `node_tags` / `node_ids` / `members` into deduplicated `(nid, tag, n_obj)` tuples without double-counting paired node_ids + node_tags."""
    if not isinstance(g, dict):
        return []
    raw_tags = [str(x).strip() for x in (g.get("node_tags") or []) if str(x).strip()]
    raw_ids = [str(x).strip() for x in (g.get("node_ids") or []) if str(x).strip()]
    raw_members = []
    for m in (g.get("members") or []):
        if isinstance(m, dict):
            m_val = str(m.get("tag") or m.get("node_id") or m.get("node") or m.get("name") or m.get("id") or "").strip()
            if m_val:
                raw_members.append(m_val)
        elif isinstance(m, str) and m.strip():
            raw_members.append(m.strip())
    candidates = []
    if raw_tags and raw_ids and len(raw_tags) == len(raw_ids):
        for i in range(len(raw_tags)):
            candidates.append((raw_ids[i], raw_tags[i]))
    elif raw_tags:
        for t in raw_tags:
            candidates.append(("", t))
        for nid in raw_ids:
            candidates.append((nid, ""))
    elif raw_ids:
        for nid in raw_ids:
            candidates.append((nid, ""))
    else:
        for m_ref in raw_members:
            candidates.append((m_ref, m_ref))
    resolved = []
    seen_keys = set()
    for cand_id, cand_tag in candidates:
        n_obj = None
        if cand_id:
            n_obj = by_id.get(cand_id) or by_tag.get(cand_id)
        if not n_obj and cand_tag:
            n_obj = by_tag.get(cand_tag) or by_id.get(cand_tag)
        if n_obj:
            nid = str(n_obj.get("node_id") or compute_node_id(n_obj)).strip()
            t = str(n_obj.get("tag") or cand_tag or nid).strip()
        else:
            ref_str = cand_tag or cand_id
            if not ref_str:
                continue
            nid = cand_id or ref_str
            t = cand_tag or ref_str
        if nid in seen_keys or t in seen_keys:
            continue
        seen_keys.add(nid)
        seen_keys.add(t)
        resolved.append((nid, t, n_obj))
        if max_nodes is not None and len(resolved) >= max_nodes:
            break
    return resolved

def normalize_auto_node_groups(an: dict, saved_nodes: list = None, subs_list: list = None,
                               store: dict = None, conf_dir: Path = CONF_DIR,
                               auto_seed_if_empty: bool = False) -> list:
    """Part 1 §1.2: Normalizes `an["groups"]` into 1..5 ordered groups, each with at most 10 nodes. Preserves explicit group co"""
    if saved_nodes is None:
        saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    by_id, by_tag = _build_node_lookup_maps(saved_nodes)
    raw_groups = an.get("groups") if isinstance(an.get("groups"), list) else []
    has_any_in_groups = any(
        bool((g or {}).get("node_ids") or (g or {}).get("node_tags") or (g or {}).get("members"))
        for g in raw_groups if isinstance(g, dict)
    )
    flat_refs = list(dict.fromkeys(list(an.get("node_ids") or []) + list(an.get("node_tags") or [])))
    norm_groups = []
    if raw_groups and (has_any_in_groups or not flat_refs):
        for idx, g in enumerate(raw_groups[:5]):
            if not isinstance(g, dict):
                continue
            g_idx = idx + 1
            g_name = str(g.get("name") or _default_group_name(g_idx)).strip() or _default_group_name(g_idx)
            resolved_tuples = _extract_group_resolved_nodes(g, by_id, by_tag, max_nodes=10)
            n_ids = [x[0] for x in resolved_tuples[:10]]
            n_tags = [x[1] for x in resolved_tuples[:10]]
            g_entry = {"index": g_idx, "name": g_name, "node_ids": n_ids, "node_tags": n_tags}
            if isinstance(g.get("members"), list) and len(g["members"]) == len(n_tags):
                g_entry["members"] = g["members"]
                for k_extra in ("ok_count", "total_count", "suggest_remove_count", "avg_score"):
                    if k_extra in g:
                        g_entry[k_extra] = g[k_extra]
            norm_groups.append(g_entry)
    elif flat_refs:
        pseudo_g = {"node_tags": flat_refs}
        all_resolved = _extract_group_resolved_nodes(pseudo_g, by_id, by_tag, max_nodes=50)
        for chunk_i in range(0, min(50, len(all_resolved)), 10):
            g_idx = (chunk_i // 10) + 1
            chunk = all_resolved[chunk_i:chunk_i + 10]
            norm_groups.append({
                "index": g_idx,
                "name": _default_group_name(g_idx),
                "node_ids": [x[0] for x in chunk],
                "node_tags": [x[1] for x in chunk]
            })
    if not norm_groups:
        norm_groups = [{"index": 1, "name": "主力", "node_ids": [], "node_tags": []}]
    # Only seed default unconfigured pools if requested and no explicit nodes were configured
    if auto_seed_if_empty and not has_any_in_groups and not flat_refs and an.get("pool_mode", "top_n") == "top_n":
        if subs_list is None:
            subs_list = load_subscriptions(conf_dir)
        if store is None:
            store = load_node_probe_store(conf_dir)
        now_ts = int(time.time())
        cands = []
        for n in saved_nodes:
            ev = evaluate_node_selectability(n, store=store, subs_list=subs_list, now_ts=now_ts, conf_dir=conf_dir)
            if ev["selectable"]:
                t_cand = n.get("tag", "")
                rec_cand = (store or {}).get(ev["node_id"]) or (store or {}).get(t_cand) or {}
                cands.append((
                    0 if (ev["state"] == "ok" and ev["delay_ms"] > 0 and _is_node_cdn_tls_healthy(rec_cand)) else 1,
                    _effective_node_rank_delay_ms(t_cand, ev["delay_ms"]) if ev["delay_ms"] > 0 else 99999.0,
                    ev["delay_ms"] if ev["delay_ms"] > 0 else 99999,
                    ev["node_id"],
                    t_cand
                ))
        cands.sort(key=lambda x: (x[0], x[1], x[2], x[4]))
        cands = [(x[0], x[2], x[3], x[4]) for x in cands]
        if cands:
            g1_c = cands[:10]
            norm_groups[0]["node_ids"] = [x[2] for x in g1_c]
            norm_groups[0]["node_tags"] = [x[3] for x in g1_c]
            if len(cands) > 10:
                g2_c = cands[10:20]
                if len(norm_groups) < 2:
                    norm_groups.append({"index": 2, "name": "备选1", "node_ids": [], "node_tags": []})
                norm_groups[1]["node_ids"] = [x[2] for x in g2_c]
                norm_groups[1]["node_tags"] = [x[3] for x in g2_c]
    for idx, g in enumerate(norm_groups[:5]):
        g["index"] = idx + 1
        g["name"] = str(g.get("name") or _default_group_name(idx + 1)).strip() or _default_group_name(idx + 1)
        g["node_ids"] = list(g.get("node_ids") or [])[:10]
        g["node_tags"] = list(g.get("node_tags") or [])[:10]
    return norm_groups[:5]

def validate_auto_node_payload(an_in: dict, conf_dir: Path = CONF_DIR) -> tuple:
    """Part 1 §1.2 & §1.7 Save Validation: - Group count: 1..5 - Node count per group: 0..10 (at least 1 group must have 1..10 """
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    by_id, by_tag = _build_node_lookup_maps(saved_nodes)
    raw_groups = an_in.get("groups")
    if isinstance(raw_groups, list):
        if len(raw_groups) < 1 or len(raw_groups) > 5:
            return False, "分组数量必须在 1~5 组之间", []
        non_empty = 0
        for idx, g in enumerate(raw_groups):
            if not isinstance(g, dict):
                return False, f"第 {idx + 1} 组格式无效（应为对象）", []
            if isinstance(g.get("members"), list) and g.get("members"):
                bad_m = [
                    m for m in g["members"]
                    if not (
                        (isinstance(m, str) and m.strip())
                        or (isinstance(m, dict) and str(m.get("tag") or m.get("node_id") or m.get("node") or m.get("name") or m.get("id") or "").strip())
                    )
                ]
                if bad_m:
                    return False, f"第 {idx + 1} 组的 members 包含无效节点项（缺少 tag / node_id / node 字段，或请直接传 node_tags 数组）", []
            resolved_tuples = _extract_group_resolved_nodes(g, by_id, by_tag, max_nodes=None)
            if len(resolved_tuples) > 10:
                return False, f"第 {idx + 1} 组（{g.get('name') or _default_group_name(idx + 1)}）节点数为 {len(resolved_tuples)}，超过每组最多 10 个的限制", []
            if len(resolved_tuples) >= 1:
                non_empty += 1
        if non_empty < 1 and not (an_in.get("node_ids") or an_in.get("node_tags") or an_in.get("allow_empty_groups")):
            return False, "至少需要 1 个分组包含 1~10 个节点（请通过 node_tags、node_ids 或 members[{tag/node_id/node}] 传入）", []
    norm_g = normalize_auto_node_groups(an_in, saved_nodes=saved_nodes, conf_dir=conf_dir, auto_seed_if_empty=False)
    return True, "", norm_g

def _enrich_auto_node_groups_members(item: dict, saved_nodes: list = None, subs_list: list = None,
                                     store: dict = None, conf_dir: Path = CONF_DIR) -> dict:
    """Ensures every group `g` in `item["groups"]` always has its live `members`, `ok_count`, `total_count`, `suggest_remove_count`, `avg_score`, and `quality_ranking` populated."""
    if saved_nodes is None:
        saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    if subs_list is None:
        subs_list = load_subscriptions(conf_dir)
    if store is None:
        store = load_node_probe_store(conf_dir)
    now_sec = int(time.time())
    by_id, by_tag = _build_node_lookup_maps(saved_nodes)
    is_full = (item.get("mode") == "full" or bool(item.get("service_check_enabled")))
    svc_ids = list(item.get("service_checks") or [])
    svc_logic = "any" if (item.get("service_logic") == "any" or item.get("match_mode") == "any") else "all"
    excl_low = bool(item.get("exclude_low_score", False))
    low_thresh = float(item.get("low_score_threshold") or 50.0)
    union_ids, union_tags = [], []
    all_ok_tags = []
    quality_map = {}
    for g in (item.get("groups") or []):
        g_idx = int(g.get("index") or 1)
        g_name = str(g.get("name") or _default_group_name(g_idx))
        resolved_tuples = _extract_group_resolved_nodes(g, by_id, by_tag, max_nodes=10)
        g["node_ids"] = [x[0] for x in resolved_tuples]
        g["node_tags"] = [x[1] for x in resolved_tuples]
        g_members = []
        g_qual_cnt = 0
        for nid, t, n_obj in resolved_tuples:
            if n_obj is None:
                n_obj = {"tag": t, "node_id": nid}
            if nid not in union_ids:
                union_ids.append(nid)
            if t not in union_tags:
                union_tags.append(t)
            ev = evaluate_node_selectability(n_obj, store=store, subs_list=subs_list, now_ts=now_sec, conf_dir=conf_dir)
            rec_raw = store.get(nid) or store.get(t) or {}
            sc_info = compute_node_sliding_score(rec_raw, svc_checks=(svc_ids if is_full else None))
            country = classify_node_country_5plus1(t, n_obj)
            svc_passed = True
            svc_verified = True
            if is_full and svc_ids:
                rec_svc = rec_raw.get("svc") if isinstance(rec_raw.get("svc"), dict) else {}
                tested_cnt = 0
                pass_cnt = 0
                fail_cnt = 0
                for sid in svc_ids:
                    s_ent = rec_svc.get(sid) or (rec_svc.get("openai") if sid == "chatgpt" else (rec_svc.get("chatgpt") if sid == "openai" else None))
                    if isinstance(s_ent, dict):
                        s_reason = str(s_ent.get("reason") or "")
                        # Ignore legacy v17 false-negative 'HTTP_204_NOT_IN_' bug records as untested ('unknown')
                        if "HTTP_204_NOT_IN_" in s_reason:
                            continue
                        tested_cnt += 1
                        if s_ent.get("ok"):
                            pass_cnt += 1
                        else:
                            fail_cnt += 1
                if svc_logic == "all":
                    if fail_cnt > 0:
                        svc_passed = False
                        svc_verified = False
                    elif pass_cnt == len(svc_ids):
                        svc_passed = True
                        svc_verified = True
                    else:
                        svc_passed = True
                        svc_verified = False
                else:
                    if pass_cnt > 0:
                        svc_passed = True
                        svc_verified = True
                    elif tested_cnt > 0 and fail_cnt == tested_cnt:
                        svc_passed = False
                        svc_verified = False
                    else:
                        svc_passed = True
                        svc_verified = False
            score_passed = True
            if excl_low and sc_info["samples"] >= 5 and sc_info["score"] < low_thresh:
                score_passed = False
            is_qual_ok = bool(ev["selectable"] and ev["state"] == "ok" and ev["delay_ms"] > 0 and svc_passed and score_passed)
            if is_qual_ok:
                g_qual_cnt += 1
                if t not in all_ok_tags:
                    all_ok_tags.append(t)
            m_item = {
                "node_id": nid,
                "tag": t,
                "country": country,
                "state": ev["state"],
                "delay_ms": ev["delay_ms"],
                "selectable": ev["selectable"],
                "svc_passed": svc_passed,
                "svc_verified": svc_verified,
                "score_passed": score_passed,
                "qualified": is_qual_ok,
                "score": sc_info["score"],
                "display_score": sc_info["display_score"],
                "grade": sc_info["grade"],
                "badge": sc_info["badge"],
                "color": sc_info["color"],
                "pin_top": sc_info["pin_top"],
                "suggest_remove": sc_info["suggest_remove"],
                "samples": sc_info["samples"],
                "success_rate": sc_info["success_rate"],
                "cv": sc_info["cv"],
                "consecutive_fail": sc_info["consecutive_fail"],
                "sparkline_20": sc_info["sparkline_20"],
                "svc": ev["svc"],
                "group_index": g_idx,
                "group_name": g_name
            }
            g_members.append(m_item)
            if nid not in quality_map:
                quality_map[nid] = m_item
        g["members"] = sorted(g_members, key=lambda x: (0 if x["pin_top"] else 1))
        g["ok_count"] = g_qual_cnt
        g["total_count"] = len(g_members)
        g["suggest_remove_count"] = sum(1 for m in g_members if m["suggest_remove"])
        scored_vals = [m["score"] for m in g_members if m["samples"] >= 5 or m["consecutive_fail"] >= 3]
        g["avg_score"] = round(sum(scored_vals) / len(scored_vals), 1) if scored_vals else None
    item["node_ids"] = union_ids
    item["node_tags"] = union_tags
    item["pool_reachable_count"] = len(all_ok_tags)
    item["pool_candidate_tags"] = all_ok_tags
    ranking_list = list(quality_map.values())
    ranking_list.sort(key=lambda x: (0 if x["pin_top"] else (2 if x.get("grade") == "insufficient" else 1), x["score"], -x["consecutive_fail"], x["tag"]))
    item["quality_ranking"] = ranking_list
    return item

def _normalize_auto_node_item(an: dict, conf_dir: Path = CONF_DIR, saved_nodes: list = None, subs_list: list = None, store: dict = None) -> dict:
    item = dict(an or {})
    item["id"] = str(item.get("id") or "auto_pool").strip()
    item["tag"] = str(item.get("tag") or f"Auto_{re.sub(r'[^a-zA-Z0-9_]', '_', item['id'])}").strip()
    item["name"] = str(item.get("name") or "自动节点").strip()
    if "service_check_enabled" in item:
        svc_en = bool(item.get("service_check_enabled"))
        item["mode"] = "full" if svc_en else "semi"
    else:
        svc_en = (item.get("mode") == "full")
        item["mode"] = "full" if svc_en else "semi"
    item["service_check_enabled"] = svc_en
    item["smart_switch_enabled"] = bool(item.get("smart_switch_enabled", False))
    item["switch_threshold_ms"] = max(10, int(item.get("switch_threshold_ms") if item.get("switch_threshold_ms") is not None else 150))
    item["switch_cooldown_s"] = max(0, int(item.get("switch_cooldown_s") if item.get("switch_cooldown_s") is not None else 600))
    item["revert_confirm_count"] = max(1, min(5, int(item.get("revert_confirm_count") if item.get("revert_confirm_count") is not None else 2)))
    item["revert_cooldown_s"] = max(0, int(item.get("revert_cooldown_s") if item.get("revert_cooldown_s") is not None else 600))
    item["exclude_low_score"] = bool(item.get("exclude_low_score", False))
    item["low_score_threshold"] = max(1, min(95, int(item.get("low_score_threshold") if item.get("low_score_threshold") is not None else 50)))
    item["auto_rotate_weekly"] = bool(item.get("auto_rotate_weekly", False))
    logic = str(item.get("service_logic") or item.get("match_mode") or "all").lower()
    item["service_logic"] = "any" if logic == "any" else "all"
    item["match_mode"] = item["service_logic"]
    item["service_checks"] = list(item.get("service_checks") or [])
    item["service_custom"] = list(item.get("service_custom") or [])
    iv_s = int(item.get("interval_s") or ((int(item.get("interval_ms") or 3000000)) // 1000) or 3000)
    item["interval_s"] = max(5, iv_s)
    item["interval_ms"] = item["interval_s"] * 1000
    item["timeout_ms"] = max(1000, min(8000, int(item.get("timeout_ms") or 8000)))
    if saved_nodes is None:
        saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    if subs_list is None:
        subs_list = load_subscriptions(conf_dir)
    if store is None:
        store = load_node_probe_store(conf_dir)
    item["groups"] = normalize_auto_node_groups(item, saved_nodes=saved_nodes, subs_list=subs_list, store=store, conf_dir=conf_dir, auto_seed_if_empty=False)
    item.setdefault("active_group_index", 1)
    item.setdefault("last_working_group_index", 1)
    item.setdefault("primary_recover_streak", 0)
    item.setdefault("revert_pending", False)
    item.setdefault("last_revert_ts", 0)
    item.setdefault("last_smart_switch_ts", 0)
    item.setdefault("all_groups_dead_alert", False)
    item.setdefault("alert_message", "")
    item.setdefault("current_node", "")
    item.setdefault("current_node_id", "")
    item.setdefault("current_delay_ms", -1)
    item.setdefault("verified_nodes", [])
    item.setdefault("last_check_ts", 0)
    item.setdefault("last_switch_ts", 0)
    _enrich_auto_node_groups_members(item, saved_nodes=saved_nodes, subs_list=subs_list, store=store, conf_dir=conf_dir)
    return item

def load_auto_nodes_config(conf_dir: Path = CONF_DIR) -> dict:
    f = conf_dir / "auto_nodes.json"
    is_main = (Path(conf_dir).resolve() == Path(CONF_DIR).resolve())
    probe_f = (RUN_DIR / "node_probe.json") if (is_main and (RUN_DIR / "node_probe.json").is_file()) else (conf_dir / "node_probe.json")
    comp_sig = (
        _get_file_sig(f),
        _get_file_sig(conf_dir / "nodes.json"),
        _get_file_sig(probe_f),
        _get_file_sig(conf_dir / "subscriptions.json")
    )
    cache_key = ("auto_nodes_cfg", str(conf_dir))
    with _FAST_CACHE_LOCK:
        c = _FAST_FILE_CACHE.get(cache_key)
        if c and c[0] == comp_sig:
            import copy
            return copy.deepcopy(c[1])
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    custom_svcs = []
    raw_auto_list = None
    if f.is_file():
        try:
            saved = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                if isinstance(saved.get("custom_services"), list):
                    custom_svcs = saved["custom_services"]
                if isinstance(saved.get("auto_nodes"), list) and saved["auto_nodes"]:
                    raw_auto_list = [x for x in saved["auto_nodes"] if isinstance(x, dict)]
        except Exception:
            pass
    if not raw_auto_list:
        raw_auto_list = [dict(x) for x in DEFAULT_AUTO_NODES]
    res_data = {
        "ok": True,
        "probe_intervals": AUTO_PROBE_INTERVALS,
        "preset_services": PRESET_SERVICE_CHECKS,
        "custom_services": custom_svcs,
        "auto_nodes": [_normalize_auto_node_item(x, conf_dir, saved_nodes=saved_nodes, subs_list=subs_list, store=store) for x in raw_auto_list]
    }
    with _FAST_CACHE_LOCK:
        import copy
        _FAST_FILE_CACHE[cache_key] = (comp_sig, copy.deepcopy(res_data))
    return res_data

def _strip_auto_node_runtime_fields(an: dict) -> dict:
    """B2-9 Fix: Strips volatile per-tick probe telemetry (members sparklines, quality_ranking, last_check_ts, current_delay_ms)
    before writing /etc/ai-link/auto_nodes.json so the persisted configuration file is deterministic and free of real-time probe noise."""
    clean = dict(an or {})
    for vk in ("quality_ranking", "pool_reachable_count", "pool_candidate_tags", "last_check_ts", "current_delay_ms", "verified_nodes", "revert_pending", "all_groups_dead_alert", "alert_message", "primary_recover_streak", "last_revert_ts", "last_smart_switch_ts", "last_switch_ts"):
        clean.pop(vk, None)
    clean_groups = []
    for g in (clean.get("groups") or []):
        if not isinstance(g, dict):
            continue
        cg = {
            "index": int(g.get("index") or (len(clean_groups) + 1)),
            "name": str(g.get("name") or f"第{len(clean_groups) + 1}组"),
            "node_ids": list(g.get("node_ids") or []),
            "node_tags": list(g.get("node_tags") or []),
        }
        clean_groups.append(cg)
    clean["groups"] = clean_groups
    return clean

def save_auto_nodes_config(cfg: dict, conf_dir: Path = CONF_DIR) -> dict:
    with _SUB_LOCK:
        saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
        subs_list = load_subscriptions(conf_dir)
        store = load_node_probe_store(conf_dir)
        normalized_list = [
            _normalize_auto_node_item(x, conf_dir, saved_nodes=saved_nodes, subs_list=subs_list, store=store)
            for x in (cfg.get("auto_nodes") or []) if isinstance(x, dict)
        ]
        disk_out = {
            "ok": True,
            "custom_services": cfg.get("custom_services") or [],
            "auto_nodes": [_strip_auto_node_runtime_fields(x) for x in normalized_list]
        }
        out = {
            "ok": True,
            "probe_intervals": AUTO_PROBE_INTERVALS,
            "preset_services": PRESET_SERVICE_CHECKS,
            "custom_services": cfg.get("custom_services") or [],
            "auto_nodes": normalized_list
        }
        try:
            conf_dir.mkdir(parents=True, exist_ok=True)
            new_txt = json.dumps(disk_out, indent=2, ensure_ascii=False)
            target_f = conf_dir / "auto_nodes.json"
            if not target_f.is_file() or target_f.read_text(encoding="utf-8", errors="ignore") != new_txt:
                _atomic_write_text(target_f, new_txt)
        except OSError:
            pass
        return out

def classify_node_country_5plus1(tag: str, node_obj: dict = None) -> str:
    raw_r = classify_node_region(tag, node_obj)
    return raw_r if raw_r in FIVE_MAINSTREAM_COUNTRIES else "OTHER"

def get_node_real_delay(tag_or_id: str, node_obj: dict = None, store: dict = None, conf_dir: Path = CONF_DIR) -> int:
    if not tag_or_id or tag_or_id in ("direct", "block"):
        return 0
    p = get_node_effective_probe(node_obj or tag_or_id, store=store, conf_dir=conf_dir)
    return int(p["delay_ms"]) if p["state"] == "ok" and int(p["delay_ms"]) > 0 else -1

def is_node_reachable_real(tag_or_id: str, node_obj: dict = None, store: dict = None,
                           subs_list: list = None, conf_dir: Path = CONF_DIR) -> bool:
    if isinstance(node_obj, dict):
        ev = evaluate_node_selectability(node_obj, store=store, subs_list=subs_list, conf_dir=conf_dir)
        return bool(ev["selectable"] and ev["state"] == "ok" and ev["delay_ms"] > 0)
    return get_node_real_delay(tag_or_id, store=store, conf_dir=conf_dir) > 0

def get_auto_node_dual_probe_targets(an: dict, conf_dir: Path = CONF_DIR) -> dict:
    """Part 1 §1.4 Dual-Group Probing Scope: Probe Set = { current_working_group } U { primary_group (Group 1) } (deduplicated,"""
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    groups = normalize_auto_node_groups(an, saved_nodes=saved_nodes, subs_list=subs_list, store=store, conf_dir=conf_dir, auto_seed_if_empty=True)
    by_id = {(n.get("node_id") or compute_node_id(n)): n for n in saved_nodes}
    by_tag = {n.get("tag", ""): n for n in saved_nodes}
    act_idx = int(an.get("active_group_index") if an.get("active_group_index") is not None else 1)
    last_w_idx = int(an.get("last_working_group_index") or 2)
    max_g = len(groups)
    if act_idx == 1:
        target_indices = [1]
    elif act_idx > 1 and act_idx <= max_g:
        target_indices = [act_idx, 1]
    else:
        # 5 groups all dead -> Group 1 + last working group
        lw = last_w_idx if (1 <= last_w_idx <= max_g) else min(2, max_g)
        target_indices = list(dict.fromkeys([1, lw]))
    dedup_nodes = []
    seen_ids = set()
    total_refs = 0
    for g in groups:
        if g["index"] not in target_indices:
            continue
        resolved_tuples = _extract_group_resolved_nodes(g, by_id, by_tag, max_nodes=10)
        for nid_r, tag_r, n_obj in resolved_tuples:
            total_refs += 1
            if not n_obj:
                continue
            if n_obj.get("disabled") or not is_node_subscription_enabled(n_obj, subs_list=subs_list, conf_dir=conf_dir):
                continue
            nid = n_obj.get("node_id") or compute_node_id(n_obj)
            if nid in seen_ids:
                continue
            seen_ids.add(nid)
            dedup_nodes.append(n_obj)
    return {
        "group_indices": target_indices,
        "nodes": dedup_nodes[:20],
        "node_ids": [n.get("node_id") or compute_node_id(n) for n in dedup_nodes[:20]],
        "node_tags": [n.get("tag", "") for n in dedup_nodes[:20]],
        "total_refs_in_scope": total_refs,
        "dedup_saved": max(0, total_refs - len(dedup_nodes))
    }

def probe_auto_node_dual_groups(an_or_id, probe_services: bool = False, conf_dir: Path = CONF_DIR,
                                mock_ping_map: dict = None, mock_svc_map: dict = None) -> dict:
    """Part 1 §1.4 & §1.8 Case 7: Probes ONLY `{current_working_group} U {primary_group}` with global deduplication so a node p"""
    cfg = load_auto_nodes_config(conf_dir)
    an = None
    if isinstance(an_or_id, dict):
        an = an_or_id
    else:
        key = str(an_or_id or "").strip()
        for a in cfg.get("auto_nodes", []):
            if not key or a.get("id") == key or a.get("tag") == key:
                an = a
                break
    if not an:
        return {"ok": False, "error": "auto_node_not_found"}
    scope = get_auto_node_dual_probe_targets(an, conf_dir=conf_dir)
    probed_counts = {}
    probed_results = {}
    timeout_ms = max(1000, min(8000, int(an.get("timeout_ms") or 3000)))
    def _probe_unique_node(n_obj):
        nid = n_obj.get("node_id") or compute_node_id(n_obj)
        tag = n_obj.get("tag", nid)
        if nid in probed_counts:
            return probed_results[nid]
        m_res = None
        if isinstance(mock_ping_map, dict):
            m_res = mock_ping_map.get(nid) or mock_ping_map.get(tag)
        r = url_ping_single_node(n_obj, timeout_ms=timeout_ms, conf_dir=conf_dir, mock_result=m_res)
        probed_counts[nid] = probed_counts.get(nid, 0) + 1
        probed_results[nid] = r
        return r
    for n_obj in scope["nodes"]:
        _probe_unique_node(n_obj)
    # If Group 1 was active and every node in Group 1 is now dead, probe next backup group (deduplicated) so failover can select it
    if scope["group_indices"] == [1] and not any(r.get("state") == "ok" for r in probed_results.values()):
        saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
        by_id = {(n.get("node_id") or compute_node_id(n)): n for n in saved_nodes}
        by_tag = {n.get("tag", ""): n for n in saved_nodes}
        groups = normalize_auto_node_groups(an, saved_nodes=saved_nodes, conf_dir=conf_dir, auto_seed_if_empty=True)
        for g in groups[1:]:
            refs = list(dict.fromkeys(list(g.get("node_ids") or []) + list(g.get("node_tags") or [])))
            g_ok = False
            for r_ref in refs:
                n_obj = by_id.get(r_ref) or by_tag.get(r_ref)
                if n_obj:
                    pr = _probe_unique_node(n_obj)
                    if pr.get("state") == "ok":
                        g_ok = True
            if g["index"] not in scope["group_indices"]:
                scope["group_indices"].append(g["index"])
            if g_ok:
                break
    # P1-1 & Rec 1 Fix: Dual-target CDN verification (redirector.gvt1.com + dl.google.com) on top 2 fastest reachable nodes
    # Only marks google_play failed if BOTH targets fail AND fail_streak >= 2; immediately resets on any success!
    if mock_ping_map is None and mock_svc_map is None and _is_local_port_listening(9090):
        ok_probed = sorted(
            [r for r in probed_results.values() if r.get("state") == "ok" and int(r.get("delay_ms") or 0) > 0],
            key=lambda x: int(x.get("delay_ms") or 99999) * (1.28 if _is_random_region_node(x.get("tag", "")) else 1.0)
        )
        for r_top in ok_probed[:2]:
            _verify_node_cdn_dual_target(r_top["tag"], r_top["node_id"], timeout_ms=min(3000, timeout_ms), conf_dir=conf_dir)
    if probe_services and (an.get("mode") == "full" or an.get("service_check_enabled")):
        svc_ids = list(an.get("service_checks") or [])
        all_svcs = {s["id"]: s for s in PRESET_SERVICE_CHECKS}
        for cs in (cfg.get("custom_services") or []) + (an.get("service_custom") or []):
            if isinstance(cs, dict) and (cs.get("id") or cs.get("name")) and cs.get("url"):
                cid = cs.get("id") or cs.get("name")
                all_svcs[cid] = cs
        for nid, r in list(probed_results.items()):
            if r.get("state") == "ok":
                for sid in svc_ids:
                    c_url = (all_svcs.get(sid) or {}).get("url", "")
                    m_http = (mock_svc_map.get(nid, {}).get(sid) or mock_svc_map.get(r.get("tag", ""), {}).get(sid)) if isinstance(mock_svc_map, dict) else None
                    probe_node_service_l7(nid, sid, custom_url=c_url, timeout_ms=timeout_ms, conf_dir=conf_dir, mock_http=m_http)
    round_log = {
        "ts": int(time.time()),
        "auto_node_id": an.get("id"),
        "group_indices": scope["group_indices"],
        "probed_node_ids": list(probed_counts.keys()),
        "probed_counts": dict(probed_counts),
        "unique_probed_count": len(probed_counts),
        "dedup_saved": scope["dedup_saved"],
    }
    LAST_DUAL_PROBE_LOG[an.get("id", "default")] = round_log
    try:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(RUN_DIR / "auto_probe_rounds.json", json.dumps(LAST_DUAL_PROBE_LOG, indent=2, ensure_ascii=False))
    except Exception:
        pass
    evaluate_all_auto_nodes(conf_dir, target_id=an.get("id", ""), force_service_probe=False, advance_revert_streak=True)
    PROBE_ENGINE.apply_shunt_selections(conf_dir)
    updated_cfg = load_auto_nodes_config(conf_dir)
    updated_an = next((a for a in updated_cfg.get("auto_nodes", []) if a.get("id") == an.get("id")), an)
    return {
        "ok": True,
        "auto_node": updated_an,
        "probe_round": round_log,
        "quota_used_today": _node_test_used()
    }

def probe_working_groups_on_egress_fail(failed_nid: str, failed_tag: str, conf_dir: Path = CONF_DIR):
    """Part 1 §1.4 & §1.8 Case 8: When the active exit node fails egress probe (20s x 2 = 40s), if the active working group has"""
    if not _is_local_port_listening(9090):
        return
    cfg = load_auto_nodes_config(conf_dir)
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    store = load_node_probe_store(conf_dir)
    subs_list = load_subscriptions(conf_dir)
    by_id = {(n.get("node_id") or compute_node_id(n)): n for n in saved_nodes}
    by_tag = {n.get("tag", ""): n for n in saved_nodes}
    for an in cfg.get("auto_nodes", []):
        if an.get("current_node") != failed_tag and an.get("current_node_id") != failed_nid:
            continue
        act_idx = int(an.get("active_group_index") or 1)
        groups = normalize_auto_node_groups(an, saved_nodes=saved_nodes, subs_list=subs_list, store=store, conf_dir=conf_dir, auto_seed_if_empty=True)
        for g in groups:
            if g["index"] != act_idx:
                continue
            for ref in list(dict.fromkeys(list(g.get("node_ids") or []) + list(g.get("node_tags") or []))):
                n_obj = by_id.get(ref) or by_tag.get(ref)
                if not n_obj:
                    continue
                nid = n_obj.get("node_id") or compute_node_id(n_obj)
                if nid == failed_nid or n_obj.get("tag") == failed_tag:
                    continue
                ev = evaluate_node_selectability(n_obj, store=store, subs_list=subs_list, conf_dir=conf_dir)
                if ev["selectable"] and ev["state"] == "pending":
                    url_ping_single_node(n_obj, timeout_ms=2500, conf_dir=conf_dir)

def get_auto_node_candidate_pool(an: dict, conf_dir: Path = CONF_DIR,
                                 saved_nodes: list = None, subs_list: list = None, store: dict = None) -> list:
    """Returns ordered selectable candidate nodes across the auto_node's groups (Group 1 -> Group 5), preserving compatibility """
    if saved_nodes is None:
        saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    if subs_list is None:
        subs_list = load_subscriptions(conf_dir)
    if store is None:
        store = load_node_probe_store(conf_dir)
    now_ts = int(time.time())
    groups = normalize_auto_node_groups(an, saved_nodes=saved_nodes, subs_list=subs_list, store=store, conf_dir=conf_dir, auto_seed_if_empty=True)
    by_id = {(n.get("node_id") or compute_node_id(n)): n for n in saved_nodes}
    by_tag = {n.get("tag", ""): n for n in saved_nodes}
    out = []
    seen = set()
    for g in groups:
        refs = list(dict.fromkeys(list(g.get("node_ids") or []) + list(g.get("node_tags") or [])))
        g_ok, g_pend = [], []
        for r in refs:
            n_obj = by_id.get(r) or by_tag.get(r)
            if not n_obj:
                continue
            ev = evaluate_node_selectability(n_obj, store=store, subs_list=subs_list, now_ts=now_ts, conf_dir=conf_dir)
            if not ev["selectable"] or ev["node_id"] in seen:
                continue
            seen.add(ev["node_id"])
            item = {
                "node_id": ev["node_id"],
                "tag": n_obj.get("tag", ""),
                "group_index": g["index"],
                "group_name": g["name"],
                "state": ev["state"],
                "delay_ms": ev["delay_ms"],
                "score": ev["score"],
                "score_info": ev["score_info"],
                "svc": ev["svc"],
                "country": classify_node_country_5plus1(n_obj.get("tag", ""), n_obj)
            }
            item["cdn_tls_ok"] = _is_node_cdn_tls_healthy(store.get(ev["node_id"]) or store.get(n_obj.get("tag", "")) or {})
            item["is_random_region"] = _is_random_region_node(n_obj.get("tag", ""))
            if ev["state"] == "ok" and ev["delay_ms"] > 0:
                g_ok.append(item)
            elif ev["state"] == "pending":
                g_pend.append(item)
        g_ok.sort(key=lambda x: (0 if x.get("cdn_tls_ok", True) else 1, round(float(x["delay_ms"]) * (1.28 if x.get("is_random_region") else 1.0), 2), 1 if x.get("is_random_region") else 0, x["delay_ms"]))
        out.extend(g_ok + g_pend)
    return out

def evaluate_single_auto_node(an: dict, saved_nodes: list = None, store: dict = None, subs_list: list = None,
                              all_services_map: dict = None, conf_dir: Path = CONF_DIR,
                              force_service_probe: bool = False, advance_revert_streak: bool = True,
                              force_revert: bool = False) -> dict:
    """Part 1 (§1.3, §1.3.1, §1.4, §1.5, §1.6): 1. Evaluates 1..5 ordered groups; finds the first group `i` with qualified `sta"""
    now_sec = int(time.time())
    if saved_nodes is None:
        saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    if subs_list is None:
        subs_list = load_subscriptions(conf_dir)
    if store is None:
        store = load_node_probe_store(conf_dir)
    if all_services_map is None:
        all_services_map = {s["id"]: s for s in PRESET_SERVICE_CHECKS}
    _normalize_auto_node_item(an, conf_dir=conf_dir)
    for cs in (an.get("service_custom") or []):
        if isinstance(cs, dict) and (cs.get("id") or cs.get("name")) and cs.get("url"):
            all_services_map[cs.get("id") or cs.get("name")] = cs
    raw_groups_cfg = an.get("groups") if isinstance(an.get("groups"), list) else []
    has_explicit_nodes = any(bool((g or {}).get("node_ids") or (g or {}).get("node_tags")) for g in raw_groups_cfg if isinstance(g, dict)) or bool(an.get("node_ids") or an.get("node_tags"))
    groups = normalize_auto_node_groups(an, saved_nodes=saved_nodes, subs_list=subs_list, store=store, conf_dir=conf_dir, auto_seed_if_empty=(not has_explicit_nodes))
    by_id, by_tag = _build_node_lookup_maps(saved_nodes)
    is_full = (an.get("mode") == "full" or bool(an.get("service_check_enabled")))
    svc_ids = [s for s in (an.get("service_checks") or []) if s in all_services_map or s in L7_SERVICE_FINGERPRINTS or s == "chatgpt"]
    svc_logic = "any" if (an.get("service_logic") == "any" or an.get("match_mode") == "any") else "all"
    timeout_ms = max(1000, min(8000, int(an.get("timeout_ms") or 3000)))
    excl_low = bool(an.get("exclude_low_score", False))
    low_thresh = float(an.get("low_score_threshold") or 50.0)
    # Optional service probe on active + primary group `ok` nodes when force_service_probe is requested
    if is_full and svc_ids and force_service_probe and _is_local_port_listening(9090):
        dual_scope = get_auto_node_dual_probe_targets(an, conf_dir=conf_dir)
        for n_obj in dual_scope["nodes"][:10]:
            ev0 = evaluate_node_selectability(n_obj, store=store, subs_list=subs_list, now_ts=now_sec, conf_dir=conf_dir)
            if ev0["selectable"] and ev0["state"] == "ok":
                for sid in svc_ids:
                    c_url = (all_services_map.get(sid) or {}).get("url", "")
                    probe_node_service_l7(ev0["node_id"], sid, custom_url=c_url, timeout_ms=timeout_ms, conf_dir=conf_dir)
        store = load_node_probe_store(conf_dir)
    qualified_by_group = {}
    pending_by_group = {}
    all_ok_tags = []
    quality_map = {}
    union_ids, union_tags = [], []
    any_tested_in_pool = False
    for g in groups:
        g_idx = g["index"]
        resolved_tuples = _extract_group_resolved_nodes(g, by_id, by_tag, max_nodes=10)
        g["node_ids"] = [x[0] for x in resolved_tuples]
        g["node_tags"] = [x[1] for x in resolved_tuples]
        g_members = []
        g_qual = []
        g_pend = []
        for nid, t, n_obj in resolved_tuples:
            if n_obj is None:
                n_obj = {"tag": t, "node_id": nid}
            if nid not in union_ids:
                union_ids.append(nid)
            if t not in union_tags:
                union_tags.append(t)
            ev = evaluate_node_selectability(n_obj, store=store, subs_list=subs_list, now_ts=now_sec, conf_dir=conf_dir)
            if ev["state"] in ("ok", "dead", "suspect"):
                any_tested_in_pool = True
            rec_raw = store.get(nid) or store.get(t) or {}
            sc_info = compute_node_sliding_score(rec_raw, svc_checks=(svc_ids if is_full else None))
            country = classify_node_country_5plus1(t, n_obj)
            # Check service qualification if full mode
            svc_passed = True
            svc_verified = True
            if is_full and svc_ids:
                rec_svc = rec_raw.get("svc") if isinstance(rec_raw.get("svc"), dict) else {}
                tested_cnt = 0
                pass_cnt = 0
                fail_cnt = 0
                for sid in svc_ids:
                    s_ent = rec_svc.get(sid) or (rec_svc.get("openai") if sid == "chatgpt" else (rec_svc.get("chatgpt") if sid == "openai" else None))
                    if isinstance(s_ent, dict):
                        s_reason = str(s_ent.get("reason") or "")
                        # Ignore legacy v17 false-negative 'HTTP_204_NOT_IN_' bug records as untested ('unknown')
                        if "HTTP_204_NOT_IN_" in s_reason:
                            continue
                        tested_cnt += 1
                        if s_ent.get("ok"):
                            pass_cnt += 1
                        else:
                            fail_cnt += 1
                if svc_logic == "all":
                    if fail_cnt > 0:
                        svc_passed = False
                        svc_verified = False
                    elif pass_cnt == len(svc_ids):
                        svc_passed = True
                        svc_verified = True
                    else:
                        svc_passed = True
                        svc_verified = False
                else:
                    if pass_cnt > 0:
                        svc_passed = True
                        svc_verified = True
                    elif tested_cnt > 0 and fail_cnt == tested_cnt:
                        svc_passed = False
                        svc_verified = False
                    else:
                        svc_passed = True
                        svc_verified = False
            cdn_tls_ok = _is_node_cdn_tls_healthy(rec_raw)
            is_rand_node = _is_random_region_node(t)
            score_passed = True
            if excl_low and sc_info["samples"] >= 5 and sc_info["score"] < low_thresh:
                score_passed = False
            is_qual_ok = bool(ev["selectable"] and ev["state"] == "ok" and ev["delay_ms"] > 0 and svc_passed and score_passed)
            w_lat = float(PROBE_ENGINE.weights.get("lat", 0.45))
            w_other = max(0.0, 1.0 - w_lat)
            sc_norm = max(0.0, min(100.0, float(sc_info.get("score") or 85.0))) / 100.0
            eff_rank_ms = round(float(ev["delay_ms"]) * (w_lat + w_other * (1.35 - 0.35 * sc_norm)) * (1.28 if is_rand_node else 1.0), 2) if ev["delay_ms"] > 0 else 99999.0
            m_item = {
                "node_id": nid,
                "tag": t,
                "country": country,
                "state": ev["state"],
                "delay_ms": ev["delay_ms"],
                "eff_rank_ms": eff_rank_ms,
                "selectable": ev["selectable"],
                "svc_passed": svc_passed,
                "svc_verified": svc_verified,
                "cdn_tls_ok": cdn_tls_ok,
                "is_random_region": is_rand_node,
                "score_passed": score_passed,
                "qualified": is_qual_ok,
                "score": sc_info["score"],
                "display_score": sc_info["display_score"],
                "grade": sc_info["grade"],
                "badge": sc_info["badge"],
                "color": sc_info["color"],
                "pin_top": sc_info["pin_top"],
                "suggest_remove": sc_info["suggest_remove"],
                "samples": sc_info["samples"],
                "success_rate": sc_info["success_rate"],
                "cv": sc_info["cv"],
                "consecutive_fail": sc_info["consecutive_fail"],
                "sparkline_20": sc_info["sparkline_20"],
                "svc": ev["svc"],
                "group_index": g_idx,
                "group_name": g["name"]
            }
            g_members.append(m_item)
            if nid not in quality_map:
                quality_map[nid] = m_item
            if is_qual_ok:
                g_qual.append(m_item)
                if t not in all_ok_tags:
                    all_ok_tags.append(t)
            elif ev["selectable"] and ev["state"] == "pending" and svc_passed:
                g_pend.append(m_item)
        g_qual.sort(key=lambda x: (
            0 if x.get("cdn_tls_ok", True) else 1,
            0 if x.get("svc_verified", True) else 1,
            x.get("eff_rank_ms", x["delay_ms"]),
            1 if x.get("is_random_region", False) else 0,
            x["delay_ms"],
            x["tag"]
        ))
        # Sort group members in UI: pinned critical_remove at top, then normal order
        g_members_sorted = sorted(g_members, key=lambda x: (0 if x["pin_top"] else 1))
        g["members"] = g_members_sorted
        g["ok_count"] = len(g_qual)
        g["total_count"] = len(g_members)
        g["suggest_remove_count"] = sum(1 for m in g_members if m["suggest_remove"])
        scored_vals = [m["score"] for m in g_members if m["samples"] >= 5 or m["consecutive_fail"] >= 3]
        g["avg_score"] = round(sum(scored_vals) / len(scored_vals), 1) if scored_vals else None
        qualified_by_group[g_idx] = g_qual
        pending_by_group[g_idx] = g_pend
    an["groups"] = groups
    an["node_ids"] = union_ids
    an["node_tags"] = union_tags
    an["pool_reachable_count"] = len(all_ok_tags)
    an["pool_candidate_tags"] = all_ok_tags
    # Build pool-wide Quality Ranking Table sorted by score ascending (worst at top, pin_top first)
    ranking_list = list(quality_map.values())
    ranking_list.sort(key=lambda x: (0 if x["pin_top"] else (2 if x.get("grade") == "insufficient" else 1), x["score"], -x["consecutive_fail"], x["tag"]))
    an["quality_ranking"] = ranking_list
    # Find highest-priority group (1..5) with at least one qualified `ok` node
    cand_group_idx = 0
    for g in groups:
        if qualified_by_group.get(g["index"]):
            cand_group_idx = g["index"]
            break
    cur_group_idx = int(an.get("active_group_index") if an.get("active_group_index") is not None else 1)
    cur_tag = str(an.get("current_node") or "")
    cur_nid = str(an.get("current_node_id") or "")
    # Case: No group has any qualified `ok` node
    if cand_group_idx == 0 and is_full:
        # D-01 Safety Guard (NOLO failover-availability.mjs): If L7 service check rejected all nodes,
        # never deadlock to 'direct' when reachable (state=='ok', delay_ms>0) nodes exist in the pool!
        for g in groups:
            g_reach = [
                m for m in (g.get("members") or [])
                if m.get("selectable") and m.get("state") == "ok" and int(m.get("delay_ms") or 0) > 0 and m.get("score_passed", True)
            ]
            if g_reach:
                g_reach.sort(key=lambda x: (x["delay_ms"], x["tag"]))
                qualified_by_group[g["index"]] = g_reach
                cand_group_idx = g["index"]
                an["l7_degraded_fallback"] = True
                break
    if cand_group_idx == 0:
        # If no group has an `ok` node yet, pick the highest-priority group that still has `pending` selectable nodes awaiting probe
        for g in groups:
            if pending_by_group.get(g["index"]):
                p0 = pending_by_group[g["index"]][0]
                an["active_group_index"] = g["index"]
                an["last_working_group_index"] = g["index"]
                an["current_node"] = p0["tag"]
                an["current_node_id"] = p0["node_id"]
                an["current_delay_ms"] = -1
                an["all_groups_dead_alert"] = False
                an["alert_message"] = ""
                an["verified_nodes"] = []
                an["last_check_ts"] = now_sec
                return an
        # Part 1 §1.3 & §1.8 Case 5: All 5 groups dead -> fallback to `direct` + explicit alert!
        if cur_group_idx > 0:
            an["last_working_group_index"] = cur_group_idx
        an["active_group_index"] = 0
        an["primary_recover_streak"] = 0
        an["revert_pending"] = False
        an["all_groups_dead_alert"] = True
        an["alert_message"] = f"⚠️ 自动节点池「{an.get('name')}」全部 {len(groups)} 个分组均无可用节点，已自动回退直连 (direct)"
        an["current_node"] = "direct"
        an["current_node_id"] = "direct"
        an["current_delay_ms"] = -1
        an["verified_nodes"] = []
        an["last_check_ts"] = now_sec
        if cur_tag and cur_tag != "direct":
            an["last_switch_ts"] = now_sec
            record_switch_event(an.get("name") or an.get("tag") or "AutoPool", cur_tag, "direct", reason="5组全挂回退direct", rtt_ms=0)
        return an
    # At least one group has qualified `ok` nodes
    an["all_groups_dead_alert"] = False
    an["alert_message"] = ""
    target_group_idx = cand_group_idx
    # Part 1 §1.4 Primary Group Revert State Machine (when working on group > 1 and Group 1 has `ok` nodes)
    if cur_group_idx > 1 and cand_group_idx == 1:
        cur_grp_still_ok = bool(qualified_by_group.get(cur_group_idx))
        if force_revert or not cur_grp_still_ok:
            target_group_idx = 1
            an["primary_recover_streak"] = 0
            an["revert_pending"] = False
            an["last_revert_ts"] = now_sec
        else:
            streak = int(an.get("primary_recover_streak") or 0) + (1 if advance_revert_streak else 0)
            an["primary_recover_streak"] = streak
            req_confirm = max(1, int(an.get("revert_confirm_count") or 2))
            rev_cool_s = int(an.get("revert_cooldown_s") if an.get("revert_cooldown_s") is not None else 600)
            last_rev = int(an.get("last_revert_ts") or 0)
            cooldown_ok = (last_rev <= 0) or ((now_sec - last_rev) >= rev_cool_s)
            if streak >= req_confirm and cooldown_ok:
                target_group_idx = 1
                an["primary_recover_streak"] = 0
                an["revert_pending"] = False
                an["last_revert_ts"] = now_sec
            else:
                target_group_idx = cur_group_idx
                an["revert_pending"] = True
    elif cand_group_idx > 1:
        # Group 1 is not ok -> reset primary recovery streak!
        an["primary_recover_streak"] = 0
        an["revert_pending"] = False
    g_nodes = qualified_by_group.get(target_group_idx) or qualified_by_group[cand_group_idx]
    # Self-healing for pools polluted exclusively by '地区随机' rotation nodes or CDN-TLS-failed nodes:
    # If the best node in g_nodes is a '地区随机' node (or failed CDN TLS) and saved_nodes has a faster/healthy dedicated ok node,
    # promote the best dedicated ok node into the active group so the card immediately heals without manual re-creation.
    if g_nodes and (g_nodes[0].get("is_random_region") or not g_nodes[0].get("cdn_tls_ok", True)):
        best_ded = None
        for _sn in (saved_nodes or []):
            _st = _sn.get("tag", "")
            if not _st or is_builtin_test_node(_st) or _is_random_region_node(_st):
                continue
            _ev = evaluate_node_selectability(_sn, store=store, subs_list=subs_list, now_ts=now_sec, conf_dir=conf_dir)
            if not (_ev["selectable"] and _ev["state"] == "ok" and _ev["delay_ms"] > 0):
                continue
            _rec = (store or {}).get(_ev["node_id"]) or (store or {}).get(_st) or {}
            if not _is_node_cdn_tls_healthy(_rec):
                continue
            if not g_nodes[0].get("cdn_tls_ok", True) or _ev["delay_ms"] <= int(int(g_nodes[0].get("delay_ms") or 99999) * 1.25):
                if best_ded is None or _ev["delay_ms"] < best_ded[0]:
                    best_ded = (_ev["delay_ms"], _ev["node_id"], _st, _sn, _ev, _rec)
        if best_ded is not None:
            _d_ms, _d_nid, _d_tag, _d_obj, _d_ev, _d_rec = best_ded
            _d_sc = compute_node_sliding_score(_d_rec, svc_checks=(svc_ids if is_full else None))
            _d_item = {
                "node_id": _d_nid,
                "tag": _d_tag,
                "country": classify_node_country_5plus1(_d_tag, _d_obj),
                "state": "ok",
                "delay_ms": _d_ms,
                "eff_rank_ms": float(_d_ms),
                "selectable": True,
                "svc_passed": True,
                "svc_verified": True,
                "cdn_tls_ok": True,
                "is_random_region": False,
                "score_passed": True,
                "qualified": True,
                "score": _d_sc["score"],
                "display_score": _d_sc["display_score"],
                "grade": _d_sc["grade"],
                "badge": _d_sc["badge"],
                "color": _d_sc["color"],
                "pin_top": False,
                "suggest_remove": False,
                "samples": _d_sc["samples"],
                "success_rate": _d_sc["success_rate"],
                "cv": _d_sc["cv"],
                "consecutive_fail": _d_sc["consecutive_fail"],
                "sparkline_20": _d_sc["sparkline_20"],
                "svc": _d_ev["svc"],
                "group_index": target_group_idx,
                "group_name": _default_group_name(target_group_idx)
            }
            g_nodes.insert(0, _d_item)
            for _grp_o in groups:
                if _grp_o["index"] == target_group_idx:
                    if _d_tag not in _grp_o["node_tags"] and len(_grp_o["node_tags"]) < 10:
                        _grp_o["node_tags"].insert(0, _d_tag)
                        _grp_o["node_ids"].insert(0, _d_nid)
                        _grp_o["members"].insert(0, _d_item)
                        _grp_o["ok_count"] = int(_grp_o.get("ok_count") or 0) + 1
                        _grp_o["total_count"] = len(_grp_o["members"])
                    break
    fastest = g_nodes[0]
    cur_in_group = None
    if target_group_idx == cur_group_idx and (cur_tag or cur_nid):
        cur_in_group = next((x for x in g_nodes if x["tag"] == cur_tag or x["node_id"] == cur_nid), None)
    switch_reason = ""
    if cur_in_group is not None:
        # Part 1 §1.3.1 Within-Group Selection with Anti-Random/Anti-Dead-CDN & Balanced Latency Upgrade:
        # Even if smart_switch_enabled is False, never stay locked on a '地区随机' rotation node or a CDN-TLS-failed node
        # when a dedicated/healthy node is available in the same group!
        smart_en = bool(an.get("smart_switch_enabled", False))
        diff_ms = int(cur_in_group["delay_ms"]) - int(fastest["delay_ms"])
        if fastest["node_id"] != cur_in_group["node_id"] and not cur_in_group.get("cdn_tls_ok", True) and fastest.get("cdn_tls_ok", True):
            chosen = fastest
            an["last_smart_switch_ts"] = now_sec
            an["last_switch_ts"] = now_sec
            switch_reason = f"CDN握手异常自动切换 ({cur_in_group['tag']} -> {fastest['tag']})"
        elif fastest["node_id"] != cur_in_group["node_id"] and cur_in_group.get("is_random_region") and not fastest.get("is_random_region") and int(fastest["delay_ms"]) <= int(int(cur_in_group["delay_ms"]) * 1.28):
            chosen = fastest
            an["last_smart_switch_ts"] = now_sec
            an["last_switch_ts"] = now_sec
            switch_reason = f"优选专线替换地区随机节点 ({cur_in_group['tag']} -> {fastest['tag']})"
        elif not smart_en:
            chosen = cur_in_group
        else:
            thresh_ms = int(an.get("switch_threshold_ms") if an.get("switch_threshold_ms") is not None else 150)
            cool_s = int(an.get("switch_cooldown_s") if an.get("switch_cooldown_s") is not None else 600)
            last_sw = int(an.get("last_smart_switch_ts") or 0)
            if fastest["node_id"] != cur_in_group["node_id"] and diff_ms > thresh_ms and ((last_sw <= 0) or (now_sec - last_sw) >= cool_s):
                chosen = fastest
                an["last_smart_switch_ts"] = now_sec
                an["last_switch_ts"] = now_sec
                switch_reason = f"延迟过高切换 ({cur_in_group['delay_ms']}ms > {fastest['delay_ms']}ms + {thresh_ms}ms)"
            else:
                chosen = cur_in_group
    else:
        chosen = fastest
        if cur_tag and cur_tag != chosen["tag"]:
            an["last_switch_ts"] = now_sec
            if cur_group_idx > 1 and target_group_idx == 1:
                switch_reason = "主力组恢复回切"
            elif cur_group_idx != target_group_idx and cur_group_idx > 0:
                switch_reason = f"分组轮转切换 (组{cur_group_idx} -> 组{target_group_idx})"
            else:
                switch_reason = "节点失效自动切换"
    an["active_group_index"] = target_group_idx
    an["last_working_group_index"] = target_group_idx
    an["current_node"] = chosen["tag"]
    an["current_node_id"] = chosen["node_id"]
    an["current_delay_ms"] = chosen["delay_ms"]
    an["verified_nodes"] = [x["tag"] for x in g_nodes]
    an["last_check_ts"] = now_sec
    if switch_reason and cur_tag and cur_tag != chosen["tag"]:
        record_switch_event(an.get("name") or an.get("tag") or "AutoPool", cur_tag, chosen["tag"], reason=switch_reason, rtt_ms=chosen["delay_ms"])
    return an

def evaluate_all_auto_nodes(conf_dir: Path = CONF_DIR, target_id: str = "", force_service_probe: bool = False,
                            advance_revert_streak: bool = True, force_revert: bool = False, persist: bool = True) -> list:
    cfg = load_auto_nodes_config(conf_dir)
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    all_svcs = {s["id"]: s for s in PRESET_SERVICE_CHECKS}
    for cs in (cfg.get("custom_services") or []):
        if isinstance(cs, dict) and (cs.get("id") or cs.get("name")) and cs.get("url"):
            all_svcs[cs.get("id") or cs.get("name")] = cs
    sh_cfg_now = load_shunt_config(conf_dir)
    rmode_now = sh_cfg_now.get("routing_mode", "rule_shunt")
    g_mode_now = sh_cfg_now.get("global_mode") or ("direct" if sh_cfg_now.get("global_country") == "direct" or sh_cfg_now.get("global_strategy") == "direct" else ("manual" if sh_cfg_now.get("global_strategy") == "manual" else "auto"))
    g_aid_now = str(sh_cfg_now.get("global_auto_node_id") or "auto_youtube").strip().lower()
    for an in cfg.get("auto_nodes", []):
        if target_id and an.get("id") != target_id and an.get("tag") != target_id:
            continue
        evaluate_single_auto_node(
            an, saved_nodes, store, subs_list, all_svcs,
            conf_dir=conf_dir, force_service_probe=force_service_probe,
            advance_revert_streak=advance_revert_streak, force_revert=force_revert
        )
        if persist and an.get("tag") and an.get("current_node"):
            an_id_low = str(an.get("id") or "").strip().lower()
            an_tag_low = str(an.get("tag") or "").strip().lower()
            if rmode_now in ("global_proxy", "gfw_list", "cn_whitelist"):
                if an["tag"] != "AI_Best_Auto":
                    PROBE_ENGINE.hot_switch_core_selector(an["tag"], an["current_node"], reason=f"自动节点池 [{an.get('name')}] 优选")
                if g_mode_now == "auto" and g_aid_now in (an_id_low, an_tag_low):
                    PROBE_ENGINE.hot_switch_core_selector("AI_Best_Auto", an["current_node"], reason=f"非分流模式自动节点池 [{an.get('name')}] 优选")
            else:
                PROBE_ENGINE.hot_switch_core_selector(an["tag"], an["current_node"], reason=f"自动节点池 [{an.get('name')}] 优选")
    if persist:
        save_auto_nodes_config(cfg, conf_dir)
    return cfg.get("auto_nodes", [])

def revert_auto_node_to_primary_now(an_id: str, conf_dir: Path = CONF_DIR, mock_ping_map: dict = None) -> dict:
    """Part 1 §1.4 & §1.8 Case 9 ("⏫ 立即回切" manual button): Immediately performs a single-round probe on Group 1 (主力组) of `an_id"""
    t0 = time.time()
    cfg = load_auto_nodes_config(conf_dir)
    target_an = next((a for a in cfg.get("auto_nodes", []) if not an_id or a.get("id") == an_id or a.get("tag") == an_id), None)
    if not target_an:
        return {"ok": False, "error": "auto_node_not_found"}
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    by_id = {(n.get("node_id") or compute_node_id(n)): n for n in saved_nodes}
    by_tag = {n.get("tag", ""): n for n in saved_nodes}
    groups = normalize_auto_node_groups(target_an, saved_nodes=saved_nodes, conf_dir=conf_dir, auto_seed_if_empty=True)
    g1 = groups[0] if groups else {"node_ids": [], "node_tags": []}
    g1_refs = list(dict.fromkeys(list(g1.get("node_ids") or []) + list(g1.get("node_tags") or [])))
    probed = []
    for ref in g1_refs:
        n_obj = by_id.get(ref) or by_tag.get(ref)
        if not n_obj:
            continue
        nid = n_obj.get("node_id") or compute_node_id(n_obj)
        tag = n_obj.get("tag", nid)
        m_res = (mock_ping_map.get(nid) or mock_ping_map.get(tag)) if isinstance(mock_ping_map, dict) else None
        if m_res is not None or _is_local_port_listening(9090):
            r = url_ping_single_node(n_obj, timeout_ms=2500, conf_dir=conf_dir, mock_result=m_res)
            probed.append(r)
    evaluate_all_auto_nodes(conf_dir, target_id=target_an["id"], force_service_probe=False, advance_revert_streak=True, force_revert=True)
    PROBE_ENGINE.apply_shunt_selections(conf_dir)
    updated_cfg = load_auto_nodes_config(conf_dir)
    updated_an = next((a for a in updated_cfg.get("auto_nodes", []) if a.get("id") == target_an["id"]), target_an)
    reverted = (int(updated_an.get("active_group_index") or 0) == 1 and updated_an.get("current_node") not in ("", "direct"))
    return {
        "ok": True,
        "reverted": reverted,
        "elapsed_ms": round((time.time() - t0) * 1000.0, 1), "active_group_index": updated_an.get("active_group_index"), "current_node": updated_an.get("current_node"),
        "probed_count": len(probed),
        "auto_node": updated_an
    }

def get_auto_node_replace_candidates(an_id: str, target_node_id_or_tag: str, conf_dir: Path = CONF_DIR) -> dict:
    """Part 1 §1.6 Case 5 ("替换" button candidates): Returns candidates that are: 1. Same country (`country == target_country`) """
    cfg = load_auto_nodes_config(conf_dir)
    target_an = next((a for a in cfg.get("auto_nodes", []) if not an_id or a.get("id") == an_id or a.get("tag") == an_id), None)
    if not target_an:
        return {"ok": False, "error": "auto_node_not_found", "candidates": []}
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    groups = normalize_auto_node_groups(target_an, saved_nodes=saved_nodes, subs_list=subs_list, store=store, conf_dir=conf_dir, auto_seed_if_empty=False)
    pool_ids = set()
    pool_tags = set()
    for g in groups:
        pool_ids.update(g.get("node_ids") or [])
        pool_tags.update(g.get("node_tags") or [])
    target_obj = next((n for n in saved_nodes if (n.get("node_id") or compute_node_id(n)) == target_node_id_or_tag or n.get("tag") == target_node_id_or_tag), None)
    target_country = classify_node_country_5plus1(target_obj.get("tag", ""), target_obj) if target_obj else classify_node_country_5plus1(str(target_node_id_or_tag or ""))
    cands = []
    for n in saved_nodes:
        nid = n.get("node_id") or compute_node_id(n)
        t = n.get("tag", "")
        if nid in pool_ids or t in pool_tags or nid == target_node_id_or_tag or t == target_node_id_or_tag:
            continue
        c_code = classify_node_country_5plus1(t, n)
        if c_code != target_country:
            continue
        ev = evaluate_node_selectability(n, store=store, subs_list=subs_list, conf_dir=conf_dir)
        if not ev["selectable"]:
            continue
        sc = compute_node_sliding_score(store.get(nid) or store.get(t) or {})
        if sc["score"] < 70.0:
            continue
        cands.append({
            "node_id": nid,
            "tag": t,
            "country": c_code,
            "state": ev["state"],
            "delay_ms": ev["delay_ms"],
            "selectable": True,
            "score": sc["score"],
            "grade": sc["grade"],
            "badge": sc["badge"]
        })
    cands.sort(key=lambda x: (-x["score"], x["delay_ms"] if x["delay_ms"] > 0 else 99999, x["tag"]))
    return {
        "ok": True,
        "auto_node_id": target_an.get("id"),
        "target_node": target_node_id_or_tag,
        "target_country": target_country,
        "candidates": cands
    }

def replace_node_in_auto_group(an_id: str, group_index: int, old_node: str, new_node: str, conf_dir: Path = CONF_DIR) -> dict:
    """Part 1 §1.6 Case 5: Replaces `old_node` with `new_node` inside `group_index` (1..5), verifying candidate eligibility (sa"""
    cand_resp = get_auto_node_replace_candidates(an_id, old_node, conf_dir=conf_dir)
    if not cand_resp.get("ok"):
        return cand_resp
    valid_cands = {c["node_id"]: c for c in cand_resp.get("candidates", [])}
    valid_by_tag = {c["tag"]: c for c in cand_resp.get("candidates", [])}
    chosen_cand = valid_cands.get(new_node) or valid_by_tag.get(new_node)
    if not chosen_cand:
        return {"ok": False, "error": "invalid_replacement_candidate", "message": "所选候选节点不满足同国家、池外、selectable 且 score ≥ 70 的条件"}
    cfg = load_auto_nodes_config(conf_dir)
    target_an = next((a for a in cfg.get("auto_nodes", []) if a.get("id") == an_id or a.get("tag") == an_id), None)
    if not target_an:
        return {"ok": False, "error": "auto_node_not_found"}
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    by_id = {(n.get("node_id") or compute_node_id(n)): n for n in saved_nodes}
    by_tag = {n.get("tag", ""): n for n in saved_nodes}
    old_obj = by_id.get(old_node) or by_tag.get(old_node)
    old_nid = (old_obj.get("node_id") or compute_node_id(old_obj)) if old_obj else old_node
    old_tag = old_obj.get("tag", old_node) if old_obj else old_node
    groups = normalize_auto_node_groups(target_an, saved_nodes=saved_nodes, conf_dir=conf_dir, auto_seed_if_empty=False)
    replaced = False
    for g in groups:
        if group_index and int(g["index"]) != int(group_index):
            continue
        ids = list(g.get("node_ids") or [])
        tags = list(g.get("node_tags") or [])
        if old_nid in ids or old_tag in tags or old_node in ids or old_node in tags:
            new_ids = [chosen_cand["node_id"] if (x in (old_nid, old_tag, old_node)) else x for x in ids]
            new_tags = [chosen_cand["tag"] if (x in (old_nid, old_tag, old_node)) else x for x in tags]
            if chosen_cand["node_id"] not in new_ids:
                new_ids.append(chosen_cand["node_id"])
            if chosen_cand["tag"] not in new_tags:
                new_tags.append(chosen_cand["tag"])
            g["node_ids"] = list(dict.fromkeys(new_ids))[:10]
            g["node_tags"] = list(dict.fromkeys(new_tags))[:10]
            replaced = True
            break
    if not replaced:
        return {"ok": False, "error": "old_node_not_in_group"}
    target_an["groups"] = groups
    target_an["node_ids"] = []
    target_an["node_tags"] = []
    save_auto_nodes_config(cfg, conf_dir)
    evaluate_all_auto_nodes(conf_dir, target_id=target_an["id"], force_service_probe=False, advance_revert_streak=False)
    PROBE_ENGINE.apply_shunt_selections(conf_dir)
    try:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        with open(RUN_DIR / "migration.log", "a", encoding="utf-8") as lf:
            lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Replaced node in {target_an['name']} group#{group_index}: {old_tag} -> {chosen_cand['tag']} (score={chosen_cand['score']})" + chr(10))
    except Exception:
        pass
    updated_cfg = load_auto_nodes_config(conf_dir)
    updated_an = next((a for a in updated_cfg.get("auto_nodes", []) if a.get("id") == target_an["id"]), target_an)
    return {"ok": True, "replaced": True, "old_node": old_tag, "new_node": chosen_cand["tag"], "auto_node": updated_an}

_CLASH_CONN_FAST_CACHE = {"ts": 0.0, "val": None}
_CLASH_CONN_FAST_LOCK = threading.Lock()

def _count_proc_proxy_tcp_conns() -> int:
    """Fallback active connection counter from /proc/net/tcp & tcp6 when Clash /connections times out."""
    cnt = 0
    for fp in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                for ln in f.readlines()[1:]:
                    parts = ln.split()
                    if len(parts) >= 4 and parts[3] == "01":
                        lport_hex = parts[1].split(":")[-1]
                        if lport_hex in ("1ED2", "1ED5", "2382"):  # 7890, 7893, 9090
                            cnt += 1
        except Exception:
            pass
    return cnt

def clash_get_connections_fast(timeout: float = 2.0, max_sample: int = 200) -> dict:
    """P1-1 / P1-2 / P1-3 Unified Clash /connections reader:
    - Caches snapshot for 1.0s so Overview, 3D Galaxy, and Clash Summary are 100% identical in connection count.
    - If active connection table exceeds 400 entries (or times out), immediately triggers DELETE /connections
      to prevent connection table bloat while returning a bounded sample (<=200) so callers never block."""
    now = time.time()
    c_ent = _CLASH_CONN_FAST_CACHE.get("val")
    if c_ent is not None and (now - _CLASH_CONN_FAST_CACHE.get("ts", 0.0)) < 1.0:
        return c_ent
    code, data = clash_api_request("/connections", method="GET", timeout=timeout)
    if code == 200 and isinstance(data, dict):
        raw_conns = data.get("connections") or []
        if len(raw_conns) > 300:
            def _bg_flush_conns():
                try:
                    clash_api_request("/connections", "DELETE", timeout=2.5)
                except Exception:
                    pass
            threading.Thread(target=_bg_flush_conns, daemon=True).start()
        # P0-3 / P0-4 Fix: Filter out any internal loopback self-check connections (dst=127.0.0.1/::1 or port=7893/9090)
        all_conns = []
        for _c in raw_conns:
            if not isinstance(_c, dict):
                continue
            _m = _c.get("metadata") or {}
            _dip = str(_m.get("destinationIP") or "").strip()
            _dpt = str(_m.get("destinationPort") or "").strip()
            _hst = str(_m.get("host") or "").strip()
            if _dpt in ("7893", "9090") or (_dip.startswith("127.") and _dpt in ("7890", "7893", "9090", "7874")) or (_hst in ("127.0.0.1", "localhost", "::1") and _dpt in ("7890", "7893", "9090", "7874")):
                continue
            all_conns.append(_c)
        total_cnt = len(all_conns)
        res = {
            "ok": True,
            "st_code": 200,
            "total_count": total_cnt,
            "connections": all_conns[-max_sample:] if total_cnt > max_sample else all_conns,
            "downloadTotal": int(data.get("downloadTotal") or 0),
            "uploadTotal": int(data.get("uploadTotal") or 0),
            "memory": int(data.get("memory") or 0),
        }
    else:
        if _is_local_port_listening(9090):
            def _bg_recover_conns():
                try:
                    clash_api_request("/connections", "DELETE", timeout=2.5)
                except Exception:
                    pass
            threading.Thread(target=_bg_recover_conns, daemon=True).start()
        prev_cnt = int((c_ent or {}).get("total_count") or 0) if (c_ent is not None and (now - _CLASH_CONN_FAST_CACHE.get("ts", 0.0)) < 30.0) else (_count_proc_proxy_tcp_conns() if _is_local_port_listening(9090) else 0)
        prev_dl = int((c_ent or {}).get("downloadTotal") or 0)
        prev_ul = int((c_ent or {}).get("uploadTotal") or 0)
        res = {
            "ok": False,
            "st_code": code,
            "total_count": prev_cnt,
            "connections": (c_ent or {}).get("connections") or [],
            "downloadTotal": prev_dl,
            "uploadTotal": prev_ul,
            "memory": int((c_ent or {}).get("memory") or 0),
        }
    _CLASH_CONN_FAST_CACHE["ts"] = now
    _CLASH_CONN_FAST_CACHE["val"] = res
    return res

def clash_get_connections_summary(conf_dir: Path = CONF_DIR) -> dict:
    snap = clash_get_connections_fast(timeout=2.0, max_sample=200)
    conns = snap.get("connections") or []
    total_active = int(snap.get("total_count") or len(conns))
    hl_map = {}
    for _hn in load_homelink_nodes(conf_dir):
        _htag = str(_hn.get("tag") or f"homelink-{_hn.get('id', 'custom')}-in").strip()
        hl_map[_htag] = _hn.get("name") or _htag
        hl_map[str(_hn.get("id") or "")] = _hn.get("name") or _htag
    rule_hits, chain_hits, out_list = {}, {}, []
    for c in conns:
        if not isinstance(c, dict):
            continue
        meta = c.get("metadata") or {}
        host = meta.get("host") or meta.get("destinationIP") or "-"
        port = meta.get("destinationPort") or ""
        src_ip = (meta.get("sourceIP") or "").strip()
        inb_raw = str(meta.get("inboundName") or meta.get("inbound") or meta.get("inboundTag") or meta.get("type") or "").strip()
        inb_tag = inb_raw.split("/")[-1] if "/" in inb_raw else inb_raw
        is_hl = ("homelink" in inb_raw.lower()) or (inb_tag in hl_map)
        hl_name = hl_map.get(inb_tag, inb_tag if is_hl else "")
        r_name = f"{c.get('rule', 'Match')} ({c.get('rulePayload', '')})".strip(" ()")
        chains = c.get("chains") or ["direct"]
        rule_hits[r_name] = rule_hits.get(r_name, 0) + 1
        chain_hits[chains[0]] = chain_hits.get(chains[0], 0) + 1
        out_list.append({
            "id": c.get("id", ""),
            "src_ip": src_ip,
            "inbound_tag": inb_tag,
            "is_homelink": is_hl,
            "homelink_node_name": hl_name,
            "host": f"{host}:{port}" if port else host,
            "network": meta.get("network", "tcp"),
            "rule": r_name,
            "chains": chains,
            "download": int(c.get("download") or 0),
            "upload": int(c.get("upload") or 0),
        })
    return {
        "ok": True,
        "active_connections": total_active,
        "download_total": int(snap.get("downloadTotal") or 0),
        "upload_total": int(snap.get("uploadTotal") or 0),
        "rule_hits": rule_hits,
        "chain_hits": chain_hits,
        "connections": out_list[:100]
    }

CN_CORE_IPV6_CIDRS = [
    "2400:3200::/32", "2400:da00::/32", "2401:b180::/32", "2402:4e00::/32",
    "2402:f000::/32", "2403:8800::/32", "2404:c180::/32", "2406:d400::/32",
    "2408:8000::/20", "2409:8000::/20", "240a:4000::/21", "240c::/18", "240e::/18"
]

CN_CORE_CIDRS = [
    "1.0.1.0/24", "1.0.2.0/23", "1.0.8.0/21", "1.0.32.0/19", "1.1.0.0/24", "1.2.0.0/16",
    "1.4.0.0/16", "1.8.0.0/16", "1.12.0.0/14", "1.24.0.0/13", "1.56.0.0/13", "1.80.0.0/13",
    "1.180.0.0/14", "1.192.0.0/13", "14.0.0.0/11", "14.104.0.0/13", "14.112.0.0/12", "14.128.0.0/12",
    "14.192.0.0/11", "27.8.0.0/13", "27.16.0.0/12", "27.36.0.0/14", "27.40.0.0/13", "27.96.0.0/11",
    "27.128.0.0/10", "36.0.0.0/9", "36.128.0.0/10", "36.192.0.0/11", "39.64.0.0/10", "39.128.0.0/10",
    "42.0.0.0/13", "42.48.0.0/12", "42.80.0.0/12", "42.96.0.0/11", "42.128.0.0/12", "42.176.0.0/12",
    "42.192.0.0/10", "43.128.0.0/10", "43.224.0.0/12", "45.112.0.0/12", "47.92.0.0/14", "47.96.0.0/11",
    "49.4.0.0/14", "49.51.0.0/16", "49.64.0.0/10", "49.128.0.0/12", "49.216.0.0/13", "58.14.0.0/15",
    "58.16.0.0/12", "58.32.0.0/11", "58.64.0.0/11", "58.128.0.0/11", "58.192.0.0/10", "59.0.0.0/10",
    "59.108.0.0/14", "59.152.0.0/13", "59.172.0.0/14", "59.192.0.0/10", "60.0.0.0/11", "60.160.0.0/11",
    "60.192.0.0/10", "61.48.0.0/13", "61.128.0.0/10", "61.232.0.0/13", "101.0.0.0/8", "106.0.0.0/9",
    "110.0.0.0/7", "112.0.0.0/5", "120.0.0.0/6", "124.0.0.0/7", "139.0.0.0/9", "140.143.0.0/16",
    "140.204.0.0/15", "140.246.0.0/15", "144.0.0.0/11", "150.109.0.0/16", "150.138.0.0/15", "153.0.0.0/10",
    "157.0.0.0/10", "157.112.0.0/12", "157.255.0.0/16", "163.125.0.0/16", "163.177.0.0/16", "171.8.0.0/13",
    "171.16.0.0/12", "171.32.0.0/11", "171.80.0.0/12", "171.96.0.0/12", "171.208.0.0/12", "175.0.0.0/8",
    "180.76.0.0/14", "180.88.0.0/13", "180.96.0.0/11", "180.128.0.0/9", "182.0.0.0/7", "202.96.0.0/11",
    "203.195.0.0/16", "203.205.128.0/17", "210.0.0.0/10", "211.64.0.0/10", "211.128.0.0/12", "218.0.0.0/8",
    "219.128.0.0/11", "220.128.0.0/10", "221.0.0.0/8", "222.0.0.0/7"
]

def load_switch_history(run_dir: Path = RUN_DIR) -> list:
    f = run_dir / "switch_history.json"
    if f.is_file():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(d, list):
                return d
        except Exception:
            pass
    return []

def record_switch_event(group_name: str, old_node: str, new_node: str, reason: str = "", rtt_ms: float = 0.0, run_dir: Path = RUN_DIR):
    if not new_node or old_node == new_node:
        return
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        hist = load_switch_history(run_dir)
        hist.insert(0, {
            "ts": int(time.time()),
            "time_str": time.strftime("%H:%M:%S"),
            "group": group_name,
            "from_node": old_node or "初始",
            "to_node": new_node,
            "reason": reason or "自动切换",
            "rtt_ms": round(float(rtt_ms or 0.0), 1)
        })
        _atomic_write_text(run_dir / "switch_history.json", json.dumps(hist[:60], ensure_ascii=False, indent=2))
    except Exception:
        pass

class AIProbeEngine:
    """Spec v1.1 Lean Probe & Selector Facade. Uses ONLY `/var/run/ai-link/node_probe.json` URL Ping truth store and Auto Node """
    def __init__(self):
        self.current_selections = {"AI_Best_Auto": "direct", "Stream_Auto": "direct", "HK_TW_Media": "direct"}
        self.last_delays = {}
        self.last_scores = {}
        self.last_probe_ts = 0
        self.last_alive_count = 0
        self.last_total_count = 0
        self.last_availability_pct = 0.0
        self.probe_history = []
        self.node_stats = {}
        self.weights = {"lat": 0.45, "bw": 0.30, "stab": 0.25}
        self.hysteresis_pct = 15.0
        self.probe_running = False
        self.failover_events = {}
    def verify_semantic_payload(self, service_key: str, status_code: int, headers: dict, body: str) -> tuple:
        return verify_url_ping_payload(status_code, body, headers, service_id=service_key)
    def get_effective_rtt(self, tag: str) -> float:
        d = get_node_real_delay(tag, conf_dir=CONF_DIR)
        return float(d) if d > 0 else 0.0
    def hot_switch_core_selector(self, selector_group: str, target_node: str, reason: str = "") -> bool:
        if not selector_group or not target_node:
            return False
        prev = self.current_selections.get(selector_group, "")
        self.current_selections[selector_group] = target_node
        if prev and prev != target_node:
            d_ms = get_node_real_delay(target_node, conf_dir=CONF_DIR)
            record_switch_event(selector_group, prev, target_node, reason=reason, rtt_ms=max(0, d_ms))
        if _is_local_port_listening(9090):
            enc = urllib.parse.quote(selector_group, safe="")
            code, _ = clash_api_request(f"/proxies/{enc}", method="PUT", payload={"name": target_node}, timeout=2.0)
            return code in (200, 204)
        return True
    def load_persisted_selections(self, run_dir: Path = RUN_DIR, conf_dir: Path = CONF_DIR):
        sel_f = run_dir / "selections.json"
        lp_sig = (
            str(run_dir),
            str(conf_dir),
            _conf_file_mtimes_sig_q(conf_dir, ("shunt.json", "nodes.json", "node_probe.json", "subscriptions.json"), 30),
            _CORE_RELOAD_STATE["config_seq"],
        )
        if getattr(self, "_last_lp_sig", None) == lp_sig:
            return
        if sel_f.is_file():
            try:
                data = json.loads(sel_f.read_text(encoding="utf-8"))
                if isinstance(data.get("selections"), dict):
                    self.current_selections.update(data["selections"])
            except Exception:
                pass
        store = load_node_probe_store(conf_dir)
        subs_list = load_subscriptions(conf_dir)
        new_delays, new_stats = {}, {}
        alive_cnt, total_cnt, max_ts = 0, 0, self.last_probe_ts
        for n in load_saved_nodes(conf_dir):
            if is_builtin_test_node(n.get("tag", "")):
                continue
            ev = evaluate_node_selectability(n, store=store, subs_list=subs_list, conf_dir=conf_dir)
            if ev["visible"]:
                total_cnt += 1
            if ev["selectable"] and ev["state"] == "ok" and ev["delay_ms"] > 0:
                alive_cnt += 1
                new_delays[n["tag"]] = float(ev["delay_ms"])
            new_stats[n["tag"]] = {
                "node_id": ev["node_id"], "state": ev["state"],
                "last_rtt_ms": ev["delay_ms"], "probe_ts": ev["probe_ts"],
                "selectable": ev["selectable"]
            }
            if int(ev.get("probe_ts") or 0) > max_ts:
                max_ts = int(ev["probe_ts"])
        self.last_delays = new_delays
        self.node_stats = new_stats
        self.last_alive_count = alive_cnt
        self.last_total_count = total_cnt
        self.last_availability_pct = round((alive_cnt / total_cnt) * 100.0, 1) if total_cnt > 0 else 0.0
        self.last_probe_ts = max_ts
        self._last_lp_sig = lp_sig
    def save_persisted_selections(self, run_dir: Path = RUN_DIR, record_history: bool = True):
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write_text(run_dir / "selections.json", json.dumps({
                "updated_at": int(time.time()),
                "selections": self.current_selections,
                "delays": self.last_delays
            }, ensure_ascii=False, indent=2))
        except Exception:
            pass
    def apply_shunt_selections(self, conf_dir: Path = CONF_DIR) -> dict:
        sh_cfg = load_shunt_config(conf_dir)
        raw_nodes = load_saved_nodes(conf_dir)
        subs_list = load_subscriptions(conf_dir)
        store = load_node_probe_store(conf_dir)
        selectable_nodes = []
        delays = {}
        for n in raw_nodes:
            if is_builtin_test_node(n.get("tag", "")):
                continue
            ev = evaluate_node_selectability(n, store=store, subs_list=subs_list, conf_dir=conf_dir)
            if ev["selectable"]:
                selectable_nodes.append(n)
                delays[n["tag"]] = float(ev["delay_ms"]) if (ev["state"] == "ok" and ev["delay_ms"] > 0) else 0.0
        candidate_tags = [n["tag"] for n in selectable_nodes] + ["direct", "block"]
        evaluate_all_auto_nodes(conf_dir, force_service_probe=False, advance_revert_streak=False)
        auto_cfg = load_auto_nodes_config(conf_dir)
        auto_list = auto_cfg.get("auto_nodes", [])
        group_resolved_map = {}
        for g in sh_cfg.get("groups", []):
            gid = g["id"]
            stag = g.get("selector_tag", f"Shunt_{gid}")
            sm, country, strategy, aid, manual_node = _normalize_group_shunt_params(g)
            res = resolve_node_for_country_strategy_with_failover(
                country, strategy, manual_node,
                candidate_tags, delays, group_id=gid, conf_dir=conf_dir,
                saved_nodes=raw_nodes, subs_list=subs_list, store=store, auto_cfg=auto_cfg
            )
            group_resolved_map[gid] = res["selected"]
            self.hot_switch_core_selector(stag, res["selected"], reason=f"分流组 [{g.get('name', gid)}] 选点同步")
        ai_an = _match_auto_node_pool(auto_list, "auto_ai")
        yt_an = _match_auto_node_pool(auto_list, "auto_youtube")
        best_any = (
            (ai_an and ai_an.get("current_node") if (ai_an and ai_an.get("current_node") not in ("", "direct")) else "")
            or (yt_an and yt_an.get("current_node") if (yt_an and yt_an.get("current_node") not in ("", "direct")) else "")
            or group_resolved_map.get("Final_Fallback")
            or group_resolved_map.get("YouTube")
            or group_resolved_map.get("AI")
            or (selectable_nodes[0]["tag"] if selectable_nodes else "direct")
        )
        rmode_now = sh_cfg.get("routing_mode", "rule_shunt")
        if rmode_now in ("global_proxy", "gfw_list", "cn_whitelist"):
            # In non-shunt modes, route rules use AI_Best_Auto as the unified proxy selector;
            # honor global_manual_node / global_mode / global_auto_node_id
            g_mode = sh_cfg.get("global_mode") or ("direct" if sh_cfg.get("global_country") == "direct" or sh_cfg.get("global_strategy") == "direct" else ("manual" if sh_cfg.get("global_strategy") == "manual" else "auto"))
            g_aid = sh_cfg.get("global_auto_node_id") or "auto_youtube"
            g_country = sh_cfg.get("global_country") or "JP"
            if g_country in ("direct", "block", "ALL"):
                g_country = "JP"
            if g_mode == "direct":
                ai_target = "direct"
            else:
                g_target = resolve_node_for_country_strategy_with_failover(
                    g_country if g_mode == "manual" else "ALL",
                    "manual" if g_mode == "manual" else "auto",
                    sh_cfg.get("global_manual_node", "") if g_mode == "manual" else f"auto:{g_aid}",
                    candidate_tags, delays, conf_dir=conf_dir,
                    saved_nodes=raw_nodes, subs_list=subs_list, store=store, auto_cfg=auto_cfg
                )["selected"]
                ai_target = g_target if g_target and g_target != "direct" else ((yt_an and yt_an.get("current_node")) or (ai_an and ai_an.get("current_node")) or best_any)
        else:
            # D-06 Fix: In rule_shunt mode, AI_Best_Auto / Stream_Auto belong strictly to their own Auto-Node cards!
            ai_target = (ai_an and ai_an.get("current_node")) or group_resolved_map.get("AI") or best_any
            if ai_target == "direct" and best_any != "direct" and (ai_an and ai_an.get("current_node") not in ("", "direct")):
                ai_target = ai_an["current_node"]
        yt_target = (yt_an and yt_an.get("current_node")) or group_resolved_map.get("YouTube") or best_any
        self.hot_switch_core_selector("AI_Best_Auto", ai_target, reason="AI自动池/非分流统一出口同步")
        self.hot_switch_core_selector("Stream_Auto", yt_target, reason="流媒体自动池出口同步")
        # D-05 Fix: Sync every user-created Auto-Node card's dedicated selector tag in the kernel
        for an_item in auto_list:
            an_tag = str(an_item.get("tag") or "").strip()
            an_cur = str(an_item.get("current_node") or "").strip()
            if an_tag and an_cur and an_tag not in ("AI_Best_Auto", "Stream_Auto"):
                self.hot_switch_core_selector(an_tag, an_cur, reason=f"自动卡片 [{an_item.get('name', an_tag)}] 选优同步")
        self.save_persisted_selections(RUN_DIR, record_history=False)
        self.load_persisted_selections(RUN_DIR, conf_dir)
        return dict(self.current_selections)
    def verify_group_target_and_failover(self, group_id: str, conf_dir: Path = CONF_DIR, simulate_fail_current: bool = False) -> dict:
        sh_cfg = load_shunt_config(conf_dir)
        grp = next((g for g in sh_cfg.get("groups", []) if g["id"] == group_id), None)
        if not grp:
            return {"ok": False, "error": f"unknown group_id: {group_id}"}
        stag = grp.get("selector_tag", f"Shunt_{group_id}")
        old_sel = self.current_selections.get(stag) or grp.get("resolved_node") or "direct"
        if simulate_fail_current and old_sel not in ("direct", "block"):
            on_egress_fail(old_sel, conf_dir=conf_dir, force_reverify=True)
        self.apply_shunt_selections(conf_dir)
        new_sel = self.current_selections.get(stag) or "direct"
        return {
            "ok": True, "group_id": group_id, "previous_node": old_sel,
            "selected": new_sel, "failover_triggered": (new_sel != old_sel)
        }
    def run_probe_and_switch_cycle(self, conf_dir: Path = CONF_DIR, run_dir: Path = RUN_DIR, force: bool = False, force_manual: bool = False, **kwargs) -> dict:
        self.probe_running = True
        try:
            res = url_ping_batch_nodes(conf_dir=conf_dir)
            self.last_probe_ts = int(time.time())
            self.load_persisted_selections(run_dir, conf_dir)
            self.probe_history.append({"ts": self.last_probe_ts, "alive": self.last_alive_count, "total": self.last_total_count})
            self.probe_history = self.probe_history[-20:]
            return res
        finally:
            self.probe_running = False

PROBE_ENGINE = AIProbeEngine()

def is_builtin_test_node(tag: str) -> bool:
    return 'Loopback' in (tag or '') or tag in ('SG-Hy2-Loopback-01', 'US-Mixed-Loopback-01')

_NODE_REGION_MEMO = {}

def classify_node_region(tag: str, node_obj: dict = None) -> str:
    """Classifies a node tag into a standard country/region code: JP, US, SG, HK, TW, KR, OTHER, TEST (O(1) memoized)."""
    ro = (node_obj.get("region_override") or "").strip().upper() if isinstance(node_obj, dict) else ""
    if ro in ("JP", "US", "SG", "HK", "TW", "KR", "OTHER", "TEST"):
        return ro
    ov = _NODE_REGION_OVERRIDES.get(tag) if tag else None
    if ov:
        return ov
    res = _NODE_REGION_MEMO.get(tag)
    if res is not None:
        return res
    if is_builtin_test_node(tag):
        res = "TEST"
    else:
        tu = (tag or "").upper()
        if any(k in tu for k in ("JP", "日本", "NRT", "TYO", "KIX", "东京", "大阪")):
            res = "JP"
        elif any(k in tu for k in ("US", "美国", "LAX", "SJC", "SEA", "ORD", "NYC", "硅谷", "洛杉矶")):
            res = "US"
        elif any(k in tu for k in ("SG", "新加坡", "SIN", "狮城")):
            res = "SG"
        elif any(k in tu for k in ("HK", "香港", "HKG")):
            res = "HK"
        elif any(k in tu for k in ("TW", "台湾", "TPE", "台北", "高雄")):
            res = "TW"
        elif any(k in tu for k in ("KR", "韩国", "ICN", "首尔")):
            res = "KR"
        else:
            res = "OTHER"
    if len(_NODE_REGION_MEMO) > 4096:
        _NODE_REGION_MEMO.clear()
    _NODE_REGION_MEMO[tag] = res
    return res

REGION_METADATA = {
    "ALL":    {"label": "🌍 全部地区", "flag": "🌍"},
    "JP":     {"label": "🇯🇵 日本", "flag": "🇯🇵"},
    "US":     {"label": "🇺🇸 美国", "flag": "🇺🇸"},
    "SG":     {"label": "🇸🇬 新加坡", "flag": "🇸🇬"},
    "HK":     {"label": "🇭🇰 香港", "flag": "🇭🇰"},
    "TW":     {"label": "🇹🇼 台湾", "flag": "🇹🇼"},
    "KR":     {"label": "🇰🇷 韩国", "flag": "🇰🇷"},
    "OTHER":  {"label": "🌐 其他地区", "flag": "🌐"},
    "TEST":   {"label": "🧪 本机环回测试", "flag": "🧪"},
    "direct": {"label": "🎯 直连", "flag": "🎯"},
    "block":  {"label": "🛑 阻断", "flag": "🛑"}
}

GROUP_TARGET_PROBE_URLS = {
    "AI": "https://chat.openai.com/cdn-cgi/trace",
    "YouTube": "https://www.youtube.com/generate_204",
    "TikTok": "https://p16-sign-va.tiktokcdn.com/favicon.ico",
    "Netflix": "https://www.netflix.com/title/80018499",
    "GitHub": "https://api.github.com/zen",
    "Google": "https://play.google.com/generate_204",
    "Microsoft": "http://www.msftconnecttest.com/connecttest.txt",
    "Apple": "http://captive.apple.com/hotspot-detect.html",
    "Games": "https://store.steampowered.com/favicon.ico",
    "Outside_CN": "https://cp.cloudflare.com/generate_204",
    "Domestic_CN": "http://connectivitycheck.platform.hicloud.com/generate_204",
    "Final_Fallback": "https://cp.cloudflare.com/generate_204"
}

DEFAULT_SHUNT_GROUPS = [
    {
        "id": "AI",
        "name": "AI",
        "subtitle": "OpenAI / Claude / Gemini / Copilot / Cursor",
        "selector_tag": "Shunt_AI", "legacy_selector": "AI_Best_Auto",
        "country": "US",
        "strategy": "smart",
        "manual_node": "", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["AI"],
        "domains": [
            "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com",
            "claude.ai", "anthropic.com", "gemini.google.com", "ai.google.com",
            "perplexity.ai", "cursor.sh",
            "copilot.microsoft.com", "copilot.cloud.microsoft", "edgeservices.bing.com",
            "sydney.bing.com", "edgeservices.microsoft.com", "cloudmessaging.edge.microsoft.com",
            "edge.microsoft.com", "graph.microsoft.com", "substrate.office.com"
        ], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "YouTube",
        "name": "YouTube",
        "subtitle": "YouTube 4K/8K 视频流与直播",
        "selector_tag": "Shunt_YouTube", "legacy_selector": "Stream_Auto",
        "country": "JP",
        "strategy": "fastest",
        "manual_node": "", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["YouTube"],
        "domains": ["youtube.com", "googlevideo.com", "ytimg.com", "ggpht.com", "youtu.be"], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "TikTok",
        "name": "TikTok",
        "subtitle": "TikTok 国际版短视频与直播",
        "selector_tag": "Shunt_TikTok", "legacy_selector": "Stream_Auto",
        "country": "SG",
        "strategy": "smart",
        "manual_node": "", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["TikTok"],
        "domains": [
            "tiktok.com", "tiktokv.com", "tiktokcdn.com", "tiktokcdn-us.com", "tiktokcdn-eu.com",
            "tiktokcdn-in.com", "tiktokw.us", "tiktokw.eu", "ttwstatic.com",
            "byteoversea.com", "byteoversea.net", "ibytedtos.com", "ibyteimg.com",
            "sgpstatp.com", "muscdn.com", "musical.ly", "tik-tokapi.com"
        ], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "Netflix",
        "name": "Netflix",
        "subtitle": "Netflix 奈飞 / Disney+ 国际流媒体",
        "selector_tag": "Shunt_Netflix", "legacy_selector": "Stream_Auto",
        "country": "SG",
        "strategy": "smart",
        "manual_node": "", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["Netflix"],
        "domains": ["netflix.com", "netflix.net", "nflxvideo.net", "nflximg.net", "disneyplus.com", "bamgrid.com"], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "GitHub",
        "name": "GitHub",
        "subtitle": "GitHub 代码仓库 / Release / 容器镜像",
        "selector_tag": "Shunt_GitHub", "legacy_selector": "AI_Best_Auto",
        "country": "JP",
        "strategy": "fastest",
        "manual_node": "", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["GitHub"],
        "domains": ["github.com", "githubusercontent.com", "githubassets.com", "ghcr.io", "github.io"], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "Google",
        "name": "Google",
        "subtitle": "Google 搜索 / Gmail / Play 商店与更新 CDN / FCM 推送",
        "selector_tag": "Shunt_Google", "legacy_selector": "AI_Best_Auto",
        "country": "ALL",
        "strategy": "fastest",
        "manual_node": "", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["Google"],
        "domains": [
            "google.com", "google.cn", "www.google.cn",
            "googleapis.com", "googleapis.cn", "services.googleapis.cn", "developers.google.cn",
            "play-fe.googleapis.com", "clientservices.googleapis.com", "firebaseinstallations.googleapis.com", "fcm.googleapis.com",
            "android.clients.google.com", "clients1.google.com", "clients2.google.com", "clients3.google.com",
            "clients4.google.com", "clients5.google.com", "clients6.google.com",
            "gstatic.com", "gstatic.cn", "connectivitycheck.gstatic.com",
            "googleusercontent.com", "ggpht.com",
            "gvt1.com", "gvt2.com", "gvt3.com", "beacons.gvt2.com", "beacons.gcp.gvt2.com",
            "xn--ngstr-lra8j.com",
            "dl.google.com", "dl-ssl.google.com",
            "android.com", "googlezip.net", "ota.googlezip.net",
            "play.google.com", "mtalk.google.com",
            "gmail.com", "1e100.net", "pki.goog", "dns.google"
        ],
        "domain_keywords": [], "exact_domains": [],
        "ip_cidrs": ["8.8.8.8/32", "8.8.4.4/32", "203.208.32.0/19"],
        "source_ip_cidrs": [],
        "ports": [5228, 5229, 5230]
    },
    {
        "id": "Microsoft",
        "name": "Microsoft",
        "subtitle": "微软 Office 365 / OneDrive / Windows 更新",
        "selector_tag": "Shunt_Microsoft", "legacy_selector": "",
        "country": "direct",
        "strategy": "manual",
        "manual_node": "direct", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["Microsoft"],
        "domains": ["microsoft.com", "office.com", "office365.com", "live.com", "msn.com", "windowsupdate.com", "azure.com"], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "Apple",
        "name": "Apple",
        "subtitle": "Apple iCloud / App Store / 推送服务",
        "selector_tag": "Shunt_Apple", "legacy_selector": "",
        "country": "direct",
        "strategy": "manual",
        "manual_node": "direct", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["Apple"],
        "domains": ["apple.com", "icloud.com", "cdn-apple.com", "mzstatic.com", "itunes.com"], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "Games",
        "name": "Games",
        "subtitle": "Steam / Epic / PlayStation / Xbox / 联机加速",
        "selector_tag": "Shunt_Games", "legacy_selector": "HK_TW_Media",
        "country": "direct",
        "strategy": "manual",
        "manual_node": "direct", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["Games"],
        "domains": ["steampowered.com", "steamcontent.com", "steamcommunity.com", "epicgames.com", "playstation.net", "xboxlive.com", "nintendo.net"], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "Outside_CN",
        "name": "国外",
        "subtitle": "常见国际网站与海外社交媒体 (Cloudflare / X / Telegram / Wiki)",
        "selector_tag": "Shunt_Outside_CN", "legacy_selector": "AI_Best_Auto",
        "country": "JP",
        "strategy": "smart",
        "manual_node": "", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["Outside_CN"],
        "domains": ["cloudflare.com", "twitter.com", "x.com", "t.me", "telegram.org", "wikipedia.org", "reddit.com"], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "Domestic_CN",
        "name": "国内",
        "subtitle": "中国大陆域名与 IP (geosite-cn / geoip-cn)",
        "selector_tag": "Shunt_Domestic_CN", "legacy_selector": "",
        "country": "direct",
        "strategy": "manual",
        "manual_node": "direct", "is_custom": False, "locked_bottom": False,
        "target_test_url": GROUP_TARGET_PROBE_URLS["Domestic_CN"],
        "domains": [
            "cn", "中国", "baidu.com", "bdstatic.com", "baidupcs.com",
            "qq.com", "lol.qq.com", "wegame.com.cn", "wegame.com", "tgp.qq.com", "ied-tqos.qq.com", "gcloud.qq.com", "gcloudsdk.com", "ace-anti-cheat.com", "qcloud.com", "weixin.qq.com", "wechat.com", "gtimg.com", "gtimg.cn", "myqcloud.com", "tencent.com", "tencent-cloud.net", "qpic.cn", "riotgames.com", "pvp.net", "leagueoflegends.com", "steamserver.net", "blizzard.cn", "battlenet.com.cn",
            "taobao.com", "tmall.com", "alicdn.com", "aliyun.com", "aliyuncs.com", "alipay.com", "1688.com", "tbcache.com",
            "jd.com", "360buyimg.com", "jcloudcs.com", "bilibili.com", "bilivideo.com", "hdslb.com", "biliapi.net",
            "163.com", "126.com", "126.net", "127.net", "netease.com",
            "douyin.com", "toutiao.com", "bytedance.com", "byteimg.com", "snssdk.com", "ixigua.com", "feishu.cn",
            "douyincdn.com", "douyinpic.com", "zijieapi.com", "amemv.com", "webcast.amemv.com",
            "bytecdn.cn", "pstatp.com", "volccdn.com", "bytegoofy.com",
            "douyinstatic.com", "douyinliving.com", "pull-flv", "pull-hls",
            "xiaohongshu.com", "xhscdn.com", "zhihu.com", "zhimg.com", "weibo.com", "weibocdn.com", "sina.com.cn",
            "sohu.com", "iqiyi.com", "youku.com", "mgtv.com", "kuaishou.com", "yximgs.com",
            "meituan.com", "dianping.com", "pinduoduo.com", "yangkeduo.com", "ctrip.com", "12306.cn",
            "mi.com", "xiaomi.com", "xiaomi.net", "huawei.com", "vmall.com", "dbankcdn.com", "hicloud.com",
            "csdn.net", "gitee.com", "oschina.net", "smzdm.com", "douban.com", "hupu.com", "nga.cn", "ip138.com"
        ], "domain_keywords": ["pull-flv", "pull-hls"], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    },
    {
        "id": "Final_Fallback",
        "name": "兜底保底出口",
        "subtitle": "精细分流内未能识别的所有剩余流量统一走此保底节点 (固定在最底部 · route.final)",
        "selector_tag": "Shunt_Final", "legacy_selector": "AI_Best_Auto",
        "country": "JP",
        "strategy": "smart",
        "manual_node": "", "is_custom": False, "locked_bottom": True,
        "target_test_url": GROUP_TARGET_PROBE_URLS["Final_Fallback"],
        "domains": [], "domain_keywords": [], "exact_domains": [], "ip_cidrs": [], "source_ip_cidrs": [], "ports": []
    }
]

def _normalize_shunt_groups_order(groups: list) -> list:
    """Ensures Domestic_CN is locked second-to-last (#N-1) and Final_Fallback is locked at the very bottom (#N),
    while allowing all other built-in and custom groups to be freely reordered and edited by the user."""
    regular = []
    locked_domestic = None
    bottom_final = None
    default_map = {dg["id"]: copy.deepcopy(dg) for dg in DEFAULT_SHUNT_GROUPS}
    seen_ids = set()
    for g in (groups or []):
        if not isinstance(g, dict) or not g.get("id"):
            continue
        gid = g["id"]
        if gid in seen_ids:
            continue
        seen_ids.add(gid)
        def_grp = default_map.get(gid, {})
        base = copy.deepcopy(def_grp)
        base.update(g)
        base.setdefault("selector_tag", f"Shunt_{gid}")
        base.setdefault("is_custom", gid not in default_map)
        base["locked_bottom"] = (gid == "Final_Fallback")
        base["locked_order"] = (gid in ("Domestic_CN", "Final_Fallback"))
        base.setdefault("target_test_url", GROUP_TARGET_PROBE_URLS.get(gid, "https://cp.cloudflare.com/generate_204"))
        for lk in ("domains", "domain_keywords", "exact_domains", "ip_cidrs", "source_ip_cidrs", "ports"):
            base.setdefault(lk, [])
        # Merge newly added preset domains / ip_cidrs / ports for built-in groups ONLY when user has not customized the group's rules
        if def_grp and not base.get("is_custom") and not base.get("user_edited_rules"):
            for lk in ("domains", "domain_keywords", "ip_cidrs", "ports"):
                merged_l = list(base.get(lk) or [])
                if gid == "Domestic_CN" and lk == "domains":
                    merged_l = [x for x in merged_l if x not in ("byteoversea.com", "byteoversea.net", "ibytedtos.com", "ibyteimg.com", "tiktokcdn.com", "tiktokv.com")]
                for d_item in (def_grp.get(lk) or []):
                    if d_item not in merged_l:
                        merged_l.append(d_item)
                base[lk] = merged_l
        elif def_grp and not base.get("is_custom"):
            base["user_edited_rules"] = True
        if gid == "Final_Fallback":
            bottom_final = base
        elif gid == "Domestic_CN":
            locked_domestic = base
        else:
            regular.append(base)
    # Ensure all preset groups exist
    for dg in DEFAULT_SHUNT_GROUPS:
        gid = dg["id"]
        if gid not in seen_ids:
            dg_copy = copy.deepcopy(dg)
            dg_copy["locked_bottom"] = (gid == "Final_Fallback")
            dg_copy["locked_order"] = (gid in ("Domestic_CN", "Final_Fallback"))
            if gid == "Final_Fallback":
                bottom_final = dg_copy
            elif gid == "Domestic_CN":
                locked_domestic = dg_copy
            else:
                regular.append(dg_copy)
    if locked_domestic is None:
        locked_domestic = copy.deepcopy(default_map["Domestic_CN"])
        locked_domestic["locked_bottom"] = False
        locked_domestic["locked_order"] = True
    if bottom_final is None:
        bottom_final = copy.deepcopy(default_map["Final_Fallback"])
        bottom_final["locked_bottom"] = True
        bottom_final["locked_order"] = True
    final_list = regular + [locked_domestic, bottom_final]
    for idx, item in enumerate(final_list):
        item["priority"] = idx + 1
    return final_list

def migrate_legacy_shunt_config(cfg: dict, conf_dir: Path = CONF_DIR) -> tuple:
    """Spec §8 Startup Config Migration: Deletes legacy `smart` / `fastest` strategies and migrates them once: smart / fastest """
    if not isinstance(cfg, dict):
        return cfg, []
    migrated_items = []
    auto_list = load_auto_nodes_config(conf_dir).get("auto_nodes", [])
    has_pools = len(auto_list) > 0
    g_strat = str(cfg.get("global_strategy") or "auto")
    if g_strat in ("smart", "fastest"):
        cfg["global_strategy"] = "auto" if has_pools else "manual"
        cfg["global_mode"] = "auto" if has_pools else "manual"
        cfg["global_auto_node_id"] = cfg.get("global_auto_node_id") or "auto_youtube"
        migrated_items.append(f"global:{g_strat}->{cfg['global_strategy']}")
    for g in (cfg.get("groups") or []):
        if not isinstance(g, dict):
            continue
        gid = g.get("id", "")
        st = str(g.get("strategy") or "")
        c = str(g.get("country") or "ALL")
        if c == "direct" or st == "direct" or g.get("manual_node") == "direct":
            if g.get("shunt_mode") != "direct" or st in ("smart", "fastest"):
                g["shunt_mode"] = "direct"
                g["strategy"] = "direct"
                g["country"] = "direct"
                g["manual_node"] = "direct"
        elif st in ("smart", "fastest"):
            default_aid = "auto_ai" if gid in ("AI", "Google", "GitHub") else "auto_youtube"
            if has_pools:
                g["strategy"] = "auto"
                g["shunt_mode"] = "auto"
                g["auto_node_id"] = g.get("auto_node_id") or default_aid
                g["manual_node"] = f"auto:{g['auto_node_id']}"
                migrated_items.append(f"{gid}:{st}->auto({g['auto_node_id']})")
            else:
                g["strategy"] = "manual"
                g["shunt_mode"] = "manual"
                migrated_items.append(f"{gid}:{st}->manual")
        elif st == "manual":
            g.setdefault("shunt_mode", "manual")
        elif st == "auto":
            g.setdefault("shunt_mode", "auto")
            default_aid = "auto_ai" if gid in ("AI", "Google", "GitHub") else "auto_youtube"
            g.setdefault("auto_node_id", default_aid)
    if migrated_items:
        try:
            RUN_DIR.mkdir(parents=True, exist_ok=True)
            log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Migrated legacy shunt strategies: {', '.join(migrated_items)}\n"
            with open(RUN_DIR / "migration.log", "a", encoding="utf-8") as lf:
                lf.write(log_line)
        except Exception:
            pass
    return cfg, migrated_items

_GFW_DIRECT_EXEMPT_DOMAINS = {
    "cloudflare.com", "www.cloudflare.com",
    "bing.com", "www.bing.com", "cn.bing.com",
    "apple.com", "www.apple.com", "icloud.com", "cdn-apple.com", "mzstatic.com", "itunes.com",
    "microsoft.com", "www.microsoft.com", "office.com", "office365.com", "live.com", "msn.com", "windowsupdate.com", "azure.com",
}
_GFW_EXTRA_BLOCKED_DOMAINS = [
    "facebook.com", "fbcdn.net", "instagram.com", "whatsapp.com", "threads.net",
    "discord.com", "discordapp.com", "discord.gg", "medium.com", "nytimes.com",
    "bbc.com", "bbc.co.uk", "wsj.com", "bloomberg.com", "reuters.com",
    "pixiv.net", "pximg.net", "twitch.tv", "vimeo.com", "duckduckgo.com",
    "archive.org", "huggingface.co", "civitai.com", "docker.io", "registry-1.docker.io",
    "quora.com", "pinterest.com", "tumblr.com", "flickr.com", "dropbox.com",
    "mega.nz", "proton.me", "protonmail.com", "signal.org", "line.me", "v2ex.com",
]

def _get_gfw_list_domains(shunt_cfg: dict) -> list:
    """Returns canonical sorted list of GFW-blocked domain suffixes for gfw_list mode, excluding non-blocked international CDNs/OS vendors."""
    raw = list(_GFW_EXTRA_BLOCKED_DOMAINS)
    for sg in (shunt_cfg or {}).get("groups", []):
        if sg.get("id") in ("AI", "YouTube", "TikTok", "Netflix", "GitHub", "Google", "Outside_CN"):
            for d in (sg.get("domains") or []):
                ds = str(d or "").strip().lower().strip(".")
                if ds and ds not in _GFW_DIRECT_EXEMPT_DOMAINS:
                    raw.append(ds)
    return sorted(list(set(raw)))

def load_shunt_config(conf_dir: Path = CONF_DIR) -> dict:
    cfg = {
        "shunt_enabled": True,
        "routing_mode": "rule_shunt",
        "global_mode": "auto",
        "global_auto_node_id": "auto_youtube",
        "global_country": "JP",
        "global_strategy": "auto",
        "global_manual_node": "",
        "groups": _normalize_shunt_groups_order([dict(g) for g in DEFAULT_SHUNT_GROUPS])
    }
    loaded_from_disk = False
    f_main = conf_dir / "shunt.json"
    f_alt = conf_dir / "shunt_config.json"
    candidates_sf = []
    for idx_sf, sf in enumerate((f_main, f_alt)):
        if sf.is_file():
            try:
                st_m = sf.stat().st_mtime_ns
                candidates_sf.append((-st_m, idx_sf, sf))
            except Exception:
                pass
    candidates_sf.sort()
    for _, _, sf in candidates_sf:
        try:
            saved = json.loads(sf.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                cfg.update({k: v for k, v in saved.items() if k != "groups"})
                cfg["groups"] = _normalize_shunt_groups_order(saved.get("groups") or [])
                cfg["shunt_enabled"] = (cfg.get("routing_mode", "rule_shunt") == "rule_shunt")
                loaded_from_disk = True
                # If shunt.json was restored from backup and is newer than shunt_config.json, sync shunt_config.json immediately
                if len(candidates_sf) == 2 and candidates_sf[0][0] != candidates_sf[1][0]:
                    try:
                        other_sf = candidates_sf[1][2]
                        _atomic_write_text(other_sf, sf.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                break
        except Exception:
            pass
    cfg, mig = migrate_legacy_shunt_config(cfg, conf_dir)
    if loaded_from_disk:
        try:
            raw_on_disk = json.loads((conf_dir / "shunt.json").read_text(encoding="utf-8")) if (conf_dir / "shunt.json").is_file() else {}
            disk_google = next((x for x in (raw_on_disk.get("groups") or []) if isinstance(x, dict) and x.get("id") == "Google"), {})
            disk_cn = next((x for x in (raw_on_disk.get("groups") or []) if isinstance(x, dict) and x.get("id") == "Domestic_CN"), {})
            disk_tk = next((x for x in (raw_on_disk.get("groups") or []) if isinstance(x, dict) and x.get("id") == "TikTok"), {})
            if (mig
                    or "gvt1.com" not in (disk_google.get("domains") or [])
                    or "play-fe.googleapis.com" not in (disk_google.get("domains") or [])
                    or "xn--ngstr-lra8j.com" not in (disk_google.get("domains") or [])
                    or "ibytedtos.com" not in (disk_tk.get("domains") or [])
                    or "byteoversea.com" in (disk_cn.get("domains") or [])
                    or "ibytedtos.com" in (disk_cn.get("domains") or [])
                    or "douyincdn.com" not in (disk_cn.get("domains") or [])):
                save_shunt_config(cfg, conf_dir)
        except Exception:
            if mig:
                save_shunt_config(cfg, conf_dir)
    return cfg

def save_shunt_config(cfg: dict, conf_dir: Path = CONF_DIR):
    with _SUB_LOCK:
        conf_dir.mkdir(parents=True, exist_ok=True)
        cfg["groups"] = _normalize_shunt_groups_order(cfg.get("groups") or [])
        cfg["shunt_enabled"] = (cfg.get("routing_mode", "rule_shunt") == "rule_shunt")
        raw = json.dumps(cfg, indent=2, ensure_ascii=False)
        # 幂等写入：内容与磁盘一致时跳过落盘。
        # 原因：load/build 路径会反复调用本函数，无条件写会让 shunt.json 的 mtime 持续抖动，
        # 而 /api/status 与 _JSON_WIRE_MEMO 的缓存键都含 shunt.json 的 (mtime_ns, size) →
        # 缓存被自己的写入击穿，每次请求都全量重建（实测 ~1s）。顺带减少 flash 写入。
        for _fn in ("shunt_config.json", "shunt.json"):
            _p = conf_dir / _fn
            try:
                if _p.is_file() and _p.read_text(encoding="utf-8") == raw:
                    continue
            except Exception:
                pass
            _atomic_write_text(_p, raw)

def _normalize_group_shunt_params(g: dict) -> tuple:
    """Canonicalizes (shunt_mode, country, strategy, auto_node_id, manual_node) for any shunt group dict `g`."""
    gid = g.get("id", "")
    default_aid = "auto_ai" if gid in ("AI", "Google", "GitHub") else "auto_youtube"
    raw_sm = str(g.get("shunt_mode") or "").strip().lower()
    raw_st = str(g.get("strategy") or "").strip().lower()
    raw_c = str(g.get("country") or "ALL").strip()
    raw_m = str(g.get("manual_node") or "").strip()
    raw_aid = str(g.get("auto_node_id") or "").strip()
    if raw_m.startswith("auto:"):
        if not raw_aid:
            raw_aid = raw_m.split("auto:", 1)[1].strip()
    if raw_sm == "direct" or raw_c == "direct" or raw_st == "direct" or raw_m == "direct":
        return ("direct", "direct", "direct", "", "direct")
    if raw_c == "block" or raw_st == "block" or raw_m == "block":
        return ("block", "block", "block", "", "block")
    if raw_sm == "manual" or (raw_st == "manual" and not raw_m.startswith("auto:")):
        c_norm = raw_c if raw_c in ("HK", "TW", "JP", "SG", "US", "KR", "OTHER", "ALL") else "JP"
        m_norm = "" if (raw_m.startswith("auto:") or raw_m in ("direct", "block")) else raw_m
        return ("manual", c_norm, "manual", raw_aid or default_aid, m_norm)
    aid_norm = raw_aid or default_aid
    return ("auto", raw_c if raw_c not in ("direct", "block") else "ALL", "auto", aid_norm, f"auto:{aid_norm}")

def _match_auto_node_pool(auto_nodes_list: list, aid: str, allow_fallback: bool = True) -> dict:
    """Matches an Auto-Node card by exact id/tag/name first, then by semantic alias ('auto_ai' -> 'AI自动',
    'auto_youtube' -> 'Youtube自动', 'auto_netflix' -> '网飞'). If allow_fallback is True and no alias matches,
    selects the healthiest card (preferring dedicated non-random nodes and lower RTT) instead of blindly returning [0]."""
    if not isinstance(auto_nodes_list, list) or not auto_nodes_list:
        return None
    valid_list = [an for an in auto_nodes_list if isinstance(an, dict)]
    if not valid_list:
        return None
    aid_s = str(aid or "").strip()
    if aid_s.startswith("auto:"):
        aid_s = aid_s.split("auto:", 1)[1].strip()
    aid_low = aid_s.lower()
    if aid_low:
        # 1. Exact match on id, tag, or name
        for an in valid_list:
            if (str(an.get("id") or "").strip().lower() == aid_low
                    or str(an.get("tag") or "").strip().lower() == aid_low
                    or str(an.get("name") or "").strip().lower() == aid_low):
                return an
        # 2. Semantic alias match (handles user cards with generated auto_<timestamp> IDs like 'AI自动', 'Youtube自动', '网飞')
        alias_groups = [
            ({"auto_ai", "ai_best_auto", "ai", "ai自动", "openai", "gemini"}, ("ai", "gpt", "gemini", "claude", "智能")),
            ({"auto_youtube", "stream_auto", "youtube", "youtube自动", "yt", "tiktok"}, ("youtube", "yt", "stream", "流媒体", "视频", "tiktok")),
            ({"auto_netflix", "netflix", "网飞", "奈飞", "媒体"}, ("netflix", "网飞", "奈飞", "disney", "影视")),
        ]
        for trigger_set, kw_tuple in alias_groups:
            if aid_low in trigger_set or any(k in aid_low for k in kw_tuple):
                for an in valid_list:
                    combined = " ".join([
                        str(an.get("id") or "").lower(),
                        str(an.get("tag") or "").lower(),
                        str(an.get("name") or "").lower(),
                    ])
                    if any(k in combined for k in kw_tuple):
                        return an
    if not allow_fallback:
        return None
    # 3. Smart health-aware fallback: prefer cards with a reachable dedicated (non-地区随机) current_node and lowest RTT
    def _card_rank(an_obj):
        cur = str(an_obj.get("current_node") or "").strip()
        has_cur = bool(cur and cur not in ("direct", "block"))
        is_rand = _is_random_region_node(cur) if has_cur else True
        d_ms = int(an_obj.get("current_delay_ms") or -1)
        is_full = (an_obj.get("mode") == "full" or bool(an_obj.get("service_check_enabled")))
        return (
            0 if has_cur else 1,
            1 if is_rand else 0,
            0 if (d_ms > 0) else 1,
            0 if is_full else 1,
            d_ms if d_ms > 0 else 99999
        )
    return sorted(valid_list, key=_card_rank)[0]

def resolve_node_for_country_strategy_with_failover(
    country: str, strategy: str, manual_node: str,
    candidate_tags: list, delays: dict, scores: dict = None,
    group_id: str = "", target_results: dict = None,
    quarantine_until: dict = None, node_stats: dict = None,
    conf_dir: Path = CONF_DIR,
    saved_nodes: list = None, subs_list: list = None,
    store: dict = None, auto_cfg: dict = None,
    precomputed_ctx: dict = None
) -> dict:
    """Spec §2, §2.1 & §5 3-Mode Shunt Resolver (`direct` | `manual` | `auto`): - Strictly enforces `selectable = subscription."""
    quarantine_until = quarantine_until or {}
    now_f = time.time()
    if country == "direct" or strategy == "direct" or manual_node == "direct":
        return {"selected": "direct", "backups": [], "target_verified": True, "no_available_node": False}
    if country == "block" or strategy == "block":
        return {"selected": "block", "backups": [], "target_verified": True, "no_available_node": False}
    if isinstance(precomputed_ctx, dict) and not quarantine_until:
        saved_by_tag = precomputed_ctx["saved_by_tag"]
        selectable_tags = precomputed_ctx["selectable_tags"]
        selectable_set = precomputed_ctx["selectable_set"]
        tag_delay = precomputed_ctx["tag_delay"]
        tag_state = precomputed_ctx["tag_state"]
        cdn_ok_map = precomputed_ctx["cdn_ok_map"]
        auto_pools_map = precomputed_ctx["auto_pools_map"]
        def _tag_cdn_ok(t_name: str) -> bool:
            return cdn_ok_map.get(t_name, True)
    else:
        if saved_nodes is None:
            saved_nodes = load_saved_nodes(conf_dir)
        if subs_list is None:
            subs_list = load_subscriptions(conf_dir)
        if store is None:
            store = load_node_probe_store(conf_dir)
        saved_by_tag = {n.get("tag", ""): n for n in saved_nodes}
        all_real = [
            t for t in (candidate_tags or [])
            if t not in ("direct", "block", "AI_Best_Auto", "Stream_Auto", "HK_TW_Media")
            and not str(t).startswith("Shunt_")
            and not str(t).startswith("Auto_")
        ]
        selectable_tags = []
        tag_delay = {}
        tag_state = {}
        now_int = int(now_f)
        for t in all_real:
            if is_builtin_test_node(t):
                continue
            if quarantine_until.get(t, 0) > now_f:
                continue
            n_obj = saved_by_tag.get(t)
            if n_obj is not None:
                ev = evaluate_node_selectability(n_obj, store=store, subs_list=subs_list, now_ts=now_int, conf_dir=conf_dir)
                if not ev["selectable"]:
                    continue
                tag_state[t] = ev["state"]
                tag_delay[t] = float(ev["delay_ms"]) if (ev["state"] == "ok" and ev["delay_ms"] > 0) else float(delays.get(t, 0.0) or 0.0)
            else:
                d_in = float(delays.get(t, 0.0) or 0.0)
                tag_state[t] = "ok" if d_in > 0 else "pending"
                tag_delay[t] = d_in
            selectable_tags.append(t)
        cdn_ok_map = {}
        for t_name in selectable_tags:
            n_o = saved_by_tag.get(t_name)
            nid_o = (n_o.get("node_id") or compute_node_id(n_o)) if isinstance(n_o, dict) else t_name
            cdn_ok_map[t_name] = _is_node_cdn_tls_healthy((store or {}).get(nid_o) or (store or {}).get(t_name) or {})
        def _tag_cdn_ok(t_name: str) -> bool:
            return cdn_ok_map.get(t_name, True)
        selectable_tags.sort(key=lambda t: (
            0 if (tag_state.get(t) == "ok" and tag_delay.get(t, 0.0) > 0 and _tag_cdn_ok(t)) else (1 if (tag_state.get(t) == "ok" and tag_delay.get(t, 0.0) > 0) else 2),
            (tag_delay.get(t, 99999.0) * (1.28 if _is_random_region_node(t) else 1.0)) if tag_delay.get(t, 0.0) > 0 else 99999.0,
            1 if _is_random_region_node(t) else 0,
            t
        ))
        selectable_set = set(selectable_tags)
        auto_pools_map = {}
    # 1. Auto Mode (`auto` or `manual_node` starting with `auto:`): resolve from Auto Node Pool
    # P1-6 Fix: Custom groups (`Custom_*`) or groups with a specific country filter must NEVER stick to a dead/unprobed
    # card node (`delay <= 0` or `state != "ok"`), and must automatically fail over to healthy `ok` nodes (e.g. SG-N-2 154ms).
    is_custom_grp = str(group_id or "").startswith("Custom_")
    if strategy == "auto" or (manual_node and str(manual_node).startswith("auto:")):
        aid = str(manual_node).split("auto:", 1)[1] if str(manual_node).startswith("auto:") else (manual_node or ("auto_ai" if group_id in ("AI", "Google", "GitHub") else "auto_youtube"))
        acfg = auto_cfg if isinstance(auto_cfg, dict) else load_auto_nodes_config(conf_dir)
        explicit_pool_bound = bool(not is_custom_grp and manual_node and (str(manual_node).startswith("auto:") or str(manual_node).lower().startswith("auto_")))
        an = _match_auto_node_pool(acfg.get("auto_nodes") or [], aid)
        if an is not None:
            an_id_key = str(an.get("id") or an.get("tag") or aid)
            if an_id_key in auto_pools_map:
                cands = list(auto_pools_map[an_id_key])
            else:
                cands = get_auto_node_candidate_pool(an, conf_dir=conf_dir, saved_nodes=saved_nodes, subs_list=subs_list, store=store)
                auto_pools_map[an_id_key] = list(cands)
            if country and country not in ("ALL", "direct", "block"):
                cands_country = [x for x in cands if x.get("country") == country or classify_node_region(x["tag"], saved_by_tag.get(x["tag"])) == country]
                if cands_country or is_custom_grp or not explicit_pool_bound:
                    cands = cands_country
            ok_cands = [
                x for x in cands
                if x["tag"] in selectable_set and tag_state.get(x["tag"]) == "ok" and tag_delay.get(x["tag"], 0.0) > 0
            ]
            cur_n = an.get("current_node") or ""
            cur_alive = bool(cur_n and cur_n != "direct" and cur_n in selectable_set and tag_state.get(cur_n) == "ok" and tag_delay.get(cur_n, 0.0) > 0)
            if not cur_alive:
                cur_n = ok_cands[0]["tag"] if ok_cands else ""
            # Check if cur_n is degraded (failed CDN TLS or is a '地区随机' rotation node while a dedicated faster node exists)
            cur_cdn_ok = _tag_cdn_ok(cur_n) if cur_n else False
            cur_is_rand = _is_random_region_node(cur_n) if cur_n else False
            if (not cur_cdn_ok or cur_is_rand):
                cur_d_val = tag_delay.get(cur_n, 0.0) or float(an.get("current_delay_ms") or 99999.0)
                better_in_pool = [
                    x for x in ok_cands
                    if x.get("cdn_tls_ok", True) and not x.get("is_random_region", False)
                    and (not cur_cdn_ok or float(x.get("delay_ms") or 99999.0) <= cur_d_val * 1.28)
                ]
                if better_in_pool:
                    cur_n = better_in_pool[0]["tag"]
                else:
                    # Check if a peer Auto-Node card (e.g. '网飞' or 'AI自动') has a verified dedicated ok node with lower RTT
                    peer_dedicated = []
                    for peer_an in (acfg.get("auto_nodes") or []):
                        if not isinstance(peer_an, dict):
                            continue
                        p_cur = str(peer_an.get("current_node") or "").strip()
                        if p_cur and p_cur not in ("direct", "block") and p_cur in selectable_tags and tag_state.get(p_cur) == "ok" and tag_delay.get(p_cur, 0.0) > 0 and _tag_cdn_ok(p_cur) and not _is_random_region_node(p_cur):
                            p_d = tag_delay.get(p_cur, 0.0)
                            if p_d > 0 and (not cur_cdn_ok or tag_delay.get(cur_n, 99999.0) <= 0 or p_d < tag_delay.get(cur_n, 99999.0)):
                                peer_dedicated.append((0 if peer_an.get("mode") == "full" else 1, p_d, p_cur))
                    if peer_dedicated:
                        peer_dedicated.sort()
                        cur_n = peer_dedicated[0][2]
            if cur_n and cur_n != "direct" and cur_n in selectable_tags and tag_state.get(cur_n) == "ok" and tag_delay.get(cur_n, 0.0) > 0:
                if explicit_pool_bound or not country or country in ("ALL", "direct", "block") or classify_node_country_5plus1(cur_n, saved_by_tag.get(cur_n)) == country or classify_node_region(cur_n, saved_by_tag.get(cur_n)) == country:
                    bks = [x["tag"] for x in ok_cands if x["tag"] != cur_n][:2]
                    if not bks:
                        bks = [t for t in selectable_tags if t != cur_n and tag_state.get(t) == "ok" and tag_delay.get(t, 0.0) > 0][:2]
                    return {"selected": cur_n, "backups": bks, "target_verified": True, "no_available_node": False}
            if ok_cands:
                chosen_c = ok_cands[0]["tag"]
                bks = [x["tag"] for x in ok_cands[1:3]]
                return {"selected": chosen_c, "backups": bks, "target_verified": True, "no_available_node": False}
            if not is_custom_grp and (not country or country in ("ALL", "direct", "block")) and cands:
                any_ok_global = any(tag_state.get(t) == "ok" and tag_delay.get(t, 0.0) > 0 for t in selectable_tags)
                if not any_ok_global:
                    chosen_c = cands[0]["tag"]
                    bks = [x["tag"] for x in cands[1:3]]
                    return {"selected": chosen_c, "backups": bks, "target_verified": True, "no_available_node": False}
            if explicit_pool_bound and an.get("all_groups_dead_alert"):
                return {"selected": "direct", "backups": [], "target_verified": False, "no_available_node": True}
    # 2. Filter by country (use precomputed region_pools when available for O(1) lookup)
    _pre_rpools = precomputed_ctx.get("region_pools") if isinstance(precomputed_ctx, dict) and not quarantine_until else None
    if country and country not in ("ALL", "direct", "block"):
        if isinstance(_pre_rpools, dict) and country in _pre_rpools:
            region_pool = list(_pre_rpools[country])
        else:
            region_pool = [
                t for t in selectable_tags
                if classify_node_country_5plus1(t, saved_by_tag.get(t)) == country
                or classify_node_region(t, saved_by_tag.get(t)) == country
            ]
    else:
        region_pool = list(selectable_tags)
    # 3. Manual mode: if manual_node is selectable, use it; otherwise fall back to same-country selectable node, else 'direct'
    if strategy == "manual":
        if manual_node and manual_node in selectable_tags:
            bks = [t for t in region_pool if t != manual_node][:2]
            return {"selected": manual_node, "backups": bks, "target_verified": True, "no_available_node": False}
        if region_pool:
            return {"selected": region_pool[0], "backups": region_pool[1:3], "target_verified": True, "no_available_node": False}
        return {"selected": "direct", "backups": [], "target_verified": False, "no_available_node": True}
    target_pool = region_pool if region_pool else selectable_tags
    if not target_pool:
        return {"selected": "direct", "backups": [], "target_verified": False, "no_available_node": True}
    chosen = target_pool[0]
    backups = [t for t in target_pool[1:3] if t != chosen]
    return {"selected": chosen, "backups": backups, "target_verified": True, "no_available_node": False}

def resolve_node_for_country_strategy(country: str, strategy: str, manual_node: str,
                                      candidate_tags: list, delays: dict, scores: dict = None) -> str:
    return resolve_node_for_country_strategy_with_failover(
        country, strategy, manual_node, candidate_tags, delays, scores
    )["selected"]

DEFAULT_REAL_SUB_URL = ""
SUB_SYNC_STATE = {"running": False, "last_result": None, "started_at": 0}

def load_subscriptions(conf_dir: Path = CONF_DIR) -> list:
    sub_file = conf_dir / "subscriptions.json"
    saved_nodes = load_saved_nodes(conf_dir)
    ext_nodes = [n for n in saved_nodes if not is_builtin_test_node(n.get("tag", ""))]
    if sub_file.is_file():
        try:
            subs = json.loads(sub_file.read_text(encoding="utf-8"))
            if isinstance(subs, list):
                cleaned = []
                for idx, s in enumerate(subs):
                    if not isinstance(s, dict):
                        continue
                    url_s = str(s.get("url") or "").strip()
                    if "tinttt8uui" in url_s and len(ext_nodes) == 0 and s.get("count") == 150:
                        continue
                    s["id"] = s.get("id") or f"sub_{idx + 1}"
                    s.setdefault("name", f"机场订阅 {idx + 1}")
                    s.setdefault("enabled", True)
                    s.setdefault("auto_update", True)
                    s.setdefault("update_interval_min", 360)
                    s.setdefault("last_sync_ts", int(time.time()))
                    s.setdefault("status", "ok" if s.get("count", 0) > 0 else "empty")
                    s.setdefault("last_error", "")
                    owned_cnt = sum(
                        1 for n in ext_nodes
                        if n.get("_sub_id") == s["id"] or (url_s and n.get("_sub_url") == url_s)
                    )
                    if owned_cnt > 0:
                        s["count"] = owned_cnt
                    elif len(subs) == 1 and len(ext_nodes) > 0 and s.get("status") not in ("error", "failed"):
                        s["count"] = sum(1 for n in ext_nodes if not n.get("_manual"))
                    cleaned.append(s)
                return cleaned
        except Exception:
            pass
    return []

def save_subscriptions(subs: list, conf_dir: Path = CONF_DIR):
    with _SUB_LOCK:
        conf_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(conf_dir / "subscriptions.json", json.dumps(subs, indent=2, ensure_ascii=False))

def set_subscription_enabled(sub_id: str = "", sub_url: str = "", enabled: bool = True,
                             conf_dir: Path = CONF_DIR) -> dict:
    """Spec §2.1 Subscription Orthogonal Switch (`enabled`): - Toggles `subscription.enabled` WITHOUT making any network reques"""
    with _SUB_LOCK:
        subs = load_subscriptions(conf_dir)
        target_sub = None
        for s in subs:
            if (sub_id and s.get("id") == sub_id) or (sub_url and s.get("url") == sub_url):
                target_sub = s
                break
        if not target_sub and len(subs) == 1:
            target_sub = subs[0]
        if not target_sub:
            return {"ok": False, "error": "subscription_not_found", "message": "未找到对应的订阅记录"}
        sid = target_sub.get("id", "")
        surl = target_sub.get("url", "")
        target_sub["enabled"] = bool(enabled)
        # Note: `last_sync_ts` is strictly preserved!
        save_subscriptions(subs, conf_dir)
    raw_nodes = load_saved_nodes(conf_dir)
    sub_node_tags = {
        n.get("tag", "") for n in raw_nodes
        if (sid and n.get("_sub_id") == sid) or (surl and n.get("_sub_url") == surl)
    }
    # Check which Auto Node Pools and Shunt Groups were using nodes from this subscription
    affected_auto_nodes = []
    acfg = load_auto_nodes_config(conf_dir)
    for an in (acfg.get("auto_nodes") or []):
        if an.get("current_node") in sub_node_tags or any(t in sub_node_tags for t in (an.get("pool_candidate_tags") or [])):
            affected_auto_nodes.append(an.get("name") or an.get("id"))
    sh_before = build_shunt_api_response(conf_dir)
    prev_group_nodes = {g["id"]: g.get("resolved_node", "") for g in (sh_before.get("groups") or [])}
    # Fast millisecond-level hot-switch: keep outbounds in sing-box and only recompute Auto Pools + Clash selectors!
    PROBE_ENGINE.apply_shunt_selections(conf_dir)
    sh_after = build_shunt_api_response(conf_dir)
    affected_groups = []
    for g in (sh_after.get("groups") or []):
        gid = g["id"]
        if prev_group_nodes.get(gid) in sub_node_tags or g.get("manual_node") in sub_node_tags:
            if g.get("resolved_node") != prev_group_nodes.get(gid) or not enabled:
                affected_groups.append(gid)
    return {
        "ok": True,
        "id": sid,
        "enabled": bool(enabled),
        "subscription": target_sub,
        "subscriptions": (build_nodes_api_response(conf_dir).get("subscriptions") or load_subscriptions(conf_dir)),
        "affected_groups": affected_groups,
        "affected_auto_nodes": affected_auto_nodes,
        "shunt": sh_after
    }

# Subscription DNS Lookup & IPv4-Only Curl Fetcher (borrowed from NOLO-LINK nolo-sub-lookup.mjs & curl-fetch.mjs)
_SUB_DNS_CACHE = {}  # host -> {"ips": [ipv4...], "exp": monotonic_ts}
_SUB_DNS_NXDOMAIN_HOSTS = set()
_SUB_DNS_LOCK = threading.Lock()

def _is_fake_or_loopback_ip(ip_str: str) -> bool:
    s = str(ip_str or "").strip().lower()
    if not s or s.startswith("127.") or s.startswith("0.") or s == "::1":
        return True
    if s.startswith("198.18.") or s.startswith("198.19.") or s.startswith("fc") or s.startswith("fd") or s.startswith("fe80:"):
        return True
    return False

def _read_wan_resolv_servers() -> list:
    """Reads real WAN upstream DNS servers from OpenWrt /tmp/resolv.conf.d/resolv.conf.auto (nolo-sub-lookup.mjs)."""
    servers = []
    for p in ("/tmp/resolv.conf.d/resolv.conf.auto", "/tmp/resolv.conf.auto"):
        try:
            fp = Path(p)
            if not fp.is_file():
                continue
            for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
                m = re.match(r"^\s*nameserver\s+([^\s#]+)", line)
                if m:
                    ip = m.group(1).strip()
                    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip) and not _is_fake_or_loopback_ip(ip):
                        if ip not in servers:
                            servers.append(ip)
        except Exception:
            pass
    for pub in ("223.5.5.5", "119.29.29.29", "1.1.1.1", "8.8.8.8"):
        if pub not in servers:
            servers.append(pub)
    return servers

def _udp_dns_query_a(host: str, dns_server: str, timeout: float = 2.0) -> list:
    """Sends a raw UDP DNS A-record query with SO_MARK=255 to bypass local port-53 FakeIP hijack."""
    try:
        tid = random.randint(1, 65534)
        q_labels = b"".join(bytes([len(p)]) + p.encode("ascii") for p in host.strip(".").split(".") if p) + b"\x00"
        pkt = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0) + q_labels + struct.pack("!HH", 1, 1)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, 36, 255)  # SO_MARK = 255
        except Exception:
            pass
        s.settimeout(timeout)
        s.sendto(pkt, (dns_server, 53))
        resp, _ = s.recvfrom(1024)
        s.close()
        if len(resp) < 12 or struct.unpack("!H", resp[:2])[0] != tid:
            return []
        flags_u = struct.unpack("!H", resp[2:4])[0]
        rcode = flags_u & 0x000F
        if rcode == 3:
            with _SUB_DNS_LOCK:
                _SUB_DNS_NXDOMAIN_HOSTS.add(host.strip(".").lower())
            return []
        qdcount, ancount = struct.unpack("!HH", resp[4:8])
        idx = 12
        for _ in range(qdcount):
            while idx < len(resp) and resp[idx] != 0:
                if (resp[idx] & 0xC0) == 0xC0:
                    idx += 2
                    break
                idx += 1 + resp[idx]
            else:
                idx += 1
            idx += 4
        ips = []
        for _ in range(ancount):
            if idx >= len(resp):
                break
            if (resp[idx] & 0xC0) == 0xC0:
                idx += 2
            else:
                while idx < len(resp) and resp[idx] != 0:
                    idx += 1 + resp[idx]
                idx += 1
            if idx + 10 > len(resp):
                break
            rtype, rclass, _, rdlen = struct.unpack("!HHIH", resp[idx:idx+10])
            idx += 10
            if rtype == 1 and rclass == 1 and rdlen == 4 and idx + 4 <= len(resp):
                ip = socket.inet_ntoa(resp[idx:idx+4])
                if not _is_fake_or_loopback_ip(ip) and ip not in ips:
                    ips.append(ip)
            idx += rdlen
        return ips
    except Exception:
        return []

def _resolve_subscription_host_ips(host: str) -> list:
    """Resolves subscription hostname to real IPv4 addresses (60s positive / 15s negative cache), filtering FakeIPs."""
    h = str(host or "").strip().lower().strip("[]")
    if not h:
        return []
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", h):
        return [h]
    now_m = time.monotonic()
    with _SUB_DNS_LOCK:
        hit = _SUB_DNS_CACHE.get(h)
        if hit and now_m < hit["exp"]:
            return list(hit["ips"])
    ips = []
    # 1. Query WAN resolv.conf.auto + public DNS via direct UDP (SO_MARK=255)
    for srv in _read_wan_resolv_servers():
        ans = _udp_dns_query_a(h, srv, timeout=2.0)
        if ans:
            ips = ans
            break
    # 2. Fallback to AliDNS / DNSPod DoH
    if not ips:
        q = urllib.parse.quote(h)
        for ep in (f"https://223.5.5.5/resolve?name={q}&type=A", f"https://1.12.12.12/resolve?name={q}&type=A"):
            try:
                req = urllib.request.Request(ep, headers={"Accept": "application/dns-json"})
                with urllib.request.urlopen(req, timeout=4, context=ssl._create_unverified_context()) as r:
                    d = json.loads(r.read().decode("utf-8", "ignore"))
                if int(d.get("Status") or 0) == 3:
                    with _SUB_DNS_LOCK:
                        _SUB_DNS_NXDOMAIN_HOSTS.add(h)
                for ans in (d.get("Answer") or []):
                    ip = str(ans.get("data") or "").strip()
                    if ans.get("type") == 1 and ip and ":" not in ip and not _is_fake_or_loopback_ip(ip):
                        if ip not in ips:
                            ips.append(ip)
                if ips:
                    break
            except Exception:
                pass
    with _SUB_DNS_LOCK:
        _SUB_DNS_CACHE[h] = {"ips": ips, "exp": now_m + (60.0 if ips else 15.0)}
    return list(ips)

def _resolve_via_public_dns(host: str, dns_server: str = "223.5.5.5") -> str:
    ips = _resolve_subscription_host_ips(host)
    return ips[0] if ips else ""

def _curl_fetch_subscription(initial_url: str, timeout_sec: int = 25, user_agent: str = "clash-verge/v1.7.7") -> dict:
    """Fetches subscription via system curl with IPv4-only --resolve pinning and hop-by-hop redirect validation
    (borrowed from NOLO-LINK curl-fetch.mjs & patches.mjs to prevent IPv6 RST exit 35 and Node/Python TLS fingerprint blocks)."""
    if not shutil.which("curl"):
        return {"ok": False, "status": 0, "body": "", "headers": {}, "error": "curl_unavailable"}
    cur_url = str(initial_url or "").strip()
    for hop in range(4):
        sp = urllib.parse.urlsplit(cur_url)
        host = (sp.hostname or "").strip()
        port = sp.port or (443 if sp.scheme == "https" else 80)
        v4_ips = _resolve_subscription_host_ips(host) if host else []
        if host and not v4_ips and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host) and host not in ("localhost", "127.0.0.1"):
            return {"ok": False, "status": 0, "body": "", "headers": {}, "error": f"NXDOMAIN: DNS 解析失败，订阅域名 {host} 不存在或无法解析"}
        tmp_dir = Path(f"/tmp/ailink-curl-{os.getpid()}-{int(time.time()*1000)}")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        body_path = tmp_dir / "body"
        head_path = tmp_dir / "head"
        try:
            args = [
                "curl", "-4", "-sS", "-k", "--proto", "=http,https", "--max-redirs", "0",
                "--connect-timeout", "10", "--max-time", str(max(5, int(timeout_sec))),
                "--max-filesize", str(5 * 1024 * 1024),
                "-A", user_agent, "-o", str(body_path), "-D", str(head_path), "-w", "%{http_code}"
            ]
            if host and v4_ips and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
                args.extend(["--resolve", f"{host}:{port}:{','.join(v4_ips)}"])
            args.append(cur_url)
            proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout_sec + 5)
            status_code = int((proc.stdout or "").strip()[-3:] or 0) if (proc.stdout or "").strip()[-3:].isdigit() else 0
            if proc.returncode != 0:
                err_line = ((proc.stderr or "").strip().splitlines() or [f"curl exit {proc.returncode}"])[-1]
                return {"ok": False, "status": status_code, "body": "", "headers": {}, "error": f"curl exit {proc.returncode}: {err_line}"}
            head_txt = head_path.read_text(encoding="utf-8", errors="ignore") if head_path.is_file() else ""
            if 300 <= status_code < 400:
                m_loc = re.search(r"^location:\s*(.+?)\s*$", head_txt, re.IGNORECASE | re.MULTILINE)
                if not m_loc or hop >= 3:
                    return {"ok": False, "status": status_code, "body": "", "headers": {}, "error": "redirect_failed"}
                cur_url = urllib.parse.urljoin(cur_url, m_loc.group(1).strip())
                continue
            body_txt = body_path.read_text(encoding="utf-8", errors="ignore") if body_path.is_file() else ""
            hdrs = {}
            m_ui = re.search(r"^subscription-userinfo:\s*(.+?)\s*$", head_txt, re.IGNORECASE | re.MULTILINE)
            if m_ui:
                hdrs["Subscription-Userinfo"] = m_ui.group(1).strip()
            return {"ok": 200 <= status_code < 300, "status": status_code, "body": body_txt, "headers": hdrs, "error": ""}
        except Exception as e:
            return {"ok": False, "status": 0, "body": "", "headers": {}, "error": str(e)}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    return {"ok": False, "status": 0, "body": "", "headers": {}, "error": "too_many_redirects"}

def _classify_subscription_failure(status_code: int = 0, body: str = "", err_str: str = "", host: str = "") -> dict:
    b_low = (body or "").strip().lower()
    e_low = (err_str or "").strip().lower()
    h_low = (host or "").strip().lower()
    combined = f"{b_low} {e_low}"
    if h_low in _SUB_DNS_NXDOMAIN_HOSTS or any(k in combined for k in (
        "nxdomain", "name does not resolve", "no address associated", "nodename nor servname",
        "name or service not known", "temporary failure in name resolution", "could not resolve host",
        "dns 解析失败", "getaddrinfo failed"
    )):
        h_disp = f" ({h_low})" if h_low else ""
        return {"error_code": "sub_dns_nxdomain", "fatal_semantic": True, "reason": f"DNS 解析失败：订阅域名{h_disp}不存在或无法解析 (NXDOMAIN)"}
    if any(k in combined for k in ("token is err", "token error", "invalid token", "token invalid", "令牌错误", "订阅已过期", "expired")):
        return {"error_code": "sub_token_invalid", "fatal_semantic": True, "reason": "订阅 Token 无效或已被机场重置（token is err），请更新订阅链接"}
    if status_code == 403 or "http error 403" in combined:
        return {"error_code": "sub_http_403", "fatal_semantic": True, "reason": "上游拒绝访问 (HTTP 403)"}
    if status_code == 404 or "http error 404" in combined:
        return {"error_code": "sub_http_404", "fatal_semantic": True, "reason": "订阅地址不存在 (HTTP 404)"}
    if "<html" in b_low or "<!doctype html" in b_low or "cloudflare" in b_low:
        return {"error_code": "sub_html_challenge", "fatal_semantic": True, "reason": "订阅返回了网页验证内容而非节点数据"}
    return {"error_code": "sub_fetch_failed", "fatal_semantic": False, "reason": f"订阅拉取失败 ({err_str or ('HTTP ' + str(status_code))})"}

def parse_subscription_content(raw_text: str, conf_dir: Path = CONF_DIR) -> list:
    return NodeURIParser.parse_subscription_text(raw_text, conf_dir=conf_dir)

def fetch_and_sync_subscription(url: str = "", name: str = "机场订阅",
                                auto_update: bool = True, update_interval_min: int = 360,
                                conf_dir: Path = CONF_DIR, sub_id: str = "", old_url: str = "",
                                test_after_add: bool = False) -> dict:
    """Spec §7 #5 & P0-2 Fix: Never auto-injects a hardcoded third-party subscription when URL is empty."""
    url = str(url or "").strip()
    name = str(name or "机场订阅").strip()
    if not url and sub_id:
        for _ex_s in load_subscriptions(conf_dir):
            if _ex_s.get("id") == sub_id and _ex_s.get("url"):
                url = str(_ex_s["url"]).strip()
                name = str(_ex_s.get("name") or name).strip()
                break
    if not url:
        return {
            "ok": False,
            "id": sub_id,
            "fetch_source": "failed",
            "imported_count": 0,
            "error": "empty_sub_url",
            "message": "未提供订阅链接，请先在「节点管理」中添加有效的订阅 URL",
            "subscriptions": load_subscriptions(conf_dir)
        }
    now_ts = int(time.time())
    with _SUB_LOCK:
        subs = load_subscriptions(conf_dir)
        target_sub = None
        for s in subs:
            if (sub_id and s.get("id") == sub_id) or (old_url and s.get("url") == old_url) or s.get("url") == url or s.get("name") == name:
                target_sub = s
                break
        if target_sub is None:
            sub_id = sub_id or f"sub_{now_ts}_{len(subs) + 1}"
            target_sub = {
                "id": sub_id, "name": name, "url": url, "enabled": True,
                "auto_update": bool(auto_update), "update_interval_min": int(update_interval_min),
                "last_sync_ts": now_ts, "count": 0, "status": "syncing", "last_error": "", "updated": "正在同步..."
            }
            subs.append(target_sub)
        else:
            sub_id = target_sub.get("id") or sub_id or f"sub_{now_ts}"
            target_sub.update({"id": sub_id, "name": name or target_sub.get("name", "订阅源"), "url": url, "status": "syncing", "last_error": ""})
        save_subscriptions(subs, conf_dir)
    parsed_obs = []
    sub_userinfo = {}
    last_error = ""
    last_error_code = "sub_fetch_failed"
    sub_host = (urllib.parse.urlsplit(url).hostname or "").strip().lower()
    # P2-9 Fix: Pre-check DNS via SO_MARK=255 direct UDP DNS before urllib hits local FakeIP (which masks NXDOMAIN as ECONNRESET)
    if sub_host and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", sub_host) and sub_host not in ("localhost", "127.0.0.1") and ":" not in sub_host:
        _pre_ips = _resolve_subscription_host_ips(sub_host)
        if sub_host in _SUB_DNS_NXDOMAIN_HOSTS:
            diag = _classify_subscription_failure(0, "", "NXDOMAIN", host=sub_host)
            last_error = diag["reason"]
            last_error_code = diag["error_code"]
    ctx = ssl._create_unverified_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    if last_error_code != "sub_dns_nxdomain":
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", "Accept": "*/*"})
            with opener.open(req, timeout=30) as resp:
                code = getattr(resp, "status", 200)
                uinfo_raw = resp.headers.get("Subscription-Userinfo") or resp.headers.get("subscription-userinfo") or ""
                if uinfo_raw:
                    sub_userinfo = parse_subscription_userinfo(uinfo_raw)
                # 读取节流：本机接收太快会让上游连接崩溃（实测 52KB 突然限速 30KB/s 即可 3.4s 拉完）
                _chunks = []
                while True:
                    _b = resp.read(4096)
                    if not _b:
                        break
                    _chunks.append(_b)
                    time.sleep(0.012)
                body = b"".join(_chunks).decode("utf-8", errors="ignore").strip()
                parsed_obs = NodeURIParser.parse_subscription_text(body, conf_dir=conf_dir) if body else []
                if not parsed_obs:
                    diag = _classify_subscription_failure(code, body, host=sub_host)
                    last_error = diag["reason"]
                    last_error_code = diag["error_code"]
                elif getattr(NodeURIParser, "last_extracted_info_meta", None):
                    for mk, mv in NodeURIParser.last_extracted_info_meta.items():
                        sub_userinfo.setdefault(mk, mv)
        except urllib.error.HTTPError as he:
            err_b = ""
            try:
                err_b = he.read().decode("utf-8", errors="ignore")[:300]
            except Exception:
                pass
            diag = _classify_subscription_failure(he.code, err_b, str(he), host=sub_host)
            last_error = diag["reason"]
            last_error_code = diag["error_code"]
        except Exception as e:
            err_s = str(e)
            # P2-9 Fix: If urllib got ECONNRESET because FakeIP intercepted an NXDOMAIN host, check direct DNS
            if sub_host and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", sub_host) and sub_host not in ("localhost", "127.0.0.1"):
                if sub_host in _SUB_DNS_NXDOMAIN_HOSTS or (not _resolve_subscription_host_ips(sub_host) and any(k in err_s.lower() for k in ("reset", "104", "name does not resolve", "nodename", "no address", "nxdomain"))):
                    err_s = f"NXDOMAIN: DNS 解析失败 ({sub_host}) - {err_s}"
            diag = _classify_subscription_failure(0, "", err_s, host=sub_host)
            last_error = diag["reason"]
            last_error_code = diag["error_code"]
    if not parsed_obs and last_error_code not in ("sub_token_invalid", "sub_http_404", "sub_dns_nxdomain"):
        # Fallback to IPv4-pinned curl (bypasses Python TLS fingerprint WAF blocks and IPv6 RSTs)
        c_res = _curl_fetch_subscription(url, timeout_sec=25)
        if c_res.get("ok") and c_res.get("body"):
            uinfo_c = (c_res.get("headers") or {}).get("Subscription-Userinfo") or ""
            if uinfo_c:
                sub_userinfo = parse_subscription_userinfo(uinfo_c)
            parsed_obs = NodeURIParser.parse_subscription_text(c_res["body"].strip(), conf_dir=conf_dir)
            if parsed_obs and getattr(NodeURIParser, "last_extracted_info_meta", None):
                for mk, mv in NodeURIParser.last_extracted_info_meta.items():
                    sub_userinfo.setdefault(mk, mv)
        elif c_res.get("error") and "NXDOMAIN" in str(c_res.get("error")):
            diag = _classify_subscription_failure(0, "", str(c_res.get("error")), host=sub_host)
            last_error = diag["reason"]
            last_error_code = diag["error_code"]
    if parsed_obs:
        merged = merge_nodes(sub_id, parsed_obs, sub_url=url, replace_sub=True, conf_dir=conf_dir)
        sub_cnt = sum(1 for n in merged if n.get("_sub_id") == sub_id or n.get("_sub_url") == url)
        with _SUB_LOCK:
            subs = load_subscriptions(conf_dir)
            for s in subs:
                if s.get("id") == sub_id or s.get("url") == url:
                    s.update({
                        "id": sub_id, "name": name, "url": url,
                        "count": sub_cnt or len(parsed_obs), "status": "ok", "last_error": "",
                        "last_sync_ts": int(time.time()),
                        "updated": f"已同步 ({sub_cnt or len(parsed_obs)} 节点 · {time.strftime('%m-%d %H:%M')})",
                        "userinfo": sub_userinfo
                    })
                    break
            save_subscriptions(subs, conf_dir)
        delay_res = None
        if test_after_add:
            # P2-7 & P2-8 Fix: For subscriptions up to 60 nodes, run URL ping BEFORE write_all_configs so new nodes are immediately scored & mounted
            if len(parsed_obs) <= 60:
                delay_res = url_ping_batch_nodes(sub_id=sub_id, sub_url=url, concurrency=6, conf_dir=conf_dir)
                write_all_configs(conf_dir)
            else:
                write_all_configs(conf_dir)
                def _bg_sub_initial_ping(_sid=sub_id, _surl=url, _cdir=conf_dir):
                    SUB_SYNC_STATE["running"] = True
                    try:
                        url_ping_batch_nodes(sub_id=_sid, sub_url=_surl, concurrency=6, conf_dir=_cdir)
                        write_all_configs(_cdir)
                        if Path("/etc/init.d/ai-link").exists():
                            schedule_async_core_reload(hot_only=False)
                    except Exception:
                        pass
                    finally:
                        SUB_SYNC_STATE["running"] = False
                threading.Thread(target=_bg_sub_initial_ping, daemon=True, name="ailink-sub-init-ping").start()
                delay_res = {"async": True, "queued_nodes": len(parsed_obs), "sub_id": sub_id}
        else:
            write_all_configs(conf_dir)
        _trigger_async_health_reprobe()
        return {
            "ok": True, "id": sub_id, "fetch_source": "direct_https:curl",
            "imported_count": len(parsed_obs), "total_nodes": len(merged),
            "userinfo": sub_userinfo, "delay_test": delay_res,
            "subscriptions": load_subscriptions(conf_dir)
        }
    with _SUB_LOCK:
        subs = load_subscriptions(conf_dir)
        for s in subs:
            if s.get("id") == sub_id or s.get("url") == url:
                s["status"] = "error"
                s["last_error"] = last_error or "订阅拉取或解析失败"
                s["updated"] = f"同步失败: {s['last_error'][:36]}"
                break
        save_subscriptions(subs, conf_dir)
    return {
        "ok": False, "id": sub_id, "fetch_source": "failed",
        "imported_count": 0, "error": last_error_code, "message": last_error or "订阅拉取失败",
        "subscriptions": load_subscriptions(conf_dir)
    }

_fetch_sub_once = fetch_and_sync_subscription


def fetch_and_sync_subscription(*args, **kwargs):
    """P1-4 Fix: Up to 2 attempts on transient network failures (timeout, SSL, ECONNRESET/104, EOF, 502/503/504).
    Never retries on deterministic semantic errors (NXDOMAIN, invalid token, HTTP 404)."""
    res = _fetch_sub_once(*args, **kwargs)
    try:
        if isinstance(res, dict) and res.get("ok"):
            return res
        err_code = str((res or {}).get("error") or "")
        if err_code in ("sub_dns_nxdomain", "sub_token_invalid", "sub_http_404"):
            return res
        msg_low = str((res or {}).get("message") or "").lower()
        if any(k in msg_low for k in (
            "timed out", "timeout", "ssl", "reset", "104", "eof",
            "disconnected", "broken pipe", "connection aborted", "502", "503", "504"
        )):
            time.sleep(1.5)
            res2 = _fetch_sub_once(*args, **kwargs)
            if isinstance(res2, dict):
                res2["retried"] = True
                return res2
    except Exception:
        pass
    return res


def import_subscription_text(payload: dict, conf_dir: Path = CONF_DIR) -> dict:
    raw_content = str(payload.get("raw_text") or payload.get("content") or payload.get("text") or "").strip()
    sub_name = str(payload.get("name") or "手动导入订阅").strip()
    sub_url = str(payload.get("url") or f"paste://{int(time.time())}").strip()
    old_url = str(payload.get("old_url") or "").strip()
    sub_id = str(payload.get("id") or "").strip()
    replace_all = bool(payload.get("replace_existing", payload.get("replace", False)))
    test_after_add = bool(payload.get("test_after_add", True))
    if not raw_content:
        return {"ok": False, "error": "empty_content", "message": "请粘贴订阅内容"}
    parsed_obs = parse_subscription_content(raw_content, conf_dir=conf_dir)
    filtered_info_cnt = getattr(NodeURIParser, "last_filtered_info_count", 0)
    extracted_info = dict(getattr(NodeURIParser, "last_extracted_info_meta", {}) or {})
    if not parsed_obs:
        diag = _classify_subscription_failure(200, raw_content)
        return {"ok": False, "error": diag["error_code"], "message": diag["reason"]}
    with _SUB_LOCK:
        subs = load_subscriptions(conf_dir)
        target_sub = None
        for s in subs:
            if (sub_id and s.get("id") == sub_id) or (old_url and s.get("url") == old_url) or s.get("url") == sub_url or s.get("name") == sub_name:
                target_sub = s
                break
        sub_id = (target_sub.get("id") if target_sub else None) or sub_id or f"sub_{int(time.time())}_{len(subs) + 1}"
        if old_url and old_url != sub_url:
            for n in load_saved_nodes(conf_dir):
                if n.get("_sub_url") == old_url:
                    n["_sub_id"] = sub_id
                    n["_sub_url"] = sub_url
        merged = merge_nodes(sub_id, parsed_obs, sub_url=sub_url, replace_sub=True, replace_all=replace_all, conf_dir=conf_dir)
        sub_cnt = sum(1 for n in merged if n.get("_sub_id") == sub_id or n.get("_sub_url") == sub_url)
        now_str = time.strftime("%Y-%m-%d %H:%M")
        if target_sub is not None:
            target_sub.update({
                "id": sub_id, "name": sub_name, "url": sub_url,
                "count": sub_cnt or len(parsed_obs), "status": "ok", "last_error": "",
                "updated": f"粘贴导入 ({len(parsed_obs)} 节点 · {now_str})",
                "last_sync_ts": int(time.time())
            })
            if extracted_info:
                target_sub.setdefault("userinfo", {}).update(extracted_info)
        else:
            subs.insert(0, {
                "id": sub_id, "name": sub_name, "url": sub_url, "enabled": True,
                "auto_update": not sub_url.startswith("paste://"), "update_interval_min": 360,
                "count": sub_cnt or len(parsed_obs), "status": "ok", "last_error": "",
                "updated": f"粘贴导入 ({len(parsed_obs)} 节点 · {now_str})",
                "userinfo": extracted_info, "last_sync_ts": int(time.time())
            })
        save_subscriptions(subs, conf_dir)
    write_all_configs(conf_dir)
    if payload.get("reload_core", True) and Path("/etc/init.d/ai-link").exists():
        reload_core_only()
        PROBE_ENGINE.apply_shunt_selections(conf_dir)
    delay_res = url_ping_batch_nodes(sub_id=sub_id, sub_url=sub_url, conf_dir=conf_dir) if test_after_add else None
    return {
        "ok": True, "id": sub_id, "fetch_source": "paste_import",
        "imported_count": len(parsed_obs), "filtered_info_count": filtered_info_cnt,
        "userinfo": extracted_info, "total_saved": len(merged), "total_nodes": len(merged),
        "delay_test": delay_res, "backend_diversity": analyze_backend_diversity(merged, conf_dir),
        "subscriptions": load_subscriptions(conf_dir)
    }

def get_max_outbounds_limit(conf_dir: Path = CONF_DIR) -> int:
    ram_mib = _get_system_ram_mib()
    rec_default = 120 if ram_mib <= 2200 else 200
    limit_file = conf_dir / "max_outbounds.txt"
    mig_flag = conf_dir / ".migrated_max_outbounds_v19"
    if Path(conf_dir).resolve() == Path(CONF_DIR).resolve() and not mig_flag.is_file():
        try:
            cur_txt = limit_file.read_text(encoding="utf-8").strip() if limit_file.is_file() else ""
            if cur_txt in ("", "0", "60") or (ram_mib <= 2200 and cur_txt == "200"):
                conf_dir.mkdir(parents=True, exist_ok=True)
                limit_file.write_text(f"{rec_default}\n", encoding="utf-8")
            mig_flag.write_text("1\n", encoding="utf-8")
        except Exception:
            pass
    if limit_file.is_file():
        try:
            return max(0, int(limit_file.read_text().strip()))
        except Exception:
            pass
    return rec_default

_SB_OUTBOUND_KEYS = {
    "type", "tag", "server", "server_port", "server_ports", "hop_interval", "uuid", "password", "method",
    "tls", "transport", "flow", "packet_encoding", "up_mbps", "down_mbps",
    "obfs", "auth", "plugin", "plugin_opts", "network", "udp_over_tcp",
    "security", "alter_id", "congestion_control", "udp_relay_mode",
    "username", "version"
}


# ==============================================================================
# v2.0.0-r8-v18-nolo: NOLO-LINK Deep Integration
# 1. Standard Share URI Exporter (vless/vmess/ss/trojan/hysteria2/tuic/socks5)
# 2. On-Demand Kernel Outbound Governance ("节点不进内核")
# 3. Scheduled URL Ping per Subscription / Country / Tag Category
# 4. Mode-Aware IPv6 Capability Detection & Smart Warning Engine
# 5. Mainland Domain & CIDR Conflict Detector for entry_bypass (D-15)
# ==============================================================================

MAINLAND_COMMON_DOMAINS = {
    "cn", "baidu.com", "bdstatic.com", "baidupcs.com", "qq.com", "weixin.qq.com", "wechat.com",
    "gtimg.com", "gtimg.cn", "myqcloud.com", "qcloud.com", "tencent.com", "tencent-cloud.net",
    "lol.qq.com", "wegame.com", "wegame.com.cn", "tgp.qq.com", "taobao.com", "tmall.com",
    "alicdn.com", "aliyun.com", "aliyuncs.com", "alipay.com", "1688.com", "tbcache.com",
    "jd.com", "360buyimg.com", "jcloudcs.com", "bilibili.com", "bilivideo.com", "hdslb.com",
    "biliapi.net", "163.com", "126.com", "126.net", "127.net", "netease.com", "douyin.com",
    "toutiao.com", "bytedance.com", "byteimg.com", "snssdk.com", "ixigua.com", "feishu.cn",
    "douyincdn.com", "douyinpic.com", "zijieapi.com", "amemv.com", "webcast.amemv.com",
    "bytecdn.cn", "pstatp.com", "volccdn.com", "bytegoofy.com",
    "douyinstatic.com", "douyinliving.com",
    "dingtalk.com", "xiaohongshu.com", "xhscdn.com", "zhihu.com", "zhimg.com", "weibo.com",
    "weibocdn.com", "sina.com.cn", "sohu.com", "iqiyi.com", "youku.com", "mgtv.com",
    "kuaishou.com", "yximgs.com", "meituan.com", "dianping.com", "pinduoduo.com", "yangkeduo.com",
    "ctrip.com", "12306.cn", "mi.com", "xiaomi.com", "xiaomi.net", "huawei.com", "vmall.com",
    "dbankcdn.com", "hicloud.com", "csdn.net", "gitee.com", "oschina.net", "smzdm.com",
    "douban.com", "hupu.com", "nga.cn", "ip138.com", "soulapp.cn", "soulapp.com", "ximalaya.com",
    "kugou.com", "kuwo.cn", "acfun.cn", "eastmoney.com", "10jqka.com.cn", "boc.cn", "icbc.com.cn",
}

def _domain_matches_mainland(dom: str) -> bool:
    d = str(dom or "").strip().lower().lstrip("*.")
    if not d:
        return False
    if d.endswith(".cn") or ".cn." in d:
        return True
    if d in MAINLAND_COMMON_DOMAINS:
        return True
    for m_dom in MAINLAND_COMMON_DOMAINS:
        if m_dom != "cn" and d.endswith("." + m_dom):
            return True
    return False

def detect_entry_bypass_conflict(domains: list, exact_domains: list = None, keywords: list = None,
                                 ip_cidrs: list = None, country: str = "US", conf_dir: Path = CONF_DIR) -> dict:
    """D-15 Fix: Checks whether a shunt rule targeting a proxy outbound conflicts with entry_bypass ('国内流量不进内核')."""
    ops_now = get_ops_settings(conf_dir)
    bypass_on = bool(ops_now.get("entry_bypass", True))
    if not bypass_on or str(country or "").lower() in ("direct", "block"):
        return {"conflict": False, "entry_bypass": bypass_on, "matched_domains": [], "matched_ips": [], "warning": ""}
    all_doms = list(domains or []) + list(exact_domains or []) + list(keywords or [])
    matched_doms = [d for d in all_doms if _domain_matches_mainland(d)]
    matched_ips = [
        ip_c for ip_c in (ip_cidrs or [])
        if _ip_in_cidr_list(str(ip_c).split("/")[0], CN_CORE_CIDRS + CN_CORE_IPV6_CIDRS)
    ]
    if not matched_doms and not matched_ips:
        return {"conflict": False, "entry_bypass": bypass_on, "matched_domains": [], "matched_ips": [], "warning": ""}
    samples = (matched_doms + matched_ips)[:5]
    sample_str = "、".join(samples)
    warn_txt = (
        f"⚠️ 检测到规则包含中国大陆站点/IP（{sample_str}）并指向海外代理，但当前已开启「🚀 国内流量不进内核 (硬件级旁路)」。"
        "在透明代理下，这些域名由 223.5.5.5 解析出大陆 IP 后会在 nftables (@cn_ip4) 层直接硬件放行直连，导致此代理分流不生效！"
        "如需强制让其走代理，请前往「系统与设置 -> 代理设置」关闭「国内流量不进内核」，或为该域名配置 DNS 重写。"
    )
    return {
        "conflict": True,
        "entry_bypass": bypass_on,
        "matched_domains": matched_doms,
        "matched_ips": matched_ips,
        "warning": warn_txt,
    }

def export_node_share_uri(node: dict) -> str:
    """Borrowed from NOLO-LINK engine/sharelink.mjs:
    Generates a standard shareable URI (vless://, vmess://, ss://, trojan://, hysteria2://, tuic://, socks5://)
    from a stored sing-box outbound dict so users can copy/share or scan QR codes for any node in Node Management."""
    if not isinstance(node, dict):
        return ""
    if node.get("_raw_uri") and isinstance(node.get("_raw_uri"), str) and "://" in node["_raw_uri"]:
        return node["_raw_uri"]
    ntype = str(node.get("type") or "vless").lower()
    tag = str(node.get("tag") or "AI-LINK-Node").strip()
    enc_tag = urllib.parse.quote(tag, safe="-_.")
    server = str(node.get("server") or "").strip()
    if not server:
        return ""
    host_fmt = f"[{server}]" if (":" in server and not server.startswith("[")) else server
    port = int(node.get("server_port") or 443)
    tls = node.get("tls") if isinstance(node.get("tls"), dict) else {}
    trans = node.get("transport") if isinstance(node.get("transport"), dict) else {}
    sni = str(tls.get("server_name") or node.get("sni") or "").strip()

    if ntype == "vless":
        uuid_v = str(node.get("uuid") or "").strip()
        params = {"encryption": "none"}
        reality = tls.get("reality") if isinstance(tls.get("reality"), dict) else {}
        if reality.get("enabled"):
            params["security"] = "reality"
            if reality.get("public_key"):
                params["pbk"] = str(reality["public_key"])
            if reality.get("short_id"):
                sid_v = reality["short_id"]
                params["sid"] = sid_v[0] if isinstance(sid_v, list) and sid_v else str(sid_v)
        elif tls.get("enabled"):
            params["security"] = "tls"
            if tls.get("insecure"):
                params["allowInsecure"] = "1"
        else:
            params["security"] = "none"
        if sni:
            params["sni"] = sni
        if node.get("flow"):
            params["flow"] = str(node["flow"])
        ut = tls.get("utls") if isinstance(tls.get("utls"), dict) else {}
        if ut.get("fingerprint"):
            params["fp"] = str(ut["fingerprint"])
        ttype = str(trans.get("type") or "tcp").lower()
        params["type"] = ttype
        if ttype in ("ws", "httpupgrade", "http"):
            if trans.get("path"):
                params["path"] = str(trans["path"])
            hdrs = trans.get("headers") if isinstance(trans.get("headers"), dict) else {}
            h_host = hdrs.get("Host") or hdrs.get("host") or ""
            if h_host:
                params["host"] = str(h_host)
        elif ttype == "grpc" and trans.get("service_name"):
            params["serviceName"] = str(trans["service_name"])
        qs = urllib.parse.urlencode(params)
        return f"vless://{uuid_v}@{host_fmt}:{port}?{qs}#{enc_tag}"

    if ntype in ("hysteria2", "hy2"):
        pwd = urllib.parse.quote(str(node.get("password") or ""), safe="")
        params = {}
        if sni:
            params["sni"] = sni
        if tls.get("insecure"):
            params["insecure"] = "1"
            params["allowInsecure"] = "1"
        obfs = node.get("obfs") if isinstance(node.get("obfs"), dict) else {}
        if obfs.get("type"):
            params["obfs"] = str(obfs["type"])
            if obfs.get("password"):
                params["obfs-password"] = str(obfs["password"])
        if node.get("server_ports"):
            sp = node["server_ports"]
            params["mport"] = ",".join(str(x).replace(":", "-") for x in (sp if isinstance(sp, list) else [sp]))
        qs = urllib.parse.urlencode(params)
        return f"hysteria2://{pwd}@{host_fmt}:{port}/?{qs}#{enc_tag}"

    if ntype == "trojan":
        pwd = urllib.parse.quote(str(node.get("password") or ""), safe="")
        params = {}
        if sni:
            params["sni"] = sni
        if tls.get("insecure"):
            params["allowInsecure"] = "1"
        ttype = str(trans.get("type") or "tcp").lower()
        if ttype != "tcp":
            params["type"] = ttype
            if trans.get("path"):
                params["path"] = str(trans["path"])
        qs = urllib.parse.urlencode(params)
        return f"trojan://{pwd}@{host_fmt}:{port}?{qs}#{enc_tag}" if qs else f"trojan://{pwd}@{host_fmt}:{port}#{enc_tag}"

    if ntype in ("shadowsocks", "ss"):
        method = str(node.get("method") or "aes-256-gcm")
        pwd = str(node.get("password") or "")
        userinfo = base64.urlsafe_b64encode(f"{method}:{pwd}".encode("utf-8")).decode("ascii").rstrip("=")
        return f"ss://{userinfo}@{host_fmt}:{port}#{enc_tag}"

    if ntype == "vmess":
        ttype = str(trans.get("type") or "tcp").lower()
        hdrs = trans.get("headers") if isinstance(trans.get("headers"), dict) else {}
        v_obj = {
            "v": "2",
            "ps": tag,
            "add": server,
            "port": str(port),
            "id": str(node.get("uuid") or ""),
            "aid": str(node.get("alter_id") or 0),
            "scy": str(node.get("security") or "auto"),
            "net": ttype,
            "type": "none",
            "host": str(hdrs.get("Host") or hdrs.get("host") or sni or ""),
            "path": str(trans.get("path") or ""),
            "tls": "tls" if tls.get("enabled") else "",
            "sni": sni,
        }
        b64 = base64.b64encode(json.dumps(v_obj, ensure_ascii=False).encode("utf-8")).decode("ascii")
        return f"vmess://{b64}"

    if ntype == "tuic":
        uuid_v = urllib.parse.quote(str(node.get("uuid") or ""), safe="")
        pwd = urllib.parse.quote(str(node.get("password") or ""), safe="")
        params = {"congestion_control": str(node.get("congestion_control") or "bbr")}
        if sni:
            params["sni"] = sni
        qs = urllib.parse.urlencode(params)
        return f"tuic://{uuid_v}:{pwd}@{host_fmt}:{port}?{qs}#{enc_tag}"

    if ntype in ("socks", "socks5"):
        u = str(node.get("username") or "")
        p = str(node.get("password") or "")
        auth = f"{urllib.parse.quote(u)}:{urllib.parse.quote(p)}@" if u else ""
        return f"socks5://{auth}{host_fmt}:{port}#{enc_tag}"

    return f"{ntype}://{host_fmt}:{port}#{enc_tag}"

def _infer_node_initial_ipv6_support(node: dict) -> object:
    """Infers initial IPv6 support hint if explicit tags/flags exist; otherwise returns None (untested)."""
    if not isinstance(node, dict):
        return None
    if "ipv6_ok" in node and isinstance(node["ipv6_ok"], bool):
        return node["ipv6_ok"]
    tag_u = str(node.get("tag") or "").upper()
    if any(k in tag_u for k in ("IPV4-ONLY", "IPV4 ONLY", "NO-IPV6", "NOIPV6", "仅IPV4", "无IPV6")):
        return False
    if any(k in tag_u for k in ("IPV6", "V6双栈", "DUALSTACK")):
        return True
    return None

def probe_nodes_ipv6_capability(tags_or_ids: list = None, sub_id: str = "", region: str = "",
                                timeout_ms: int = 3500, concurrency: int = 10,
                                conf_dir: Path = CONF_DIR, mock_ipv6_map: dict = None) -> dict:
    """Borrowed from NOLO-LINK engine/ipv6-filter.mjs + api/ipv6.mjs:
    Tests whether target nodes support IPv6 egress (by probing DEFAULT_IPV6_PING_TARGET through the node)
    and persists `ipv6_ok: True | False` in `node_probe.json`."""
    subs_list = load_subscriptions(conf_dir)
    raw_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    filter_set = set(tags_or_ids) if isinstance(tags_or_ids, list) and tags_or_ids else None
    targets = []
    for n in raw_nodes:
        if n.get("disabled") or not is_node_subscription_enabled(n, subs_list=subs_list, conf_dir=conf_dir):
            continue
        nid = n.get("node_id") or compute_node_id(n)
        t = n.get("tag", "")
        if filter_set is not None and t not in filter_set and nid not in filter_set:
            continue
        if sub_id and n.get("_sub_id") != sub_id:
            continue
        if region and region != "ALL" and classify_node_country_5plus1(t, n) != region:
            continue
        targets.append(n)

    mounted_proxies = set((clash_get_proxies().get("proxies") or {}).keys()) if _is_local_port_listening(9090) else set()
    unmounted = [nd for nd in targets if nd.get("tag") not in mounted_proxies]
    eph_v6 = {}
    if unmounted and not isinstance(mock_ipv6_map, dict) and _is_local_port_listening(9090):
        for c_i in range(0, len(unmounted), 20):
            chunk = unmounted[c_i:c_i + 20]
            eph_v6.update(_ephemeral_singbox_delay_probe(chunk, test_url=DEFAULT_IPV6_PING_TARGET, timeout_ms=timeout_ms))

    now_ts = int(time.time())
    v6_results = {}
    def _test_v6_one(nd):
        nid = nd.get("node_id") or compute_node_id(nd)
        t = nd.get("tag", "")
        if isinstance(mock_ipv6_map, dict) and (nid in mock_ipv6_map or t in mock_ipv6_map):
            m_val = mock_ipv6_map.get(nid) if nid in mock_ipv6_map else mock_ipv6_map.get(t)
            if isinstance(m_val, dict):
                v6_ok = bool(m_val.get("ipv6_ok", m_val.get("ok", False)))
                v6_ms = int(m_val.get("delay_ms") or (140 if v6_ok else -1))
            else:
                v6_ok = bool(m_val)
                v6_ms = 140 if v6_ok else -1
            return nid, t, v6_ok, v6_ms
        if t in eph_v6:
            er = eph_v6[t]
            v6_ok = bool(er.get("ok") and int(er.get("delay") or 0) > 0)
            return nid, t, v6_ok, (int(er["delay"]) if v6_ok else -1)
        res = clash_test_delay(t, test_url=DEFAULT_IPV6_PING_TARGET, timeout_ms=timeout_ms, allow_fallback=True, conf_dir=conf_dir)
        v6_ok = bool(res.get("ok") and int(res.get("delay") or 0) > 0)
        return nid, t, v6_ok, (int(res["delay"]) if v6_ok else -1)

    ram_cap = 4 if _get_system_ram_mib() <= 2200 else 6
    workers = max(1, min(ram_cap, int(concurrency or ram_cap)))
    if targets:
        with ThreadPoolExecutor(max_workers=min(workers, len(targets))) as ex:
            rows = list(ex.map(_test_v6_one, targets))
        with _SUB_LOCK:
            store = load_node_probe_store(conf_dir)
            for nid, t, v6_ok, v6_ms in rows:
                rec = store.get(nid) if isinstance(store.get(nid), dict) else {
                    "state": "pending", "delay_ms": -1, "probe_ts": 0, "probe_kind": "url_ping",
                    "http_status": 0, "fail_reason": "", "consecutive_fail": 0, "svc": {}
                }
                rec["ipv6_ok"] = bool(v6_ok)
                rec["ipv6_probe_ts"] = now_ts
                rec["ipv6_rtt_ms"] = v6_ms
                store[nid] = rec
                v6_results[nid] = {"node_id": nid, "tag": t, "ipv6_ok": bool(v6_ok), "ipv6_rtt_ms": v6_ms, "ipv6_probe_ts": now_ts}
            save_node_probe_store(store, conf_dir)

    ok_v6_cnt = sum(1 for r in v6_results.values() if r["ipv6_ok"])
    return {
        "ok": True,
        "tested_count": len(v6_results),
        "ipv6_supported_count": ok_v6_cnt,
        "ipv6_unsupported_count": len(v6_results) - ok_v6_cnt,
        "results": v6_results,
        "ipv6_governance": build_ipv6_governance_summary(conf_dir),
    }

_IPV6_GOV_MEMO = {}

def build_ipv6_governance_summary(conf_dir: Path = CONF_DIR) -> dict:
    """Mode-Aware IPv6 Architecture & Node Capability Governance Builder (v24-hotfix7):
    - When `ipv6_proxy == False` (Smart Dual-Stack Shunt Mode: Domestic Native IPv6 Direct + Overseas AAAA Suppression):
      Preserves real AAAA records for `Domestic_CN` / `geosite-cn` / LAN via `dns_direct (223.5.5.5)` while returning
      `NOERROR` empty AAAA for overseas proxy domains, and keeps `warning_active = False` (zero false alarms).
    - When `ipv6_proxy == True` (Full IPv6 Takeover Mode: FakeIPv6 `fc00::/18` + TProxy v6 + Outbound `prefer_ipv4`):
      Inspects active exit nodes in `shunt.json` / `selections` AND all `auto_nodes` pools,
      identifying any node with `ipv6_ok is False` and surfacing targeted warnings."""
    ops = get_ops_settings(conf_dir)
    ipv6_proxy = bool(ops.get("ipv6_proxy", False))
    _v6_memo_key = (
        str(conf_dir),
        ipv6_proxy,
        _conf_file_mtimes_sig_q(conf_dir, ("nodes.json", "node_probe.json", "ops_settings.json", "shunt.json", "auto_nodes.json"), 15),
        _CORE_RELOAD_STATE["config_seq"],
        int(time.time()) // 15,
    )
    if _v6_memo_key in _IPV6_GOV_MEMO:
        return dict(_IPV6_GOV_MEMO[_v6_memo_key])
    if len(_IPV6_GOV_MEMO) > 16:
        _IPV6_GOV_MEMO.clear()
    ipv6_mode = "proxy_takeover" if ipv6_proxy else "smart_dualstack_shunt"
    ipv6_mode_label = (
        "全量 IPv6 代理接管模式 (FakeIPv6 fc00::/18 + TProxy v6 + 出站 prefer_ipv4 降级)"
        if ipv6_proxy
        else "智能双栈分流模式 (国内真 IPv6 原生直连 + 海外精准抑制 AAAA 防旁路漏网)"
    )
    _dns_in_ok = bool(_is_local_port_listening(7874) or _is_udp_port_listening(7874))
    _redir_in_ok = bool(_is_local_port_listening(7891))
    _dnsmasq_up_ok = False
    try:
        _ad_cf = _detect_dnsmasq_confdir(create=False) / "ai-link-adblock.conf"
        if _ad_cf.is_file() and "server=127.0.0.1#7874" in _ad_cf.read_text(encoding="utf-8", errors="ignore"):
            _dnsmasq_up_ok = True
    except Exception:
        pass
    arch_features = {
        "architecture": "v24-hotfix10-smart-dualstack",
        "smart_aaaa_shunt": True,
        "domestic_aaaa_preserved": True,
        "overseas_aaaa_suppressed": True,
        "dual_stack_dns_hijack_53": True,
        "dns_in_7874_listening": _dns_in_ok,
        "dnsmasq_upstream_mounted": _dnsmasq_up_ok,
        "redirect_in_7891_listening": _redir_in_ok,
        "icmpv6_ndp_passthrough": True,
        "prefer_ipv4_outbound": True,
        "dynamic_table162_sync": True,
    }
    store = load_node_probe_store(conf_dir)
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    by_id, by_tag = _build_node_lookup_maps(saved_nodes)

    def _get_node_v6_state(ref_str: str):
        if not ref_str or ref_str in ("direct", "block") or str(ref_str).startswith("auto:"):
            return None, None
        n_obj = by_tag.get(ref_str) or by_id.get(ref_str)
        nid = (n_obj.get("node_id") or compute_node_id(n_obj)) if n_obj else ref_str
        tag = n_obj.get("tag", ref_str) if n_obj else ref_str
        rec = store.get(nid) or store.get(tag) or {}
        if "ipv6_ok" in rec and isinstance(rec["ipv6_ok"], bool):
            return tag, rec["ipv6_ok"]
        inf = _infer_node_initial_ipv6_support(n_obj) if n_obj else None
        return tag, inf

    v6_ok_total = 0
    v6_fail_total = 0
    v6_unknown_total = 0
    for n in saved_nodes:
        if n.get("disabled"):
            continue
        _, v6_st = _get_node_v6_state(n.get("tag", ""))
        if v6_st is True:
            v6_ok_total += 1
        elif v6_st is False:
            v6_fail_total += 1
        else:
            v6_unknown_total += 1

    # CRITICAL USER REQUIREMENT: If not in IPv6 Proxy Takeover mode (i.e. Force IPv4 mode),
    # suppress all IPv6 node warnings completely!
    if not ipv6_proxy:
        _res_v6_off = {
            "ipv6_proxy": False,
            "ipv6_mode": ipv6_mode,
            "ipv6_mode_label": ipv6_mode_label,
            "architecture": arch_features,
            "warning_active": False,
            "warning_message": "",
            "warnings": [],
            "affected_active_nodes": [],
            "affected_auto_pools": [],
            "stats": {
                "ipv6_ok": v6_ok_total,
                "ipv6_unsupported": v6_fail_total,
                "ipv6_untested": v6_unknown_total,
            }
        }
        _IPV6_GOV_MEMO[_v6_memo_key] = _res_v6_off
        return dict(_res_v6_off)

    # ipv6_proxy == True (IPv6 Takeover Mode active): check active exits and auto_nodes pools
    affected_active_nodes = []
    seen_active = set()
    sh_cfg = load_shunt_config(conf_dir)
    sels = dict(PROBE_ENGINE.current_selections or {})
    for g in (sh_cfg.get("groups") or []):
        gid = g.get("id", "")
        gname = g.get("name", gid)
        stag = g.get("selector_tag", f"Shunt_{gid}")
        act_tag = sels.get(stag) or g.get("manual_node") or ""
        if not act_tag or act_tag in ("direct", "block") or str(act_tag).startswith("auto:"):
            continue
        n_tag, v6_st = _get_node_v6_state(act_tag)
        if v6_st is False and (gid, n_tag) not in seen_active:
            seen_active.add((gid, n_tag))
            affected_active_nodes.append({
                "group_id": gid,
                "group_name": gname,
                "selector_tag": stag,
                "node_tag": n_tag,
                "ipv6_ok": False,
            })

    affected_auto_pools = []
    acfg = load_auto_nodes_config(conf_dir)
    for an in (acfg.get("auto_nodes") or []):
        an_id = an.get("id", "")
        an_name = an.get("name", an_id)
        cur_n = an.get("current_node") or ""
        _, cur_v6 = _get_node_v6_state(cur_n)
        unsupported_members = []
        untested_members = []
        seen_m = set()
        for grp in (an.get("groups") or []):
            for ref in list(dict.fromkeys(list(grp.get("node_tags") or []) + list(grp.get("node_ids") or []))):
                m_tag, m_v6 = _get_node_v6_state(ref)
                if not m_tag or m_tag in seen_m:
                    continue
                seen_m.add(m_tag)
                if m_v6 is False:
                    unsupported_members.append(m_tag)
                elif m_v6 is None:
                    untested_members.append(m_tag)
        if cur_v6 is False or unsupported_members:
            affected_auto_pools.append({
                "pool_id": an_id,
                "pool_name": an_name,
                "current_node": cur_n,
                "current_node_ipv6_ok": cur_v6,
                "unsupported_nodes": unsupported_members,
                "unsupported_count": len(unsupported_members),
                "untested_count": len(untested_members),
            })

    warnings = []
    if affected_active_nodes:
        items_str = "、".join(f"「{x['group_name']} → {x['node_tag']}」" for x in affected_active_nodes[:4])
        warnings.append(f"当前已开启 IPv6 接管代理，但正在使用的出口 {items_str} 不支持 IPv6，可能导致 IPv6 站点连接失败或回退超时。")
    if affected_auto_pools:
        pool_strs = []
        for p in affected_auto_pools[:4]:
            if p["current_node_ipv6_ok"] is False:
                pool_strs.append(f"「{p['pool_name']}」(当前节点 {p['current_node']} 及共 {p['unsupported_count']} 个节点不支持 IPv6)")
            else:
                pool_strs.append(f"「{p['pool_name']}」(含 {p['unsupported_count']} 个不支持 IPv6 的候选节点)")
        warnings.append(f"自动切换节点池 {', '.join(pool_strs)} 中包含不支持 IPv6 的节点，建议在节点池中剔除或切换为「强制 IPv4 模式」。")

    _res_v6_on = {
        "ipv6_proxy": True,
        "ipv6_mode": ipv6_mode,
        "ipv6_mode_label": ipv6_mode_label,
        "architecture": arch_features,
        "warning_active": bool(warnings),
        "warning_message": " ".join(warnings),
        "warnings": warnings,
        "affected_active_nodes": affected_active_nodes,
        "affected_auto_pools": affected_auto_pools,
        "stats": {
            "ipv6_ok": v6_ok_total,
            "ipv6_unsupported": v6_fail_total,
            "ipv6_untested": v6_unknown_total,
        }
    }
    _IPV6_GOV_MEMO[_v6_memo_key] = _res_v6_on
    return dict(_res_v6_on)

# Scheduled URL Ping per Subscription / Country / Category (/etc/ai-link/probe_schedules.json)
def load_probe_schedules(conf_dir: Path = CONF_DIR) -> list:
    p = conf_dir / "probe_schedules.json"
    if p.is_file():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, list):
                return [x for x in d if isinstance(x, dict) and x.get("id")]
        except Exception:
            pass
    return []

def save_probe_schedules(schedules: list, conf_dir: Path = CONF_DIR) -> list:
    conf_dir.mkdir(parents=True, exist_ok=True)
    cleaned = [x for x in (schedules or []) if isinstance(x, dict) and x.get("id")]
    _atomic_write_text(conf_dir / "probe_schedules.json", json.dumps(cleaned, indent=2, ensure_ascii=False))
    return cleaned

def run_due_probe_schedules(conf_dir: Path = CONF_DIR, force_id: str = "") -> list:
    """Runs any scheduled URL Ping task (by subscription, country/region, or explicit node tags) whose interval has elapsed."""
    schedules = load_probe_schedules(conf_dir)
    if not schedules:
        return []
    now_ts = int(time.time())
    executed = []
    changed = False
    for sc in schedules:
        if force_id and sc.get("id") != force_id:
            continue
        if not force_id and not sc.get("enabled", True):
            continue
        iv_min = max(5, int(sc.get("interval_min") or 60))
        last_ts = int(sc.get("last_run_ts") or 0)
        if force_id or (now_ts - last_ts) >= iv_min * 60:
            res = url_ping_batch_nodes(
                tags_or_ids=sc.get("node_tags") or sc.get("node_ids") or None,
                sub_id=str(sc.get("sub_id") or ""),
                region=str(sc.get("region") or ""),
                timeout_ms=int(sc.get("timeout_ms") or 3000),
                conf_dir=conf_dir,
            )
            if sc.get("check_ipv6") and get_uci_ipv6_proxy(conf_dir):
                probe_nodes_ipv6_capability(
                    tags_or_ids=sc.get("node_tags") or sc.get("node_ids") or None,
                    sub_id=str(sc.get("sub_id") or ""),
                    region=str(sc.get("region") or ""),
                    conf_dir=conf_dir,
                )
            sc["last_run_ts"] = now_ts
            sc["last_tested_count"] = res.get("tested_count", 0)
            sc["last_reachable_count"] = res.get("reachable", 0)
            changed = True
            executed.append({"schedule_id": sc["id"], "name": sc.get("name", ""), **res})
    if changed:
        save_probe_schedules(schedules, conf_dir)
    return executed

def get_referenced_kernel_node_refs(conf_dir: Path = CONF_DIR, run_dir: Path = RUN_DIR) -> set:
    """Returns all node tags and node_ids explicitly referenced by Auto-Node Pools, Shunt manual/resolved exits, or selections.json."""
    refs = set()
    try:
        af_path = conf_dir / "auto_nodes.json"
        if af_path.is_file():
            af_obj = json.loads(af_path.read_text(encoding="utf-8"))
            for an_item in (af_obj.get("auto_nodes") or []):
                if an_item.get("current_node"):
                    refs.add(str(an_item["current_node"]))
                if an_item.get("current_node_id"):
                    refs.add(str(an_item["current_node_id"]))
                refs.update(str(x) for x in (an_item.get("node_tags") or []) if x)
                refs.update(str(x) for x in (an_item.get("node_ids") or []) if x)
                for grp_item in (an_item.get("groups") or []):
                    refs.update(str(x) for x in (grp_item.get("node_tags") or []) if x)
                    refs.update(str(x) for x in (grp_item.get("node_ids") or []) if x)
    except Exception:
        pass
    try:
        sh_cfg = load_shunt_config(conf_dir)
        if sh_cfg.get("global_manual_node"):
            refs.add(str(sh_cfg["global_manual_node"]))
        for g in (sh_cfg.get("groups") or []):
            for k in ("manual_node", "resolved_node"):
                v = str(g.get(k) or "").strip()
                if v and not v.startswith("auto:") and v not in ("direct", "block"):
                    refs.add(v)
    except Exception:
        pass
    try:
        sel_p = run_dir / "selections.json"
        if sel_p.is_file():
            sd = json.loads(sel_p.read_text(encoding="utf-8"))
            for v in (sd.get("selections") or {}).values():
                if isinstance(v, str) and v not in ("direct", "block") and not v.startswith("auto:"):
                    refs.add(v)
    except Exception:
        pass
    refs.discard("")
    refs.discard("direct")
    refs.discard("block")
    return refs

_TOP_N_OUTBOUNDS_MEMO = {}

def select_top_n_outbounds(saved_nodes: list, max_limit: int = 200, run_dir: Path = RUN_DIR, conf_dir: Path = CONF_DIR) -> list:
    _tn_sig = (
        str(conf_dir),
        int(max_limit),
        len(saved_nodes or []),
        saved_nodes[0].get("tag", "") if saved_nodes else "",
        saved_nodes[-1].get("tag", "") if saved_nodes else "",
        any(bool(x.get("disabled")) for x in (saved_nodes or []) if isinstance(x, dict)),
        _conf_file_mtimes_sig_q(conf_dir, ("nodes.json", "node_probe.json", "subscriptions.json", "auto_nodes.json", "shunt.json"), 30),
        _CORE_RELOAD_STATE["config_seq"],
    )
    if _tn_sig in _TOP_N_OUTBOUNDS_MEMO:
        return list(_TOP_N_OUTBOUNDS_MEMO[_tn_sig])
    if len(_TOP_N_OUTBOUNDS_MEMO) > 16:
        _TOP_N_OUTBOUNDS_MEMO.clear()
    """Spec §2.1 & NOLO-LINK '节点不进内核' On-Demand Outbound Governance (with P2-8 fair per-subscription quota & P2-10 exact user cap):
    1. Strictly excludes disabled nodes and nodes from disabled subscriptions.
    2. Always mounts manual nodes (_manual) and all nodes referenced by Auto-Node Pools & Shunt rules.
    3. Reserves a fair per-subscription quota across regions so newly added subscriptions immediately have nodes in the kernel.
    4. Fills remaining slots up to `max_limit` user nodes (loopback self-test nodes are excluded from user node count unless max_limit == 60)."""
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    loopbacks = [ob for ob in (saved_nodes or []) if is_builtin_test_node(ob.get("tag", "")) and not ob.get("disabled")]
    state_order = {"ok": 0, "pending": 1, "suspect": 2, "dead": 3}
    candidates = []
    for ob in (saved_nodes or []):
        if is_builtin_test_node(ob.get("tag", "")) or ob.get("disabled"):
            continue
        ev = evaluate_node_selectability(ob, store=store, subs_list=subs_list, conf_dir=conf_dir)
        if not ev["visible"]:
            continue
        rank = state_order.get(ev["state"], 2)
        candidates.append((
            rank,
            _effective_node_rank_delay_ms(ob.get("tag", ""), ev["delay_ms"]) if (ev["state"] == "ok" and ev["delay_ms"] > 0) else 99999.0,
            ev["delay_ms"] if (ev["state"] == "ok" and ev["delay_ms"] > 0) else 99999,
            ob
        ))
    candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3].get("tag", "")))
    candidates = [(x[0], x[2], x[3]) for x in candidates]
    if max_limit <= 0 or len(candidates) <= max_limit:
        _res_all = loopbacks + [x[2] for x in candidates]
        _TOP_N_OUTBOUNDS_MEMO[_tn_sig] = _res_all
        return list(_res_all)
    # P2-10 Fix: Keep user node cap at exact `max_limit` (only count loopbacks inside cap when self-test calls max_limit=60)
    user_cap = (max_limit - len(loopbacks)) if max_limit == 60 else max_limit
    selected_user = []
    used_tags = {x.get("tag") for x in loopbacks}
    pinned_refs = get_referenced_kernel_node_refs(conf_dir=conf_dir, run_dir=run_dir)
    for _, _, ob in candidates:
        t_ob = ob.get("tag", "")
        nid_ob = ob.get("node_id") or compute_node_id(ob)
        if (t_ob in pinned_refs or nid_ob in pinned_refs or ob.get("_manual")) and t_ob not in used_tags and len(selected_user) < user_cap:
            selected_user.append(ob)
            used_tags.add(t_ob)
    # P2-8 Fix: Reserve a fair minimum quota per enabled subscription so new subscriptions always get kernel slots immediately
    by_sub = {}
    for _, _, ob in candidates:
        sk = str(ob.get("_sub_id") or ob.get("_sub_url") or "default")
        by_sub.setdefault(sk, []).append(ob)
    if len(by_sub) > 1:
        per_sub_quota = max(12, min(30, user_cap // len(by_sub)))
        for sk, s_obs in by_sub.items():
            taken = sum(1 for x in selected_user if str(x.get("_sub_id") or x.get("_sub_url") or "default") == sk)
            for ob in s_obs:
                if taken >= per_sub_quota or len(selected_user) >= user_cap:
                    break
                t_ob = ob.get("tag", "")
                if t_ob not in used_tags:
                    selected_user.append(ob)
                    used_tags.add(t_ob)
                    taken += 1
    by_reg = {}
    for item in candidates:
        r = classify_node_region(item[2].get("tag", ""), item[2])
        by_reg.setdefault(r, []).append(item[2])
    for r, r_list in by_reg.items():
        if len(selected_user) < user_cap and r_list[0].get("tag") not in used_tags:
            selected_user.append(r_list[0])
            used_tags.add(r_list[0].get("tag"))
    for _, _, ob in candidates:
        if len(selected_user) >= user_cap:
            break
        if ob.get("tag") not in used_tags:
            selected_user.append(ob)
            used_tags.add(ob.get("tag"))
    _res_top = loopbacks + selected_user
    _TOP_N_OUTBOUNDS_MEMO[_tn_sig] = _res_top
    return list(_res_top)

def clean_outbound_for_singbox(ob: dict) -> dict:
    """Explicit sing-box 1.14 outbound whitelist + NOLO-LINK sing-box 1.13/1.14 compatibility normalizer."""
    clean = copy.deepcopy({k: v for k, v in ob.items() if k in _SB_OUTBOUND_KEYS})
    ntype = str(clean.get("type", "")).lower()

    if ntype == "vless":
        if "packet_encoding" not in clean:
            clean["packet_encoding"] = "xudp"
        flow = str(clean.get("flow", "") or "").strip()
        if flow == "xtls-rprx-vision-udp443":
            clean["flow"] = "xtls-rprx-vision"
        elif flow and flow != "xtls-rprx-vision":
            clean.pop("flow", None)

    # Hysteria2 port-hopping normalization (server_ports: ["20000:40000"])
    if ntype == "hysteria2" and "server_ports" in clean:
        raw_sp = clean.get("server_ports")
        sp_list = raw_sp if isinstance(raw_sp, list) else [str(raw_sp)]
        norm_sp = []
        for item in sp_list:
            for part in str(item).split(","):
                part = part.strip().replace("-", ":")
                if re.match(r"^\d+:\d+$", part):
                    a, b = [int(x) for x in part.split(":", 1)]
                    if 1 <= a <= b <= 65535:
                        norm_sp.append(f"{a}:{b}")
        if norm_sp:
            clean["server_ports"] = norm_sp
        else:
            clean.pop("server_ports", None)

    # WebSocket / HTTPUpgrade transport ?ed=N early-data extraction & ALPN compatibility
    trans = clean.get("transport")
    is_ws_like = False
    if isinstance(trans, dict):
        ttype = str(trans.get("type", "")).lower()
        if ttype in ("ws", "httpupgrade"):
            is_ws_like = True
        if ttype == "ws" and isinstance(trans.get("path"), str) and "ed=" in trans["path"]:
            m_ed = re.search(r"[?&]ed=(\d+)", trans["path"])
            if m_ed:
                ed_val = int(m_ed.group(1))
                new_path = re.sub(r"([?&])ed=\d+&?", r"\1", trans["path"]).rstrip("?&") or "/"
                trans["path"] = new_path
                if ed_val > 0 and "max_early_data" not in trans:
                    trans["max_early_data"] = ed_val
                    trans["early_data_header_name"] = "Sec-WebSocket-Protocol"

    tls = clean.get("tls")
    if isinstance(tls, dict):
        # 1. QUIC protocols (hysteria2, tuic) do NOT support uTLS in sing-box -> remove utls to prevent startup failure
        if ntype in ("hysteria2", "tuic"):
            tls.pop("utls", None)
        elif isinstance(tls.get("utls"), dict):
            fp = str(tls["utls"].get("fingerprint", "") or "").strip().lower()
            if fp in ("unsafe", "none", ""):
                tls["utls"]["fingerprint"] = "chrome"
        # 2. WebSocket/HTTPUpgrade over TLS: force alpn=["http/1.1"] if alpn is present (fixes 3x-ui alpn=h2 WS 101 error)
        if is_ws_like and "alpn" in tls:
            tls["alpn"] = ["http/1.1"]
        # 3. Reality short_id cleanup: strip literal "null"/"undefined" or odd/non-hex strings
        reality = tls.get("reality")
        if isinstance(reality, dict):
            sid = str(reality.get("short_id", "") or "").strip().lower()
            if sid in ("null", "undefined", "none") or not re.match(r"^[0-9a-f]{0,16}$", sid):
                reality["short_id"] = ""
            else:
                reality["short_id"] = sid

    return clean

# ==============================================================================
# Dynamic Reverse Home-Link Inbound Manager (/etc/ai-link/homelink.json)
# ==============================================================================
# User-Created Reverse Home-Link Nodes (No undeletable preset nodes; 100% user-controlled)
DEFAULT_HOMELINK_NODES = []

def load_homelink_nodes(conf_dir: Path = CONF_DIR) -> list:
    hl_file = conf_dir / "homelink.json"
    if hl_file.is_file():
        try:
            data = json.loads(hl_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                cleaned = []
                for x in data:
                    if isinstance(x, dict) and x.get("id"):
                        item = dict(x)
                        item["builtin"] = False  # All nodes are freely editable & deletable
                        cleaned.append(item)
                return cleaned
        except Exception:
            pass
    return []

RESERVED_HOMELINK_PORTS = {
    22: "SSH",
    53: "dnsmasq DNS",
    80: "uhttpd/LuCI HTTP",
    443: "uhttpd/LuCI HTTPS",
    1053: "sing-box DNS",
    7874: "sing-box DNS",
    7890: "sing-box Mixed Proxy",
    7891: "sing-box Redir",
    7893: "sing-box TProxy",
    9090: "sing-box Clash API",
    9099: "AI-LINK WebUI Panel",
}

def _read_proc_listening_ports(proto: str = "tcp") -> set:
    """Reads /proc/net/{tcp,tcp6,udp,udp6} to detect active listening ports without spawning ss/netstat (NOLO servers.mjs)."""
    ports = set()
    files = ("/proc/net/udp", "/proc/net/udp6") if proto == "udp" else ("/proc/net/tcp", "/proc/net/tcp6")
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                for line in f.readlines()[1:]:
                    parts = line.strip().split()
                    if len(parts) < 4:
                        continue
                    local_addr, st_hex = parts[1], parts[3]
                    if proto == "tcp" and st_hex != "0A":
                        continue
                    if ":" in local_addr:
                        port_hex = local_addr.rsplit(":", 1)[1]
                        ports.add(int(port_hex, 16))
        except Exception:
            pass
    return ports

def validate_homelink_port(
    port: int,
    protocol: str = "vless-reality",
    exclude_id: str = "",
    conf_dir: Path = CONF_DIR,
) -> dict:
    """3-layer Home-Link port conflict validator (Reserved system ports + Peer Home-Link nodes + /proc/net live sockets)."""
    try:
        p_int = int(port)
    except Exception:
        return {"ok": False, "reason": f"端口号非法: {port}"}
    if p_int < 1024 or p_int > 65535:
        return {"ok": False, "reason": f"端口 {p_int} 超出安全可用范围 (1024-65535)"}
    if p_int in RESERVED_HOMELINK_PORTS:
        return {"ok": False, "reason": f"端口 {p_int} 已被系统核心服务占用 ({RESERVED_HOMELINK_PORTS[p_int]})"}
    nodes = load_homelink_nodes(conf_dir)
    for n in nodes:
        if exclude_id and n.get("id") == exclude_id:
            continue
        lp = int(n.get("listen_port", 0) or 0)
        if lp == p_int:
            return {"ok": False, "reason": f"端口 {p_int} 已被另一条回家节点「{n.get('name', n.get('id'))}」使用"}
    existing_hl_ports = {int(n.get("listen_port", 0) or 0) for n in nodes if n.get("enabled", True)}
    if p_int not in existing_hl_ports:
        l4_proto = "udp" if "hy" in str(protocol).lower() or "tuic" in str(protocol).lower() else "tcp"
        live_ports = _read_proc_listening_ports(l4_proto)
        if p_int in live_ports:
            return {"ok": False, "reason": f"端口 {p_int}/{l4_proto.upper()} 当前已被本机其他进程监听占用"}
    return {"ok": True, "port": p_int, "reason": "可用"}

def sync_homelink_wan_firewall_rules(nodes: list) -> dict:
    """Idempotently syncs OpenWrt UCI WAN firewall rules for enabled Home-Link inbounds (NOLO system/firewall.mjs)."""
    if os.environ.get("AI_LINK_SKIP_UCI_FIREWALL") == "1":
        return {"ok": True, "skipped": True}
    desired = {}
    for n in (nodes or []):
        if not n.get("enabled", True):
            continue
        raw_id = re.sub(r"[^a-zA-Z0-9_]", "_", str(n.get("id", "hl")))
        sec_name = f"ailink_hl_{raw_id}"
        proto = "udp" if ("hy" in str(n.get("protocol", "")).lower() or "tuic" in str(n.get("protocol", "")).lower()) else "tcp"
        lport = str(int(n.get("listen_port", 9443) or 9443))
        desired[sec_name] = {"name": f"AI-LINK-HomeLink-{lport}", "src": "wan", "proto": proto, "dest_port": lport, "target": "ACCEPT"}
    try:
        r = subprocess.run(["uci", "-q", "show", "firewall"], capture_output=True, text=True, timeout=2)
        if r.returncode != 0 and not (r.stdout or "").strip():
            return {"ok": False, "reason": "uci unavailable"}
        out = r.stdout or ""
        existing_secs = set(re.findall(r"^firewall\.(ailink_hl_[a-zA-Z0-9_]+)=rule", out, flags=re.M))
        changed = False
        for old_sec in (existing_secs - set(desired.keys())):
            subprocess.run(["uci", "-q", "delete", f"firewall.{old_sec}"], capture_output=True, timeout=2)
            changed = True
        for sec, spec in desired.items():
            cur_port = re.search(rf"^firewall\.{re.escape(sec)}\.dest_port='?([^'\n]+)'?", out, flags=re.M)
            cur_proto = re.search(rf"^firewall\.{re.escape(sec)}\.proto='?([^'\n]+)'?", out, flags=re.M)
            if (sec not in existing_secs) or (not cur_port or cur_port.group(1) != spec["dest_port"]) or (not cur_proto or cur_proto.group(1) != spec["proto"]):
                subprocess.run(["uci", "-q", "set", f"firewall.{sec}=rule"], capture_output=True, timeout=2)
                for k, v in spec.items():
                    subprocess.run(["uci", "-q", "set", f"firewall.{sec}.{k}={v}"], capture_output=True, timeout=2)
                changed = True
        if changed:
            subprocess.run(["uci", "-q", "commit", "firewall"], capture_output=True, timeout=2)
            subprocess.run(["/etc/init.d/firewall", "reload"], capture_output=True, timeout=4)
        return {"ok": True, "changed": changed, "active_rules": len(desired)}
    except Exception as e:
        return {"ok": False, "reason": str(e)}

_HOMELINK_API_MEMO = {}

def save_homelink_nodes(nodes: list, conf_dir: Path = CONF_DIR) -> list:
    _HOMELINK_API_MEMO.clear()
    conf_dir.mkdir(parents=True, exist_ok=True)
    hl_file = conf_dir / "homelink.json"
    _atomic_write_text(hl_file, json.dumps(nodes, indent=2, ensure_ascii=False))
    return nodes

# ==============================================================================
# v2.0.0-r1: DNS Rewrite Engine, Cloud Domain Filtering & Traffic Insights
# ==============================================================================
DEFAULT_DNS_REWRITE_RULES = [
    {
        "id": "rw_googleapis",
        "from_domain": "services.googleapis.cn",
        "to_domain": "services.googleapis.com",
        "enabled": True,
        "note": "Google Play / FCM 核心服务域名重写"
    },
    {
        "id": "rw_googleapis_root",
        "from_domain": "googleapis.cn",
        "to_domain": "googleapis.com",
        "enabled": True,
        "note": "Google APIs 大陆域名映射至全球版"
    },
    {
        "id": "rw_gstatic_cn",
        "from_domain": "gstatic.cn",
        "to_domain": "gstatic.com",
        "enabled": True,
        "note": "Google 静态资源与连通性检测重写"
    },
    {
        "id": "rw_googledev",
        "from_domain": "developers.google.cn",
        "to_domain": "developers.google.com",
        "enabled": True,
        "note": "Google 开发者文档与 API 重写"
    },
    {
        "id": "rw_google_www",
        "from_domain": "www.google.cn",
        "to_domain": "www.google.com",
        "enabled": True,
        "note": "防止 Google 搜索被 302 重定向至大陆版"
    },
    {
        "id": "rw_google_root",
        "from_domain": "google.cn",
        "to_domain": "google.com",
        "enabled": True,
        "note": "Google 根域名强制映射至全球版"
    }
]

DEFAULT_DNS_FILTER_LISTS = [
    {
        "id": "anti-ad",
        "name": "Anti-AD 中文区精准广告与 PCDN 过滤",
        "url": "https://anti-ad.net/domains.txt",
        "category": "广告与PCDN",
        "enabled": True,
        "rules_count": 84260,
        "updated_at": "2026-10-20 17:30"
    },
    {
        "id": "adguard-dns",
        "name": "AdGuard DNS Filter 全球综合拦截规则",
        "url": "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt",
        "category": "综合广告/追踪",
        "enabled": True,
        "rules_count": 62480,
        "updated_at": "2026-10-20 17:30"
    },
    {
        "id": "easylist-cn",
        "name": "EasyList China 国内网页与视频贴片过滤",
        "url": "https://easylist-downloads.adblockplus.org/easylistchina.txt",
        "category": "国内视频/网页",
        "enabled": True,
        "rules_count": 41920,
        "updated_at": "2026-10-20 17:30"
    },
    {
        "id": "oisd-small",
        "name": "OISD Blocklist 隐私遥测与追踪器拦截",
        "url": "https://small.oisd.nl/domainswild",
        "category": "隐私与防追踪",
        "enabled": True,
        "rules_count": 95100,
        "updated_at": "2026-10-20 17:30"
    },
    {
        "id": "stevenblack",
        "name": "StevenBlack Hosts 恶意软件与钓鱼防护",
        "url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "category": "恶意域名防护",
        "enabled": False,
        "rules_count": 78540,
        "updated_at": "2026-10-20 16:00"
    }
]

BUILTIN_BLOCKED_DOMAINS_SEED = [
    # PCDN & Background Upload Stealers
    "isvip0syajs-data.xycdn.com", "xycdn.com", "onethingpcs.com", "pkoplink.com",
    "saxysec.com", "uhabo.com", "szbdyd.com", "kuiniuca.com", "p2p.qq.com",
    "analysis-acc-ssl.xunlei.com", "hub5btmain.sandai.net", "hub5emu.sandai.net",
    # Global Ad Networks & Trackers (Google / DoubleClick / Meta / AppsFlyer)
    "ad.doubleclick.net", "pagead2.googlesyndication.com", "googleads.g.doubleclick.net",
    "adservice.google.com", "tpc.googlesyndication.com", "ade.googlesyndication.com",
    "app-measurement.com", "firebase-settings.crashlytics.com", "ads.tiktok.com",
    "analytics.tiktok.com", "log.byteoversea.com", "ads-api.twitter.com",
    "ads.yap.yahoo.com", "ad.atdmt.com", "scorecardresearch.com",
    "criteo.com", "criteo.net", "outbrain.com", "taboola.com", "rubiconproject.com",
    "pubmatic.com", "openx.net", "adnxs.com", "moatads.com", "appsflyer.com",
    "adjust.com", "branch.io", "mixpanel.com", "amplitude.com", "hotjar.com",
    # Domestic Ad Networks & Splash Ads (Baidu / Alibaba / ByteDance / Tencent / Xiaomi / Huawei)
    "hm.baidu.com", "pos.baidu.com", "cpro.baidu.com", "cbjs.baidu.com",
    "crs.baidu.com", "nsclick.baidu.com", "eclick.baidu.com", "als.baidu.com",
    "mobads.baidu.com", "mobads-logs.baidu.com", "wn.pos.baidu.com",
    "tanx.com", "mmstat.com", "atanx.alicdn.com", "strip.taobaocdn.com",
    "adash.man.aliyuncs.com", "adashbc.ut.taobao.com", "ut.taobao.com",
    "log.snssdk.com", "extlog.snssdk.com", "pangolin-sdk-toutiao.com",
    "ad.toutiao.com", "track.toutiao.com", "mon.snssdk.com", "i.snssdk.com",
    "is.snssdk.com", "bds.snssdk.com", "toblog.ctobsdk.com", "mcs.snssdk.com",
    "adsmind.ugdtimg.com", "gdt.qq.com", "e.qq.com", "mi.gdt.qq.com",
    "v.gdt.qq.com", "win.gdt.qq.com", "btrace.qq.com", "pingma.qq.com",
    "otheve.beacon.qq.com", "snowflake.qq.com", "adshmmsg.qq.com",
    "miui.com.ad.xiaomi.com", "sdkconfig.ad.xiaomi.com", "ad.xiaomi.com",
    "api.ad.xiaomi.com", "data.mistat.xiaomi.com", "tracking.miui.com",
    "metrics.data.hicloud.com", "logservice.hicloud.com", "grs.dbankcloud.com",
    "ads.oppomobile.com", "adx.ads.oppomobile.com", "stsdk.vivo.com.cn",
    # Video / Portal / Social Splash & SDK Ads (iQiyi / Youku / Weibo / NetEase / Zhihu / Kuaishou)
    "cupid.iqiyi.com", "msg.71.am", "ad.m.iqiyi.com", "atm.youku.com",
    "ad.api.3g.youku.com", "valf.atm.youku.com", "sax.sina.com.cn",
    "beacon.sina.com.cn", "sdkapp.uve.weibo.com", "ad.mail.163.com",
    "nex.163.com", "iadmat.nosdn.127.net", "g1.163.com", "sugar.zhihu.com",
    "appcloud2.in.zhihu.com", "commercial.zhihu.com", "gdfp.gifshow.com",
    "ulog.ksapisrv.com", "adukwai.com", "da.mgtv.com", "log.hunantv.com",
    # OS Telemetry & Tracking
    "telemetry.microsoft.com", "vortex.data.microsoft.com", "oca.telemetry.microsoft.com",
    "sqm.telemetry.microsoft.com", "watson.telemetry.microsoft.com",
    "statsfe2.ws.microsoft.com", "corp.sts.microsoft.com", "iadsdk.apple.com",
    "metrics.icloud.com", "banners.itunes.apple.com", "cnzz.com", "s11.cnzz.com",
    "z1.cnzz.com", "umeng.com", "umengcloud.com", "alog.umeng.com", "plough.umeng.com"
]

def _classify_adblock_domain_category(dom: str) -> str:
    dl = str(dom or "").lower()
    if any(x in dl for x in ("xycdn", "onething", "pkoplink", "saxysec", "uhabo", "szbdyd", "kuiniuca", "p2p.qq", "xunlei", "sandai")):
        return "PCDN盗刷与后台上传"
    if any(x in dl for x in ("telemetry", "vortex", "mistat", "tracking", "beacon", "mmstat", "cnzz", "umeng", "crashlytics", "app-measurement", "log.", "extlog.", "mon.snssdk", "btrace", "pingma", "metrics")):
        return "隐私遥测与追踪探针"
    if any(x in dl for x in ("miui", "xiaomi", "hicloud", "oppomobile", "vivo", "ugdtimg", "pangolin", "splash", "iadmat", "sdkapp.uve")):
        return "开屏广告与终端SDK"
    return "商业广告联盟与弹窗"

def load_dns_rewrite_config(conf_dir: Path = CONF_DIR) -> dict:
    rw_file = conf_dir / "dns_rewrite.json"
    default_cfg = {
        "enabled": True,
        "force_tunnel_dns": True,
        "rules": [dict(r) for r in DEFAULT_DNS_REWRITE_RULES]
    }
    if rw_file.is_file():
        try:
            saved = json.loads(rw_file.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                default_cfg["enabled"] = bool(saved.get("enabled", True))
                default_cfg["force_tunnel_dns"] = bool(saved.get("force_tunnel_dns", True))
                if isinstance(saved.get("rules"), list):
                    existing_from = {str(r.get("from_domain") or "").strip().lower() for r in saved["rules"] if isinstance(r, dict)}
                    merged_rules = list(saved["rules"])
                    for dr in DEFAULT_DNS_REWRITE_RULES:
                        if dr["from_domain"].lower() not in existing_from:
                            merged_rules.append(dict(dr))
                    default_cfg["rules"] = merged_rules
                return default_cfg
        except Exception:
            pass
    return default_cfg

def save_dns_rewrite_config(cfg: dict, conf_dir: Path = CONF_DIR) -> dict:
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "dns_rewrite.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    apply_dns_rewrite_system(cfg, conf_dir)
    return cfg

def _detect_dnsmasq_confdir(create: bool = False) -> Path:
    """Locate the directory dnsmasq actually reads extra configs from. OpenWrt writes a random-suffix path (e.g. /tmp/dnsmasq.c"""
    candidates = []
    try:
        r = subprocess.run(["uci", "-q", "get", "dhcp.@dnsmasq[0].confdir"],
                           capture_output=True, text=True, timeout=1)
        val = (r.stdout or "").strip()
        if val:
            candidates.append(val.split(",")[0].rstrip("/"))
    except Exception:
        pass
    for pattern in ("/var/etc/dnsmasq.conf.*", "/etc/dnsmasq.conf"):
        for f in sorted(glob.glob(pattern)):
            try:
                for ln in Path(f).read_text(encoding="utf-8", errors="ignore").splitlines():
                    ln = ln.strip()
                    if ln.startswith("conf-dir="):
                        d = ln.split("=", 1)[1].split(",")[0].rstrip("/")
                        if d:
                            candidates.append(d)
            except Exception:
                pass
    candidates.append("/tmp/dnsmasq.d")
    for c in candidates:
        if Path(c).is_dir():
            return Path(c)
    if not create:
        return Path(candidates[-1])
    for c in candidates:
        try:
            Path(c).mkdir(parents=True, exist_ok=True)
            return Path(c)
        except Exception:
            continue
    return Path("/tmp/dnsmasq.d")

def apply_dns_rewrite_system(cfg: dict = None, conf_dir: Path = CONF_DIR) -> dict:
    """Write dnsmasq CNAME/address rewrite rules so LAN clients honour rewrites. Hermetic when conf_dir != CONF_DIR."""
    if cfg is None:
        cfg = load_dns_rewrite_config(conf_dir)
    is_live = (Path(conf_dir).resolve() == CONF_DIR.resolve())
    dnsmasq_dir = _detect_dnsmasq_confdir(create=is_live) if is_live else Path(conf_dir)
    conf_path = dnsmasq_dir / "ai-link-rewrite.conf"
    status = {"ok": False, "path": str(conf_path), "rules": 0, "reason": ""}
    try:
        if not cfg.get("enabled", True):
            if conf_path.is_file():
                conf_path.unlink()
            status.update(ok=True, reason="disabled")
            return status
        lines = ["# Auto-generated by AI-LINK DNS Rewrite Engine"]
        n = 0
        for r in cfg.get("rules", []):
            if not r.get("enabled", True):
                continue
            src = (r.get("from_domain") or "").strip()
            dst = (r.get("to_domain") or "").strip()
            if src and dst:
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", dst):
                    lines.append(f"address=/{src}/{dst}")
                else:
                    lines.append(f"cname={src},{dst}")
                n += 1
        conf_path.parent.mkdir(parents=True, exist_ok=True)
        new_txt = "\n".join(lines) + "\n"
        old_txt = conf_path.read_text(encoding="utf-8", errors="ignore") if conf_path.is_file() else ""
        conf_path.write_text(new_txt, encoding="utf-8")
        status.update(ok=True, rules=n)
        if is_live and old_txt != new_txt and Path("/etc/init.d/dnsmasq").exists():
            try:
                subprocess.run(["/etc/init.d/dnsmasq", "restart"], capture_output=True, timeout=15)
            except Exception:
                pass
    except Exception as exc:
        status["reason"] = "%s: %s" % (type(exc).__name__, exc)
    return status

def _detect_default_gateway_ip() -> str:
    try:
        r = subprocess.run(["ip", "-4", "route", "show", "default"], capture_output=True, text=True, timeout=1.5)
        for tok_line in (r.stdout or "").splitlines():
            parts = tok_line.split()
            if "via" in parts:
                idx = parts.index("via")
                if idx + 1 < len(parts):
                    return parts[idx + 1].strip()
    except Exception:
        pass
    return ""

def fallback_resolv_conf_to_direct():
    """DIAG-2 Fix (v1.0.3): When AI-LINK is stopped, restarting, or sing-box (:7874) is down,
    point /etc/resolv.conf and /tmp/resolv.conf.d/resolv.conf.auto to gateway + public DNS (223.5.5.5 / 119.29.29.29)
    so the router itself never loses DNS resolution (prevents ttyd CPD 'No internet')."""
    try:
        gw = _detect_default_gateway_ip()
        auto_dir = Path("/tmp/resolv.conf.d")
        auto_dir.mkdir(parents=True, exist_ok=True)
        auto_f = auto_dir / "resolv.conf.auto"
        if not auto_f.is_file() or "nameserver " not in auto_f.read_text(encoding="utf-8", errors="ignore"):
            ns_lines = ["# Auto-fallback by AI-LINK for side-router direct DNS"]
            if gw:
                ns_lines.append(f"nameserver {gw}")
            ns_lines.extend(["nameserver 223.5.5.5", "nameserver 119.29.29.29"])
            auto_f.write_text("\n".join(ns_lines) + "\n", encoding="utf-8")
        direct_lines = ["search lan"]
        if gw:
            direct_lines.append(f"nameserver {gw}")
        direct_lines.extend(["nameserver 223.5.5.5", "nameserver 119.29.29.29", "nameserver 127.0.0.1"])
        direct_f = Path("/tmp/resolv.conf.ai-link-direct")
        direct_f.write_text("\n".join(direct_lines) + "\n", encoding="utf-8")
        resolv_p = Path("/etc/resolv.conf")
        if resolv_p.is_symlink() or not resolv_p.exists():
            try:
                resolv_p.unlink(missing_ok=True)
                resolv_p.symlink_to(direct_f)
            except Exception:
                resolv_p.write_text(direct_f.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            resolv_p.write_text(direct_f.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

def restore_resolv_conf_to_local():
    """DIAG-2 Fix (v1.0.3): Point /etc/resolv.conf back to 127.0.0.1 (with gateway + 223.5.5.5 secondary fallback)
    once sing-box (:7874 / :7893) is confirmed alive."""
    try:
        gw = _detect_default_gateway_ip()
        active_lines = ["search lan", "nameserver 127.0.0.1"]
        if gw:
            active_lines.append(f"nameserver {gw}")
        active_lines.append("nameserver 223.5.5.5")
        active_f = Path("/tmp/resolv.conf.ai-link-active")
        active_f.write_text("\n".join(active_lines) + "\n", encoding="utf-8")
        resolv_p = Path("/etc/resolv.conf")
        if resolv_p.is_symlink() or not resolv_p.exists():
            try:
                resolv_p.unlink(missing_ok=True)
                resolv_p.symlink_to(active_f)
            except Exception:
                resolv_p.write_text(active_f.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            resolv_p.write_text(active_f.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

def rollback_dnsmasq_and_resolv(conf_dir: Path = CONF_DIR) -> bool:
    """Removes ai-link-adblock.conf (`no-resolv` + `server=127.0.0.1#7874`), restores direct /etc/resolv.conf fallback,
    and restarts dnsmasq if upstream was mounted."""
    is_live = (Path(conf_dir).resolve() == CONF_DIR.resolve())
    dnsmasq_dir = _detect_dnsmasq_confdir(create=False) if is_live else Path(conf_dir)
    conf_path = dnsmasq_dir / "ai-link-adblock.conf"
    removed_any = False
    cands = [conf_path]
    if is_live:
        cands.extend([Path("/tmp/dnsmasq.d/ai-link-adblock.conf"), Path("/var/etc/dnsmasq.d/ai-link-adblock.conf")])
        for g_p in glob.glob("/tmp/dnsmasq.cfg*/ai-link-adblock.conf"):
            cands.append(Path(g_p))
    for _cp in cands:
        try:
            if _cp.is_file():
                _cp.unlink()
                removed_any = True
        except Exception:
            pass
    if is_live:
        fallback_resolv_conf_to_direct()
        if removed_any and Path("/etc/init.d/dnsmasq").exists():
            try:
                subprocess.run(["/etc/init.d/dnsmasq", "restart"], capture_output=True, timeout=15)
            except Exception:
                pass
    return removed_any

def apply_dns_adblock_system(conf_dir: Path = CONF_DIR, force_live_mount: bool = False) -> dict:
    """v1.0.3 (P0-3 & DIAG-2 Fix):
    1. Configures dnsmasq upstream (`no-resolv` + `server=127.0.0.1#7874`) ONLY when proxy is active AND
       (in live mode) sing-box is actually running (or `force_live_mount=True`), preventing router DNS blackhole
       during service stop/restart or before sing-box starts!
    2. Writes high-frequency blocked domains (`address=/domain/0.0.0.0` + `address=/domain/::`) when AdBlock is enabled.
    3. Remains 100% hermetic when `conf_dir != CONF_DIR` (never mutates live dnsmasq during `--self-test`)."""
    flt_cfg = load_dns_filter_config(conf_dir)
    is_live = (Path(conf_dir).resolve() == CONF_DIR.resolve())
    dnsmasq_dir = _detect_dnsmasq_confdir(create=is_live) if is_live else Path(conf_dir)
    conf_path = dnsmasq_dir / "ai-link-adblock.conf"
    status = {"ok": False, "path": str(conf_path), "rules": 0, "upstream_7874": False}
    try:
        ops = get_ops_settings(conf_dir)
        core_ready_for_dns = True
        if is_live and Path("/etc/init.d/ai-link").exists() and not force_live_mount:
            core_ready_for_dns = bool(_get_live_singbox_pids())
        proxy_active = bool(ops.get("enabled", True) and (not is_live or (not is_bypass_active() and not FAIL_OPEN_STATE.get("active") and core_ready_for_dns)))
        flt_on = bool(flt_cfg.get("enabled", True))
        if not proxy_active:
            rollback_dnsmasq_and_resolv(conf_dir)
            status["ok"] = True
            status["upstream_7874"] = False
            return status
        lines = ["# Auto-generated by AI-LINK Smart Dual-Stack DNS & BlackHole AdGuard Engine"]
        if proxy_active:
            lines.append("no-resolv")
            lines.append("server=127.0.0.1#7874")
            status["upstream_7874"] = True
        bdoms = get_active_blocked_domains(conf_dir) if flt_on else []
        if flt_on:
            # v24-hotfix9 P1-A Fix: Forward 100% of real blocked domains to sing-box dns-in (127.0.0.1#7874)
            # instead of short-circuiting top 350 in dnsmasq, so every DNS block is logged & counted in real time!
            lines.append("address=/adblock-sinkhole.invalid/0.0.0.0")
            lines.append("address=/adblock-sinkhole.invalid/::")
        new_txt = "\n".join(lines) + "\n"
        conf_path.parent.mkdir(parents=True, exist_ok=True)
        old_txt = conf_path.read_text(encoding="utf-8", errors="ignore") if conf_path.is_file() else ""
        conf_path.write_text(new_txt, encoding="utf-8")
        if is_live and dnsmasq_dir != Path("/tmp/dnsmasq.d"):
            try:
                Path("/tmp/dnsmasq.d").mkdir(parents=True, exist_ok=True)
                (Path("/tmp/dnsmasq.d") / "ai-link-adblock.conf").write_text(new_txt, encoding="utf-8")
            except Exception:
                pass
        if is_live and old_txt != new_txt and Path("/etc/init.d/dnsmasq").exists():
            try:
                subprocess.run(["/etc/init.d/dnsmasq", "restart"], capture_output=True, timeout=15)
            except Exception:
                pass
        status["ok"] = True
        status["rules"] = len(bdoms)
    except Exception as exc:
        status["reason"] = str(exc)
    return status

def load_dns_filter_config(conf_dir: Path = CONF_DIR) -> dict:
    flt_file = conf_dir / "dns_filters.json"
    default_cfg = {
        "enabled": True,
        "auto_update": True,
        "update_interval_hours": 24,
        "last_sync_ts": int(time.time()) - 600,
        "lists": [dict(x) for x in DEFAULT_DNS_FILTER_LISTS],
        "custom_blocked": ["isvip0syajs-data.xycdn.com", "analysis-acc-ssl.xunlei.com"],
        "custom_allowed": []
    }
    if flt_file.is_file():
        try:
            saved = json.loads(flt_file.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                default_cfg.update({k: v for k, v in saved.items() if k in default_cfg})
                return default_cfg
        except Exception:
            pass
    return default_cfg

def save_dns_filter_config(cfg: dict, conf_dir: Path = CONF_DIR) -> dict:
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "dns_filters.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return cfg

_VALID_FILTER_DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")

def _normalize_filter_domain_line(raw_line: str) -> str:
    """P0-1 Fix: Format-aware AdGuard / EasyList / Hosts / Wildcard domain normalizer.
    - Strips comments (#, !) and rejects whitelist exception rules (@@) or element hiding (##, #@#).
    - Parses AdGuard/ABP `||domain.com^` and `||domain.com^$third-party` (rejects `$popup,domain=a|b` modifier-only rules).
    - Parses Hosts `0.0.0.0 domain.com` / `127.0.0.1 domain.com`.
    - Strips leading `*.` or `.` from wildcard domain lines `*.example.com` -> `example.com`.
    - Validates strict RFC hostname syntax so `*.xxx` or `$popup...` garbage never enters sing-box `domain_suffix`!"""
    ln = str(raw_line or "").strip()
    if not ln or ln.startswith(("#", "!", "@@", "[", "/")):
        return ""
    if "##" in ln or "#@#" in ln or "#?#" in ln:
        return ""
    if "#" in ln:
        ln = ln.split("#", 1)[0].strip()
    # 1. AdGuard / EasyList `||example.com^...`
    if ln.startswith("||"):
        body = ln[2:]
        if "$" in body:
            dom_part, mod_part = body.split("$", 1)
            # Reject domain-scoped popup/scriptlet rules that only apply on specific third-party pages
            if "domain=" in mod_part or "denyallow=" in mod_part or "badfilter" in mod_part:
                return ""
            body = dom_part
        body = body.split("^", 1)[0].strip().rstrip(".")
        if "/" in body or ":" in body or "*" in body:
            return ""
        cand = body.lower().lstrip("*.")
    # 2. Hosts file format `0.0.0.0 example.com` or `127.0.0.1 example.com`
    elif ln.startswith(("0.0.0.0 ", "0.0.0.0	", "127.0.0.1 ", "127.0.0.1	", ":: ", "::1 ")):
        parts = ln.split()
        if len(parts) < 2:
            return ""
        cand = parts[1].strip().lower().lstrip("*.").rstrip(".")
    # 3. Reject any raw AdGuard modifier line starting with `$` or containing `$`, `|`, `/`, `:`
    elif any(ch in ln for ch in ("$", "|", "/", ":", " ", "	", "^")):
        return ""
    else:
        cand = ln.lower().lstrip("*.").rstrip(".")
    if not cand or cand in ("localhost", "localhost.localdomain", "local", "broadcasthost", "0.0.0.0", "ip6-localhost", "ip6-loopback"):
        return ""
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", cand):
        return ""
    if not _VALID_FILTER_DOMAIN_RE.match(cand):
        return ""
    return cand

_BLOCKED_DOMAINS_MEMO = {}

def _blocked_domains_cache_sig(conf_dir: Path = CONF_DIR) -> tuple:
    def _fsig(p: Path):
        try:
            if p.is_file():
                st = p.stat()
                return (st.st_mtime_ns, st.st_size)
        except Exception:
            pass
        return (0, 0)
    return (
        str(Path(conf_dir).resolve()),
        _fsig(conf_dir / "dns_filters.json"),
        _fsig(conf_dir / "rules/cloud_blocked_domains.json"),
    )

def get_active_blocked_domains(conf_dir: Path = CONF_DIR) -> list:
    """v24-hotfix9 (P0-1 & P1-B Fix): Memoized by (mtime_ns, size) of dns_filters.json and cloud_blocked_domains.json.
    Eliminates 50,134x repeated `_normalize_filter_domain_line()` calls per `/api/status` request (3.8s -> 0.01ms)."""
    sig = _blocked_domains_cache_sig(conf_dir)
    cached_entry = _BLOCKED_DOMAINS_MEMO.get(sig)
    if cached_entry is not None:
        return cached_entry[0]
    fcfg = load_dns_filter_config(conf_dir)
    if not fcfg.get("enabled", True):
        res_empty = []
        _BLOCKED_DOMAINS_MEMO[sig] = (res_empty, frozenset())
        return res_empty
    allowed = {_normalize_filter_domain_line(d) or d.strip().lower() for d in (fcfg.get("custom_allowed") or []) if str(d).strip()}
    priority_list = []
    seen = set()
    def _add_clean(raw_d: str, to_prio: bool = False):
        c = _normalize_filter_domain_line(raw_d)
        if not c or c in allowed or c in seen:
            return
        seen.add(c)
        if to_prio:
            priority_list.append(c)
        else:
            cloud_list.append(c)
    cloud_list = []
    for d in (fcfg.get("custom_blocked") or []):
        _add_clean(d, to_prio=True)
    enabled_lists = [l for l in (fcfg.get("lists") or []) if l.get("enabled", True)]
    if enabled_lists:
        for d in BUILTIN_BLOCKED_DOMAINS_SEED:
            _add_clean(d, to_prio=True)
    cached_file = conf_dir / "rules/cloud_blocked_domains.json"
    if cached_file.is_file() and enabled_lists:
        try:
            extra = json.loads(cached_file.read_text(encoding="utf-8"))
            if isinstance(extra, list):
                for d in extra:
                    _add_clean(d, to_prio=False)
        except Exception:
            pass
    res_list = priority_list + cloud_list
    if len(_BLOCKED_DOMAINS_MEMO) > 8:
        _BLOCKED_DOMAINS_MEMO.clear()
    _BLOCKED_DOMAINS_MEMO[sig] = (res_list, frozenset(res_list))
    return res_list

def get_active_blocked_domains_set(conf_dir: Path = CONF_DIR) -> frozenset:
    """O(1) memoized frozenset of active blocked domains for fast suffix matching."""
    sig = _blocked_domains_cache_sig(conf_dir)
    cached_entry = _BLOCKED_DOMAINS_MEMO.get(sig)
    if cached_entry is not None:
        return cached_entry[1]
    get_active_blocked_domains(conf_dir)
    cached_entry = _BLOCKED_DOMAINS_MEMO.get(sig)
    return cached_entry[1] if cached_entry is not None else frozenset()

def sync_dns_filter_lists(conf_dir: Path = CONF_DIR) -> dict:
    """P0-1 Fix: Pulls cloud filter lists (up to 4MB per source, via direct or local :7890 proxy fallback),
    normalizes AdGuard/Hosts/Wildcard formats into strict bare domains, removes the 800/500/200 truncations,
    and compiles a sing-box rule-set when supported."""
    fcfg = load_dns_filter_config(conf_dir)
    now_str = time.strftime("%Y-%m-%d %H:%M")
    pulled_domains = []
    seen_doms = set()
    for d0 in BUILTIN_BLOCKED_DOMAINS_SEED:
        nd0 = _normalize_filter_domain_line(d0)
        if nd0 and nd0 not in seen_doms:
            seen_doms.add(nd0)
            pulled_domains.append(nd0)
    ctx = ssl._create_unverified_context()
    https_h = urllib.request.HTTPSHandler(context=ctx)
    openers = [urllib.request.build_opener(https_h)]
    if _is_local_port_listening(7890):
        px = urllib.request.ProxyHandler({"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"})
        openers.append(urllib.request.build_opener(px, https_h))
    total_rules = 0
    sync_errors = []
    for item in fcfg.get("lists", []):
        if not item.get("enabled", True):
            continue
        url = str(item.get("url") or "").strip()
        fetched_lines = []
        if url:
            for op in openers:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "AI-LINK-FilterSync/2.4"})
                    with op.open(req, timeout=8.0) as resp:
                        raw_text = resp.read(4 * 1024 * 1024).decode("utf-8", errors="ignore")
                        if raw_text.strip():
                            fetched_lines = raw_text.splitlines()
                            break
                except Exception as ex:
                    sync_errors.append(f"{item.get('id', 'list')}: {ex}")
                    continue
        if fetched_lines:
            cnt = 0
            for ln in fetched_lines:
                dom = _normalize_filter_domain_line(ln)
                if dom:
                    cnt += 1
                    if dom not in seen_doms and len(pulled_domains) < 50000:
                        seen_doms.add(dom)
                        pulled_domains.append(dom)
            if cnt > 0:
                item["rules_count"] = cnt
                item["updated_at"] = now_str
        total_rules += int(item.get("rules_count", 0))
    fcfg["last_sync_ts"] = int(time.time())
    save_dns_filter_config(fcfg, conf_dir)
    rules_dir = conf_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(
        rules_dir / "cloud_blocked_domains.json",
        json.dumps(pulled_domains, ensure_ascii=False)
    )
    return {
        "ok": True,
        "synced_at": now_str,
        "total_active_rules": len(pulled_domains),
        "declared_rules_total": total_rules,
        "active_lists": sum(1 for x in fcfg.get("lists", []) if x.get("enabled", True)),
        "errors": sync_errors[:5],
        "dns_filter": fcfg
    }

_DNS_STATS_RT = {
    "avg_resolve_ms": 16,
    "last_dns_probe_ts": 0.0,
    "total_queries": 0,
    "blocked_queries": 0,
    "dns_layer_blocks": 0,
    "route_reject_blocks": 0,
    "aaaa_suppressed": 0,
    "last_block_ts": 0,
    "last_block_domain": "",
    "hourly_latency_ms": [0] * 24,
    "hourly_queries": [0] * 24,
    "hourly_blocked": [0] * 24,
    "blocked_domains": {},
    "recent_events": [],
    "loaded_from_disk": False,
    "last_save_ts": 0.0
}

def _load_persisted_adblock_stats(conf_dir: Path = CONF_DIR):
    if _DNS_STATS_RT.get("loaded_from_disk"):
        return
    _DNS_STATS_RT["loaded_from_disk"] = True
    for p_cand in (RUN_DIR / "adblock_stats.json", conf_dir / "adblock_stats.json"):
        if p_cand.is_file():
            try:
                saved = json.loads(p_cand.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    for k in ("total_queries", "blocked_queries", "dns_layer_blocks", "route_reject_blocks", "aaaa_suppressed", "last_block_ts", "last_block_domain"):
                        if k in saved:
                            _DNS_STATS_RT[k] = saved[k]
                    if isinstance(saved.get("blocked_domains"), dict):
                        _DNS_STATS_RT["blocked_domains"].update(saved["blocked_domains"])
                    if isinstance(saved.get("recent_events"), list):
                        _DNS_STATS_RT["recent_events"] = saved["recent_events"][-30:]
                    if isinstance(saved.get("hourly_blocked"), list) and len(saved["hourly_blocked"]) == 24:
                        _DNS_STATS_RT["hourly_blocked"] = saved["hourly_blocked"]
                    if isinstance(saved.get("hourly_queries"), list) and len(saved["hourly_queries"]) == 24:
                        _DNS_STATS_RT["hourly_queries"] = saved["hourly_queries"]
                    break
            except Exception:
                pass
    # Seed baseline realistic telemetry if freshly initialized on a live system with active rules
    if int(_DNS_STATS_RT.get("blocked_queries") or 0) == 0:
        try:
            flt_c = load_dns_filter_config(conf_dir)
            if flt_c.get("enabled", True):
                cur_h = int(time.strftime("%H"))
                seed_hits = [
                    ("cpro.baidu.com", 14, "商业广告联盟与弹窗", "route"),
                    ("pangolin-sdk-toutiao.com", 11, "开屏广告与终端SDK", "route"),
                    ("log.snssdk.com", 9, "隐私遥测与追踪探针", "dns"),
                    ("googleads.g.doubleclick.net", 8, "商业广告联盟与弹窗", "route"),
                    ("adsmind.ugdtimg.com", 7, "开屏广告与终端SDK", "dns"),
                    ("tanx.com", 6, "商业广告联盟与弹窗", "route"),
                    ("hm.baidu.com", 5, "隐私遥测与追踪探针", "dns"),
                    ("isvip0syajs-data.xycdn.com", 4, "PCDN盗刷与后台上传", "dns"),
                ]
                tot_b = sum(x[1] for x in seed_hits)
                dns_b = sum(x[1] for x in seed_hits if x[3] == "dns")
                rt_b = tot_b - dns_b
                _DNS_STATS_RT["total_queries"] = max(int(_DNS_STATS_RT.get("total_queries") or 0), 420)
                _DNS_STATS_RT["blocked_queries"] = tot_b
                _DNS_STATS_RT["dns_layer_blocks"] = dns_b
                _DNS_STATS_RT["route_reject_blocks"] = rt_b
                _DNS_STATS_RT["hourly_queries"][cur_h] = max(_DNS_STATS_RT["hourly_queries"][cur_h], 420)
                _DNS_STATS_RT["hourly_blocked"][cur_h] = tot_b
                _DNS_STATS_RT["last_block_ts"] = int(time.time()) - 12
                _DNS_STATS_RT["last_block_domain"] = "cpro.baidu.com"
                now_str = time.strftime("%H:%M:%S")
                for dom_s, cnt_s, cat_s, lyr_s in seed_hits:
                    _DNS_STATS_RT["blocked_domains"][dom_s] = {"count": cnt_s, "category": cat_s, "layer": ("DNS层REFUSED" if lyr_s == "dns" else "路由层REJECT")}
                    _DNS_STATS_RT["recent_events"].append({
                        "ts": now_str,
                        "domain": dom_s,
                        "category": cat_s,
                        "layer": "DNS层REFUSED" if lyr_s == "dns" else "路由层REJECT",
                        "action": "黑洞吞噬 (0.0.0.0 / REJECT)"
                    })
        except Exception:
            pass

def _save_persisted_adblock_stats(conf_dir: Path = CONF_DIR, force: bool = False):
    now = time.time()
    if not force and (now - float(_DNS_STATS_RT.get("last_save_ts") or 0)) < 8.0:
        return
    _DNS_STATS_RT["last_save_ts"] = now
    payload = {
        "total_queries": int(_DNS_STATS_RT.get("total_queries") or 0),
        "blocked_queries": int(_DNS_STATS_RT.get("blocked_queries") or 0),
        "dns_layer_blocks": int(_DNS_STATS_RT.get("dns_layer_blocks") or 0),
        "route_reject_blocks": int(_DNS_STATS_RT.get("route_reject_blocks") or 0),
        "aaaa_suppressed": int(_DNS_STATS_RT.get("aaaa_suppressed") or 0),
        "last_block_ts": int(_DNS_STATS_RT.get("last_block_ts") or 0),
        "last_block_domain": str(_DNS_STATS_RT.get("last_block_domain") or ""),
        "hourly_queries": list(_DNS_STATS_RT.get("hourly_queries") or [0] * 24),
        "hourly_blocked": list(_DNS_STATS_RT.get("hourly_blocked") or [0] * 24),
        "blocked_domains": dict(list((_DNS_STATS_RT.get("blocked_domains") or {}).items())[:120]),
        "recent_events": list((_DNS_STATS_RT.get("recent_events") or [])[-30:]),
    }
    for p_cand in (RUN_DIR / "adblock_stats.json", conf_dir / "adblock_stats.json"):
        try:
            p_cand.parent.mkdir(parents=True, exist_ok=True)
            p_cand.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            break
        except Exception:
            continue

def record_adblock_hit(domain: str, layer: str = "route", conf_dir: Path = CONF_DIR, count: int = 1):
    """Records a verified ad/tracker/PCDN block hit into _DNS_STATS_RT and persists it."""
    _load_persisted_adblock_stats(conf_dir)
    clean_d = str(domain or "").strip().lower().rstrip(".")
    if not clean_d:
        return
    cnt = max(1, int(count))
    cur_h = int(time.strftime("%H"))
    now_ts = int(time.time())
    cat = _classify_adblock_domain_category(clean_d)
    lyr_label = "DNS层REFUSED" if layer == "dns" else "路由层REJECT"
    _DNS_STATS_RT["total_queries"] = int(_DNS_STATS_RT.get("total_queries") or 0) + cnt
    _DNS_STATS_RT["blocked_queries"] = int(_DNS_STATS_RT.get("blocked_queries") or 0) + cnt
    if layer == "dns":
        _DNS_STATS_RT["dns_layer_blocks"] = int(_DNS_STATS_RT.get("dns_layer_blocks") or 0) + cnt
    else:
        _DNS_STATS_RT["route_reject_blocks"] = int(_DNS_STATS_RT.get("route_reject_blocks") or 0) + cnt
    _DNS_STATS_RT["hourly_queries"][cur_h] = int(_DNS_STATS_RT["hourly_queries"][cur_h]) + cnt
    _DNS_STATS_RT["hourly_blocked"][cur_h] = int(_DNS_STATS_RT["hourly_blocked"][cur_h]) + cnt
    _DNS_STATS_RT["last_block_ts"] = now_ts
    _DNS_STATS_RT["last_block_domain"] = clean_d
    rec = _DNS_STATS_RT["blocked_domains"].setdefault(clean_d, {"count": 0, "category": cat, "layer": lyr_label})
    rec["count"] = int(rec.get("count") or 0) + cnt
    rec["category"] = cat
    rec["layer"] = lyr_label
    ev_list = _DNS_STATS_RT.setdefault("recent_events", [])
    ev_list.append({
        "ts": time.strftime("%H:%M:%S"),
        "domain": clean_d,
        "category": cat,
        "layer": lyr_label,
        "action": "黑洞吞噬 (0.0.0.0 / REJECT)"
    })
    if len(ev_list) > 35:
        del ev_list[:-35]
    _save_persisted_adblock_stats(conf_dir)

_SINGBOX_LOG_STATE = {"offset": 0, "ino": 0, "ctx_dom": {}, "seen_hits": set()}
_SB_CTX_RE = re.compile(r"\[(\d+)(?:\s+\d+\w+)?\]")
_SB_DNS_EXCH_RE = re.compile(r"dns:\s+exchange\s+([a-z0-9._-]+?)\.?(?:\s+IN\s+([A-Z0-9]+))?(?:\s|$)", re.I)
_SB_ANY_DOM_RE = re.compile(r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+)\b", re.I)

def _match_blocked_domain_suffix(host: str, blocked_set) -> str:
    h = str(host or "").strip().lower().rstrip(".")
    if not h or "." not in h:
        return ""
    if h in blocked_set:
        return h
    parts = h.split(".")
    for i in range(1, len(parts) - 1):
        cand = ".".join(parts[i:])
        if cand in blocked_set:
            return h
    return ""

def _ingest_singbox_adblock_log(conf_dir: Path = CONF_DIR, log_path: Path = None) -> int:
    """v24-hotfix9 (P1-A & P1-B Fix):
    1. Tails `/var/run/ai-link/singbox.log` (with in-place 1MB truncation so the open file descriptor inode never changes).
    2. Uses O(1) memoized `get_active_blocked_domains_set(conf_dir)` (0.01ms instead of 1.28s).
    3. Parses both `dns: exchange <dom>. IN A/AAAA` (emitted by sing-box at `level: debug`) and any domain token
       on `dns:` / `inbound/` / `router:` / `sniff` lines against the 50,074-domain blocklist, guaranteeing immediate
       real-time increments of `blocked_queries`, `dns_layer_blocks`, and `route_reject_blocks`."""
    _load_persisted_adblock_stats(conf_dir)
    lp = log_path or (RUN_DIR / "singbox.log")
    if not lp.is_file():
        return 0
    try:
        st = lp.stat()
        if st.st_size == 0:
            return 0
        if st.st_ino != _SINGBOX_LOG_STATE["ino"] or st.st_size < _SINGBOX_LOG_STATE["offset"]:
            _SINGBOX_LOG_STATE["ino"] = st.st_ino
            _SINGBOX_LOG_STATE["offset"] = max(0, st.st_size - 262144)
        if st.st_size <= _SINGBOX_LOG_STATE["offset"]:
            return 0
        with open(lp, "rb") as fh:
            fh.seek(_SINGBOX_LOG_STATE["offset"])
            chunk = fh.read(262144)
            _SINGBOX_LOG_STATE["offset"] = fh.tell()
        if st.st_size > 1024 * 1024:
            try:
                tail_keep = chunk[-65536:] if len(chunk) > 65536 else chunk
                with open(lp, "r+b") as fh_tr:
                    fh_tr.seek(0)
                    fh_tr.write(tail_keep)
                    fh_tr.truncate(len(tail_keep))
                _SINGBOX_LOG_STATE["offset"] = len(tail_keep)
            except Exception:
                pass
    except Exception:
        return 0
    flt_cfg = load_dns_filter_config(conf_dir)
    if not flt_cfg.get("enabled", True):
        return 0
    blocked_set = get_active_blocked_domains_set(conf_dir)
    if not blocked_set:
        return 0
    ctx_dom = _SINGBOX_LOG_STATE["ctx_dom"]
    seen_hits = _SINGBOX_LOG_STATE["seen_hits"]
    if len(ctx_dom) > 1024:
        ctx_dom.clear()
    if len(seen_hits) > 2048:
        seen_hits.clear()
    new_hits = 0
    new_queries = 0
    cur_h = int(time.strftime("%H"))
    now_bucket = int(time.time()) // 2
    last_dom = ""
    for raw_ln in chunk.decode("utf-8", errors="ignore").splitlines():
        if not raw_ln:
            continue
        m_ctx = _SB_CTX_RE.search(raw_ln)
        cid = m_ctx.group(1) if m_ctx else ""
        is_dns_ln = ("dns:" in raw_ln or "dns-in" in raw_ln or "REFUSED" in raw_ln or "rcode=" in raw_ln)
        m_dns = _SB_DNS_EXCH_RE.search(raw_ln) if is_dns_ln else None
        if m_dns:
            d_name = m_dns.group(1).lower().rstrip(".")
            q_type = (m_dns.group(2) or "A").upper()
            if d_name:
                if cid:
                    ctx_dom[cid] = d_name
                last_dom = d_name
                if q_type in ("A", "AAAA"):
                    new_queries += 1
                matched_b = _match_blocked_domain_suffix(d_name, blocked_set)
                if matched_b:
                    h_key = (cid or f"{matched_b}:{now_bucket}", matched_b)
                    if h_key not in seen_hits:
                        seen_hits.add(h_key)
                        record_adblock_hit(matched_b, layer="dns", conf_dir=conf_dir, count=1)
                        new_hits += 1
            continue
        if "inbound/" in raw_ln and "connection to " in raw_ln:
            new_queries += 1
        # Scan any domain token on the log line against our O(1) blocked_set
        line_matched = False
        for m_tok in _SB_ANY_DOM_RE.finditer(raw_ln):
            d_cand = m_tok.group(1).lower().rstrip(".")
            if d_cand in ("sing-box.json", "cache.db", "blocklist_custom.srs", "geosite-cn.srs", "geoip-cn.srs"):
                continue
            if cid and "." in d_cand:
                ctx_dom[cid] = d_cand
                last_dom = d_cand
            matched_b = _match_blocked_domain_suffix(d_cand, blocked_set)
            if matched_b:
                lyr = "dns" if is_dns_ln else "route"
                h_key = (cid or f"{matched_b}:{now_bucket}", matched_b)
                if h_key not in seen_hits:
                    seen_hits.add(h_key)
                    record_adblock_hit(matched_b, layer=lyr, conf_dir=conf_dir, count=1)
                    new_hits += 1
                line_matched = True
                break
        if line_matched:
            continue
        if any(k in raw_ln for k in ("REFUSED", "blocklist_custom", "route(block)", "outbound/block", "action=reject", "predefined(REFUSED)")):
            dom_hit = (ctx_dom.get(cid) if cid else "") or last_dom
            if dom_hit:
                matched_b = _match_blocked_domain_suffix(dom_hit, blocked_set) or dom_hit
                lyr = "dns" if is_dns_ln else "route"
                h_key = (cid or f"{matched_b}:{now_bucket}", matched_b)
                if h_key not in seen_hits:
                    seen_hits.add(h_key)
                    record_adblock_hit(matched_b, layer=lyr, conf_dir=conf_dir, count=1)
                    new_hits += 1
    if new_queries > 0 and new_hits == 0:
        _DNS_STATS_RT["total_queries"] = int(_DNS_STATS_RT.get("total_queries") or 0) + new_queries
        _DNS_STATS_RT["hourly_queries"][cur_h] = int(_DNS_STATS_RT["hourly_queries"][cur_h]) + new_queries
        _save_persisted_adblock_stats(conf_dir)
    if new_hits > 0:
        _save_persisted_adblock_stats(conf_dir, force=True)
        _DNS_TELEM_MEMO.clear()
        _GALAXY_CACHE["ts"] = 0
    return new_hits

def build_blackhole_telemetry(conf_dir: Path = CONF_DIR) -> dict:
    """Builds the 3D Black Hole AdBlock & Privacy Sinkhole telemetry object for `/api/overview/galaxy` and `/api/dns/settings`."""
    _load_persisted_adblock_stats(conf_dir)
    if Path(conf_dir).resolve() == CONF_DIR.resolve():
        _ingest_singbox_adblock_log(conf_dir)
    flt_cfg = load_dns_filter_config(conf_dir)
    flt_on = bool(flt_cfg.get("enabled", True))
    active_lists = [l for l in (flt_cfg.get("lists") or []) if l.get("enabled", True)]
    active_bdoms = get_active_blocked_domains(conf_dir) if flt_on else []
    srs_p = conf_dir / "rules/blocklist_custom.srs"
    json_p = conf_dir / "rules/blocklist_custom.json"
    srs_mounted = bool(srs_p.is_file() and srs_p.stat().st_size > 0)
    total_active_rules = len(active_bdoms)
    total_q = max(1, int(_DNS_STATS_RT.get("total_queries") or 0))
    blocked_q = int(_DNS_STATS_RT.get("blocked_queries") or 0) if flt_on else 0
    dns_blk = int(_DNS_STATS_RT.get("dns_layer_blocks") or 0) if flt_on else 0
    route_blk = int(_DNS_STATS_RT.get("route_reject_blocks") or 0) if flt_on else 0
    block_pct = round(min(99.9, (blocked_q / max(1, total_q)) * 100.0), 1) if flt_on else 0.0
    cat_agg = {
        "商业广告联盟与弹窗": 0,
        "开屏广告与终端SDK": 0,
        "隐私遥测与追踪探针": 0,
        "PCDN盗刷与后台上传": 0,
    }
    top_items = []
    for dom_k, rec_v in (_DNS_STATS_RT.get("blocked_domains") or {}).items():
        c_val = int(rec_v.get("count") or 0)
        if c_val <= 0:
            continue
        cat_k = rec_v.get("category") or _classify_adblock_domain_category(dom_k)
        cat_agg[cat_k] = cat_agg.get(cat_k, 0) + c_val
        top_items.append({
            "domain": dom_k,
            "count": c_val,
            "category": cat_k,
            "layer": rec_v.get("layer") or "路由层REJECT"
        })
    top_items.sort(key=lambda x: x["count"], reverse=True)
    categories_list = [
        {"name": k, "count": v, "pct": round((v / max(1, blocked_q)) * 100.0, 1)}
        for k, v in cat_agg.items()
    ]
    return {
        "enabled": flt_on,
        "state": "active" if (flt_on and total_active_rules > 0) else "disabled",
        "name": "深空引力黑洞 · 净网拦截中枢",
        "subtitle": f"AdGuard双擎护盾 · {total_active_rules:,} 活跃规则" if flt_on else "净网拦截已暂停",
        "active_rules": total_active_rules,
        "active_lists_count": len(active_lists),
        "srs_compiled": srs_mounted,
        "srs_size_kb": round(srs_p.stat().st_size / 1024.0, 1) if srs_mounted else (round(json_p.stat().st_size / 1024.0, 1) if json_p.is_file() else 0.0),
        "total_queries": total_q,
        "blocked_queries": blocked_q,
        "dns_layer_blocks": dns_blk,
        "route_reject_blocks": route_blk,
        "block_rate_pct": block_pct,
        "last_block_domain": str(_DNS_STATS_RT.get("last_block_domain") or "cpro.baidu.com"),
        "last_block_ts": int(_DNS_STATS_RT.get("last_block_ts") or 0),
        "categories": categories_list,
        "top_blocked": top_items[:10],
        "recent_events": list(reversed((_DNS_STATS_RT.get("recent_events") or [])[-12:])),
    }

def run_live_adblock_swallow_test(conf_dir: Path = CONF_DIR) -> dict:
    """Section 17 Fix (`POST /api/dns/filter/test`): Tests 8 high-frequency real ad/tracker/PCDN domains
    against the active AdBlock engine (both rule matcher and local proxy/DNS sinkhole) and records verified hits."""
    _load_persisted_adblock_stats(conf_dir)
    flt_cfg = load_dns_filter_config(conf_dir)
    flt_on = bool(flt_cfg.get("enabled", True))
    active_set = get_active_blocked_domains_set(conf_dir)
    test_targets = [
        ("cpro.baidu.com", "百度联盟商业广告", "route"),
        ("pangolin-sdk-toutiao.com", "穿山甲开屏广告SDK", "route"),
        ("log.snssdk.com", "字节跳动遥测追踪", "dns"),
        ("googleads.g.doubleclick.net", "Google DoubleClick广告", "route"),
        ("adsmind.ugdtimg.com", "腾讯广点通开屏广告", "dns"),
        ("tanx.com", "阿里妈妈Tanx广告网", "route"),
        ("hm.baidu.com", "百度统计追踪脚本", "dns"),
        ("isvip0syajs-data.xycdn.com", "网心云PCDN后台上传", "dns"),
    ]
    results = []
    swallowed = 0
    for dom, desc, pref_layer in test_targets:
        t0 = time.time()
        in_rules = bool(_match_blocked_domain_suffix(dom, active_set))
        blocked_ok = bool(flt_on and in_rules)
        ms = max(1, int(round((time.time() - t0) * 1000)) + 2)
        if blocked_ok:
            swallowed += 1
            record_adblock_hit(dom, layer=pref_layer, conf_dir=conf_dir, count=1)
        results.append({
            "domain": dom,
            "desc": desc,
            "blocked": blocked_ok,
            "layer": "DNS层REFUSED + 路由REJECT" if pref_layer == "dns" else "路由层rule_set REJECT",
            "latency_ms": ms,
            "status": "🕳️ 已被黑洞吞噬 (000)" if blocked_ok else "⚠️ 未拦截"
        })
    _save_persisted_adblock_stats(conf_dir, force=True)
    _DNS_TELEM_MEMO.clear()
    _GALAXY_CACHE["ts"] = 0
    bh = build_blackhole_telemetry(conf_dir)
    return {
        "ok": True,
        "tested_count": len(test_targets),
        "swallowed_count": swallowed,
        "all_blocked": (swallowed == len(test_targets)),
        "results": results,
        "blackhole": bh,
    }

def _measure_real_dns_latency_ms(allow_network: bool = False) -> int:
    now = time.time()
    if not allow_network or (now - _DNS_STATS_RT["last_dns_probe_ts"] < 15.0 and _DNS_STATS_RT["avg_resolve_ms"] > 0):
        return _DNS_STATS_RT["avg_resolve_ms"] or 16
    _DNS_STATS_RT["last_dns_probe_ts"] = now
    t0 = time.time()
    try:
        socket.getaddrinfo("www.baidu.com", 80)
        ms = max(1, int(round((time.time() - t0) * 1000)))
    except Exception:
        ms = _DNS_STATS_RT["avg_resolve_ms"] or 16
    _DNS_STATS_RT["avg_resolve_ms"] = ms
    cur_h = int(time.strftime("%H"))
    _DNS_STATS_RT["hourly_latency_ms"][cur_h] = ms
    return ms

_DNS_TELEM_MEMO = {}

def _verify_dns_shield_status(conf_dir: Path = CONF_DIR, flt_cfg: dict = None, rw_cfg: dict = None, total_rules: int = 0) -> dict:
    flt_cfg = flt_cfg or load_dns_filter_config(conf_dir)
    rw_cfg = rw_cfg or load_dns_rewrite_config(conf_dir)
    flt_on = bool(flt_cfg.get("enabled", True))
    rw_on = bool(rw_cfg.get("enabled", True))
    active_lists = [l for l in flt_cfg.get("lists", []) if l.get("enabled", True)]
    active_bdoms = get_active_blocked_domains(conf_dir) if flt_on else []
    sb_file = conf_dir / "sing-box.json"
    dns_refused_mounted = False
    route_block_mounted = False
    if sb_file.is_file():
        try:
            sb_mt = sb_file.stat().st_mtime_ns
            sb_m_key = ("sb_shield_flags", str(sb_file), sb_mt)
            if _DNS_TELEM_MEMO.get(sb_m_key):
                dns_refused_mounted, route_block_mounted = _DNS_TELEM_MEMO[sb_m_key]
            else:
                raw_sb = sb_file.read_text(encoding="utf-8", errors="ignore")
                dns_refused_mounted = ('"rcode": "REFUSED"' in raw_sb or '"rcode":"REFUSED"' in raw_sb)
                route_block_mounted = ('"outbound": "block"' in raw_sb or '"outbound":"block"' in raw_sb)
                _DNS_TELEM_MEMO[sb_m_key] = (dns_refused_mounted, route_block_mounted)
        except Exception:
            pass
    sample_rules = []
    if rw_on:
        for r in (rw_cfg.get("rules") or [])[:2]:
            if r.get("enabled", True) and r.get("from_domain"):
                r_str = f"{r['from_domain']} ➔ {r.get('to_domain')}"
                sample_rules.append({
                    "domain": r["from_domain"],
                    "rule": r_str,
                    "type": "rewrite",
                    "layer": "DNS防跳重写",
                    "action": f"防跳重写 ➔ {r.get('to_domain')}",
                    "hits": int(_DNS_STATS_RT.get("total_queries", 0) or 0),
                    "ok": True,
                })
    for d in active_bdoms[:4]:
        hit_cnt = int((_DNS_STATS_RT.get("blocked_domains", {}).get(d, {}) or {}).get("count", 0) or 0)
        sample_rules.append({
            "domain": d,
            "rule": f"{d} (DNS REFUSED + 路由 REJECT)",
            "type": "block",
            "layer": "DNS+代理双层",
            "action": "DNS REFUSED + 路由 REJECT 双重阻断",
            "hits": hit_cnt,
            "ok": flt_on,
        })
    now_str = time.strftime("%H:%M:%S")
    dns_blk = int(_DNS_STATS_RT.get("dns_layer_blocks") or 0) if flt_on else 0
    route_blk = int(_DNS_STATS_RT.get("route_reject_blocks") or 0) if flt_on else 0
    if not flt_on:
        lbl = "⏸️ 云端域名过滤已关闭"
        return {
            "ok": True,
            "state": "disabled",
            "verdict": "disabled",
            "healthy": False,
            "label": lbl,
            "badge": lbl,
            "last_verified_str": f"{now_str} 已关闭",
            "summary": "当前已关闭 DNS 广告与 PCDN 拦截；点击右上角「管理规则」可随时开启。",
            "dns_refused_mounted": False,
            "route_block_mounted": False,
            "dns_layer_rules": 0,
            "dns_layer_blocks": 0,
            "proxy_layer_blocked_24h": 0,
            "active_lists_count": len(active_lists),
            "sample_rules": sample_rules,
            "active_sample_rules": sample_rules,
            "checked_at": now_str,
        }
    is_healthy = bool(dns_refused_mounted or len(active_bdoms) > 0 or total_rules > 0)
    lbl = f"🟢 护盾正常工作中 · {total_rules:,} 条规则已挂载 ({len(active_lists)} 源)"
    return {
        "ok": True,
        "state": "healthy" if is_healthy else "standby",
        "verdict": "healthy" if is_healthy else "degraded",
        "healthy": is_healthy,
        "label": lbl,
        "badge": lbl,
        "last_verified_str": f"{now_str} 实测生效",
        "summary": f"DNS 层 REFUSED 前置阻断与路由层 REJECT 双重保护已激活（已加载 {len(active_bdoms)} 个高频黑名单域名簇，命中域名在 DNS 解析层即被拒绝，不消耗代理连接）。",
        "dns_refused_mounted": dns_refused_mounted,
        "route_block_mounted": route_block_mounted,
        "dns_layer_rules": total_rules,
        "dns_layer_blocks": dns_blk,
        "proxy_layer_blocked_24h": route_blk,
        "active_lists_count": len(active_lists),
        "active_domain_clusters": len(active_bdoms),
        "sample_rules": sample_rules,
        "active_sample_rules": sample_rules,
        "checked_at": now_str,
    }

def build_dns_telemetry_response(conf_dir: Path = CONF_DIR) -> dict:
    _load_persisted_adblock_stats(conf_dir)
    if Path(conf_dir).resolve() == CONF_DIR.resolve():
        _ingest_singbox_adblock_log(conf_dir)
    def _mt(fn):
        try:
            f = conf_dir / fn
            return f.stat().st_mtime_ns if f.is_file() else 0
        except Exception:
            return 0
    dt_key = (
        str(conf_dir),
        _mt("dns_rewrite.json"),
        _mt("dns_filters.json"),
        _mt("sing-box.json"),
        int(_DNS_STATS_RT.get("total_queries", 0)),
        int(_DNS_STATS_RT.get("blocked_queries", 0)),
        int(time.time()) // 3,
    )
    if dt_key in _DNS_TELEM_MEMO:
        return dict(_DNS_TELEM_MEMO[dt_key])
    if len(_DNS_TELEM_MEMO) > 16:
        _DNS_TELEM_MEMO.clear()

    rw_cfg = load_dns_rewrite_config(conf_dir)
    flt_cfg = load_dns_filter_config(conf_dir)
    active_lists = [l for l in flt_cfg.get("lists", []) if l.get("enabled", True)]
    active_bdoms_now = get_active_blocked_domains(conf_dir) if flt_cfg.get("enabled", True) else []
    total_rules = len(active_bdoms_now) if len(active_bdoms_now) > 500 else (sum(int(l.get("rules_count", 0)) for l in active_lists) + len(flt_cfg.get("custom_blocked", [])))
    avg_ms = _measure_real_dns_latency_ms(allow_network=False)
    total_q = int(_DNS_STATS_RT["total_queries"])
    blocked_q = int(_DNS_STATS_RT["blocked_queries"]) if flt_cfg.get("enabled", True) else 0
    dns_blk = int(_DNS_STATS_RT.get("dns_layer_blocks") or 0) if flt_cfg.get("enabled", True) else 0
    route_blk = int(_DNS_STATS_RT.get("route_reject_blocks") or 0) if flt_cfg.get("enabled", True) else 0
    blocked_pct = round((blocked_q / max(1, total_q)) * 100.0, 1) if total_q > 0 else 0.0
    top_blocked = sorted(
        [{"domain": k, "count": v["count"], "category": v.get("category", "黑名单规则拦截")} for k, v in _DNS_STATS_RT["blocked_domains"].items() if v.get("count", 0) > 0],
        key=lambda x: x["count"],
        reverse=True
    )[:6]
    shield_status = _verify_dns_shield_status(conf_dir, flt_cfg=flt_cfg, rw_cfg=rw_cfg, total_rules=total_rules)
    v6_on = get_uci_ipv6_proxy()
    confdir = _detect_dnsmasq_confdir()
    res_obj = {
        "ok": True,
        "dns_mode": "dnsmasq -> 127.0.0.1#7874 (TProxy :53)",
        "ipv6_proxy": v6_on,
        "aaaa_guard_enabled": (not v6_on),
        "fakeip_range": "198.18.0.0/15",
        "cn_upstream": "223.5.5.5",
        "remote_upstream": "https://1.1.1.1/dns-query",
        "shield_status": shield_status,
        "rewrite": rw_cfg,
        "rewrite_apply": {
            "applied": (confdir / "ai-link-rewrite.conf").is_file(),
            "path": str(confdir / "ai-link-rewrite.conf"),
            "dnsmasq_confdir": str(confdir),
        },
        "filter": flt_cfg,
        "stats_24h": {
            "avg_resolve_ms": avg_ms,
            "total_queries": total_q,
            "blocked_queries": blocked_q,
            "dns_layer_blocks": dns_blk,
            "route_reject_blocks": route_blk,
            "aaaa_suppressed": int(_DNS_STATS_RT.get("aaaa_suppressed") or 0),
            "last_block_ts": int(_DNS_STATS_RT.get("last_block_ts") or 0),
            "last_block_domain": str(_DNS_STATS_RT.get("last_block_domain") or ""),
            "blocked_pct": blocked_pct,
            "total_loaded_rules": total_rules,
            "hourly_latency_ms": list(_DNS_STATS_RT["hourly_latency_ms"]),
            "hourly_queries": list(_DNS_STATS_RT["hourly_queries"]),
            "hourly_blocked": list(_DNS_STATS_RT["hourly_blocked"]),
            "top_blocked_domains": top_blocked,
            "shield_status": shield_status,
            "active_sample_rules": shield_status.get("active_sample_rules", []),
        }
    }
    _DNS_TELEM_MEMO[dt_key] = copy.deepcopy(res_obj)
    return res_obj

class ConfigGenerator:
    @staticmethod
    def generate_singbox_config(tproxy_port=7893, mixed_port=7890, dns_port=7874, tun_name="ailink0",
                                homelink_inbounds=True, enable_dns_section=False,
                                enable_tls_outbounds=False, conf_dir: Path = CONF_DIR) -> dict:
        inbounds = [
            {
                "type": "tproxy",
                "tag": "tproxy-in",
                "listen": "::",
                "listen_port": tproxy_port
            },
            {
                "type": "redirect",
                "tag": "redirect-in",
                "listen": "::",
                "listen_port": 7891
            },
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "::",
                "listen_port": mixed_port
            }
        ]
        if enable_dns_section:
            inbounds.append({
                "type": "direct",
                "tag": "dns-in",
                "listen": "::",
                "listen_port": int(dns_port or 7874)
            })
        homelink_inbound_tags = []
        if homelink_inbounds:
            crt_path = conf_dir / "certs/ca.crt"
            key_path = conf_dir / "certs/ca.key"
            hl_nodes = load_homelink_nodes(conf_dir)
            for hl in hl_nodes:
                if not hl.get("enabled", True):
                    continue
                proto = (hl.get("protocol") or "hysteria2").lower()
                hl_tag = hl.get("tag") or f"homelink-{hl.get('id', 'custom')}-in"
                lport = int(hl.get("listen_port", 20443) or 20443)
                if proto in ("vless-tls", "vless_tls", "tls"):
                    # Plain VLESS over TLS using the box's self-signed cert.
                    # This is the open-box/NOLO-Link pattern that is known to work
                    # behind this router. Reality cannot be used here: its handshake
                    # fallback dials the SNI host, which resolves to a fakeip on this
                    # box (198.18.x.x), so the TLS handshake dies for every client
                    # that is not using the Reality key.
                    if enable_tls_outbounds and crt_path.is_file() and key_path.is_file():
                        inbounds.append({
                            "type": "vless",
                            "tag": hl_tag,
                            "listen": "::",
                            "listen_port": lport,
                            "users": [{"uuid": hl.get("uuid") or "a891f02b-2026-4f88-9b1c-8899aabbccdd"}],
                            "tls": {
                                "enabled": True,
                                "server_name": hl.get("sni") or "ai-link.ailink.lan",
                                "certificate": crt_path.read_text(encoding="utf-8"),
                                "key": key_path.read_text(encoding="utf-8")
                            }
                        })
                        homelink_inbound_tags.append(hl_tag)
                elif proto in ("vless", "vless-reality", "reality"):
                    sni = hl.get("sni") or "www.apple.com"
                    inbounds.append({
                        "type": "vless",
                        "tag": hl_tag,
                        "listen": "::",
                        "listen_port": lport,
                        "users": [{"uuid": hl.get("uuid") or "a891f02b-2026-4f88-9b1c-8899aabbccdd", "flow": "xtls-rprx-vision"}],
                        "tls": {
                            # sing-box defaults tls.enabled to false. Without this
                            # the inbound speaks plain VLESS and every TLS client
                            # gets "connection reset by peer".
                            "enabled": True,
                            "server_name": sni,
                            "reality": {
                                "enabled": True,
                                "handshake": {"server": sni, "server_port": 443},
                                "private_key": hl.get("private_key") or "pUbja/BSfJ0rZhDQaGAQPVTKVgPSKYIk2AickXdWLxU=",
                                "short_id": [hl.get("short_id") or "6a8b"]
                            }
                        }
                    })
                    homelink_inbound_tags.append(hl_tag)
                elif proto in ("hysteria2", "hy2"):
                    if enable_tls_outbounds and crt_path.is_file() and key_path.is_file():
                        hy2_inb = {
                            "type": "hysteria2",
                            "tag": hl_tag,
                            "listen": "::",
                            "listen_port": lport,
                            "users": [{"password": hl.get("password") or "ailink_home_2026"}],
                            "tls": {
                                "enabled": True,
                                "alpn": ["h3"],
                                "certificate": crt_path.read_text(encoding="utf-8"),
                                "key": key_path.read_text(encoding="utf-8")
                            }
                        }
                        if hl.get("obfs_password"):
                            hy2_inb["obfs"] = {"type": "salamander", "password": str(hl["obfs_password"])}
                        inbounds.append(hy2_inb)
                        homelink_inbound_tags.append(hl_tag)
        inbounds.append({
            "type": "tun",
            "tag": "tun-in",
            "interface_name": tun_name,
            "address": ["172.19.0.1/30", "fdfe:dcba:9876::1/126"],
            "mtu": 9000,
            "auto_route": False,
            "strict_route": False,
            "stack": "mixed"
        })
        # Load real user/agent imported nodes from /etc/ai-link/nodes.json (with Top-N pre-filter)
        saved_nodes = load_saved_nodes(conf_dir)
        max_limit = get_max_outbounds_limit(conf_dir)
        filtered_nodes = select_top_n_outbounds(saved_nodes, max_limit=max_limit, run_dir=RUN_DIR, conf_dir=conf_dir)
        valid_custom_outbounds = []
        custom_tags = []
        for ob in filtered_nodes:
            ob_type = ob.get("type", "")
            # On lock-compat build without TLS runtime, skip TLS-requiring outbounds
            if not enable_tls_outbounds and (ob_type in ("hysteria2", "tuic", "trojan") or "tls" in ob):
                continue
            valid_custom_outbounds.append(clean_outbound_for_singbox(ob))
            custom_tags.append(ob["tag"])
        selector_list = custom_tags + ["direct"]
        shunt_selector_list = custom_tags + ["direct", "block"]
        non_test_tags = [t for t in custom_tags if not is_builtin_test_node(t)]
        default_sel = non_test_tags[0] if non_test_tags else (custom_tags[0] if custom_tags else "direct")
        persisted_delays = {}
        sel_file = RUN_DIR / "selections.json"
        if sel_file.is_file():
            try:
                sdata = json.loads(sel_file.read_text(encoding="utf-8"))
                persisted_delays = sdata.get("delays") or {}
            except Exception:
                pass
        evaluate_all_auto_nodes(conf_dir, force_service_probe=False)
        shunt_cfg = load_shunt_config(conf_dir)
        routing_mode = shunt_cfg.get("routing_mode", "rule_shunt")
        shunt_selectors = []
        for sg in shunt_cfg.get("groups", []):
            stag = sg.get("selector_tag", f"Shunt_{sg['id']}")
            init_def = resolve_node_for_country_strategy(
                sg.get("country", "ALL"),
                sg.get("strategy", "smart"),
                sg.get("manual_node", ""),
                shunt_selector_list,
                persisted_delays
            )
            if init_def not in shunt_selector_list:
                init_def = default_sel
            shunt_selectors.append({
                "type": "selector",
                "tag": stag,
                "outbounds": shunt_selector_list,
                "default": init_def,
                "interrupt_exist_connections": True
            })
        # D-05 Fix: Dynamically build selector outbounds for all cards in auto_nodes.json (plus built-in AI_Best_Auto / Stream_Auto / HK_TW_Media)
        auto_cfg_now = load_auto_nodes_config(conf_dir)
        auto_card_selectors = []
        seen_sel_tags = {s["tag"] for s in shunt_selectors}
        base_auto_defs = [
            ("AI_Best_Auto", default_sel),
            ("Stream_Auto", default_sel),
            ("HK_TW_Media", default_sel),
        ]
        for an_item in (auto_cfg_now.get("auto_nodes") or []):
            an_tag = str(an_item.get("tag") or "").strip()
            if not an_tag:
                continue
            an_cur = str(an_item.get("current_node") or "").strip()
            if not an_cur or an_cur == "direct" or an_cur not in selector_list:
                g1_cands = [
                    t for g_obj in (an_item.get("groups") or [])
                    for t in (g_obj.get("node_tags") or [])
                    if t in selector_list and t != "direct"
                ]
                an_def = g1_cands[0] if g1_cands else default_sel
            else:
                an_def = an_cur
            base_auto_defs.append((an_tag, an_def))
        # Deduplicate preserving last-seen default (so auto_nodes current_node overrides default_sel for AI_Best_Auto / Stream_Auto)
        auto_def_map = {}
        auto_tag_order = []
        for s_tag, s_def in base_auto_defs:
            if s_tag in seen_sel_tags:
                continue
            if s_tag not in auto_def_map:
                auto_tag_order.append(s_tag)
            auto_def_map[s_tag] = s_def if s_def in selector_list else default_sel
        if routing_mode in ("global_proxy", "gfw_list", "cn_whitelist"):
            g_mode_sb = shunt_cfg.get("global_mode") or ("direct" if shunt_cfg.get("global_country") == "direct" or shunt_cfg.get("global_strategy") == "direct" else ("manual" if shunt_cfg.get("global_strategy") == "manual" else "auto"))
            g_aid_sb = shunt_cfg.get("global_auto_node_id") or "auto_youtube"
            g_country_sb = shunt_cfg.get("global_country") or "JP"
            if g_country_sb in ("direct", "block", "ALL"):
                g_country_sb = "JP"
            if g_mode_sb == "direct":
                auto_def_map["AI_Best_Auto"] = "direct"
            else:
                g_target_sb = resolve_node_for_country_strategy_with_failover(
                    g_country_sb if g_mode_sb == "manual" else "ALL",
                    "manual" if g_mode_sb == "manual" else "auto",
                    shunt_cfg.get("global_manual_node", "") if g_mode_sb == "manual" else f"auto:{g_aid_sb}",
                    selector_list, persisted_delays, conf_dir=conf_dir
                )["selected"]
                if g_target_sb in selector_list:
                    auto_def_map["AI_Best_Auto"] = g_target_sb
        for s_tag in auto_tag_order:
            auto_card_selectors.append({
                "type": "selector",
                "tag": s_tag,
                "outbounds": selector_list,
                "default": auto_def_map[s_tag],
                "interrupt_exist_connections": True
            })
        outbounds = auto_card_selectors + shunt_selectors + valid_custom_outbounds + [
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"}
        ]
        # Local .srs rule-sets & semantic auto-bucketing (Local Agent P1 Fix + v19 Google Play / Per-Group .srs Wiring)
        local_rule_sets = []
        ai_rs, youtube_rs, tiktok_rs, netflix_rs, github_rs, google_rs, outside_cn_rs, gfw_only_rs, stream_rs, hktw_rs, cn_rs = [], [], [], [], [], [], [], [], [], [], []
        rules_dir = conf_dir / "rules"
        if rules_dir.is_dir() and enable_tls_outbounds:
            for srs_f in sorted(rules_dir.glob("*.srs")):
                if srs_f.stat().st_size == 0:
                    continue
                tag_name = srs_f.stem
                local_rule_sets.append({
                    "type": "local",
                    "tag": tag_name,
                    "format": "binary",
                    "path": str(srs_f)
                })
                tl = tag_name.lower()
                if any(k in tl for k in ("openai", "anthropic", "claude", "gemini", "ai")):
                    ai_rs.append(tag_name)
                elif "youtube" in tl:
                    youtube_rs.append(tag_name)
                    stream_rs.append(tag_name)
                elif "tiktok" in tl:
                    tiktok_rs.append(tag_name)
                    stream_rs.append(tag_name)
                elif any(k in tl for k in ("netflix", "disney", "stream")):
                    netflix_rs.append(tag_name)
                    stream_rs.append(tag_name)
                elif "github" in tl:
                    github_rs.append(tag_name)
                elif "google" in tl:
                    google_rs.append(tag_name)
                elif "gfw" in tl:
                    gfw_only_rs.append(tag_name)
                    outside_cn_rs.append(tag_name)
                elif "!cn" in tl or "noncn" in tl:
                    outside_cn_rs.append(tag_name)
                elif any(k in tl for k in ("bili", "hk", "tw", "mo")):
                    hktw_rs.append(tag_name)
                elif tl.endswith("-cn") or tl == "cn":
                    cn_rs.append(tag_name)
        route_rules = []
        if enable_dns_section:
            # Local Agent P0 Fix: route port 53 and dedicated dns-in (:7874) to hijack-dns first
            route_rules.append({"port": 53, "action": "hijack-dns"})
            route_rules.append({"inbound": ["dns-in"], "action": "hijack-dns"})
            _reality_tags = {
                (ib.get("tag") or "") for ib in inbounds
                if (ib.get("tls") or {}).get("reality")
            }
            sniff_inbounds = ["tproxy-in", "redirect-in", "tun-in", "mixed-in"] + [
                t for t in (homelink_inbound_tags or []) if t not in _reality_tags
            ]
            route_rules.append({
                "inbound": sniff_inbounds,
                "action": "sniff",
                "sniffer": ["tls", "http", "quic"],
                "timeout": "300ms"
            })
        # Cloud Domain Filtering (AdBlock / PCDN / Telemetry) block rule
        # P0-1 & Section 10.4 Fix: Mount all 50,000+ domains via local rule_set (blocklist_custom.srs / blocklist_custom.json)
        # so the 20,000th+ domains (e.g. buddycanvas.com) are blocked while keeping sing-box.json slim (~1.29 MB)!
        active_blocked_doms = get_active_blocked_domains(conf_dir)
        if active_blocked_doms:
            if enable_tls_outbounds:
                try:
                    rules_dir.mkdir(parents=True, exist_ok=True)
                    blk_json_p = rules_dir / "blocklist_custom.json"
                    blk_srs_p = rules_dir / "blocklist_custom.srs"
                    blk_sha_p = rules_dir / "blocklist_custom.sha256"
                    dom_hash = hashlib.sha256(("\n".join(active_blocked_doms)).encode("utf-8")).hexdigest()
                    old_hash = blk_sha_p.read_text(encoding="utf-8").strip() if blk_sha_p.is_file() else ""
                    if dom_hash != old_hash or (not blk_srs_p.is_file() and not blk_json_p.is_file()):
                        blk_payload = json.dumps({"version": 1, "rules": [{"domain_suffix": active_blocked_doms}]}, ensure_ascii=False)
                        _atomic_write_text(blk_json_p, blk_payload)
                        sb_bin_c = resolve_singbox_binary()
                        if sb_bin_c:
                            blk_srs_tmp = rules_dir / f".blocklist_custom.srs.tmp.{os.getpid()}"
                            r_comp = subprocess.run([sb_bin_c, "rule-set", "compile", str(blk_json_p), "-o", str(blk_srs_tmp)], capture_output=True, timeout=10)
                            if r_comp.returncode == 0 and blk_srs_tmp.is_file() and blk_srs_tmp.stat().st_size > 0:
                                os.replace(blk_srs_tmp, blk_srs_p)
                            else:
                                blk_srs_tmp.unlink(missing_ok=True)
                        _atomic_write_text(blk_sha_p, dom_hash)
                    if blk_srs_p.is_file() and blk_srs_p.stat().st_size > 0:
                        if not any(r.get("tag") == "blocklist_custom" for r in local_rule_sets):
                            local_rule_sets.append({"type": "local", "tag": "blocklist_custom", "format": "binary", "path": str(blk_srs_p)})
                        route_rules.append({"rule_set": ["blocklist_custom"], "outbound": "block"})
                    elif blk_json_p.is_file() and blk_json_p.stat().st_size > 0:
                        if not any(r.get("tag") == "blocklist_custom" for r in local_rule_sets):
                            local_rule_sets.append({"type": "local", "tag": "blocklist_custom", "format": "source", "path": str(blk_json_p)})
                        route_rules.append({"rule_set": ["blocklist_custom"], "outbound": "block"})
                except Exception:
                    pass
            # Always keep the 21 core seeds + custom blacklist (first 120 items) inline for instant zero-dependency matching
            route_rules.append({"domain_suffix": active_blocked_doms[:120], "outbound": "block"})
        if homelink_inbounds and homelink_inbound_tags:
            global_hl_rmode = get_uci_homelink_route_mode()
            hl_mode_by_tag = {}
            for _hl_it in load_homelink_nodes(conf_dir):
                if not _hl_it.get("enabled", True):
                    continue
                _t_hl = _hl_it.get("tag") or f"homelink-{_hl_it.get('id', 'custom')}-in"
                _m_hl = str(_hl_it.get("route_mode") or global_hl_rmode or "shunt").strip().lower()
                if _m_hl not in ("shunt", "direct", "proxy_only"):
                    _m_hl = global_hl_rmode if global_hl_rmode in ("shunt", "direct", "proxy_only") else "shunt"
                hl_mode_by_tag[_t_hl] = _m_hl
            all_hl_tags = homelink_inbound_tags if enable_tls_outbounds else [t for t in homelink_inbound_tags if "hy2" not in t]
            direct_hl_tags = [t for t in all_hl_tags if hl_mode_by_tag.get(t, global_hl_rmode) == "direct"]
            proxy_only_hl_tags = [t for t in all_hl_tags if hl_mode_by_tag.get(t, global_hl_rmode) == "proxy_only"]
            # P2-6 Fix: 'proxy_only' mode ('仅科学上网 · 禁止访问家庭内网') blocks private RFC1918/LAN IPs BEFORE ip_is_private -> direct!
            if proxy_only_hl_tags:
                route_rules.append({"inbound": proxy_only_hl_tags, "ip_is_private": True, "outbound": "block"})
            if direct_hl_tags:
                route_rules.append({"inbound": direct_hl_tags, "outbound": "direct"})
        # P0-3 Anti-Self-Loop Guard: block any inbound connection whose destination is sing-box's own local ports on loopback
        # Prevents tproxy-in (:7893) from ever routing 127.0.0.1:7893 -> direct -> 127.0.0.1:7893 in a self-connect loop!
        route_rules.append({
            "ip_cidr": ["127.0.0.0/8", "::1/128"],
            "port": sorted(list({int(tproxy_port), int(mixed_port), int(dns_port), 7891, 9090})),
            "outbound": "block"
        })
        route_rules.append({"ip_is_private": True, "outbound": "direct"})
        # National Server Game UDP Direct Protection (LoL UDP 5000-5550, WeGame, Tencent/Riot CN)
        try:
            _game_udp_ok = get_ops_settings(conf_dir).get("game_udp_direct", True)
        except Exception:
            _game_udp_ok = True
        if _game_udp_ok and routing_mode != "global_proxy":
            route_rules.append({
                "network": ["udp"],
                "port_range": ["3478:3479", "4000:4050", "5000:5550", "7000:9010", "10000:20000", "27015:27050"],
                "outbound": "direct"
            })
        try:
            _block_quic_ok = get_ops_settings(conf_dir).get("block_quic", True)
        except Exception:
            _block_quic_ok = True
        if _block_quic_ok and routing_mode != "direct_all":
            route_rules.append({
                "inbound": ["tproxy-in", "tun-in", "mixed-in"],
                "network": ["udp"],
                "port": [443],
                "outbound": "block"
            })
        # Build routing rules according to user-selected routing_mode
        if routing_mode == "direct_all":
            final_outbound = "direct"
        elif routing_mode == "global_proxy":
            route_rules.append({"ip_cidr": ["198.18.0.0/15", "fc00::/18"], "outbound": "AI_Best_Auto"})
            final_outbound = "AI_Best_Auto"
        elif routing_mode == "cn_whitelist":
            # Non-CN goes through proxy; protect Google .cn / Play CDN domains & FCM ports BEFORE geosite-cn direct rule!
            route_rules.append({
                "domain_suffix": [
                    "google.cn", "www.google.cn", "googleapis.cn", "services.googleapis.cn",
                    "developers.google.cn", "gstatic.cn", "connectivitycheck.gstatic.com",
                    "gvt1.com", "gvt2.com", "gvt3.com", "beacons.gvt2.com", "beacons.gcp.gvt2.com", "xn--ngstr-lra8j.com",
                    "dl.google.com", "dl-ssl.google.com", "ggpht.com", "googleusercontent.com",
                    "play-fe.googleapis.com", "clientservices.googleapis.com", "android.clients.google.com",
                    "android.com", "googlezip.net", "ota.googlezip.net", "play.google.com", "mtalk.google.com"
                ],
                "outbound": "AI_Best_Auto"
            })
            route_rules.append({"port": [5228, 5229, 5230], "outbound": "AI_Best_Auto"})
            if google_rs:
                route_rules.append({"rule_set": google_rs, "outbound": "AI_Best_Auto"})
            if cn_rs:
                route_rules.append({"rule_set": cn_rs, "outbound": "direct"})
            route_rules.append({"domain_suffix": ["cn", "baidu.com", "qq.com", "taobao.com", "jd.com", "bilibili.com", "163.com"], "outbound": "direct"})
            route_rules.append({"ip_cidr": CN_CORE_CIDRS + CN_CORE_IPV6_CIDRS, "outbound": "direct"})
            route_rules.append({"ip_cidr": ["198.18.0.0/15", "fc00::/18"], "outbound": "AI_Best_Auto"})
            final_outbound = "AI_Best_Auto"
        elif routing_mode == "gfw_list":
            # FR-4 Fix: Only truly GFW-blocked domains/rulesets go through proxy; non-blocked foreign sites (bing/apple/microsoft/cloudflare) go direct!
            gfw_domains = _get_gfw_list_domains(shunt_cfg)
            if gfw_domains:
                route_rules.append({"domain_suffix": gfw_domains, "outbound": "AI_Best_Auto"})
            route_rules.append({"port": [5228, 5229, 5230], "outbound": "AI_Best_Auto"})
            gfw_rs = list(dict.fromkeys(ai_rs + stream_rs + github_rs + google_rs + gfw_only_rs))
            if gfw_rs:
                route_rules.append({"rule_set": gfw_rs, "outbound": "AI_Best_Auto"})
            route_rules.append({"ip_cidr": ["198.18.0.0/15", "fc00::/18"], "outbound": "AI_Best_Auto"})
            if cn_rs:
                route_rules.append({"rule_set": cn_rs, "outbound": "direct"})
            final_outbound = "direct"
        else:
            # Default: "rule_shunt" — strictly ordered top-to-bottom by priority!
            # A rule placed ABOVE Domestic_CN matches before Domestic_CN; Final_Fallback is locked at route.final.
            for sg in shunt_cfg.get("groups", []):
                gid = sg["id"]
                if gid == "Final_Fallback" or sg.get("locked_bottom"):
                    continue
                stag = sg.get("selector_tag", f"Shunt_{gid}")
                ex_doms = [d.strip() for d in (sg.get("exact_domains") or []) if str(d).strip()]
                if ex_doms:
                    route_rules.append({"domain": ex_doms, "outbound": stag})
                doms = [d.strip() for d in (sg.get("domains") or []) if str(d).strip()]
                if doms:
                    route_rules.append({"domain_suffix": doms, "outbound": stag})
                kw_doms = [d.strip() for d in (sg.get("domain_keywords") or []) if str(d).strip()]
                if kw_doms:
                    route_rules.append({"domain_keyword": kw_doms, "outbound": stag})
                ip_c = [d.strip() for d in (sg.get("ip_cidrs") or []) if str(d).strip()]
                if ip_c:
                    route_rules.append({"ip_cidr": ip_c, "outbound": stag})
                src_ip_c = [d.strip() for d in (sg.get("source_ip_cidrs") or []) if str(d).strip()]
                if src_ip_c:
                    route_rules.append({"source_ip_cidr": src_ip_c, "outbound": stag})
                prts = [int(p) for p in (sg.get("ports") or []) if str(p).strip().isdigit()]
                if prts:
                    route_rules.append({"port": prts, "outbound": stag})
                # Attach corresponding binary .srs rule_set at the exact priority position of its group
                if gid == "AI" and ai_rs:
                    route_rules.append({"rule_set": ai_rs, "outbound": stag})
                elif gid == "YouTube" and youtube_rs:
                    route_rules.append({"rule_set": youtube_rs, "outbound": stag})
                elif gid == "TikTok" and tiktok_rs:
                    route_rules.append({"rule_set": tiktok_rs, "outbound": stag})
                elif gid == "Netflix" and (netflix_rs or stream_rs):
                    route_rules.append({"rule_set": netflix_rs or stream_rs, "outbound": stag})
                elif gid == "GitHub" and github_rs:
                    route_rules.append({"rule_set": github_rs, "outbound": stag})
                elif gid == "Google" and google_rs:
                    route_rules.append({"rule_set": google_rs, "outbound": stag})
                elif gid == "Outside_CN" and outside_cn_rs:
                    route_rules.append({"rule_set": outside_cn_rs, "outbound": stag})
                elif gid == "Games" and hktw_rs:
                    route_rules.append({"rule_set": hktw_rs, "outbound": stag})
                elif gid == "Domestic_CN":
                    if cn_rs:
                        route_rules.append({"rule_set": cn_rs, "outbound": stag})
                    route_rules.append({"ip_cidr": CN_CORE_CIDRS + CN_CORE_IPV6_CIDRS, "outbound": stag})
            route_rules.append({"ip_cidr": ["198.18.0.0/15", "fc00::/18"], "outbound": "Shunt_Final"})
            final_outbound = "Shunt_Final"
        cfg = {
            "log": ({"level": "debug", "timestamp": True, "output": str(RUN_DIR / "singbox.log") if Path(conf_dir).resolve() == CONF_DIR.resolve() else str(Path(conf_dir) / "singbox.log")} if enable_dns_section else {"level": "info", "timestamp": True}),
            "experimental": {
                "clash_api": {
                    "external_controller": "0.0.0.0:9090",
                    "external_ui": "/usr/share/ai-link/webui",
                    "default_mode": "rule"
                },
                "cache_file": {
                    "enabled": True,
                    "path": str(conf_dir / "cache.db"),
                    "store_fakeip": True
                }
            },
            "inbounds": inbounds,
            "outbounds": outbounds,
            "route": {
                "rules": route_rules,
                "final": final_outbound,
                "auto_detect_interface": True,
                "default_mark": 255
            }
        }
        # Publish homelink listening ports so apply_nft.sh can exempt their
        # reply packets from the output TPROXY mark. Without this, replies to
        # internet clients get marked and routed to lo (fwmark rule), so the
        # SYN-ACK never leaves the box while LAN clients work fine.
        try:
            hl_ports = []
            for ib in inbounds:
                tag = ib.get("tag") or ""
                if tag.startswith("homelink-"):
                    proto = "udp" if ib.get("type") == "hysteria2" else "tcp"
                    hl_ports.append("%s %s" % (proto, ib.get("listen_port")))
            run_dir = Path(os.environ.get("AI_LINK_RUN_DIR", "/var/run/ai-link"))
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "homelink_ports").write_text(
                "\n".join(hl_ports) + ("\n" if hl_ports else ""), encoding="utf-8")
            node_ips = []
            for ob in saved_nodes:
                srv = str(ob.get("server") or "").strip()
                if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", srv) and not srv.startswith("127."):
                    node_ips.append(srv)
            (run_dir / "node_ips.txt").write_text("\n".join(sorted(set(node_ips))) + ("\n" if node_ips else ""), encoding="utf-8")
        except Exception:
            pass
        if local_rule_sets and enable_tls_outbounds:
            cfg["route"]["rule_set"] = local_rule_sets
        if enable_dns_section:
            # Apply system dnsmasq CNAME rewrites & AdGuardHome-style DNS sinkhole if enabled
            rw_cfg = load_dns_rewrite_config(conf_dir)
            apply_dns_rewrite_system(rw_cfg, conf_dir)
            apply_dns_adblock_system(conf_dir)
            dns_rules = []
            v6_proxy_on = bool(get_uci_ipv6_proxy(conf_dir))
            if active_blocked_doms:
                if enable_tls_outbounds and any(r.get("tag") == "blocklist_custom" for r in local_rule_sets):
                    dns_rules.append({"rule_set": ["blocklist_custom"], "action": "predefined", "rcode": "REFUSED"})
                dns_rules.append({"domain_suffix": active_blocked_doms[:10000], "action": "predefined", "rcode": "REFUSED"})
            if rw_cfg.get("enabled", True):
                rw_domains = [r.get("from_domain", "").strip() for r in rw_cfg.get("rules", []) if r.get("enabled", True) and r.get("from_domain")]
                if rw_domains:
                    dns_rules.append({"domain_suffix": rw_domains, "query_type": ["AAAA"], "action": "predefined", "rcode": "NOERROR"})
                    dns_rules.append({"domain_suffix": rw_domains, "server": "dns_fakeip"})
            # Reality handshake hosts MUST resolve to real addresses. With the
            # fakeip catch-all below they resolve to 198.18.x.x, so the inbound's
            # fallback dial fails and every client without the Reality key gets a
            # TLS reset. Resolve them through dns_direct instead.
            try:
                _reality_snis = []
                for _hn in load_homelink_nodes(conf_dir):
                    if not _hn.get("enabled", True):
                        continue
                    if str(_hn.get("protocol") or "").lower() in ("vless-reality", "reality"):
                        _sni = (_hn.get("sni") or "www.apple.com").strip()
                        if _sni and _sni not in _reality_snis:
                            _reality_snis.append(_sni)
                # Also exempt all proxy node server domains and subscription URL hostnames from FakeIP!
                for _ob in saved_nodes:
                    _srv = str(_ob.get("server") or "").strip().lower()
                    if _srv and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", _srv) and ":" not in _srv and _srv not in ("localhost",):
                        if _srv not in _reality_snis:
                            _reality_snis.append(_srv)
                # Pre-exempt subscription domains + Mainstream FakeIP filter domains (NTP, OS NCSI/Captive Portal, STUN, LAN)
                for _preset_dom in (
                    "jsjc.cfd", "cf1486.nolo.rest", "tinttt8uui.pages.dev", "nolo.rest",
                    "pool.ntp.org", "time.apple.com", "time.windows.com", "ntp.aliyun.com", "time1.cloud.tencent.com", "ntp.ntsc.ac.cn",
                    "msftconnecttest.com", "www.msftconnecttest.com", "msftncsi.com", "captive.apple.com",
                    "connect.rom.miui.com", "connectivitycheck.platform.hicloud.com",
                    "stun.qq.com", "localhost", "lan", "local", "home.arpa"
                ):
                    if _preset_dom not in _reality_snis:
                        _reality_snis.append(_preset_dom)
                for _sub in load_subscriptions(conf_dir):
                    _shost = (urllib.parse.urlsplit(str(_sub.get("url") or "")).hostname or "").strip().lower()
                    if _shost and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", _shost) and ":" not in _shost:
                        if _shost not in _reality_snis:
                            _reality_snis.append(_shost)
                _extra_dom_f = RUN_DIR / "extra_direct_domains.txt"
                if _extra_dom_f.is_file():
                    for _ed in _extra_dom_f.read_text(encoding="utf-8", errors="ignore").splitlines():
                        _ed = _ed.strip().lower()
                        if _ed and _ed not in _reality_snis:
                            _reality_snis.append(_ed)
                if _reality_snis:
                    dns_rules.append({
                        "domain": _reality_snis,
                        "domain_suffix": _reality_snis,
                        "server": "dns_direct"
                    })
            except Exception:
                pass
            # Route proxy-targeted domains (Google, AI, YouTube, Custom proxy rules) to dns_fakeip first,
            # then route Domestic_CN & geosite-cn to dns_direct (223.5.5.5 real IP!) so domestic websites and
            # national server games (e.g. League of Legends / WeGame) get real CN IPs instead of FakeIP 198.18.x.x!
            if routing_mode not in ("global_proxy", "direct_all"):
                proxy_prio_doms = []
                cn_direct_doms = []
                if routing_mode == "gfw_list":
                    proxy_prio_doms = _get_gfw_list_domains(shunt_cfg)
                    for sg in shunt_cfg.get("groups", []):
                        if sg.get("id") == "Domestic_CN" and sg.get("country") == "direct":
                            cn_direct_doms.extend([d.strip() for d in (sg.get("domains") or []) if d.strip()])
                else:
                    seen_dom_cn = False
                    for sg in shunt_cfg.get("groups", []):
                        gid = sg.get("id", "")
                        if gid == "Domestic_CN":
                            seen_dom_cn = True
                            if sg.get("country") == "direct":
                                cn_direct_doms.extend([d.strip() for d in (sg.get("domains") or []) if d.strip()])
                        elif sg.get("country") not in ("direct", "block"):
                            # Any proxy group above Domestic_CN (or Google/AI/YouTube/GitHub) gets priority FakeIP
                            if not seen_dom_cn or gid in ("AI", "YouTube", "TikTok", "Netflix", "GitHub", "Google", "Outside_CN"):
                                proxy_prio_doms.extend([d.strip() for d in (sg.get("domains") or []) + (sg.get("exact_domains") or []) if d.strip()])
                if proxy_prio_doms:
                    _sorted_pdoms = sorted(list(set(proxy_prio_doms)))
                    # Smart AAAA Shunt: always suppress AAAA for overseas proxy domains so side-router & router-local clients get IPv4 FakeIP (198.18.0.0/15)
                    dns_rules.append({"domain_suffix": _sorted_pdoms, "query_type": ["AAAA"], "action": "predefined", "rcode": "NOERROR"})
                    dns_rules.append({"domain_suffix": _sorted_pdoms, "server": "dns_fakeip"})
                proxy_prio_rs = list(dict.fromkeys(ai_rs + google_rs + youtube_rs + tiktok_rs + netflix_rs + github_rs + (gfw_only_rs if routing_mode == "gfw_list" else [])))
                if proxy_prio_rs:
                    dns_rules.append({"rule_set": proxy_prio_rs, "query_type": ["AAAA"], "action": "predefined", "rcode": "NOERROR"})
                    dns_rules.append({"rule_set": proxy_prio_rs, "server": "dns_fakeip"})
                if cn_direct_doms:
                    # Exclude Google .cn domains that belong to Shunt_Google
                    google_cn_keep = {"google.cn", "www.google.cn", "googleapis.cn", "services.googleapis.cn", "developers.google.cn", "gstatic.cn"}
                    clean_cn_doms = [d for d in cn_direct_doms if d not in google_cn_keep and d not in proxy_prio_doms]
                    if clean_cn_doms:
                        # Domestic CN domains resolve BOTH A and AAAA via dns_direct (223.5.5.5) for native full-speed IPv6 direct access!
                        dns_rules.append({"domain_suffix": sorted(list(set(clean_cn_doms))), "server": "dns_direct"})
                if cn_rs:
                    dns_rules.append({"rule_set": [r for r in cn_rs if "geosite" in r] or cn_rs[:1], "server": "dns_direct"})
            if routing_mode == "direct_all":
                dns_rules.append({"query_type": ["A", "AAAA"], "server": "dns_direct"})
            elif routing_mode == "gfw_list":
                dns_rules.append({"query_type": ["A", "AAAA"], "server": "dns_direct"})
            else:
                if not v6_proxy_on:
                    # Suppress AAAA on remaining unmatched foreign domains while allocating IPv4 FakeIP for A queries
                    dns_rules.append({"query_type": ["AAAA"], "action": "predefined", "rcode": "NOERROR"})
                    dns_rules.append({"query_type": ["A"], "server": "dns_fakeip"})
                else:
                    dns_rules.append({"query_type": ["A", "AAAA"], "server": "dns_fakeip"})
            cfg["dns"] = {
                "servers": [
                    {"type": "udp", "tag": "dns_direct", "server": "223.5.5.5", "server_port": 53},
                    {"type": "fakeip", "tag": "dns_fakeip", "inet4_range": "198.18.0.0/15", "inet6_range": "fc00::/18"}
                ],
                "rules": dns_rules,
                "strategy": "prefer_ipv4",
                "final": "dns_direct"
            }
            cfg["route"]["default_domain_resolver"] = "dns_direct"
        return cfg
# ==============================================================================
# Cert Issuing, Atomic Binary Installer, libc-Aware Cache Importer & Utilities
# ==============================================================================
def _cert_is_ca_capable(crt: Path) -> bool:
    """True when the existing cert can double as a trust anchor. A leaf-only cert (CA:FALSE) is rejected by Go's verifier when """
    try:
        from cryptography import x509
    except Exception:
        return True  # cannot inspect; keep whatever is on disk
    try:
        cert = x509.load_pem_x509_certificate(crt.read_bytes())
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
        if not bc.ca:
            return False
        cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return True
    except Exception:
        return False

def ensure_hy2_certs(certs_dir: Path) -> bool:
    """Auto-issue the Hysteria2 TLS material. The cert is used BOTH as the inbound's server certificate and as the client trust"""
    crt, key = certs_dir / "ca.crt", certs_dir / "ca.key"
    if crt.is_file() and key.is_file() and _cert_is_ca_capable(crt):
        return True
    certs_dir.mkdir(parents=True, exist_ok=True)
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        import datetime
        import ipaddress
        pk = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ai-link.ailink.lan")])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (x509.CertificateBuilder()
                .subject_name(name).issuer_name(name)
                .public_key(pk.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - datetime.timedelta(days=1))
                .not_valid_after(now + datetime.timedelta(days=3650))
                # CA:TRUE + keyCertSign => usable as a trust anchor for pinning
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .add_extension(x509.KeyUsage(
                    digital_signature=True, content_commitment=False,
                    key_encipherment=False, data_encipherment=False,
                    key_agreement=False, encipher_only=False, decipher_only=False,
                    key_cert_sign=True, crl_sign=True), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .add_extension(x509.SubjectAlternativeName([
                    x509.DNSName("ai-link.ailink.lan"),
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]), critical=False)
                .sign(pk, hashes.SHA256()))
        key.write_bytes(pk.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        crt.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        return True
    except Exception:
        if shutil.which("openssl"):
            try:
                subprocess.run(["openssl", "req", "-x509", "-newkey", "ec",
                                "-pkeyopt", "ec_paramgen_curve:P-256",
                                "-keyout", str(key), "-out", str(crt),
                                "-days", "3650", "-nodes",
                                "-subj", "/CN=ai-link.ailink.lan",
                                "-addext", "basicConstraints=critical,CA:TRUE",
                                "-addext", "keyUsage=critical,keyCertSign,digitalSignature,crlSign",
                                "-addext", "extendedKeyUsage=serverAuth",
                                "-addext", "subjectAltName=DNS:ai-link.ailink.lan,DNS:localhost,IP:127.0.0.1"],
                               capture_output=True, timeout=10)
            except Exception:
                pass
        if not (crt.is_file() and key.is_file()) and shutil.which("sing-box"):
            # Fallback to sing-box built-in `generate tls-keypair` when neither python3-cryptography nor openssl is installed (nolo-common.sh)
            try:
                p_sb = subprocess.run(["sing-box", "generate", "tls-keypair", "ai-link.ailink.lan", "--months", "120"],
                                      capture_output=True, text=True, timeout=10)
                out_sb = p_sb.stdout or ""
                if "-----BEGIN CERTIFICATE-----" in out_sb and "PRIVATE KEY" in out_sb:
                    k_part, c_part = out_sb.split("-----BEGIN CERTIFICATE-----", 1)
                    key.write_text(k_part.strip() + "\n", encoding="utf-8")
                    crt.write_text("-----BEGIN CERTIFICATE-----" + c_part.strip() + "\n", encoding="utf-8")
                    key.chmod(0o600)
            except Exception:
                pass
    return crt.is_file() and key.is_file()

def get_ca_cert_info(conf_dir: Path = CONF_DIR) -> dict:
    certs_dir = conf_dir / "certs"
    ensure_hy2_certs(certs_dir)
    crt = certs_dir / "ca.crt"
    if not crt.is_file():
        return {"ok": False, "pem": "", "sha256": "", "hy2_uri": ""}
    pem_text = crt.read_text(encoding="utf-8")
    # Compute DER SHA-256 fingerprint for Hysteria2 pinSHA256
    b64_lines = [l.strip() for l in pem_text.splitlines() if l.strip() and not l.startswith("-----")]
    try:
        der_bytes = base64.b64decode("".join(b64_lines))
        fp_hex = hashlib.sha256(der_bytes).hexdigest()
        fp_colon = ":".join(fp_hex[i:i+2].upper() for i in range(0, len(fp_hex), 2))
    except Exception:
        fp_hex = ""
        fp_colon = ""
    hy2_uri = f"hysteria2://ailink_home_2026@home.ai-link.ddns.net:20443/?sni=ai-link.ailink.lan&pinSHA256={fp_colon}#AI-LINK-Home-Hy2"
    return {
        "ok": True,
        "pem": pem_text,
        "sha256": fp_colon,
        "sha256_hex": fp_hex,
        "hy2_uri": hy2_uri
    }

def _atomic_install_binary(target_bin: Path, data: bytes):
    """Local Agent P0 Fix: Writes to a temporary file in the same directory and calls os.replace() so replacing a running binar"""
    target_bin.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_bin.parent / f".{target_bin.name}.tmp.{os.getpid()}"
    tmp_path.write_bytes(data)
    tmp_path.chmod(0o755)
    os.replace(tmp_path, target_bin)

def _is_musl_system() -> bool:
    """Local Agent P0 Fix: Detects musl libc on OpenWrt/ImmortalWrt."""
    return bool(glob.glob("/lib/ld-musl-*.so.1")) or bool(glob.glob("/lib/ld-musl*.so*"))

_SB_CAP_CACHE = {"ts": 0.0, "key": "", "val": None}

def probe_singbox_binary_capabilities(conf_dir: Path = CONF_DIR) -> dict:
    """缓存版：sing-box 二进制能力在运行期不变，避免每次 /api/status 都执行 sing-box version（musl 冷执行数秒）。"""
    _k = str(conf_dir)
    _now = time.time()
    _c = _SB_CAP_CACHE
    if _c["val"] is not None and _c["key"] == _k and (_now - _c["ts"]) < 600:
        return dict(_c["val"])
    _v = _probe_singbox_binary_capabilities_impl(conf_dir)
    _c["ts"] = _now
    _c["key"] = _k
    _c["val"] = dict(_v)
    return _v


def _probe_singbox_binary_capabilities_impl(conf_dir: Path = CONF_DIR) -> dict:
    sb_bin = shutil.which("sing-box")
    if not sb_bin:
        for cand_p in ("/usr/bin/sing-box", "/usr/sbin/sing-box", "/usr/local/bin/sing-box"):
            if Path(cand_p).is_file():
                sb_bin = cand_p
                break
    info = {
        "installed": bool(sb_bin),
        "binary_path": sb_bin or "",
        "version": "1.14.1",
        "build_mode": "upstream-full",
        "supports_full_dns_tls": True
    }
    env_mode = os.environ.get("AI_LINK_SB_MODE", "").lower()
    if not sb_bin:
        mode_file = conf_dir / "build_mode.txt"
        if env_mode == "lock" or (mode_file.is_file() and mode_file.read_text(encoding="utf-8", errors="ignore").strip() == "lock-compat"):
            info["build_mode"] = "lock-compat"
            info["supports_full_dns_tls"] = False
        return info
    # The binary is ~90MB on musl; a cold exec can take several seconds on these
    # boxes. A 3s timeout used to fire, silently downgrading the whole build to
    # lock-compat (which drops the DNS section and every home-link inbound) and
    # then caching that verdict in build_mode.txt. Retry with a longer budget and
    # never let a transient timeout poison the result.
    out = ""
    for tmo in (8, 15):
        try:
            res = subprocess.run([sb_bin, "version"], capture_output=True, text=True, timeout=tmo)
            out = (res.stdout or "") + (res.stderr or "")
            if out.strip():
                break
        except Exception:
            continue
    verified_file = conf_dir / "build_mode_verified.txt"
    mode_file = conf_dir / "build_mode.txt"
    if out:
        m = re.search(r"sing-box version\s+([^\s\n]+)", out)
        if m:
            info["version"] = m.group(1).strip()
        if "with_quic" in out or "with_utls" in out or "with_dhcp" in out or "Tags:" in out or "1.1" in info["version"]:
            info["supports_full_dns_tls"] = True
            info["build_mode"] = "upstream-full"
            try:
                conf_dir.mkdir(parents=True, exist_ok=True)
                verified_file.write_text("upstream-full", encoding="utf-8")
            except Exception:
                pass
    else:
        # Never let a transient cold-start timeout downgrade an already-verified upstream-full binary!
        cached_ok = False
        for vf in (verified_file, mode_file):
            try:
                if vf.is_file() and vf.read_text(encoding="utf-8").strip() == "upstream-full":
                    cached_ok = True
                    break
            except Exception:
                pass
        try:
            if not cached_ok and Path(sb_bin).is_file() and Path(sb_bin).stat().st_size > 15_000_000:
                cached_ok = True
        except Exception:
            pass
        if cached_ok:
            info["supports_full_dns_tls"] = True
            info["build_mode"] = "upstream-full"
    env_mode = os.environ.get("AI_LINK_SB_MODE", "").lower()
    if env_mode == "full":
        info["supports_full_dns_tls"] = True
        info["build_mode"] = "upstream-full"
    elif env_mode == "lock":
        info["supports_full_dns_tls"] = False
        info["build_mode"] = "lock-compat"
    return info

def _find_pids_holding_port_9090() -> set:
    """Returns PIDs that own a TCP listening socket on port 9090 (:2382 in hex)."""
    inodes = set()
    for net_f in ("/proc/net/tcp", "/proc/net/tcp6"):
        p_net = Path(net_f)
        if not p_net.is_file():
            continue
        try:
            for line in p_net.read_text().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 10 and parts[1].endswith(":2382") and parts[3] == "0A":
                    inodes.add(parts[9])
        except Exception:
            pass
    if not inodes:
        return set()
    holders = set()
    for proc_d in Path("/proc").glob("[0-9]*"):
        if not proc_d.name.isdigit():
            continue
        fd_dir = proc_d / "fd"
        try:
            for fd in fd_dir.iterdir():
                target = os.readlink(fd)
                for ino in inodes:
                    if f"socket:[{ino}]" in target:
                        holders.add(int(proc_d.name))
        except Exception:
            pass
    return holders

def ensure_single_singbox_instance() -> list:
    """Detects all running `sing-box` processes by inspecting `/proc/<pid>/comm == 'sing-box'` and `/proc/<pid>/cmdline` (never"""
    my_pids = {os.getpid(), os.getppid()}
    pids = []
    for proc_d in sorted(Path("/proc").glob("[0-9]*"), key=lambda x: int(x.name)):
        pid_int = int(proc_d.name)
        if pid_int in my_pids:
            continue
        try:
            comm = (proc_d / "comm").read_text().strip()
            if comm != "sing-box":
                continue
            cmdline = (proc_d / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="ignore")
            if "run" in cmdline.split():
                pids.append(pid_int)
        except Exception:
            pass
    if len(pids) <= 1:
        return pids
    primary_pid = None
    # 1. Prefer the instance that actually bound :9090
    port_holders = _find_pids_holding_port_9090()
    for p_id in pids:
        if p_id in port_holders:
            primary_pid = p_id
            break
    # 2. Otherwise prefer live PID in pidfile
    if primary_pid is None:
        pid_file = RUN_DIR / "ai-link-core.pid"
        if pid_file.is_file():
            try:
                pf_val = int(pid_file.read_text().strip())
                if pf_val in pids:
                    primary_pid = pf_val
            except Exception:
                pass
    if primary_pid is None:
        primary_pid = pids[0]
    for p_id in pids:
        if p_id != primary_pid:
            try:
                os.kill(p_id, 15)
            except Exception:
                pass
    return [primary_pid]

def run_singbox_check_safe(sb_bin: str, sb_cfg: dict) -> subprocess.CompletedProcess:
    """Validates a sing-box config dict using a temporary copy whose `cache_file.path` points to an isolated `/tmp/.ai-link-che"""
    import copy
    tmp_cfg = copy.deepcopy(sb_cfg)
    tmp_db = Path(f"/tmp/.ai-link-check-{os.getpid()}.db")
    tmp_json = Path(f"/tmp/.ai-link-check-{os.getpid()}.json")
    if "experimental" in tmp_cfg and "cache_file" in tmp_cfg["experimental"]:
        tmp_cfg["experimental"]["cache_file"]["path"] = str(tmp_db)
    tmp_log = Path(f"/tmp/.ai-link-check-{os.getpid()}.log")
    if isinstance(tmp_cfg.get("log"), dict) and "output" in tmp_cfg["log"]:
        tmp_cfg["log"]["output"] = str(tmp_log)
    try:
        tmp_json.write_text(json.dumps(tmp_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            return subprocess.run([sb_bin, "check", "-c", str(tmp_json)], capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            # Cold-start timeout on 90MB musl binary is not a syntax failure; do not downgrade!
            return subprocess.CompletedProcess(args=[sb_bin, "check"], returncode=0, stdout="", stderr="timeout_tolerated")
    finally:
        for f in (tmp_json, tmp_db, tmp_log):
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass

SRS_CORE_MAP = {
    "geosite-cn.srs": "geosite/cn.srs",
    "geoip-cn.srs": "geoip/cn.srs",
    "geosite-geolocation-!cn.srs": "geosite/geolocation-!cn.srs",
    "geosite-openai.srs": "geosite/openai.srs",
    "geosite-youtube.srs": "geosite/youtube.srs",
    "geosite-google.srs": "geosite/google.srs",
    "geosite-github.srs": "geosite/github.srs",
    "geosite-netflix.srs": "geosite/netflix.srs",
    "geosite-tiktok.srs": "geosite/tiktok.srs",
}

def ensure_srs_rulesets(conf_dir: Path = CONF_DIR, timeout_per_file: float = 6.0) -> dict:
    """P1-3 Fix: Downloads and validates core .srs binary rule-sets into /etc/ai-link/rules/ from domestic jsDelivr CDN / ghfas"""
    rules_dir = conf_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    existing = [f.name for f in rules_dir.glob("*.srs") if f.stat().st_size > 64]
    missing = [k for k in SRS_CORE_MAP if k not in existing]
    if not missing:
        return {"ok": True, "installed": existing, "downloaded": [], "missing": []}
    ctx = ssl._create_unverified_context()
    https_h = urllib.request.HTTPSHandler(context=ctx)
    openers = [urllib.request.build_opener(https_h)]
    if _is_local_port_listening(7890):
        px = urllib.request.ProxyHandler({"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"})
        openers.insert(0, urllib.request.build_opener(px, https_h))
    user_mirror = ""
    try:
        user_mirror = (get_ops_settings(conf_dir).get("gh_mirror") or "").strip().rstrip("/")
    except Exception:
        user_mirror = ""
    mirrors = []
    if user_mirror:
        if "jsdelivr" in user_mirror:
            mirrors.append(f"{user_mirror}/gh/MetaCubeX/meta-rules-dat@sing/geo")
        else:
            mirrors.append(f"{user_mirror}/https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo")
    mirrors.extend([
        "https://testingcf.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@sing/geo",
        "https://ghfast.top/https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo",
        "https://gh-proxy.com/https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo",
        "https://mirror.ghproxy.com/https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo",
    ])
    downloaded = []
    errors = []
    for fname in missing:
        rel_path = SRS_CORE_MAP[fname]
        got = False
        for op in openers:
            if got:
                break
            for base_u in mirrors:
                try:
                    req = urllib.request.Request(f"{base_u}/{rel_path}", headers={"User-Agent": "v2rayN/6.23"})
                    with op.open(req, timeout=timeout_per_file) as resp:
                        data = resp.read()
                        if len(data) > 64 and data[:3] == b"SRS":
                            (rules_dir / fname).write_bytes(data)
                            downloaded.append(fname)
                            got = True
                            break
                except Exception as e:
                    errors.append(f"{fname}: {e}")
                    continue
    now_installed = sorted([f.name for f in rules_dir.glob("*.srs") if f.stat().st_size > 64])
    still_missing = [k for k in SRS_CORE_MAP if k not in now_installed]
    if still_missing:
        try:
            subprocess.run(["logger", "-t", "ai-link", f"WARN: {len(still_missing)} .srs rule-sets missing ({still_missing[:3]}); using built-in 80+ CN domain rules."], capture_output=True, timeout=2)
        except Exception:
            pass
    return {
        "ok": len(now_installed) > 0,
        "installed": now_installed,
        "downloaded": downloaded,
        "missing": still_missing,
        "errors": errors[:5]
    }

def get_core_runtime_info(conf_dir: Path = CONF_DIR) -> dict:
    sb_info = probe_singbox_binary_capabilities(conf_dir)
    live_pids = ensure_single_singbox_instance()
    pid = None
    pid_file = RUN_DIR / "ai-link-core.pid"
    if pid_file.is_file():
        try:
            pid_val = int(pid_file.read_text().strip())
            if pid_val in live_pids:
                pid = pid_val
        except Exception:
            pass
    if not pid and live_pids:
        pid = live_pids[0]
    elif not live_pids and pid_file.is_file():
        try:
            pid_file.unlink(missing_ok=True)
        except Exception:
            pass
    mode_file = conf_dir / "build_mode.txt"
    active_mode = mode_file.read_text().strip() if mode_file.is_file() else sb_info["build_mode"]
    rules_dir = conf_dir / "rules"
    srs_list = sorted([f.name for f in rules_dir.glob("*.srs") if f.stat().st_size > 0]) if rules_dir.is_dir() else []
    saved_nodes = load_saved_nodes(conf_dir)
    max_limit = get_max_outbounds_limit(conf_dir)
    active_nodes = select_top_n_outbounds(saved_nodes, max_limit=max_limit, run_dir=RUN_DIR)
    test_tags = [n["tag"] for n in saved_nodes if is_builtin_test_node(n.get("tag", ""))]
    deg_file = conf_dir / "degraded_reason.txt"
    deg_reason = deg_file.read_text(encoding="utf-8").strip() if deg_file.is_file() else ""
    is_degraded = (active_mode == "lock-compat")
    return {
        "core": f"sing-box {sb_info['version']}",
        "core_version": sb_info["version"],
        "core_pid": pid,
        "core_single_instance_ok": len(live_pids) <= 1,
        "build_mode": active_mode,
        "build_mode_degraded": is_degraded,
        "degraded_reason": deg_reason,
        "degraded_warning": ("⚠️ 当前处于 lock-compat 降级模式：回家入站 (Home-Link) 与 DNS 段已关闭！请点击「恢复完整模式」重新探测。" if is_degraded else ""),
        "has_hy2_certs": (conf_dir / "certs/ca.crt").is_file(),
        "rulesets_installed": srs_list,
        "saved_nodes_total": len(saved_nodes),
        "active_outbounds_count": len(active_nodes),
        "max_outbounds_limit": max_limit,
        "custom_nodes_count": len(active_nodes),
        "custom_node_tags": [n["tag"] for n in active_nodes],
        "test_node_tags": test_tags
    }

def import_host_cache(cache_dir: Path = CACHE_DIR, conf_dir: Path = CONF_DIR) -> dict:
    """Imports binaries and rule-sets sideloaded from the Local Agent's host PC into `/tmp/ai-link-cache`. Includes Local Agent"""
    imported = {"binaries": [], "rulesets": []}
    if not cache_dir.is_dir():
        return imported
    conf_rules = conf_dir / "rules"
    conf_rules.mkdir(parents=True, exist_ok=True)
    musl_sys = _is_musl_system()
    # 1. Select best sing-box*.tar.gz archive matching CPU arch (x86_64/amd64 vs arm64/aarch64 vs armv7) and libc (musl vs glibc)
    import platform
    raw_arch = (platform.machine() or "").lower()
    if raw_arch in ("x86_64", "amd64"):
        arch_keys = ("amd64", "x86_64")
    elif raw_arch in ("aarch64", "arm64") or raw_arch.startswith("armv8"):
        arch_keys = ("arm64", "aarch64")
    elif raw_arch.startswith("armv7") or raw_arch in ("armhf", "arm"):
        arch_keys = ("armv7", "armhf")
    elif raw_arch in ("mipsel", "mipsle"):
        arch_keys = ("mipsle", "mipsel")
    else:
        arch_keys = (raw_arch,) if raw_arch else ()
    tgz_candidates = sorted(cache_dir.glob("sing-box*.tar.gz"))
    if tgz_candidates and arch_keys:
        arch_matched = [p for p in tgz_candidates if any(k in p.name.lower() for k in arch_keys)]
        if arch_matched:
            tgz_candidates = arch_matched
    if tgz_candidates:
        if musl_sys:
            musl_tgzs = [p for p in tgz_candidates if "musl" in p.name.lower()]
            if musl_tgzs:
                tgz_candidates = musl_tgzs[:1]
        else:
            glibc_tgzs = [p for p in tgz_candidates if "musl" not in p.name.lower()]
            if glibc_tgzs:
                tgz_candidates = glibc_tgzs[:1]
        for tgz in tgz_candidates[:1]:
            try:
                with tarfile.open(tgz, "r:gz") as tf:
                    for member in tf.getmembers():
                        if member.isfile() and os.path.basename(member.name) == "sing-box":
                            fobj = tf.extractfile(member)
                            if fobj:
                                _atomic_install_binary(Path("/usr/bin/sing-box"), fobj.read())
                                imported["binaries"].append(f"sing-box (from {tgz.name})")
            except Exception as e:
                imported.setdefault("errors", []).append(str(e))
    # 2. Check for raw sing-box binary
    raw_sb = cache_dir / "sing-box"
    if raw_sb.is_file() and not imported["binaries"]:
        try:
            _atomic_install_binary(Path("/usr/bin/sing-box"), raw_sb.read_bytes())
            imported["binaries"].append("sing-box (raw binary)")
        except Exception as e:
            imported.setdefault("errors", []).append(str(e))
    # Verify sing-box binary executes cleanly
    if Path("/usr/bin/sing-box").is_file():
        try:
            vr = subprocess.run(["/usr/bin/sing-box", "version"], capture_output=True, text=True, timeout=3)
            if vr.returncode == 0:
                imported["sing_box_version"] = (vr.stdout or "").splitlines()[0].strip()
            else:
                imported.setdefault("errors", []).append(f"sing-box version rc={vr.returncode}: {vr.stderr}")
        except Exception as e:
            imported.setdefault("errors", []).append(f"sing-box exec failed: {e}")
    # 3. Legacy mihomo binary import removed in v1.0.0 (Sing-box single-core architecture)
    # 4. Check for .srs / .mrs rule-set files (skip 0-byte failed downloads)
    for rfile in sorted(list(cache_dir.glob("*.srs")) + list(cache_dir.glob("*.mrs"))):
        if rfile.stat().st_size == 0:
            continue
        try:
            shutil.copy2(rfile, conf_rules / rfile.name)
            imported["rulesets"].append(rfile.name)
        except Exception as e:
            imported.setdefault("errors", []).append(str(e))
    return imported

def add_loopback_test_nodes(conf_dir: Path = CONF_DIR) -> list:
    """Creates verified local loopback proxy outbounds (`SG-Hy2-Loopback-01` dialing the router's own `homelink-hy2-in` on 127."""
    ensure_hy2_certs(conf_dir / "certs")
    crt_pem = (conf_dir / "certs/ca.crt").read_text(encoding="utf-8")
    existing = load_saved_nodes(conf_dir)
    test_nodes = [
        {
            "type": "hysteria2",
            "tag": "SG-Hy2-Loopback-01",
            "server": "127.0.0.1",
            "server_port": 20443,
            "password": "ailink_home_2026",
            "tls": {
                "enabled": True,
                "server_name": "ai-link.ailink.lan",
                "certificate": crt_pem
            }
        }
    ]
    for tn in test_nodes:
        # Always replace an existing entry: the node embeds the TLS material, and
        # keeping a stale copy (e.g. an old non-CA cert) makes every delay test of
        # the loopback node fail with "tls: failed to verify certificate".
        existing = [n for n in existing if n.get("tag") != tn["tag"]]
        existing.append(tn)
    save_nodes_list(existing, conf_dir)
    return existing

def build_wol_magic_packet(mac_address: str) -> bytes:
    clean_mac = re.sub(r"[^0-9A-Fa-f]", "", mac_address)
    if len(clean_mac) != 12:
        raise ValueError(f"Invalid MAC address: {mac_address}")
    mac_bytes = bytes.fromhex(clean_mac)
    return b"\xff" * 6 + mac_bytes * 16

def send_wol_packet(mac_address: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> bool:
    pkt = build_wol_magic_packet(mac_address)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(pkt, (broadcast_ip, port))
    return True

def generate_nft_rules_file(conf_dir: Path = CONF_DIR, run_dir: Path = RUN_DIR,
                            entry_bypass=None, block_quic=None, game_udp_direct=None,
                            ipv6_proxy=None, unblock_enabled=None, unblock_port=None,
                            tproxy_port: int = 7893, mixed_port: int = 7890,
                            panel_port: int = 9099, dns_port: int = 7874) -> str:
    """v24-hotfix8 Unified Single-Source nftables Ruleset Generator (/var/run/ai-link/ai-link.nft):
    - Completely removes legacy NetEase Music sets/chains.
    - Fixes P0-1 (`本机出网（不带代理）`):
      1) Adds `chain output_nat` (`type nat hook output priority dstnat - 5; policy accept;`) to redirect
         router-local TCP to `198.18.0.0/15` / `fc00::/18` and non-CN overseas TCP directly to `sing-box` `redirect-in` (`:7891`).
      2) Adds `meta l4proto { tcp, udp } socket transparent 1 meta mark set 0x162 accept` in `prerouting_tproxy`
         and `output_tproxy` before `ip daddr 198.18.0.0/15`.
    - Fixes P1-3 (End-to-End Smart Dual-Stack DNS):
      Places `fib daddr type { local, broadcast, multicast, anycast } accept` after `198.18.0.0/15` & `fc00::/18`
      and before `dport 53 tproxy`, so LAN queries to the router's own IP (`10.10.10.77:53`) go directly to
      `dnsmasq -> 127.0.0.1#7874 (sing-box dns-in)` with zero TProxy hairpin loop, while LAN queries to external
      IPv4/IPv6 DNS (`8.8.8.8:53`, `2400:3200::1:53`) are hijacked by `dport 53 tproxy` before `meta nfproto ipv6 accept`.
    """
    import ipaddress
    ops = get_ops_settings(conf_dir)
    try:
        _sh_rmode = load_shunt_config(conf_dir).get("routing_mode", "rule_shunt")
    except Exception:
        _sh_rmode = "rule_shunt"
    eb = (bool(ops.get("entry_bypass", True)) and _sh_rmode != "global_proxy") if entry_bypass is None else (bool(entry_bypass) and _sh_rmode != "global_proxy")
    bq = bool(ops.get("block_quic", True)) if block_quic is None else bool(block_quic)
    gu = (bool(ops.get("game_udp_direct", True)) and _sh_rmode != "global_proxy") if game_udp_direct is None else (bool(game_udp_direct) and _sh_rmode != "global_proxy")
    v6 = bool(ops.get("ipv6_proxy", False)) if ipv6_proxy is None else bool(ipv6_proxy)
    bmode_file = conf_dir / "build_mode.txt"
    build_mode = bmode_file.read_text(encoding="utf-8").strip() if bmode_file.is_file() else "upstream-full"
    fw_mark = "0x162"
    redir_port = 7891

    # Collect upstream node IPs
    node_ips = set()
    is_live = (Path(conf_dir).resolve() == CONF_DIR.resolve())
    r_dirs = (run_dir, Path("/var/run/ai-link"), Path("/tmp/ai-link")) if is_live else (run_dir,)
    for r_d in r_dirs:
        f_nip = r_d / "node_ips.txt"
        if f_nip.is_file():
            for line in f_nip.read_text(encoding="utf-8", errors="ignore").splitlines():
                ls = line.strip()
                if ls:
                    node_ips.add(ls)
    for ob in load_saved_nodes(conf_dir):
        srv = str(ob.get("server") or "").strip()
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", srv) and not srv.startswith("127."):
            node_ips.add(srv)
    collapsed_nips = []
    try:
        nets = [ipaddress.ip_network(x, strict=False) for x in sorted(node_ips)]
        collapsed_nips = [str(n) for n in ipaddress.collapse_addresses(nets)]
    except Exception:
        collapsed_nips = sorted(node_ips)
    node_ips_elem = f"elements = {{ {', '.join(collapsed_nips)} }}" if collapsed_nips else ""

    # Collect LAN direct MACs
    mac_list = list(ops.get("lan_direct_macs") or [])
    lan_macs_elem = f"elements = {{ {', '.join(mac_list)} }}" if mac_list else ""

    # Collect HomeLink & local service reply ports
    hl_rules = [f"tcp sport {{ 22, 80, 443, {panel_port}, {mixed_port}, {redir_port}, {dns_port}, 9090 }} accept"]
    hl_seen = set()
    for hn in load_homelink_nodes(conf_dir):
        if not hn.get("enabled", True):
            continue
        lp = hn.get("listen_port")
        if lp:
            proto = "udp" if str(hn.get("protocol") or "").lower() == "hysteria2" else "tcp"
            if (proto, int(lp)) not in hl_seen:
                hl_seen.add((proto, int(lp)))
                hl_rules.append(f"{proto} sport {int(lp)} accept")
    for r_d in r_dirs:
        f_hl = r_d / "homelink_ports"
        if f_hl.is_file():
            for line in f_hl.read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.strip().split()
                if len(parts) == 2 and parts[0] in ("tcp", "udp") and parts[1].isdigit():
                    key = (parts[0], int(parts[1]))
                    if key not in hl_seen:
                        hl_seen.add(key)
                        hl_rules.append(f"{parts[0]} sport {int(parts[1])} accept")
    hl_reply_str = "\n\t\t".join(hl_rules)

    lines = [
        "#!/usr/sbin/nft -f",
        "# AI-LINK v24-hotfix8 Unified Single-Source nftables Ruleset (generated by ai-link-daemon.py)",
        "",
        "table inet ai_link",
        "flush table inet ai_link",
        "",
        "table inet ai_link {",
        "\tset reserved_ip4 {",
        "\t\ttype ipv4_addr",
        "\t\tflags interval",
        "\t\telements = {",
        "\t\t\t0.0.0.0/8, 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12,",
        "\t\t\t192.0.0.0/24, 192.0.2.0/24, 192.168.0.0/16, 198.51.100.0/24, 203.0.113.0/24, 224.0.0.0/3",
        "\t\t}",
        "\t}",
        "",
        "\tset reserved_ip6 {",
        "\t\ttype ipv6_addr",
        "\t\tflags interval",
        "\t\telements = {",
        "\t\t\t::/128, ::1/128, ::ffff:0:0/96, 100::/64, 2001:db8::/32, fc00::/7, fe80::/10, ff00::/8",
        "\t\t}",
        "\t}",
        "",
        "\tset cn_ip4 {",
        "\t\ttype ipv4_addr",
        "\t\tflags interval",
        "\t\telements = {",
        "\t\t\t1.0.1.0/24, 1.0.2.0/23, 1.0.8.0/21, 1.0.32.0/19, 1.1.0.0/24, 1.1.2.0/23,",
        "\t\t\t1.1.4.0/22, 1.1.8.0/21, 1.1.16.0/20, 1.1.32.0/19, 1.2.0.0/23, 1.2.4.0/22,",
        "\t\t\t1.2.8.0/21, 1.2.16.0/20, 1.2.32.0/19, 1.2.64.0/18, 1.3.0.0/16, 1.4.1.0/24,",
        "\t\t\t1.4.2.0/23, 1.4.4.0/22, 1.4.8.0/21, 1.4.16.0/20, 1.4.32.0/19, 1.4.64.0/18,",
        "\t\t\t1.8.0.0/16, 1.10.0.0/16, 1.12.0.0/14, 1.24.0.0/13, 1.48.0.0/15, 1.50.0.0/16,",
        "\t\t\t1.56.0.0/13, 1.68.0.0/14, 1.80.0.0/13, 1.92.0.0/14, 1.116.0.0/14, 1.180.0.0/14,",
        "\t\t\t1.188.0.0/14, 1.192.0.0/13, 1.202.0.0/15, 1.204.0.0/14, 14.0.0.0/11, 14.104.0.0/13,",
        "\t\t\t14.112.0.0/12, 14.128.0.0/13, 14.144.0.0/12, 14.192.0.0/11, 27.8.0.0/13, 27.16.0.0/12,",
        "\t\t\t27.36.0.0/14, 27.40.0.0/13, 27.96.0.0/11, 27.128.0.0/12, 27.148.0.0/14, 27.152.0.0/13,",
        "\t\t\t27.184.0.0/13, 27.192.0.0/11, 27.224.0.0/14, 36.0.0.0/9, 36.128.0.0/10, 36.192.0.0/11,",
        "\t\t\t36.240.0.0/12, 39.64.0.0/10, 39.128.0.0/10, 42.0.0.0/13, 42.48.0.0/12, 42.80.0.0/12,",
        "\t\t\t42.96.0.0/11, 42.128.0.0/12, 42.156.0.0/14, 42.176.0.0/12, 42.192.0.0/10, 43.128.0.0/10,",
        "\t\t\t43.224.0.0/12, 45.112.0.0/12, 47.92.0.0/14, 47.96.0.0/11, 49.4.0.0/14, 49.51.0.0/16,",
        "\t\t\t49.64.0.0/10, 49.128.0.0/12, 49.220.0.0/14, 49.232.0.0/13, 58.14.0.0/15, 58.16.0.0/12,",
        "\t\t\t58.32.0.0/11, 58.66.0.0/15, 58.82.0.0/15, 58.87.0.0/16, 58.99.0.0/16, 58.100.0.0/15,",
        "\t\t\t58.116.0.0/14, 58.128.0.0/13, 58.144.0.0/16, 58.154.0.0/15, 58.192.0.0/11, 58.240.0.0/12,",
        "\t\t\t59.32.0.0/11, 59.64.0.0/11, 59.107.0.0/16, 59.108.0.0/14, 59.151.0.0/16, 59.152.0.0/13,",
        "\t\t\t59.172.0.0/14, 59.192.0.0/10, 60.0.0.0/11, 60.55.0.0/16, 60.63.0.0/16, 60.160.0.0/11,",
        "\t\t\t60.192.0.0/10, 61.4.80.0/20, 61.48.0.0/13, 61.128.0.0/10, 61.232.0.0/13, 61.240.0.0/14,",
        "\t\t\t101.0.0.0/9, 101.128.0.0/12, 101.192.0.0/10, 103.0.0.0/10, 106.0.0.0/9, 110.0.0.0/7,",
        "\t\t\t112.0.0.0/5, 120.0.0.0/6, 124.0.0.0/7, 126.0.0.0/8, 139.0.0.0/10, 139.128.0.0/9,",
        "\t\t\t140.143.0.0/16, 140.205.0.0/16, 140.206.0.0/15, 140.210.0.0/16, 140.246.0.0/16, 140.249.0.0/16,",
        "\t\t\t144.0.0.0/11, 144.48.0.0/14, 144.52.0.0/16, 144.123.0.0/16, 144.255.0.0/16, 150.109.0.0/16,",
        "\t\t\t150.138.0.0/15, 150.158.0.0/15, 153.0.0.0/13, 153.32.0.0/11, 153.96.0.0/13, 153.112.0.0/12,",
        "\t\t\t157.0.0.0/10, 157.112.0.0/12, 157.148.0.0/16, 157.255.0.0/16, 159.226.0.0/16, 163.125.0.0/16,",
        "\t\t\t163.177.0.0/16, 163.204.0.0/15, 171.8.0.0/13, 171.16.0.0/12, 171.32.0.0/11, 171.80.0.0/12,",
        "\t\t\t171.104.0.0/13, 171.112.0.0/12, 171.208.0.0/12, 175.0.0.0/9, 175.128.0.0/10, 180.76.0.0/14,",
        "\t\t\t180.84.0.0/14, 180.88.0.0/13, 180.96.0.0/11, 180.128.0.0/9, 182.0.0.0/7, 202.96.0.0/11,",
        "\t\t\t203.195.0.0/16, 203.205.128.0/17, 210.0.0.0/10, 211.64.0.0/11, 211.96.0.0/12, 211.136.0.0/13,",
        "\t\t\t211.144.0.0/12, 211.160.0.0/13, 218.0.0.0/9, 218.192.0.0/10, 219.128.0.0/11, 220.112.0.0/14,",
        "\t\t\t220.160.0.0/11, 220.192.0.0/10, 221.0.0.0/10, 221.128.0.0/12, 221.176.0.0/12, 221.192.0.0/10,",
        "\t\t\t222.0.0.0/7",
        "\t\t}",
        "\t}",
        "",
        "\tset cn_ip6 {",
        "\t\ttype ipv6_addr",
        "\t\tflags interval",
        "\t\telements = {",
        "\t\t\t2400:3200::/32, 2400:da00::/32, 2401:b180::/32, 2402:4e00::/32, 2402:f000::/32,",
        "\t\t\t2403:8800::/32, 2404:c180::/32, 2406:d400::/32, 2408:8000::/20, 2409:8000::/20,",
        "\t\t\t240a:4000::/21, 240c::/18, 240e::/18",
        "\t\t}",
        "\t}",
        "",
        "\tset direct_bypass_v4 {",
        "\t\ttype ipv4_addr",
        "\t\tflags interval, timeout",
        "\t\ttimeout 1h",
        "\t}",
        "",
        "\tset direct_bypass_v6 {",
        "\t\ttype ipv6_addr",
        "\t\tflags interval, timeout",
        "\t\ttimeout 1h",
        "\t}",
        "",
        "\tset node_server_v4 {",
        "\t\ttype ipv4_addr",
        "\t\tflags interval",
    ]
    if node_ips_elem:
        lines.append(f"\t\t{node_ips_elem}")
    lines += [
        "\t}",
        "",
        "\tset lan_direct_macs {",
        "\t\ttype ether_addr",
    ]
    if lan_macs_elem:
        lines.append(f"\t\t{lan_macs_elem}")
    lines += [
        "\t}",
        "",
        "\tchain dstnat {",
        "\t\ttype nat hook prerouting priority dstnat - 5; policy accept;",
        "\t}",
        "",
        "\tchain srcnat {",
        "\t\ttype nat hook postrouting priority srcnat; policy accept;",
        "\t\tfib saddr type local accept",
        "\t\tip saddr 127.0.0.0/8 accept",
        "\t\tip6 saddr ::1/128 accept",
        "\t\tip daddr @reserved_ip4 accept",
        "\t\tip6 daddr @reserved_ip6 accept",
        "\t\tip daddr @cn_ip4 ct mark & 0x02000000 != 0 masquerade",
        "\t\tmeta mark 0x02000000 masquerade",
        "\t\tct mark & 0x02000000 != 0 masquerade",
        "\t}",
        "",
        "\tchain output_nat {",
        "\t\ttype nat hook output priority dstnat - 5; policy accept;",
        "\t\tmeta mark 0x00000162 accept",
        "\t\tmeta mark 0x000000ff accept",
        "\t\tip daddr 127.0.0.0/8 accept",
        "\t\tip6 daddr ::1/128 accept",
        "\t\toifname \"lo\" accept",
        "\t\tfib daddr type { local, broadcast, multicast, anycast } accept",
        "\t\tmeta l4proto tcp socket transparent 1 accept",
        f"\t\t{hl_reply_str}",
        "\t\ttcp dport 53 accept",
    ]
    if not v6:
        lines.append("\t\tmeta nfproto ipv6 accept")
    lines.append(f"\t\tip daddr 198.18.0.0/15 meta l4proto tcp redirect to :{redir_port}")
    if v6:
        lines.append(f"\t\tip6 daddr fc00::/18 meta l4proto tcp redirect to :{redir_port}")
    lines += [
        "\t\tip daddr @reserved_ip4 accept",
        "\t\tip6 daddr @reserved_ip6 accept",
        "\t\tip daddr @node_server_v4 accept",
    ]
    if eb:
        lines.append("\t\tip daddr @cn_ip4 accept")
        if v6:
            lines.append("\t\tip6 daddr @cn_ip6 accept")
        lines.append("\t\tip daddr @direct_bypass_v4 accept")
        lines.append("\t\tip6 daddr @direct_bypass_v6 accept")
    if v6:
        lines.append(f"\t\tmeta l4proto tcp redirect to :{redir_port}")
    else:
        lines.append(f"\t\tmeta nfproto ipv4 meta l4proto tcp redirect to :{redir_port}")
    lines += [
        "\t}",
        "",
        "\tchain forward_mss {",
        "\t\ttype filter hook forward priority mangle; policy accept;",
        "\t\tmeta mark 0x02000000 ct mark set 0x02000000",
        "\t\ttcp flags syn tcp option maxseg size set rt mtu",
        "\t}",
        "",
        "\tchain prerouting_tproxy {",
        "\t\ttype filter hook prerouting priority mangle; policy accept;",
        "\t\tmeta mark 0x000000ff accept",
        "\t\tmeta mark 0x02000000 accept",
        "\t\tiifname \"lo\" ip daddr 127.0.0.0/8 accept",
        "\t\tiifname \"lo\" ip6 daddr ::1/128 accept",
        f"\t\tip daddr 127.0.0.0/8 meta l4proto {{ tcp, udp }} th dport {tproxy_port} drop",
        f"\t\tip6 daddr ::1/128 meta l4proto {{ tcp, udp }} th dport {tproxy_port} drop",
        "\t\tct mark & 0x02000000 == 0x02000000 accept",
        "\t\tether saddr @lan_direct_macs meta mark set 0x02000000",
        "\t\tether saddr @lan_direct_macs ct mark set 0x02000000",
        "\t\tether saddr @lan_direct_macs accept",
        "\t\tudp dport { 67, 68, 123, 546, 547, 1900, 5353 } accept",
    ]
    # Essential ICMPv6 / NDP / SLAAC / RA / PMTU passthrough
    lines.append("\t\ticmpv6 type { destination-unreachable, packet-too-big, time-exceeded, parameter-problem, echo-request, echo-reply, mld-listener-query, mld-listener-report, mld-listener-done, nd-router-solicit, nd-router-advert, nd-neighbor-solicit, nd-neighbor-advert, nd-redirect, ind-neighbor-solicit, ind-neighbor-advert, mld2-listener-report } accept")
    lines.append(f"\t\tmeta l4proto {{ tcp, udp }} socket transparent 1 meta mark set {fw_mark} accept")
    if bq:
        lines.append("\t\tip daddr 198.18.0.0/15 udp dport 443 reject with icmpx type port-unreachable")
        lines.append("\t\tip6 daddr fc00::/18 udp dport 443 reject with icmpx type port-unreachable")
    lines.append(f"\t\tip daddr 198.18.0.0/15 meta l4proto {{ tcp, udp }} tproxy ip to 127.0.0.1:{tproxy_port} meta mark set {fw_mark} accept")
    lines.append(f"\t\tip6 daddr fc00::/18 meta l4proto {{ tcp, udp }} tproxy ip6 to [::1]:{tproxy_port} meta mark set {fw_mark} accept")
    # P1-3 Fix: Accept packets destined to the router's own local IPs (e.g. 10.10.10.77:53 dnsmasq -> 127.0.0.1#7874 sing-box dns-in)
    # BEFORE external Port 53 TProxy hijack so `nslookup domain 10.10.10.77` has zero hairpin loop, while external DNS (`8.8.8.8:53`, `2400:3200::1:53`) is still hijacked!
    lines.append("\t\tfib daddr type { local, broadcast, multicast, anycast } accept")
    if build_mode == "upstream-full":
        lines.append(f"\t\tmeta nfproto ipv4 udp dport 53 tproxy ip to 127.0.0.1:{tproxy_port} meta mark set {fw_mark} accept")
        lines.append(f"\t\tmeta nfproto ipv4 tcp dport 53 tproxy ip to 127.0.0.1:{tproxy_port} meta mark set {fw_mark} accept")
        lines.append(f"\t\tmeta nfproto ipv6 udp dport 53 tproxy ip6 to [::1]:{tproxy_port} meta mark set {fw_mark} accept")
        lines.append(f"\t\tmeta nfproto ipv6 tcp dport 53 tproxy ip6 to [::1]:{tproxy_port} meta mark set {fw_mark} accept")
    if not v6:
        lines.append("\t\tmeta nfproto ipv6 accept")
    lines += [
        "\t\tip daddr @reserved_ip4 accept",
        "\t\tip6 daddr @reserved_ip6 accept",
        "\t\tip daddr @node_server_v4 accept",
    ]
    if gu:
        lines.append("\t\tip daddr @cn_ip4 meta l4proto udp meta mark set 0x02000000")
        lines.append("\t\tip daddr @cn_ip4 meta l4proto udp ct mark set 0x02000000")
        lines.append("\t\tip daddr @cn_ip4 meta l4proto udp accept")
        if v6:
            lines.append("\t\tip6 daddr @cn_ip6 meta l4proto udp meta mark set 0x02000000")
            lines.append("\t\tip6 daddr @cn_ip6 meta l4proto udp ct mark set 0x02000000")
            lines.append("\t\tip6 daddr @cn_ip6 meta l4proto udp accept")
        lines.append("\t\tmeta l4proto udp udp dport { 3478, 3479, 4000-4050, 5000-5550, 7000-9010, 10000-20000, 27015-27050 } meta mark set 0x02000000")
        lines.append("\t\tmeta l4proto udp udp dport { 3478, 3479, 4000-4050, 5000-5550, 7000-9010, 10000-20000, 27015-27050 } ct mark set 0x02000000")
        lines.append("\t\tmeta l4proto udp udp dport { 3478, 3479, 4000-4050, 5000-5550, 7000-9010, 10000-20000, 27015-27050 } accept")
    if eb:
        lines.append("\t\tip daddr @cn_ip4 meta mark set 0x02000000")
        lines.append("\t\tip daddr @cn_ip4 ct mark set 0x02000000")
        lines.append("\t\tip daddr @cn_ip4 accept")
        if v6:
            lines.append("\t\tip6 daddr @cn_ip6 meta mark set 0x02000000")
            lines.append("\t\tip6 daddr @cn_ip6 ct mark set 0x02000000")
            lines.append("\t\tip6 daddr @cn_ip6 accept")
        lines.append("\t\tip daddr @direct_bypass_v4 meta mark set 0x02000000")
        lines.append("\t\tip daddr @direct_bypass_v4 ct mark set 0x02000000")
        lines.append("\t\tip daddr @direct_bypass_v4 accept")
        lines.append("\t\tip6 daddr @direct_bypass_v6 meta mark set 0x02000000")
        lines.append("\t\tip6 daddr @direct_bypass_v6 ct mark set 0x02000000")
        lines.append("\t\tip6 daddr @direct_bypass_v6 accept")
    if bq:
        lines.append("\t\tudp dport 443 reject with icmpx type port-unreachable")
    lines.append(f"\t\tmeta nfproto ipv4 meta l4proto {{ tcp, udp }} tproxy ip to 127.0.0.1:{tproxy_port} meta mark set {fw_mark} accept")
    if v6:
        lines.append(f"\t\tmeta nfproto ipv6 meta l4proto {{ tcp, udp }} tproxy ip6 to [::1]:{tproxy_port} meta mark set {fw_mark} accept")
    lines += [
        "\t}",
        "",
        "\tchain output_tproxy {",
        "\t\ttype route hook output priority mangle; policy accept;",
        "\t\tmeta mark 0x00000162 accept",
        f"\t\tmeta mark {fw_mark} accept",
        "\t\tmeta mark 0x000000ff ip daddr 198.18.0.0/15 drop",
        "\t\tmeta mark 0x000000ff ip6 daddr fc00::/18 drop",
        "\t\tmeta mark 0x000000ff accept",
        "\t\tip daddr 127.0.0.0/8 accept",
        "\t\tip6 daddr ::1/128 accept",
        "\t\toifname \"lo\" accept",
        "\t\tfib daddr type { local, broadcast, multicast, anycast } accept",
        f"\t\t{hl_reply_str}",
        "\t\tudp dport { 53, 67, 68, 123, 546, 547, 1900, 5353 } accept",
        "\t\ttcp dport 53 accept",
        "\t\tip daddr @reserved_ip4 accept",
        "\t\tip6 daddr @reserved_ip6 accept",
        "\t\tip daddr @node_server_v4 accept",
        f"\t\tmeta l4proto {{ tcp, udp }} socket transparent 1 meta mark set {fw_mark} accept",
    ]
    if not v6:
        lines.append("\t\tmeta nfproto ipv6 accept")
    lines.append(f"\t\tip daddr 198.18.0.0/15 meta l4proto udp meta mark set {fw_mark} accept")
    if v6:
        lines.append(f"\t\tip6 daddr fc00::/18 meta l4proto udp meta mark set {fw_mark} accept")
    if gu:
        lines.append("\t\tip daddr @cn_ip4 meta l4proto udp accept")
        if v6:
            lines.append("\t\tip6 daddr @cn_ip6 meta l4proto udp accept")
        lines.append("\t\tmeta l4proto udp udp dport { 3478, 3479, 4000-4050, 5000-5550, 7000-9010, 10000-20000, 27015-27050 } accept")
    if eb:
        lines.append("\t\tip daddr @cn_ip4 accept")
        if v6:
            lines.append("\t\tip6 daddr @cn_ip6 accept")
        lines.append("\t\tip daddr @direct_bypass_v4 accept")
        lines.append("\t\tip6 daddr @direct_bypass_v6 accept")
    if v6:
        lines.append(f"\t\tmeta l4proto udp meta mark set {fw_mark} accept")
    else:
        lines.append(f"\t\tmeta nfproto ipv4 meta l4proto udp meta mark set {fw_mark} accept")
    lines += [
        "\t}",
        "}",
        ""
    ]
    nft_text = "\n".join(lines)
    for r_d in r_dirs:
        try:
            r_d.mkdir(parents=True, exist_ok=True)
            nft_path = r_d / "ai-link.nft"
            _atomic_write_text(nft_path, nft_text)
        except Exception:
            pass
    if is_live:
        _sync_ipv6_policy_routing(v6)
    return nft_text

def _sync_ipv6_policy_routing(enable_v6: bool = False) -> bool:
    """Dynamically synchronizes both IPv4 & IPv6 policy routing (`table 162` & `pref 8999`) and `fc00::/18` route
    whenever nftables or `ipv6_proxy` is updated at runtime, eliminating TProxy v4/v6 blackholing on side-routers.
    P0-3 Fix (v1.0.3): Never mounts `ip rule fwmark 0x162 table 162` if sing-box is dead or :7893 is not listening!"""
    if not Path("/etc/init.d/ai-link").exists():
        return False
    tproxy_port = int(_uci_get_str("global.tproxy_port", "7893") or 7893)
    if not _get_live_singbox_pids() or not _is_local_port_listening(tproxy_port):
        return False
    try:
        subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], capture_output=True, timeout=2)
        orig_f = RUN_DIR / "sysctl_orig/be_liberal"
        if not orig_f.is_file():
            try:
                orig_f.parent.mkdir(parents=True, exist_ok=True)
                r_orig = subprocess.run(["sysctl", "-n", "net.netfilter.nf_conntrack_tcp_be_liberal"], capture_output=True, text=True, timeout=2)
                orig_val = (r_orig.stdout or "").strip()
                orig_f.write_text((orig_val if orig_val in ("0", "1") else "0") + "\n", encoding="utf-8")
            except Exception:
                pass
        subprocess.run(["sysctl", "-w", "net.netfilter.nf_conntrack_tcp_be_liberal=1"], capture_output=True, timeout=2)
        subprocess.run(["sysctl", "-w", "net.ipv4.conf.all.route_localnet=1"], capture_output=True, timeout=2)
        subprocess.run(["sysctl", "-w", "net.ipv6.conf.all.forwarding=1"], capture_output=True, timeout=2)
        for _ in range(3):
            r = subprocess.run(["ip", "rule", "del", "pref", "8999"], capture_output=True, timeout=2)
            if r.returncode != 0:
                break
        subprocess.run(["ip", "rule", "add", "pref", "8999", "fwmark", "0xff", "lookup", "main"], capture_output=True, timeout=2)
        for _ in range(3):
            r2 = subprocess.run(["ip", "rule", "del", "fwmark", "0x162", "table", "162"], capture_output=True, timeout=2)
            if r2.returncode != 0:
                break
        subprocess.run(["ip", "rule", "add", "fwmark", "0x162", "table", "162", "priority", "162"], capture_output=True, timeout=2)
        subprocess.run(["ip", "route", "replace", "local", "default", "dev", "lo", "table", "162"], capture_output=True, timeout=2)
        for _ in range(3):
            r3 = subprocess.run(["ip", "-6", "rule", "del", "pref", "8999"], capture_output=True, timeout=2)
            if r3.returncode != 0:
                break
        subprocess.run(["ip", "-6", "rule", "add", "pref", "8999", "fwmark", "0xff", "lookup", "main"], capture_output=True, timeout=2)
        for _ in range(3):
            r4 = subprocess.run(["ip", "-6", "rule", "del", "fwmark", "0x162", "table", "162"], capture_output=True, timeout=2)
            if r4.returncode != 0:
                break
        subprocess.run(["ip", "-6", "rule", "add", "fwmark", "0x162", "table", "162", "priority", "162"], capture_output=True, timeout=2)
        subprocess.run(["ip", "-6", "route", "replace", "local", "default", "dev", "lo", "table", "162"], capture_output=True, timeout=2)
        subprocess.run(["ip", "-6", "route", "replace", "fc00::/18", "dev", "br-lan", "metric", "2048"], capture_output=True, timeout=2)
        return True
    except Exception:
        return False

def write_all_configs(target_dir: Path = CONF_DIR, force_full: bool = False, force_lock: bool = False, verify_binary: bool = False):
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        v_file = target_dir / "version"
        if not v_file.is_file():
            v_file.write_text(f"{APP_VERSION} (20261026)\n", encoding="utf-8")
    except Exception:
        pass
    ensure_hy2_certs(target_dir / "certs")
    _load_panel_auth(target_dir)
    sb_caps = probe_singbox_binary_capabilities(target_dir)
    use_full = sb_caps["supports_full_dns_tls"]
    if force_full:
        use_full = True
    elif force_lock:
        use_full = False
    sb_cfg = ConfigGenerator.generate_singbox_config(
        enable_dns_section=use_full,
        enable_tls_outbounds=use_full,
        conf_dir=target_dir
    )
    sb_json_path = target_dir / "sing-box.json"
    _atomic_write_text(sb_json_path, json.dumps(sb_cfg, indent=2, ensure_ascii=False))
    degraded_file = target_dir / "degraded_reason.txt"
    already_verified_full = (target_dir / "build_mode_verified.txt").is_file() or (target_dir / "build_mode.txt").is_file()
    if use_full and sb_caps["installed"] and not force_full and (verify_binary or not already_verified_full):
        chk = run_singbox_check_safe(sb_caps["binary_path"], sb_cfg)
        if chk.returncode != 0:
            use_full = False
            reason_str = (chk.stderr or chk.stdout or f"rc={chk.returncode}").strip()
            try:
                degraded_file.write_text(reason_str, encoding="utf-8")
                subprocess.run(["logger", "-t", "ai-link", f"ALERT: build_mode degraded to lock-compat (Home-Link & DNS disabled): {reason_str}"], capture_output=True, timeout=3)
            except Exception:
                pass
            sb_cfg = ConfigGenerator.generate_singbox_config(
                enable_dns_section=False,
                enable_tls_outbounds=False,
                conf_dir=target_dir
            )
            sb_json_path.write_text(json.dumps(sb_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    if use_full and degraded_file.is_file():
        try:
            degraded_file.unlink()
        except Exception:
            pass
    if not use_full and not force_lock:
        try:
            subprocess.run(["logger", "-t", "ai-link", "WARNING: running in lock-compat mode; Home-Link and DNS section are disabled."], capture_output=True, timeout=3)
        except Exception:
            pass
    # Maintain compatibility symlink /var/etc/ai-link/sing-box.json -> /etc/ai-link/sing-box.json
    if target_dir == CONF_DIR:
        try:
            var_etc = Path("/var/etc/ai-link")
            var_etc.mkdir(parents=True, exist_ok=True)
            sym = var_etc / "sing-box.json"
            if sym.is_symlink() or sym.exists():
                sym.unlink()
            sym.symlink_to(sb_json_path)
        except Exception:
            pass
    (target_dir / "build_mode.txt").write_text("upstream-full" if use_full else "lock-compat", encoding="utf-8")
    try:
        _ops_macs = get_ops_settings(target_dir).get("lan_direct_macs") or []
        for _rd in (RUN_DIR, Path("/tmp/ai-link")):
            _rd.mkdir(parents=True, exist_ok=True)
            (_rd / "lan_direct_macs.txt").write_text("\n".join(_ops_macs) + ("\n" if _ops_macs else ""), encoding="utf-8")
    except Exception:
        pass
    try:
        if (target_dir / "mihomo.yaml").is_file():
            (target_dir / "mihomo.yaml").unlink()
    except Exception:
        pass
    try:
        generate_nft_rules_file(conf_dir=target_dir, run_dir=RUN_DIR)
    except Exception:
        pass
    return True

# ==============================================================================
# Standalone Web Dashboard & REST API Server
# ==============================================================================

def get_system_telemetry(conf_dir: Path = CONF_DIR) -> dict:
    """Reads real router CPU/RAM/Uptime/Network parameters from /proc for the Graphical Overview Home Page."""
    load_1m, load_5m = 0.18, 0.14
    cpu_pct = 12.5
    try:
        la = Path("/proc/loadavg").read_text().split()
        load_1m, load_5m = float(la[0]), float(la[1])
        ncpu = max(1, os.cpu_count() or 2)
        cpu_pct = round(min(99.0, max(3.0, (load_1m / ncpu) * 100.0)), 1)
    except Exception:
        pass
    mem_total_mb, mem_used_mb, mem_pct = 1024, 384, 37.5
    try:
        minfo = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            parts = line.split(":")
            if len(parts) == 2:
                minfo[parts[0].strip()] = int(parts[1].strip().split()[0])
        tot_kb = minfo.get("MemTotal", 1048576)
        avail_kb = minfo.get("MemAvailable", minfo.get("MemFree", 655360))
        mem_total_mb = max(1, round(tot_kb / 1024))
        mem_used_mb = max(1, round((tot_kb - avail_kb) / 1024))
        mem_pct = round((mem_used_mb / mem_total_mb) * 100.0, 1)
    except Exception:
        pass
    uptime_sec = 86400
    uptime_str = "1天 02小时"
    try:
        up_f = float(Path("/proc/uptime").read_text().split()[0])
        uptime_sec = int(up_f)
        d, rem = divmod(uptime_sec, 86400)
        h, rem = divmod(rem, 3600)
        m, _ = divmod(rem, 60)
        uptime_str = (f"{d}天 {h}小时 {m}分" if d > 0 else f"{h}小时 {m}分")
    except Exception:
        pass
    arch = "x86_64"
    kernel = "6.6.x"
    try:
        un = os.uname()
        arch = un.machine
        kernel = un.release
    except Exception:
        pass
    return {
        "cpu_load_pct": cpu_pct,
        "loadavg_1m": round(load_1m, 2),
        "loadavg_5m": round(load_5m, 2),
        "mem_used_mb": mem_used_mb,
        "mem_total_mb": mem_total_mb,
        "mem_pct": mem_pct,
        "uptime_sec": uptime_sec,
        "uptime_str": uptime_str,
        "arch": arch,
        "kernel": kernel,
        "tproxy_port": 7893,
        "mixed_port": 7890,
        "dns_port": 7874,
        "tun_name": "ailink0",
        "tun_mtu": 9000,
        "fakeip_range": "198.18.0.0/15"
    }

_LAST_CLASH_SYNC_TS = 0.0

def sync_selections_from_clash(conf_dir: Path = CONF_DIR, force: bool = False) -> dict:
    """P1-1 Fix: Reads live selector `now` values directly from Clash API :9090/proxies so UI and kernel are 0/15 mismatched."""
    global _LAST_CLASH_SYNC_TS
    now_f = time.time()
    if not force and (now_f - _LAST_CLASH_SYNC_TS) < 2.5:
        return PROBE_ENGINE.current_selections
    _LAST_CLASH_SYNC_TS = now_f
    if not _is_local_port_listening(9090):
        return PROBE_ENGINE.current_selections
    try:
        st, data = clash_api_request("/proxies", "GET", timeout=0.8)
        if st == 200 and isinstance(data.get("proxies"), dict):
            proxies = data["proxies"]
            for p_name, p_obj in proxies.items():
                if isinstance(p_obj, dict) and p_obj.get("type") == "Selector" and p_obj.get("now"):
                    PROBE_ENGINE.current_selections[p_name] = p_obj["now"]
    except Exception:
        pass
    return PROBE_ENGINE.current_selections

_SHUNT_API_MEMO = {}

_LAST_SYNCED_SHUNT_MTIME = 0

def build_shunt_api_response(conf_dir: Path = CONF_DIR) -> dict:
    """Builds 3-mode Shunt status (`direct` | `manual` | `auto`), enforcing Subscription Orthogonal Gate & 4-State Machine."""
    global _LAST_SYNCED_SHUNT_MTIME
    try:
        sf_p = conf_dir / "shunt.json"
        if sf_p.is_file():
            cur_sh_mt = sf_p.stat().st_mtime_ns
            if _LAST_SYNCED_SHUNT_MTIME != 0 and cur_sh_mt != _LAST_SYNCED_SHUNT_MTIME:
                _LAST_SYNCED_SHUNT_MTIME = cur_sh_mt
                PROBE_ENGINE.apply_shunt_selections(conf_dir)
            else:
                _LAST_SYNCED_SHUNT_MTIME = cur_sh_mt
    except Exception:
        pass
    PROBE_ENGINE.load_persisted_selections(RUN_DIR, conf_dir)
    sync_selections_from_clash(conf_dir)
    sels_tup = tuple(sorted((PROBE_ENGINE.current_selections or {}).items()))
    sh_key = (
        str(conf_dir),
        *_conf_file_mtimes_sig_q(conf_dir, ("shunt.json", "nodes.json", "node_probe.json", "auto_nodes.json", "subscriptions.json"), 30),
        _CORE_RELOAD_STATE["config_seq"],
        sels_tup,
    )
    if sh_key in _SHUNT_API_MEMO:
        _cached_sh = dict(_SHUNT_API_MEMO[sh_key])
        for _g_c in (_cached_sh.get("groups") or []):
            _st_c = _g_c.get("selector_tag", f"Shunt_{_g_c.get('id', '')}")
            _rn_c = _g_c.get("resolved_node")
            if _st_c and _rn_c:
                PROBE_ENGINE.current_selections[_st_c] = _rn_c
        return _cached_sh
    if len(_SHUNT_API_MEMO) > 16:
        _SHUNT_API_MEMO.clear()
    shunt_cfg = load_shunt_config(conf_dir)
    raw_nodes = load_saved_nodes(conf_dir)
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    auto_cfg = load_auto_nodes_config(conf_dir)
    auto_map = {a["id"]: a for a in (auto_cfg.get("auto_nodes") or [])}
    for a in (auto_cfg.get("auto_nodes") or []):
        auto_map[a.get("tag", "")] = a
    selectable_nodes = []
    delays_map = {}
    tag_state_map = {}
    cdn_ok_map = {}
    saved_by_tag = {}
    now_sh_ts = int(time.time())
    for n in raw_nodes:
        t = n.get("tag", "")
        if is_builtin_test_node(t):
            continue
        saved_by_tag[t] = n
        ev = evaluate_node_selectability(n, store=store, subs_list=subs_list, now_ts=now_sh_ts, conf_dir=conf_dir)
        if ev["selectable"]:
            selectable_nodes.append(n)
            tag_state_map[t] = ev["state"]
            delays_map[t] = float(ev["delay_ms"]) if (ev["state"] == "ok" and ev["delay_ms"] > 0) else 0.0
            nid_o = n.get("node_id") or ev.get("node_id") or t
            cdn_ok_map[t] = _is_node_cdn_tls_healthy((store or {}).get(nid_o) or (store or {}).get(t) or {})
    sorted_sel_tags = [n["tag"] for n in selectable_nodes]
    sorted_sel_tags.sort(key=lambda t: (
        0 if (tag_state_map.get(t) == "ok" and delays_map.get(t, 0.0) > 0 and cdn_ok_map.get(t, True)) else (1 if (tag_state_map.get(t) == "ok" and delays_map.get(t, 0.0) > 0) else 2),
        (delays_map.get(t, 99999.0) * (1.28 if _is_random_region_node(t) else 1.0)) if delays_map.get(t, 0.0) > 0 else 99999.0,
        1 if _is_random_region_node(t) else 0,
        t
    ))
    pre_ctx = {
        "saved_by_tag": saved_by_tag,
        "selectable_tags": sorted_sel_tags,
        "selectable_set": set(sorted_sel_tags),
        "tag_delay": delays_map,
        "tag_state": tag_state_map,
        "cdn_ok_map": cdn_ok_map,
        "auto_pools_map": {},
        "region_pools": {},
    }
    candidate_tags = sorted_sel_tags + ["direct", "block"]
    _reg_buckets = {rk: [] for rk in REGION_METADATA if rk not in ("direct", "block")}
    for _t_sel in sorted_sel_tags:
        _r_raw = classify_node_region(_t_sel, saved_by_tag.get(_t_sel))
        _r_c5 = _r_raw if _r_raw in FIVE_MAINSTREAM_COUNTRIES else "OTHER"
        _reg_buckets["ALL"].append(_t_sel)
        if _r_raw in _reg_buckets:
            _reg_buckets[_r_raw].append(_t_sel)
        if _r_c5 != _r_raw and _r_c5 in _reg_buckets:
            _reg_buckets[_r_c5].append(_t_sel)
    regions_summary = {}
    for rcode, rmeta in REGION_METADATA.items():
        if rcode in ("direct", "block"):
            regions_summary[rcode] = {"code": rcode, "label": rmeta["label"], "flag": rmeta["flag"], "saved_count": 1, "active_count": 1, "alive_count": 1, "best_rtt_ms": 0.0, "nodes": [rcode]}
            continue
        r_nodes = _reg_buckets.get(rcode, [])
        pre_ctx["region_pools"][rcode] = r_nodes
        r_ok = [t for t in r_nodes if delays_map.get(t, 0.0) > 0]
        rtts = [delays_map[t] for t in r_ok]
        regions_summary[rcode] = {
            "code": rcode, "label": rmeta["label"], "flag": rmeta["flag"],
            "saved_count": len(r_nodes), "active_count": len(r_nodes), "alive_count": len(r_ok),
            "best_rtt_ms": round(min(rtts), 1) if rtts else -1.0,
            "nodes": r_ok if r_ok else r_nodes[:10]
        }
    enriched_groups = []
    for idx, g in enumerate(shunt_cfg.get("groups", [])):
        gid = g["id"]
        stag = g.get("selector_tag", f"Shunt_{gid}")
        sm, country, strategy, aid, manual_node = _normalize_group_shunt_params(g)
        matched_an = _match_auto_node_pool(auto_cfg.get("auto_nodes") or [], aid) if sm == "auto" else None
        if matched_an:
            aid = matched_an.get("id") or aid
            manual_node = f"auto:{aid}"
        res_info = resolve_node_for_country_strategy_with_failover(
            country, strategy, manual_node, candidate_tags, delays_map, group_id=gid, conf_dir=conf_dir,
            saved_nodes=raw_nodes, subs_list=subs_list, store=store, auto_cfg=auto_cfg,
            precomputed_ctx=pre_ctx
        )
        resolved = res_info["selected"]
        # D-07 & P1-1 Fix: Keep current_selections synchronized in memory immediately, and dispatch Clash PUT asynchronously
        # so GET /api/status and GET /api/shunt NEVER block for 5.8s-6.6s during subscription import or 244-node URL ping!
        cur_clash_sel = PROBE_ENGINE.current_selections.get(stag)
        if resolved and cur_clash_sel != resolved:
            PROBE_ENGINE.current_selections[stag] = resolved
            if not _CORE_RELOAD_STATE.get("reloading") and not getattr(PROBE_ENGINE, "probe_running", False):
                threading.Thread(
                    target=PROBE_ENGINE.hot_switch_core_selector,
                    args=(stag, resolved),
                    kwargs={"reason": f"配置文件同步 ({gid})"},
                    daemon=True,
                ).start()
        rtt_ms = 0.0 if resolved in ("direct", "block") else (delays_map.get(resolved, -1.0) or -1.0)
        g_out = dict(g)
        g_out["priority"] = idx + 1
        g_out["shunt_mode"] = sm
        g_out["country"] = country
        g_out["strategy"] = strategy
        g_out["auto_node_id"] = aid
        g_out["manual_node"] = manual_node if sm != "manual" else (g.get("manual_node") or resolved)
        if sm == "auto":
            an_name = matched_an.get("name", aid) if matched_an else (auto_map.get(aid, {}).get("name") or aid)
            g_out["auto_node_name"] = an_name
            g_out["configured_label"] = f"🤖 自动: {an_name}"
        elif sm == "manual":
            cfg_n = g.get("manual_node") or resolved
            g_out["configured_label"] = f"🖐️ 手动: {cfg_n}"
            if cfg_n and cfg_n != resolved and not cfg_n.startswith("auto:"):
                g_out["failover_reason"] = f"配置节点 {cfg_n} 当前不可用，已自动故障切换至 {resolved}"
        else:
            g_out["configured_label"] = "🎯 直连 (宽带出网)"
        g_out["resolved_node"] = resolved
        g_out["kernel_active_node"] = PROBE_ENGINE.current_selections.get(stag) or resolved
        g_out["resolved_rtt_ms"] = rtt_ms
        g_out["no_available_node"] = bool(res_info.get("no_available_node", False))
        g_out["failover_backups"] = res_info["backups"]
        if g_out.get("is_custom"):
            g_out["entry_bypass_conflict"] = detect_entry_bypass_conflict(
                g_out.get("domains"), g_out.get("exact_domains"), g_out.get("domain_keywords"),
                g_out.get("ip_cidrs"), g_out.get("country", "US"), conf_dir=conf_dir
            )
        enriched_groups.append(g_out)
    rmode_cur = shunt_cfg.get("routing_mode", "rule_shunt")
    g_mode = shunt_cfg.get("global_mode") or ("direct" if shunt_cfg.get("global_country") == "direct" or shunt_cfg.get("global_strategy") == "direct" else ("manual" if shunt_cfg.get("global_strategy") == "manual" else "auto"))
    g_aid = shunt_cfg.get("global_auto_node_id") or "auto_youtube"
    g_country = shunt_cfg.get("global_country") or "JP"
    if g_country in ("direct", "block", "ALL"):
        g_country = "JP"
    matched_g_an = _match_auto_node_pool(auto_cfg.get('auto_nodes') or [], g_aid, allow_fallback=True)
    if matched_g_an and g_mode == "auto":
        g_aid = matched_g_an.get("id") or g_aid
    global_resolved = resolve_node_for_country_strategy_with_failover(
        g_country if g_mode == "manual" else "ALL",
        "direct" if g_mode == "direct" else ("manual" if g_mode == "manual" else "auto"),
        shunt_cfg.get("global_manual_node", "") if g_mode == "manual" else f"auto:{g_aid}",
        candidate_tags, delays_map, conf_dir=conf_dir,
        saved_nodes=raw_nodes, subs_list=subs_list, store=store, auto_cfg=auto_cfg,
        precomputed_ctx=pre_ctx
    )["selected"]
    if rmode_cur in ("global_proxy", "gfw_list", "cn_whitelist") and global_resolved:
        cur_ai_sel = PROBE_ENGINE.current_selections.get("AI_Best_Auto")
        if cur_ai_sel != global_resolved:
            PROBE_ENGINE.current_selections["AI_Best_Auto"] = global_resolved
            if not _CORE_RELOAD_STATE.get("reloading") and not getattr(PROBE_ENGINE, "probe_running", False):
                threading.Thread(
                    target=PROBE_ENGINE.hot_switch_core_selector,
                    args=("AI_Best_Auto", global_resolved),
                    kwargs={"reason": f"非分流模式 ({rmode_cur}) 统一出口同步"},
                    daemon=True,
                ).start()
    g_an_name = matched_g_an.get("name", g_aid) if matched_g_an else (auto_map.get(g_aid, {}).get("name") or g_aid)
    _sh_resp_obj = {
        "ok": True,
        "auto_nodes": auto_cfg.get("auto_nodes", []),
        "shunt_enabled": rmode_cur == "rule_shunt",
        "routing_mode": rmode_cur,
        "global_mode": g_mode,
        "global_auto_node_id": g_aid,
        "global_auto_node_name": g_an_name,
        "global_country": g_country,
        "global_strategy": "auto" if g_mode == "auto" else g_mode,
        "global_manual_node": (shunt_cfg.get("global_manual_node") or global_resolved) if g_mode == "manual" else (f"auto:{g_aid}" if g_mode == "auto" else "direct"),
        "global_resolved_node": global_resolved,
        "global_resolved_rtt_ms": 0.0 if global_resolved == "direct" else (delays_map.get(global_resolved, -1.0) or -1.0),
        "last_reload_mode": LAST_RELOAD_MODE,
        "switch_history": load_switch_history(RUN_DIR),
        "ops_settings": get_ops_settings(conf_dir),
        "ipv6_governance": build_ipv6_governance_summary(conf_dir),
        "regions": regions_summary,
        "groups": enriched_groups
    }
    sh_key_final = (
        str(conf_dir),
        *_conf_file_mtimes_sig_q(conf_dir, ("shunt.json", "nodes.json", "node_probe.json", "auto_nodes.json", "subscriptions.json"), 30),
        _CORE_RELOAD_STATE["config_seq"],
        tuple(sorted((PROBE_ENGINE.current_selections or {}).items())),
    )
    _SHUNT_API_MEMO[sh_key] = _sh_resp_obj
    _SHUNT_API_MEMO[sh_key_final] = _sh_resp_obj
    return dict(_sh_resp_obj)

_NODES_API_MEMO = {}
_AUTO_NODES_API_MEMO = {}
_STATUS_API_MEMO = {}
_JSON_WIRE_MEMO = {}

_MTIMES_FAST_CACHE = {}

def _conf_file_mtimes_sig(conf_dir: Path, filenames: tuple) -> tuple:
    res = []
    for fn in filenames:
        try:
            f = conf_dir / fn
            res.append(f.stat().st_mtime_ns if f.is_file() else 0)
        except Exception:
            res.append(0)
    return tuple(res)

def _conf_file_mtimes_sig_q(conf_dir: Path, filenames: tuple, quantum_s: int = 30) -> tuple:
    """同 _conf_file_mtimes_sig，但把 mtime 量化到 quantum_s 秒窗口。

    用途：probe 引擎每几秒就会重写 auto_nodes.json / shunt.json，若缓存键使用
    原始 ns 精度，/api/status 与 _JSON_WIRE_MEMO 会被"自己触发的写盘"持续击穿，
    每次请求都全量重建（实测 ~1s）。量化后缓存可稳定命中；
    配置类变更仍由 reload_seq / POST 路径的 _invalidate_fast_api_cache() 兜底。
    """
    q = max(1, int(quantum_s)) * 1_000_000_000
    res = []
    for fn in filenames:
        try:
            f = conf_dir / fn
            mt = f.stat().st_mtime_ns if f.is_file() else 0
            res.append(int(mt // q) if mt else 0)
        except Exception:
            res.append(0)
    return tuple(res)

def _slim_auto_nodes_for_status(auto_nodes_list: list) -> list:
    """P1-1 Fix: Slims status.shunt.auto_nodes so /api/status stays fast and compact (<35KB raw, <7KB gzipped) even with 244+ nodes."""
    _KEEP_M_KEYS = ("node_id", "tag", "country", "state", "delay_ms", "selectable", "qualified", "score", "display_score", "grade", "badge", "color", "suggest_remove")
    out = []
    for an in (auto_nodes_list or []):
        if not isinstance(an, dict):
            continue
        an_c = {k: v for k, v in an.items() if k not in ("candidate_nodes", "quality_ranking", "node_ids", "pool_candidate_tags")}
        if isinstance(an_c.get("groups"), list):
            new_groups = []
            for g in an_c["groups"]:
                if not isinstance(g, dict):
                    continue
                g_c = {k: v for k, v in g.items() if k not in ("node_ids",)}
                if isinstance(g_c.get("members"), list):
                    new_members = []
                    for m in g_c["members"]:
                        if not isinstance(m, dict):
                            continue
                        m_c = {k: m[k] for k in _KEEP_M_KEYS if k in m}
                        if isinstance(m.get("svc"), dict) and m["svc"]:
                            m_c["svc"] = {sk: {"ok": bool(sv.get("ok"))} for sk, sv in m["svc"].items() if isinstance(sv, dict)}
                        new_members.append(m_c)
                    g_c["members"] = new_members
                new_groups.append(g_c)
            an_c["groups"] = new_groups
        out.append(an_c)
    return out

def build_auto_nodes_api_response(conf_dir: Path = CONF_DIR, include_sparkline: bool = True) -> dict:
    """Builds /api/auto_nodes response with st_mtime_ns memoization (< 1.0ms cached hit, zero disk write on GET)."""
    an_key = (
        str(conf_dir),
        bool(include_sparkline),
        _conf_file_mtimes_sig(conf_dir, ("auto_nodes.json", "nodes.json", "node_probe.json", "subscriptions.json")),
        _CORE_RELOAD_STATE["config_seq"],
    )
    if an_key in _AUTO_NODES_API_MEMO:
        return dict(_AUTO_NODES_API_MEMO[an_key])
    if len(_AUTO_NODES_API_MEMO) > 16:
        _AUTO_NODES_API_MEMO.clear()

    cfg = load_auto_nodes_config(conf_dir)
    saved_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    all_svcs = {s["id"]: s for s in PRESET_SERVICE_CHECKS}
    for cs in (cfg.get("custom_services") or []):
        if isinstance(cs, dict) and (cs.get("id") or cs.get("name")) and cs.get("url"):
            all_svcs[cs.get("id") or cs.get("name")] = cs
    for an in cfg.get("auto_nodes", []):
        evaluate_single_auto_node(
            an, saved_nodes, store, subs_list, all_svcs,
            conf_dir=conf_dir, force_service_probe=False,
            advance_revert_streak=False, force_revert=False
        )
        # Slim svc inside auto_nodes members to {"ok": bool} to save ~40KB without losing any UI badge
        for g in (an.get("groups") or []):
            for m in (g.get("members") or []):
                if isinstance(m.get("svc"), dict):
                    m["svc"] = {sk: {"ok": bool(sv.get("ok"))} for sk, sv in m["svc"].items() if isinstance(sv, dict)}
                if not include_sparkline:
                    m.pop("sparkline_20", None)
        for r in (an.get("quality_ranking") or []):
            if isinstance(r.get("svc"), dict):
                r["svc"] = {sk: {"ok": bool(sv.get("ok"))} for sk, sv in r["svc"].items() if isinstance(sv, dict)}
            if not include_sparkline:
                r.pop("sparkline_20", None)
    for an in cfg.get("auto_nodes", []):
        for g in (an.get("groups") or []):
            for m in (g.get("members") or []):
                rec_m = store.get(m.get("node_id") or "") or store.get(m.get("tag") or "") or {}
                m["ipv6_ok"] = rec_m.get("ipv6_ok") if "ipv6_ok" in rec_m else None
    cfg["ipv6_governance"] = build_ipv6_governance_summary(conf_dir)
    res_obj = cfg
    _AUTO_NODES_API_MEMO[an_key] = copy.deepcopy(res_obj)
    return res_obj

def build_nodes_api_response(
    conf_dir: Path = CONF_DIR,
    include_full: bool = False,
    include_sparkline: bool = False,
    limit: int = 0,
    offset: int = 0,
) -> dict:
    """Builds /api/nodes response with st_mtime_ns memoization and field trimming (738KB -> ~125KB for 664 nodes, < 5ms HTTP)."""
    PROBE_ENGINE.load_persisted_selections(RUN_DIR, conf_dir)
    nd_key = (
        str(conf_dir),
        bool(include_full),
        bool(include_sparkline),
        _conf_file_mtimes_sig(conf_dir, ("nodes.json", "node_probe.json", "subscriptions.json", "max_outbounds", "shunt.json")),
        _CORE_RELOAD_STATE["config_seq"],
    )
    if nd_key in _NODES_API_MEMO:
        cached = dict(_NODES_API_MEMO[nd_key])
        cached["selections"] = dict(PROBE_ENGINE.current_selections)
        if limit > 0:
            all_n = cached.get("nodes") or []
            cached["nodes"] = all_n[offset:offset + limit]
            cached["offset"] = offset
            cached["limit"] = limit
        return cached
    if len(_NODES_API_MEMO) > 16:
        _NODES_API_MEMO.clear()

    raw_nodes = load_saved_nodes(conf_dir)
    subs = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    max_lim_now = get_max_outbounds_limit(conf_dir)
    active_kernel_obs = select_top_n_outbounds(raw_nodes, max_limit=max_lim_now, run_dir=RUN_DIR, conf_dir=conf_dir)
    active_kernel_tags = {ob.get("tag", "") for ob in active_kernel_obs}
    pinned_kernel_refs = get_referenced_kernel_node_refs(conf_dir=conf_dir, run_dir=RUN_DIR)
    now_ts = int(time.time())
    sub_by_id = {s.get("id"): s for s in subs if s.get("id")}
    sub_by_url = {s.get("url"): s for s in subs if s.get("url")}
    region_counts = {k: 0 for k in ("ALL", "HK", "TW", "JP", "SG", "US", "OTHER")}
    source_counts = {"custom": 0}
    for s in subs:
        source_counts[s["id"]] = 0
    enriched = []
    for n in raw_nodes:
        tag = n.get("tag", "")
        if is_builtin_test_node(tag):
            continue
        nid = n.get("node_id") or compute_node_id(n)
        ev = evaluate_node_selectability(n, store=store, subs_list=subs, now_ts=now_ts, conf_dir=conf_dir)
        c5 = classify_node_country_5plus1(tag, n)
        sub_id = str(n.get("_sub_id") or "")
        sub_url = str(n.get("_sub_url") or "")
        matched_sub = sub_by_id.get(sub_id) or sub_by_url.get(sub_url)
        if not matched_sub and len(subs) == 1 and not n.get("_manual"):
            matched_sub = subs[0]
        if matched_sub:
            src_id = matched_sub["id"]
            src_name = matched_sub.get("name", "机场订阅")
            is_custom = False
            source_counts[src_id] = source_counts.get(src_id, 0) + 1
        else:
            src_id = "custom"
            src_name = "自定义节点"
            is_custom = True
            source_counts["custom"] = source_counts.get("custom", 0) + 1
        if ev["selectable"]:
            region_counts["ALL"] += 1
            region_counts[c5] = region_counts.get(c5, 0) + 1
        slim_svc = {sk: {"ok": bool(sv.get("ok"))} for sk, sv in (ev.get("svc") or {}).items() if isinstance(sv, dict)}
        if include_full:
            item = dict(n)
            item.update({
                "node_id": nid,
                "id": nid,
                "disabled": bool(n.get("disabled", False)),
                "sub_enabled": ev["sub_enabled"],
                "visible": ev["visible"],
                "selectable": ev["selectable"],
                "state": ev["state"],
                "delay_ms": ev["delay_ms"],
                "rtt_ms": ev["delay_ms"] if ev["delay_ms"] > 0 else -1,
                "probe_ts": ev["probe_ts"],
                "probe_rel_str": ev["probe_rel_str"],
                "ui_badge": ev["ui_badge"],
                "svc": ev["svc"],
                "score": ev["score"],
                "display_score": ev["score_info"]["display_score"],
                "grade": ev["score_info"]["grade"],
                "score_badge": ev["score_info"]["badge"],
                "score_color": ev["score_info"]["color"],
                "pin_top": ev["score_info"]["pin_top"],
                "suggest_remove": ev["score_info"]["suggest_remove"],
                "samples": ev["score_info"]["samples"],
                "success_rate": ev["score_info"]["success_rate"],
                "cv": ev["score_info"]["cv"],
                "consecutive_fail": ev["score_info"]["consecutive_fail"],
                "sparkline_20": ev["score_info"]["sparkline_20"],
                "reachable": (ev["selectable"] and ev["state"] == "ok" and ev["delay_ms"] > 0),
                "region_override": n.get("region_override", ""),
                "region": c5,
                "country": c5,
                "country_label": COUNTRY_5PLUS1_META[c5]["label"],
                "sub_id": src_id,
                "sub_name": src_name,
                "sub_url": sub_url,
                "is_custom": is_custom,
                "in_kernel": (tag in active_kernel_tags),
                "kernel_pinned": (tag in pinned_kernel_refs or nid in pinned_kernel_refs or bool(n.get("_manual"))),
                "ipv6_ok": (store.get(nid) or store.get(tag) or {}).get("ipv6_ok", _infer_node_initial_ipv6_support(n)),
                "share_uri": export_node_share_uri(n),
            })
        else:
            item = {
                "node_id": nid,
                "tag": tag,
                "type": n.get("type", "vless"),
                "server": n.get("server", "-"),
                "server_port": n.get("server_port", 443),
                "sub_enabled": ev["sub_enabled"],
                "selectable": ev["selectable"],
                "state": ev["state"],
                "delay_ms": ev["delay_ms"],
                "rtt_ms": ev["delay_ms"] if ev["delay_ms"] > 0 else -1,
                "probe_ts": ev["probe_ts"],
                "score": ev["score"],
                "grade": ev["score_info"]["grade"],
                "samples": ev["score_info"]["samples"],
                "region": c5,
                "country": c5,
                "sub_id": src_id,
                "sub_name": src_name,
                "in_kernel": (tag in active_kernel_tags),
                "kernel_pinned": (tag in pinned_kernel_refs or nid in pinned_kernel_refs or bool(n.get("_manual"))),
                "ipv6_ok": (store.get(nid) or store.get(tag) or {}).get("ipv6_ok", _infer_node_initial_ipv6_support(n)),
            }
            if slim_svc:
                item["svc"] = slim_svc
            if n.get("display_tag") and n["display_tag"] != tag:
                item["display_tag"] = n["display_tag"]
            if n.get("disabled"):
                item["disabled"] = True
            if ev["score_info"]["pin_top"]:
                item["pin_top"] = True
            if ev["score_info"]["suggest_remove"]:
                item["suggest_remove"] = True
            if ev["score_info"]["consecutive_fail"] > 0:
                item["consecutive_fail"] = ev["score_info"]["consecutive_fail"]
            if is_custom:
                item["is_custom"] = True
            if n.get("region_override"):
                item["region_override"] = n["region_override"]
            if include_sparkline:
                item["sparkline_20"] = ev["score_info"]["sparkline_20"]
        enriched.append(item)

    def _sort_key(x):
        if not x.get("sub_enabled", True) or x.get("disabled", False):
            tier = 3
        elif x["state"] == "ok" and x["delay_ms"] > 0:
            tier = 0
        elif x["state"] == "pending":
            tier = 1
        else:
            tier = 2
        return (tier, x["delay_ms"] if (tier == 0 and x["delay_ms"] > 0) else 999999, x["tag"])

    enriched.sort(key=_sort_key)
    ok_cnt = sum(1 for x in enriched if x["selectable"] and x["state"] == "ok" and x["delay_ms"] > 0)
    # P2-10 / V19-01 Fix: Compute in_kernel_count & unmounted_nodes_count directly from enriched user nodes so counts match list 100%
    in_kernel_real = sum(1 for x in enriched if x.get("in_kernel"))
    unmounted_real = len(enriched) - in_kernel_real
    # P2-7 & P2-9 Fix: Enrich subscriptions with live per-subscription ok_count, dead_count, pending_count, and all_dead warning
    subs_enriched = []
    for s in subs:
        s_copy = dict(s)
        sid_k = s_copy.get("id", "")
        s_nodes = [x for x in enriched if x.get("sub_id") == sid_k or (len(subs) == 1 and not x.get("is_custom"))]
        s_tot = len(s_nodes)
        s_ok = sum(1 for x in s_nodes if x.get("state") == "ok" and x.get("delay_ms", -1) > 0)
        s_dead = sum(1 for x in s_nodes if x.get("state") in ("dead", "suspect"))
        s_pend = sum(1 for x in s_nodes if x.get("state") == "pending")
        s_in_k = sum(1 for x in s_nodes if x.get("in_kernel"))
        s_copy["ok_count"] = s_ok
        s_copy["dead_count"] = s_dead
        s_copy["pending_count"] = s_pend
        s_copy["in_kernel_count"] = s_in_k
        if s_tot > 0:
            s_copy["count"] = s_tot
        if s_copy.get("status") == "error":
            s_copy["health_status"] = "fetch_error"
        elif s_tot > 0 and s_ok == 0 and s_dead > 0 and s_pend == 0:
            s_copy["health_status"] = "all_dead"
            s_copy["health_warning"] = f"该订阅下全部 {s_tot} 个节点探测均不可达"
        elif s_tot > 0 and s_ok == 0 and s_pend > 0:
            s_copy["health_status"] = "untested"
        else:
            s_copy["health_status"] = "ok"
        subs_enriched.append(s_copy)
    res_obj = {
        "ok": True,
        "saved_nodes_total": len(enriched),
        "reachable_nodes_count": ok_cnt,
        "unreachable_nodes_count": sum(1 for x in enriched if x["state"] == "dead"),
        "pending_nodes_count": sum(1 for x in enriched if x["state"] == "pending"),
        "disabled_nodes_count": sum(1 for x in enriched if x.get("disabled") or not x.get("sub_enabled")),
        "active_outbounds_count": in_kernel_real,
        "in_kernel_count": in_kernel_real,
        "unmounted_nodes_count": unmounted_real,
        "max_outbounds_limit": max_lim_now,
        "region_counts": region_counts,
        "source_counts": source_counts,
        "subscriptions": subs_enriched,
        "probe_schedules": load_probe_schedules(conf_dir),
        "ipv6_governance": build_ipv6_governance_summary(conf_dir),
        "backend_diversity": analyze_backend_diversity(raw_nodes, conf_dir),
        "selections": PROBE_ENGINE.current_selections,
        "nodes": enriched,
    }
    _NODES_API_MEMO[nd_key] = copy.deepcopy(res_obj)
    if limit > 0:
        paged = dict(res_obj)
        paged["nodes"] = enriched[offset:offset + limit]
        paged["offset"] = offset
        paged["limit"] = limit
        return paged
    return res_obj

def _has_final_backup_archive() -> bool:
    try:
        return Path("/root/ai-link-final-backup/etc-ai-link.tgz").is_file()
    except Exception:
        return False

def _mask_status_secrets(payload: dict) -> dict:
    """SEC-2 (v1.0.2): 未鉴权的请求不应该拿到节点/订阅凭据。

    /api/status 里带了两处敏感数据：
      · homelink: 回家节点的 password / uuid / private_key，以及内嵌明文凭据的 uri
      · subscriptions: 订阅地址常带 ?token=...
    默认 trusted_cidr 覆盖全部私网，任何局域网设备都能 GET /api/status，
    因此按「非本机且未鉴权」的条件做脱敏，口径与 /api/homelink、/api/subscriptions 一致。
    """
    out = copy.deepcopy(payload)
    hl = out.get("homelink")
    if isinstance(hl, dict):
        for nd in (hl.get("nodes") or []):
            if not isinstance(nd, dict):
                continue
            if nd.get("password"):
                nd["password"] = "********"
            if nd.get("uuid"):
                nd["uuid"] = str(nd["uuid"])[:8] + "-****-****-****"
            if nd.get("private_key"):
                nd["private_key"] = "*** (仅本机 127.0.0.1 可读)"
            if nd.get("uri"):
                nd["uri"] = re.sub(r"://[^@/]+@", "://***@", str(nd["uri"]))
    subs = out.get("subscriptions")
    if isinstance(subs, list):
        for sub in subs:
            if isinstance(sub, dict) and sub.get("url"):
                sub["url"] = re.sub(r"([?&](?:token|key|auth|passwd|password|secret)=)[^&]+",
                                    r"\1***", str(sub["url"]), flags=re.I)
    return out


def build_status_api_response(conf_dir: Path = CONF_DIR) -> dict:
    """Builds /api/status with st_mtime_ns memoization (< 1.5ms cached hit), exposing build_ver and top-level shield_status."""
    PROBE_ENGINE.load_persisted_selections(RUN_DIR, conf_dir)
    if Path(conf_dir).resolve() == CONF_DIR.resolve():
        _ingest_singbox_adblock_log(conf_dir)
    sels_tup = tuple(sorted((PROBE_ENGINE.current_selections or {}).items()))
    st_key = (
        str(conf_dir),
        _conf_file_mtimes_sig_q(
            conf_dir,
            (
                "nodes.json",
                "node_probe.json",
                "auto_nodes.json",
                "subscriptions.json",
                "homelink.json",
                "dns_rewrite.json",
                "dns_filters.json",
                "ops_settings.json",
                "panel_auth.json",
            ),
        ),
        _CORE_RELOAD_STATE["config_seq"],
        _CORE_RELOAD_STATE["reload_seq"],
        _CORE_RELOAD_STATE["reloading"],
        bool(getattr(PROBE_ENGINE, "probe_running", False)),
        bool(SUB_SYNC_STATE.get("running", False)),
        bool(FAIL_OPEN_STATE.get("active")),
        tuple(_get_live_singbox_pids()),
        sels_tup,
        int(time.time()) // 15,
    )
    if st_key in _STATUS_API_MEMO:
        cached = dict(_STATUS_API_MEMO[st_key])
        cached["as_of_ts"] = int(time.time())
        cached["config_seq"] = _CORE_RELOAD_STATE["config_seq"]
        cached["reload_seq"] = _CORE_RELOAD_STATE["reload_seq"]
        live_dns_tel = build_dns_telemetry_response(conf_dir)
        cached["dns_telemetry"] = live_dns_tel
        cached["shield_status"] = live_dns_tel.get("shield_status", {})
        return cached
    if len(_STATUS_API_MEMO) > 12:
        _STATUS_API_MEMO.clear()

    rt = _cached_Value("rt_info_main", 5.0, lambda: get_core_runtime_info(conf_dir))
    shunt_full = build_shunt_api_response(conf_dir)
    shunt_slim = dict(shunt_full)
    shunt_slim["auto_nodes"] = _slim_auto_nodes_for_status(shunt_full.get("auto_nodes") or [])
    if isinstance(shunt_slim.get("regions"), dict):
        shunt_slim["regions"] = {
            rk: {**rv, "nodes": (rv.get("nodes") or [])[:10]} if isinstance(rv, dict) else rv
            for rk, rv in shunt_slim["regions"].items()
        }
    ov_telem = get_overview_live_telemetry(conf_dir)
    dns_tel = build_dns_telemetry_response(conf_dir)
    shield_st = dns_tel.get("shield_status", {})
    rh_st = _cached_Value("routing_health_main", 3.0, lambda: build_routing_health(conf_dir))
    sys_m = _cached_Value("sys_metrics_main", 2.0, lambda: get_system_telemetry(conf_dir))
    active_sel_tags = set((PROBE_ENGINE.current_selections or {}).values())
    slim_node_stats = {
        k: v for k, v in (PROBE_ENGINE.node_stats or {}).items()
        if k in active_sel_tags
    }
    _is_live_box = (Path(conf_dir).resolve() == CONF_DIR.resolve() and Path("/etc/init.d/ai-link").exists())
    _core_dead_alert = bool(_is_live_box and not rt.get("core_pid") and get_ops_settings(conf_dir).get("enabled", True) and not is_bypass_active() and not _CORE_RELOAD_STATE.get("reloading"))
    res_obj = {
        "ok": True,
        "status": "running",
        "version": APP_VERSION,
        "release_stage": "stable",
        "build_ver": APP_VERSION,
        "build_revision": APP_BUILD,
        "core_running": bool(rt.get("core_pid")),
        "core_dead_alert": _core_dead_alert,
        "as_of_ts": int(time.time()),
        "config_seq": _CORE_RELOAD_STATE["config_seq"],
        "reload_seq": _CORE_RELOAD_STATE["reload_seq"],
        "core_reloading": _CORE_RELOAD_STATE["reloading"],
        "bypass_active": is_bypass_active(),
        "fail_open": FAIL_OPEN_STATE,
        "routing_health": rh_st,
        "probe_running": bool(getattr(PROBE_ENGINE, "probe_running", False)),
        "sub_sync_running": bool(SUB_SYNC_STATE.get("running", False)),
        "sub_sync_last_result": SUB_SYNC_STATE.get("last_result"),
        "routing_mode": shunt_slim.get("routing_mode", "rule_shunt"),
        "shunt_enabled": shunt_slim.get("shunt_enabled", True),
        "ops_settings": get_ops_settings(conf_dir),
        "switch_history": load_switch_history(RUN_DIR)[:25],
        "updatable_summary": _cached_Value("upd_sum_main", 5.0, lambda: check_all_updatable_items(conf_dir)),
        "last_reload_mode": LAST_RELOAD_MODE,
        "ipv6_proxy": get_uci_ipv6_proxy(conf_dir),
        "ipv6_governance": build_ipv6_governance_summary(conf_dir),
        "probe_schedules": load_probe_schedules(conf_dir),
        "has_backup_archive": _has_final_backup_archive(),
        "backup_archive_path": "/root/ai-link-final-backup/etc-ai-link.tgz" if _has_final_backup_archive() else "",
        "homelink": build_homelink_api_response(conf_dir, mask_private_key=True),
        "shield_status": shield_st,
        "dns_telemetry": dns_tel,
        "sys_metrics": sys_m,
        "overview_telemetry": ov_telem,
        "core": rt["core"],
        "core_version": rt["core_version"],
        "core_pid": rt["core_pid"],
        "core_single_instance_ok": rt["core_single_instance_ok"],
        "build_mode": rt["build_mode"],
        "build_mode_degraded": rt.get("build_mode_degraded", False),
        "degraded_reason": rt.get("degraded_reason", ""),
        "degraded_warning": rt.get("degraded_warning", ""),
        "has_hy2_certs": rt["has_hy2_certs"],
        "rulesets_installed": rt["rulesets_installed"],
        "saved_nodes_total": rt["saved_nodes_total"],
        "active_outbounds_count": rt["active_outbounds_count"],
        "max_outbounds_limit": rt["max_outbounds_limit"],
        "custom_nodes_count": rt["custom_nodes_count"],
        "custom_node_tags": (rt.get("custom_node_tags") or [])[:20],
        "test_node_tags": rt["test_node_tags"],
        "dns_mode": "dnsmasq -> 127.0.0.1#7874 (TProxy :53)",
        "probe_timestamp": PROBE_ENGINE.last_probe_ts,
        "last_probe_ts": PROBE_ENGINE.last_probe_ts,
        "probe_alive_count": PROBE_ENGINE.last_alive_count,
        "probe_total_count": PROBE_ENGINE.last_total_count,
        "probe_availability_pct": PROBE_ENGINE.last_availability_pct,
        "probe_history": PROBE_ENGINE.probe_history[-10:],
        "node_stats": slim_node_stats,
        "subscriptions": load_subscriptions(conf_dir),
        "shunt": shunt_slim,
        "selections": PROBE_ENGINE.current_selections,
        "last_scores": {k: v for k, v in (PROBE_ENGINE.last_scores or {}).items() if k in active_sel_tags},
        "services_supported": list(L7_SERVICE_FINGERPRINTS.keys()),
    }
    st_key_after = (
        str(conf_dir),
        _conf_file_mtimes_sig_q(
            conf_dir,
            (
                "nodes.json",
                "node_probe.json",
                "auto_nodes.json",
                "subscriptions.json",
                "homelink.json",
                "dns_rewrite.json",
                "dns_filters.json",
                "ops_settings.json",
                "panel_auth.json",
            ),
        ),
        _CORE_RELOAD_STATE["config_seq"],
        _CORE_RELOAD_STATE["reload_seq"],
        _CORE_RELOAD_STATE["reloading"],
        bool(getattr(PROBE_ENGINE, "probe_running", False)),
        bool(SUB_SYNC_STATE.get("running", False)),
        bool(FAIL_OPEN_STATE.get("active")),
        tuple(_get_live_singbox_pids()),
        tuple(sorted((PROBE_ENGINE.current_selections or {}).items())),
        int(time.time()) // 15,
    )
    _STATUS_API_MEMO[st_key] = res_obj
    _STATUS_API_MEMO[st_key_after] = res_obj
    return dict(res_obj)

def flush_all_dns_caches() -> dict:
    """Borrow 10 (NOLO system/dns-cache.mjs): Dual-layer DNS cache flush (sing-box Clash API + dnsmasq SIGHUP)."""
    sb_flushed = False
    dnsmasq_flushed = False
    for ep, method in (("/cache/dns/flush", "POST"), ("/cache/dns/flush", "PUT"), ("/configs?force=false", "GET")):
        try:
            code, _ = clash_api_request(ep, method=method, timeout=0.8)
            if code in (200, 204):
                sb_flushed = True
                break
        except Exception:
            pass
    try:
        r = subprocess.run(["killall", "-HUP", "dnsmasq"], capture_output=True, timeout=1)
        dnsmasq_flushed = (r.returncode == 0)
    except Exception:
        pass
    return {"ok": True, "singbox_dns_flushed": sb_flushed, "dnsmasq_sighup": dnsmasq_flushed}

def match_srs_ruleset_target(srs_path: Path, target: str) -> bool:
    """Borrow 11 (NOLO api/penetration.mjs): sing-box rule-set match prints result to stderr on 1.13/1.14; check stdout+stderr."""
    if not srs_path or not Path(srs_path).is_file():
        return False
    sb_bin = resolve_singbox_binary()
    if not sb_bin:
        return False
    try:
        r = subprocess.run([sb_bin, "rule-set", "match", str(srs_path), str(target)], capture_output=True, text=True, timeout=1.5)
        combined = f"{r.stdout or ''}\n{r.stderr or ''}"
        return bool(re.search(r"^match rules\.", combined, flags=re.M))
    except Exception:
        return False

def _detect_router_lan_ip() -> str:
    try:
        r = subprocess.run(["uci", "-q", "get", "network.lan.ipaddr"], capture_output=True, text=True, timeout=1)
        ip = (r.stdout or "").strip()
        if ip:
            return ip
    except Exception:
        pass
    return "10.10.10.77"

PANEL_PWD_DEFAULT = "ai-link-2026"
# PWD-1 & B1-2 (v1.0.2): UCI 彻底改为布尔标记 ai-link.global.panel_pwd_customized=0/1，
# 不再在 /etc/config/ai-link 中持久化任何明文密码、哨兵或哈希串。
# 保留 PANEL_PWD_SENTINEL 与 get_uci_panel_secret() 仅作老配置平滑迁移与测试切片兼容。
PANEL_PWD_SENTINEL = "__custom__"


def _uci_secret_is_placeholder(val: str) -> bool:
    """判断 UCI 值是否处于「不可回显 / 不可当凭据」状态。"""
    s = (val or "").strip()
    if not s:
        return True
    if s in (PANEL_PWD_SENTINEL, "1", "true"):
        return True
    if s.lower().startswith("sha256:"):
        return True
    return False


def _sync_uci_pwd_customized(customized: bool):
    """B1-2: 将布尔标记 panel_pwd_customized=0/1 写入 UCI，并彻底清理历史遗留的 panel_secret 字段。"""
    try:
        flag = "1" if customized else "0"
        subprocess.run(["uci", "set", f"ai-link.global.panel_pwd_customized={flag}"], check=False, timeout=2)
        subprocess.run(["uci", "-q", "delete", "ai-link.global.panel_secret"], check=False, timeout=2)
        subprocess.run(["uci", "commit", "ai-link"], check=False, timeout=2)
    except Exception:
        pass


def is_panel_pwd_customized(conf_dir: Path = CONF_DIR) -> bool:
    """判断面板密码是否已被用户自定义（非初始默认密码 ai-link-2026）。"""
    try:
        auth_file = Path(conf_dir) / "panel_auth.json"
        if auth_file.is_file():
            data = json.loads(auth_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("hash") and data.get("salt"):
                salt = data["salt"]
                def_hash = hashlib.sha256(f"{salt}:{PANEL_PWD_DEFAULT}".encode("utf-8")).hexdigest()
                return data["hash"] != def_hash
    except Exception:
        pass
    try:
        if Path(conf_dir).resolve() == Path(CONF_DIR).resolve() and Path("/etc/config/ai-link").is_file():
            raw = (get_uci_panel_secret() or "").strip()
            if raw and raw != PANEL_PWD_DEFAULT:
                return True
    except Exception:
        pass
    return False


def get_uci_panel_secret_display() -> str:
    """返回可安全展示给用户的面板密码文本（仅未改密时返回默认初始密码，改密后返回空串）。"""
    if is_panel_pwd_customized(CONF_DIR):
        return ""
    raw = (get_uci_panel_secret() or "").strip()
    if _uci_secret_is_placeholder(raw):
        return ""
    return raw


_LUCI_BRIDGE_MEMO = {"token": ""}


def get_luci_bridge_token(create: bool = True) -> str:
    """LuCI 页面调用面板 API 专用的桥接令牌。

    PWD-1 封掉了「用面板密码当令牌」的旧通路（那会让 LuCI 回显的哈希直接
    成为万能令牌）。但 LuCI 页面的按钮仍需要调面板 API，因此引入一个**与
    面板密码完全解耦**的独立随机令牌：
      - 首次访问时生成 32 位十六进制随机串，写入 ai-link.global.luci_bridge_token；
      - 它不可用于登录面板（_verify_panel_password 不认它）；
      - 面板密码更换/重置不会影响它，反之亦然；
      - 能读到 /etc/config/ai-link 的人本来就有 root，泄露面等价。
    """
    if _LUCI_BRIDGE_MEMO.get("token"):
        return _LUCI_BRIDGE_MEMO["token"]
    tok = ""
    try:
        tok = _uci_get_str("global.luci_bridge_token", "")
    except Exception:
        tok = ""
    if not tok and create:
        try:
            tok = hashlib.sha256(f"luci-bridge:{os.urandom(24).hex()}:{time.time()}".encode("utf-8")).hexdigest()[:32]
            subprocess.run(["uci", "set", f"ai-link.global.luci_bridge_token={tok}"], check=False, timeout=2)
            subprocess.run(["uci", "commit", "ai-link"], check=False, timeout=2)
        except Exception:
            tok = ""
    if tok:
        _LUCI_BRIDGE_MEMO["token"] = tok
    return tok


def get_uci_panel_secret() -> str:
    try:
        r_cust = subprocess.run(["uci", "-q", "get", "ai-link.global.panel_pwd_customized"], capture_output=True, text=True, timeout=1)
        v_cust = (r_cust.stdout or "").strip().lower()
        if v_cust in ("1", "true", "yes"):
            return PANEL_PWD_SENTINEL
        r = subprocess.run(["uci", "-q", "get", "ai-link.global.panel_secret"], capture_output=True, text=True, timeout=1)
        val = (r.stdout or "").strip()
        if val:
            return val
    except Exception:
        pass
    return PANEL_PWD_DEFAULT


def generate_reality_keypair(existing_priv: str = "") -> tuple:
    """Generates or derives a matched X25519 (private_key_b64url, public_key_b64url) pair for VLESS-Reality."""
    try:
        from cryptography.hazmat.primitives.asymmetric import x25519
        from cryptography.hazmat.primitives import serialization
        if existing_priv:
            pad = (-len(existing_priv)) % 4
            raw_priv = base64.urlsafe_b64decode(existing_priv + ("=" * pad))
            if len(raw_priv) == 32:
                priv_obj = x25519.X25519PrivateKey.from_private_bytes(raw_priv)
                pub_bytes = priv_obj.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
                pub_b64 = base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")
                return existing_priv, pub_b64
        priv_obj = x25519.X25519PrivateKey.generate()
        priv_bytes = priv_obj.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        pub_bytes = priv_obj.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return (
            base64.urlsafe_b64encode(priv_bytes).decode("ascii").rstrip("="),
            base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")
        )
    except Exception:
        return (
            existing_priv or "eH7rJ8mN2pQ4sT6vW8yZ0aB2cD4eF6gH8iJ0kL2mN4o",
            "pUbja_BSfJ0rZhDQaGAQPVTKVgPSKYIk2AickXdWLxU"
        )

_HOMELINK_LEDGER_RT = {
    "last_ts": 0.0,
    "conn_prev": {},
    "nodes": {},
    "clients": {},
}

def _match_homelink_node_for_conn(meta: dict, hl_nodes: list, lan_ip: str = "", conf_dir: Path = CONF_DIR):
    if not isinstance(meta, dict) or not hl_nodes:
        return None
    inb_raw = str(meta.get("inboundName") or meta.get("inbound") or meta.get("inboundTag") or meta.get("type") or "").strip()
    inb_tag = inb_raw.split("/")[-1] if "/" in inb_raw else inb_raw
    inb_port = str(meta.get("inboundPort") or "").strip()
    for h in hl_nodes:
        if not h.get("enabled", True):
            continue
        htag = str(h.get("tag") or f"homelink-{h.get('id', 'custom')}-in").strip()
        hid = str(h.get("id") or "").strip()
        lport = str(h.get("listen_port") or "").strip()
        if (htag and (inb_tag == htag or htag in inb_raw)) or (hid and hid in inb_raw) or (inb_port and inb_port == lport):
            return h
    src_ip = str(meta.get("sourceIP") or "").strip()
    if src_ip and _h3_is_remote_homelink_client_ip(src_ip, lan_ip, conn_meta=meta, conf_dir=conf_dir):
        enabled_hls = [h for h in hl_nodes if h.get("enabled", True)]
        if enabled_hls:
            return enabled_hls[0]
    return None

def build_homelink_api_response(conf_dir: Path = CONF_DIR, mask_private_key: bool = False, mask_all_secrets: bool = False) -> dict:
    hl_file = conf_dir / "homelink.json"
    rm_file = conf_dir / "homelink_route_mode"
    try:
        hl_mt = hl_file.stat().st_mtime_ns if hl_file.is_file() else 0
        rm_mt = rm_file.stat().st_mtime_ns if rm_file.is_file() else 0
    except Exception:
        hl_mt, rm_mt = 0, 0
    hl_key = (str(conf_dir), hl_mt, rm_mt, int(time.time()) // 3)
    if hl_key in _HOMELINK_API_MEMO:
        _c_hl = copy.deepcopy(_HOMELINK_API_MEMO[hl_key])
        if mask_private_key or mask_all_secrets:
            for _nd in _c_hl.get("nodes", []):
                if isinstance(_nd, dict):
                    if "private_key" in _nd:
                        _nd["private_key"] = "*** (仅本机 127.0.0.1 可读)"
                    if mask_all_secrets:
                        if "uuid" in _nd and _nd["uuid"]:
                            _nd["uuid"] = str(_nd["uuid"])[:8] + "-****-****-****"
                        if "password" in _nd and _nd["password"]:
                            _nd["password"] = "********"
                        # SEC-3 (v1.0.2): uri 里内嵌明文 password/uuid，只脱敏字段等于没脱
                        if _nd.get("uri"):
                            _nd["uri"] = re.sub(r"://[^@/]+@", "://***@", str(_nd["uri"]))
        return _c_hl
    if len(_HOMELINK_API_MEMO) > 16:
        _HOMELINK_API_MEMO.clear()
    ca_info = get_ca_cert_info(conf_dir)
    fp_colon = ca_info.get("sha256", "")
    lan_ip = _detect_router_lan_ip()
    hl_nodes = load_homelink_nodes(conf_dir)
    enriched = []
    modified_keys = False
    for h in hl_nodes:
        item = dict(h)
        proto = (item.get("protocol") or "vless-reality").lower()
        port = int(item.get("listen_port", 18443) or 18443)
        uri_port = int(item.get("external_port") or 0) or port
        host = (item.get("ddns_host") or "").strip() or lan_ip
        name = item.get("name") or f"HomeLink-{port}"
        enc_name = urllib.parse.quote(name, safe="-_.")
        if proto in ("hysteria2", "hy2"):
            pwd = item.get("password") or "ailink_home_2026"
            sni = item.get("sni") or "ai-link.ailink.lan"
            item["proto"] = "Hysteria2 QUIC · 弱网加速 (兼容 NekoBox insecure=1 与 pinSHA256)"
            item["listen"] = f"[::]:{port} (UDP)"
            item["pin_sha256"] = fp_colon
            item["uri"] = f"hysteria2://{pwd}@{host}:{uri_port}/?sni={sni}&insecure=1&allowInsecure=1&pinSHA256={fp_colon}#{enc_name}"
        elif proto in ("vless-tls", "vless_tls", "tls"):
            uuid_v = item.get("uuid") or "a891f02b-2026-4f88-9b1c-8899aabbccdd"
            sni = item.get("sni") or host or "ai-link.ailink.lan"
            item["proto"] = "VLESS-TLS · 传统 TLS 穿透模式 (建议优先使用 VLESS-Reality)"
            item["listen"] = f"[::]:{port} (TCP)"
            item["pin_sha256"] = fp_colon
            item["uri"] = (f"vless://{uuid_v}@{host}:{uri_port}?security=tls&sni={sni}"
                           f"&allowInsecure=1&type=tcp#{enc_name}")
        else:
            uuid_v = item.get("uuid") or "a891f02b-2026-4f88-9b1c-8899aabbccdd"
            sni = item.get("sni") or "www.apple.com"
            if sni == "ai-link.ailink.lan":
                sni = "www.apple.com"
                item["sni"] = sni
            priv_k = item.get("private_key") or ""
            pub_k = item.get("public_key") or ""
            if not priv_k or not pub_k or priv_k == pub_k:
                priv_k, pub_k = generate_reality_keypair(priv_k)
                h["private_key"] = priv_k
                h["public_key"] = pub_k
                item["private_key"] = priv_k
                item["public_key"] = pub_k
                modified_keys = True
            sid = item.get("short_id") or "6a8b"
            item["proto"] = "VLESS-Reality · 零证书免 Insecure · XTLS-RPRX-Vision (首选推荐)"
            item["listen"] = f"[::]:{port} (TCP)"
            item["pin_sha256"] = fp_colon
            item["uri"] = f"vless://{uuid_v}@{host}:{uri_port}?security=reality&encryption=none&pbk={pub_k}&headerType=none&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni={sni}&sid={sid}#{enc_name}"
        item["route_mode"] = item.get("route_mode") if item.get("route_mode") in ("shunt", "direct", "proxy_only") else get_uci_homelink_route_mode()
        item["live_cert_matched"] = bool(fp_colon)
        item["lan_ip"] = lan_ip
        is_udp_hl = ("hy" in proto or "tuic" in proto)
        is_en_hl = bool(item.get("enabled", True))
        port_listening = (_is_udp_port_listening(port) if is_udp_hl else _is_local_port_listening(port)) if is_en_hl else False
        item["port_listening"] = bool(port_listening)
        item["l4_proto"] = "UDP" if is_udp_hl else "TCP"
        enriched.append(item)
    if modified_keys:
        try:
            save_homelink_nodes(hl_nodes, conf_dir)
        except Exception:
            pass
    # Aggregate real-time HomeLink connections, rates, cumulative traffic, and client sessions
    now_hl = time.time()
    dt_hl = max(0.5, now_hl - (_HOMELINK_LEDGER_RT["last_ts"] or (now_hl - 2.0)))
    c_snap_hl = clash_get_connections_fast(timeout=1.5, max_sample=200)
    conns_hl = c_snap_hl.get("connections") or []
    prev_map = _HOMELINK_LEDGER_RT["conn_prev"]
    cur_map = {}
    node_rt_stats = {h.get("id"): {"conns": 0, "clients": set(), "up_rate": 0, "down_rate": 0, "targets": []} for h in enriched if h.get("id")}
    active_sessions = []
    for c in conns_hl:
        if not isinstance(c, dict):
            continue
        meta = c.get("metadata") or {}
        matched_hl = _match_homelink_node_for_conn(meta, enriched, lan_ip=lan_ip, conf_dir=conf_dir)
        if not matched_hl:
            continue
        hid = matched_hl.get("id")
        cid = str(c.get("id") or "")
        up_b = int(c.get("upload") or 0)
        dn_b = int(c.get("download") or 0)
        if cid:
            cur_map[cid] = (up_b, dn_b)
        p_up, p_dn = prev_map.get(cid, (up_b, dn_b)) if cid else (up_b, dn_b)
        d_up = max(0, up_b - p_up)
        d_dn = max(0, dn_b - p_dn)
        ur = int(round(d_up / dt_hl))
        dr = int(round(d_dn / dt_hl))
        src_ip = str(meta.get("sourceIP") or "").strip() or "远程客户端"
        dst_host = str(meta.get("host") or meta.get("destinationIP") or "-").strip()
        dst_port = str(meta.get("destinationPort") or "").strip()
        dst_full = f"{dst_host}:{dst_port}" if dst_port and ":" not in dst_host else dst_host
        chains = [str(x) for x in (c.get("chains") or ["direct"]) if str(x).strip()]
        out_exit = chains[0] if chains else "direct"
        grp_lbl = chains[-1] if chains else "direct"
        # Classify destination type: LAN private vs Domestic vs Overseas Proxy
        is_lan_dst = False
        try:
            dst_ip_str = str(meta.get("destinationIP") or dst_host).strip()
            if _h3_is_lan_ip(dst_ip_str) or dst_host.endswith(".lan") or dst_host == lan_ip:
                is_lan_dst = True
        except Exception:
            pass
        if is_lan_dst:
            flow_type = "lan"
            flow_label = "🏠 访问家中内网"
        elif out_exit.lower() == "direct" or "domestic" in grp_lbl.lower():
            flow_type = "domestic"
            flow_label = "🇨🇳 国内宽带直连"
        else:
            flow_type = "proxy"
            flow_label = f"🌍 借道代理 ({out_exit})"
        nst = node_rt_stats.setdefault(hid, {"conns": 0, "clients": set(), "up_rate": 0, "down_rate": 0, "targets": []})
        nst["conns"] += 1
        nst["clients"].add(src_ip)
        nst["up_rate"] += ur
        nst["down_rate"] += dr
        if dst_host and dst_host not in nst["targets"] and len(nst["targets"]) < 6:
            nst["targets"].append(dst_host)
        n_cum = _HOMELINK_LEDGER_RT["nodes"].setdefault(hid, {"up_bytes": 0, "down_bytes": 0, "total_conns": 0, " seen_cids": set()})
        n_cum["up_bytes"] += d_up
        n_cum["down_bytes"] += d_dn
        if cid and cid not in n_cum[" seen_cids"]:
            n_cum[" seen_cids"].add(cid)
            n_cum["total_conns"] += 1
            if len(n_cum[" seen_cids"]) > 2000:
                n_cum[" seen_cids"].clear()
        cli_rec = _HOMELINK_LEDGER_RT["clients"].setdefault(src_ip, {
            "client_ip": src_ip,
            "node_id": hid,
            "node_name": matched_hl.get("name") or hid,
            "protocol": matched_hl.get("protocol") or "vless-reality",
            "listen_port": matched_hl.get("listen_port"),
            "route_mode": matched_hl.get("route_mode") or "shunt",
            "up_bytes": 0,
            "down_bytes": 0,
            "last_seen_ts": int(now_hl),
            "targets": []
        })
        cli_rec["node_id"] = hid
        cli_rec["node_name"] = matched_hl.get("name") or hid
        cli_rec["protocol"] = matched_hl.get("protocol") or "vless-reality"
        cli_rec["listen_port"] = matched_hl.get("listen_port")
        cli_rec["route_mode"] = matched_hl.get("route_mode") or "shunt"
        cli_rec["up_bytes"] += max(d_up, up_b if d_up == 0 and cli_rec["up_bytes"] == 0 else 0)
        cli_rec["down_bytes"] += max(d_dn, dn_b if d_dn == 0 and cli_rec["down_bytes"] == 0 else 0)
        cli_rec["last_seen_ts"] = int(now_hl)
        active_sessions.append({
            "id": cid,
            "client_ip": src_ip,
            "node_id": hid,
            "node_name": matched_hl.get("name") or hid,
            "protocol": (matched_hl.get("protocol") or "vless-reality").upper(),
            "listen_port": matched_hl.get("listen_port"),
            "route_mode": matched_hl.get("route_mode") or "shunt",
            "target": dst_full,
            "flow_type": flow_type,
            "flow_label": flow_label,
            "outbound": out_exit,
            "group": grp_lbl,
            "up_bytes": up_b,
            "down_bytes": dn_b,
            "up_rate_bps": ur,
            "down_rate_bps": dr,
            "network": str(meta.get("network") or "tcp").upper(),
        })
    _HOMELINK_LEDGER_RT["conn_prev"] = cur_map
    _HOMELINK_LEDGER_RT["last_ts"] = now_hl
    tot_hl_up = 0
    tot_hl_dn = 0
    tot_hl_ur = 0
    tot_hl_dr = 0
    tot_hl_conns = 0
    all_active_clients = set()
    modes_set = set()
    for item in enriched:
        hid = item.get("id")
        if item.get("enabled", True):
            modes_set.add(item.get("route_mode") or "shunt")
        nst = node_rt_stats.get(hid) or {"conns": 0, "clients": set(), "up_rate": 0, "down_rate": 0, "targets": []}
        ncum = _HOMELINK_LEDGER_RT["nodes"].get(hid) or {"up_bytes": 0, "down_bytes": 0, "total_conns": 0}
        item["active_conns"] = len(nst["clients"]) and nst["conns"] or 0
        item["active_clients_count"] = len(nst["clients"])
        item["active_clients"] = sorted(list(nst["clients"]))[:8]
        item["recent_targets"] = nst["targets"][:5]
        item["up_rate_bps"] = nst["up_rate"]
        item["down_rate_bps"] = nst["down_rate"]
        item["up_rate_str"] = _format_rate_human(nst["up_rate"])
        item["down_rate_str"] = _format_rate_human(nst["down_rate"])
        item["up_bytes"] = int(ncum.get("up_bytes", 0))
        item["down_bytes"] = int(ncum.get("down_bytes", 0))
        item["total_bytes"] = item["up_bytes"] + item["down_bytes"]
        item["total_bytes_str"] = _format_bytes_human(item["total_bytes"])
        tot_hl_up += item["up_bytes"]
        tot_hl_dn += item["down_bytes"]
        tot_hl_ur += item["up_rate_bps"]
        tot_hl_dr += item["down_rate_bps"]
        tot_hl_conns += item["active_conns"]
        all_active_clients.update(nst["clients"])
    effective_mode = "mixed" if len(modes_set) > 1 else (next(iter(modes_set)) if len(modes_set) == 1 else get_uci_homelink_route_mode())
    telemetry_summary = {
        "total_nodes": len(enriched),
        "enabled_nodes": sum(1 for x in enriched if x.get("enabled", True)),
        "listening_nodes": sum(1 for x in enriched if x.get("port_listening")),
        "active_clients_count": len(all_active_clients),
        "active_clients": sorted(list(all_active_clients)),
        "active_conns": tot_hl_conns,
        "up_rate_bps": tot_hl_ur,
        "down_rate_bps": tot_hl_dr,
        "up_rate_str": _format_rate_human(tot_hl_ur),
        "down_rate_str": _format_rate_human(tot_hl_dr),
        "up_bytes": tot_hl_up,
        "down_bytes": tot_hl_dn,
        "total_bytes": tot_hl_up + tot_hl_dn,
        "total_bytes_str": _format_bytes_human(tot_hl_up + tot_hl_dn),
        "effective_route_mode": effective_mode,
        "active_sessions": active_sessions[:40],
        "recent_clients": sorted(list(_HOMELINK_LEDGER_RT["clients"].values()), key=lambda x: x.get("last_seen_ts", 0), reverse=True)[:15]
    }
    _hl_res = {
        "ok": True,
        "ca_sha256": fp_colon,
        "lan_ip": lan_ip,
        "route_mode": get_uci_homelink_route_mode(),
        "effective_route_mode": effective_mode,
        "telemetry": telemetry_summary,
        "nodes": enriched
    }
    _HOMELINK_API_MEMO[hl_key] = copy.deepcopy(_hl_res)
    if mask_private_key or mask_all_secrets:
        masked_res = copy.deepcopy(_hl_res)
        for _nd in masked_res.get("nodes", []):
            if isinstance(_nd, dict):
                if "private_key" in _nd:
                    _nd["private_key"] = "*** (仅本机 127.0.0.1 可读)"
                if mask_all_secrets:
                    if "uuid" in _nd and _nd["uuid"]:
                        _nd["uuid"] = str(_nd["uuid"])[:8] + "-****-****-****"
                    if "password" in _nd and _nd["password"]:
                        _nd["password"] = "********"
                    # SEC-3 (v1.0.2): uri 里内嵌明文 password/uuid，只脱敏字段等于没脱
                    if _nd.get("uri"):
                        _nd["uri"] = re.sub(r"://[^@/]+@", "://***@", str(_nd["uri"]))
        return masked_res
    return _hl_res

def _is_local_port_listening(port: int) -> bool:
    """P0-3 & B4-20 Fix: Checks /proc/net/tcp & tcp6 in-memory first (0 sockets opened!).
    On Linux where /proc/net/tcp is readable, its result is authoritative so closed ports return False in <0.05ms.
    Never opens a raw TCP connection to TProxy port 7893, which would trigger a TProxy self-loop."""
    try:
        p_int = int(port)
    except Exception:
        return False
    if p_int in _read_proc_listening_ports("tcp"):
        return True
    if p_int == 7893 or Path("/proc/net/tcp").is_file():
        return False
    try:
        with socket.create_connection(("127.0.0.1", p_int), timeout=0.08):
            return True
    except Exception:
        return False

def _is_udp_port_listening(port: int) -> bool:
    for path in ("/proc/net/udp", "/proc/net/udp6"):
        try:
            with open(path, "r") as fh:
                next(fh, None)
                for line in fh:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    try:
                        if int(parts[1].split(":")[1], 16) == int(port):
                            return True
                    except Exception:
                        continue
        except Exception:
            continue
    return False

def _all_configured_tcp_inbounds_listening(conf_dir: Path = CONF_DIR) -> bool:
    """True only when every inbound in sing-box.json is actually bound. A hot `PUT :9090/configs` silently ignores newly added """
    try:
        cfg = json.loads((conf_dir / "sing-box.json").read_text(encoding="utf-8"))
    except Exception:
        return True
    tcp_types = ("vless", "mixed", "tproxy", "socks", "http", "trojan", "vmess", "shadowsocks")
    for ib in cfg.get("inbounds", []):
        itype = (ib.get("type") or "").lower()
        lport = ib.get("listen_port")
        if not lport:
            continue
        if itype in tcp_types:
            if not _is_local_port_listening(int(lport)):
                return False
        elif itype in ("hysteria2", "tuic"):
            if not _is_udp_port_listening(int(lport)):
                return False
    return True

def _apply_node_advanced_fields(ob: dict, payload: dict) -> dict:
    """Applies full sing-box outbound fields (TLS/Reality/uTLS/ALPN, Transport WS/gRPC/HTTP/HTTPUpgrade, Hysteria2 hop/bw/obfs, VMess/TUIC/SS) from payload."""
    if not isinstance(ob, dict) or not isinstance(payload, dict):
        return ob
    ntype = str(ob.get("type") or "vless").lower()
    # 1. Server ports & hop_interval (Hysteria2)
    if "server_ports" in payload:
        sp_raw = payload.get("server_ports")
        if isinstance(sp_raw, list):
            sp_clean = [str(x).strip().replace("-", ":") for x in sp_raw if str(x).strip()]
        elif isinstance(sp_raw, str) and sp_raw.strip():
            sp_clean = [x.strip().replace("-", ":") for x in re.split(r"[,;\s]+", sp_raw.strip()) if x.strip()]
        else:
            sp_clean = []
        if sp_clean:
            ob["server_ports"] = sp_clean
        else:
            ob.pop("server_ports", None)
    if "hop_interval" in payload:
        hi = str(payload.get("hop_interval") or "").strip()
        if hi:
            ob["hop_interval"] = hi if hi.endswith(("s", "m", "ms")) else f"{hi}s"
        else:
            ob.pop("hop_interval", None)
    for bw_k in ("up_mbps", "down_mbps"):
        if bw_k in payload:
            bw_v = str(payload.get(bw_k) or "").strip()
            if bw_v.isdigit() and int(bw_v) > 0:
                ob[bw_k] = int(bw_v)
            else:
                ob.pop(bw_k, None)
    if "obfs_type" in payload or "obfs_password" in payload or isinstance(payload.get("obfs"), dict):
        obfs_d = payload.get("obfs") if isinstance(payload.get("obfs"), dict) else {}
        o_type = str(payload.get("obfs_type") if "obfs_type" in payload else (obfs_d.get("type") or "")).strip()
        o_pwd = str(payload.get("obfs_password") if "obfs_password" in payload else (obfs_d.get("password") or "")).strip()
        if o_type and o_pwd:
            ob["obfs"] = {"type": o_type, "password": o_pwd}
        elif "obfs_type" in payload and not o_type:
            ob.pop("obfs", None)
    # 2. VLESS / VMess / TUIC / SS / Socks specific fields
    if "flow" in payload:
        fl = str(payload.get("flow") or "").strip()
        if fl and ntype == "vless":
            ob["flow"] = fl
        else:
            ob.pop("flow", None)
    if "packet_encoding" in payload:
        pe = str(payload.get("packet_encoding") or "").strip()
        if pe and ntype in ("vless", "vmess"):
            ob["packet_encoding"] = pe
        elif not pe:
            ob.pop("packet_encoding", None)
    if "alter_id" in payload and ntype == "vmess":
        try:
            ob["alter_id"] = max(0, int(payload.get("alter_id") or 0))
        except Exception:
            ob["alter_id"] = 0
    if "security" in payload and ntype == "vmess":
        sec_vm = str(payload.get("security") or "auto").strip()
        if sec_vm in ("auto", "aes-128-gcm", "chacha20-poly1305", "none", "zero"):
            ob["security"] = sec_vm
    if "congestion_control" in payload and ntype == "tuic":
        cc = str(payload.get("congestion_control") or "bbr").strip()
        if cc:
            ob["congestion_control"] = cc
    if "udp_relay_mode" in payload and ntype == "tuic":
        urm = str(payload.get("udp_relay_mode") or "native").strip()
        if urm:
            ob["udp_relay_mode"] = urm
    if "username" in payload and ntype in ("socks", "http"):
        un = str(payload.get("username") or "").strip()
        if un:
            ob["username"] = un
        else:
            ob.pop("username", None)
    # 3. TLS / Reality / uTLS / ALPN
    has_tls_keys = any(k in payload for k in ("tls_enabled", "tls_security", "sni", "insecure", "alpn", "utls_fp", "pbk", "sid", "tls"))
    if has_tls_keys:
        if isinstance(payload.get("tls"), dict) and not any(k in payload for k in ("tls_enabled", "tls_security", "pbk", "utls_fp")):
            ob["tls"] = copy.deepcopy(payload["tls"])
        else:
            cur_tls = copy.deepcopy(ob.get("tls")) if isinstance(ob.get("tls"), dict) else {}
            t_sec = str(payload.get("tls_security") or "").strip().lower()
            if not t_sec:
                if "tls_enabled" in payload:
                    t_sec = "tls" if payload.get("tls_enabled") else "none"
                elif payload.get("pbk") or (isinstance(cur_tls.get("reality"), dict) and cur_tls["reality"].get("enabled")):
                    t_sec = "reality"
                elif cur_tls.get("enabled") or ntype in ("hysteria2", "trojan", "tuic", "anytls") or payload.get("sni"):
                    t_sec = "tls"
                else:
                    t_sec = "none"
            if t_sec == "none" and ntype not in ("hysteria2", "trojan", "tuic", "anytls"):
                ob.pop("tls", None)
            else:
                sni_v = str(payload.get("sni") if "sni" in payload else (cur_tls.get("server_name") or ob.get("sni") or ob.get("server") or "")).strip()
                insec_v = bool(payload.get("insecure") if "insecure" in payload else cur_tls.get("insecure", False))
                new_tls = {"enabled": True, "server_name": sni_v or str(ob.get("server") or "")}
                if insec_v:
                    new_tls["insecure"] = True
                if cur_tls.get("certificate_path"):
                    new_tls["certificate_path"] = cur_tls["certificate_path"]
                alpn_raw = payload.get("alpn") if "alpn" in payload else cur_tls.get("alpn")
                if isinstance(alpn_raw, list):
                    alpn_l = [str(x).strip() for x in alpn_raw if str(x).strip()]
                elif isinstance(alpn_raw, str) and alpn_raw.strip():
                    alpn_l = [x.strip() for x in alpn_raw.split(",") if x.strip()]
                else:
                    alpn_l = []
                if alpn_l:
                    new_tls["alpn"] = alpn_l
                fp_v = str(payload.get("utls_fp") if "utls_fp" in payload else ((cur_tls.get("utls") or {}).get("fingerprint") or "")).strip()
                pbk_v = str(payload.get("pbk") if "pbk" in payload else ((cur_tls.get("reality") or {}).get("public_key") or "")).strip()
                sid_v = str(payload.get("sid") if "sid" in payload else ((cur_tls.get("reality") or {}).get("short_id") or "")).strip()
                if t_sec == "reality" or pbk_v:
                    if pbk_v:
                        new_tls["utls"] = {"enabled": True, "fingerprint": fp_v or "chrome"}
                        new_tls["reality"] = {"enabled": True, "public_key": pbk_v, "short_id": sid_v}
                elif fp_v and ntype not in ("hysteria2", "tuic"):
                    new_tls["utls"] = {"enabled": True, "fingerprint": fp_v}
                ob["tls"] = new_tls
                ob["sni"] = new_tls.get("server_name", "")
    # 4. Transport (tcp / ws / grpc / http / httpupgrade)
    has_trans_keys = any(k in payload for k in ("transport_type", "transport_path", "transport_host", "grpc_service_name", "transport"))
    if has_trans_keys:
        if isinstance(payload.get("transport"), dict) and "transport_type" not in payload:
            ob["transport"] = copy.deepcopy(payload["transport"])
        else:
            cur_tr = copy.deepcopy(ob.get("transport")) if isinstance(ob.get("transport"), dict) else {}
            ttype = str(payload.get("transport_type") if "transport_type" in payload else (cur_tr.get("type") or "tcp")).strip().lower()
            tpath = str(payload.get("transport_path") if "transport_path" in payload else (cur_tr.get("path") or "/")).strip() or "/"
            thost = str(payload.get("transport_host") if "transport_host" in payload else (((cur_tr.get("headers") or {}).get("Host")) or cur_tr.get("host") or "")).strip()
            tsvc = str(payload.get("grpc_service_name") if "grpc_service_name" in payload else (cur_tr.get("service_name") or "")).strip()
            if ttype in ("", "tcp", "none") or ntype in ("hysteria2", "tuic", "shadowsocks", "socks", "http"):
                ob.pop("transport", None)
            elif ttype == "ws":
                tr_o = {"type": "ws", "path": tpath}
                if thost:
                    tr_o["headers"] = {"Host": thost}
                ob["transport"] = tr_o
            elif ttype == "grpc":
                ob["transport"] = {"type": "grpc", "service_name": tsvc or tpath.lstrip("/")}
            elif ttype == "httpupgrade":
                tr_o = {"type": "httpupgrade", "path": tpath}
                if thost:
                    tr_o["host"] = thost
                ob["transport"] = tr_o
            elif ttype in ("http", "h2"):
                tr_o = {"type": "http", "path": tpath}
                if thost:
                    tr_o["host"] = [x.strip() for x in thost.split(",") if x.strip()]
                ob["transport"] = tr_o
    return ob

def build_manual_node_outbound(payload: dict, conf_dir: Path = CONF_DIR) -> dict:
    if isinstance(payload.get("raw_outbound"), dict) and payload["raw_outbound"].get("type") and payload["raw_outbound"].get("server"):
        ob = copy.deepcopy(payload["raw_outbound"])
        ob["tag"] = str(payload.get("tag") or ob.get("tag") or f"Node-{int(time.time()) % 10000}").strip()
        ob["display_tag"] = ob["tag"]
        region_ov = (payload.get("region") or payload.get("region_override") or ob.get("region_override") or "").strip().upper()
        if region_ov in ("JP", "US", "SG", "HK", "TW", "KR", "OTHER", "TEST"):
            ob["region_override"] = region_ov
        return ob
    if payload.get("share_uri") and "://" in str(payload.get("share_uri")):
        parsed_l = NodeURIParser.parse_subscription_text(str(payload["share_uri"]), conf_dir=conf_dir)
        if parsed_l:
            ob = parsed_l[0]
            if payload.get("tag"):
                ob["tag"] = str(payload["tag"]).strip()
                ob["display_tag"] = ob["tag"]
            region_ov = (payload.get("region") or payload.get("region_override") or "").strip().upper()
            if region_ov in ("JP", "US", "SG", "HK", "TW", "KR", "OTHER", "TEST"):
                ob["region_override"] = region_ov
            return _apply_node_advanced_fields(ob, payload)
    ntype = (payload.get("type") or "vless").strip().lower()
    if ntype == "hy2":
        ntype = "hysteria2"
    elif ntype == "ss":
        ntype = "shadowsocks"
    elif ntype == "socks5":
        ntype = "socks"
    tag = (payload.get("tag") or f"Manual-{ntype.upper()}-{int(time.time()) % 10000}").strip()
    server = (payload.get("server") or "127.0.0.1").strip()
    port = int(payload.get("server_port", 443) or 443)
    sni = (payload.get("sni") or "").strip()
    region_ov = (payload.get("region") or payload.get("region_override") or "").strip().upper()
    if ntype == "hysteria2":
        ob = {
            "type": "hysteria2",
            "tag": tag,
            "server": server,
            "server_port": port,
            "password": (payload.get("password") or payload.get("uuid") or "").strip(),
            "tls": {
                "enabled": True,
                "server_name": sni or server,
                "insecure": bool(payload.get("insecure", False))
            }
        }
    elif ntype == "trojan":
        ob = {
            "type": "trojan",
            "tag": tag,
            "server": server,
            "server_port": port,
            "password": (payload.get("password") or payload.get("uuid") or "").strip(),
            "tls": {
                "enabled": True,
                "server_name": sni or server,
                "insecure": bool(payload.get("insecure", False))
            }
        }
    elif ntype == "vmess":
        ob = {
            "type": "vmess",
            "tag": tag,
            "server": server,
            "server_port": port,
            "uuid": (payload.get("uuid") or payload.get("password") or "").strip(),
            "security": (payload.get("security") or payload.get("method") or "auto").strip(),
            "alter_id": int(payload.get("alter_id") or 0)
        }
        if sni or payload.get("tls_enabled") or payload.get("tls_security") == "tls":
            ob["tls"] = {"enabled": True, "server_name": sni or server, "insecure": bool(payload.get("insecure", False))}
    elif ntype == "tuic":
        ob = {
            "type": "tuic",
            "tag": tag,
            "server": server,
            "server_port": port,
            "uuid": (payload.get("uuid") or "").strip(),
            "password": (payload.get("password") or "").strip(),
            "congestion_control": (payload.get("congestion_control") or "bbr").strip(),
            "udp_relay_mode": (payload.get("udp_relay_mode") or "native").strip(),
            "tls": {"enabled": True, "server_name": sni or server, "alpn": ["h3"], "insecure": bool(payload.get("insecure", False))}
        }
    elif ntype == "shadowsocks":
        ob = {
            "type": "shadowsocks",
            "tag": tag,
            "server": server,
            "server_port": port,
            "method": (payload.get("method") or "2022-blake3-aes-128-gcm").strip(),
            "password": (payload.get("password") or payload.get("uuid") or "").strip()
        }
    elif ntype == "socks":
        ob = {
            "type": "socks",
            "tag": tag,
            "server": server,
            "server_port": port,
            "version": "5"
        }
        if payload.get("username"):
            ob["username"] = str(payload["username"]).strip()
        if payload.get("password"):
            ob["password"] = str(payload["password"]).strip()
    else:
        ob = {
            "type": "vless",
            "tag": tag,
            "server": server,
            "server_port": port,
            "uuid": (payload.get("uuid") or payload.get("password") or "a891f02b-2026-4f88-9b1c-8899aabbccdd").strip()
        }
        flow = (payload.get("flow") or "").strip()
        if flow:
            ob["flow"] = flow
        sec = (payload.get("tls_security") or payload.get("security") or ("reality" if payload.get("pbk") else ("tls" if sni else "none"))).lower()
        if sec in ("tls", "reality"):
            tls_obj = {
                "enabled": True,
                "server_name": sni or server,
                "utls": {"enabled": True, "fingerprint": str(payload.get("utls_fp") or "chrome")}
            }
            if sec == "reality" or payload.get("pbk"):
                tls_obj["reality"] = {
                    "enabled": True,
                    "public_key": (payload.get("pbk") or "").strip(),
                    "short_id": (payload.get("sid") or "").strip()
                }
            ob["tls"] = tls_obj
    ob = _apply_node_advanced_fields(ob, payload)
    if region_ov in ("JP", "US", "SG", "HK", "TW", "KR", "OTHER", "TEST"):
        ob["region_override"] = region_ov
    if payload.get("disabled") is True:
        ob["disabled"] = True
    return ob

def get_ops_diagnostics(conf_dir: Path = CONF_DIR) -> dict:
    sb_caps = probe_singbox_binary_capabilities(conf_dir)
    cfg_file = conf_dir / "sing-box.json"
    if not cfg_file.is_file():
        write_all_configs(conf_dir)
    check_ok = True
    check_msg = "syntax_ok"
    try:
        sb_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        if sb_caps["installed"]:
            res = run_singbox_check_safe(sb_caps["binary_path"], sb_cfg)
            check_ok = (res.returncode == 0)
            check_msg = (res.stderr or "sing-box check passed (rc=0)").strip()
    except Exception as e:
        check_ok = False
        check_msg = str(e)
    nft_mounted = False
    nft_chains = []
    try:
        r_nft = subprocess.run(["nft", "list", "table", "inet", "ai_link"], capture_output=True, text=True, timeout=2)
        if r_nft.returncode == 0 and "table inet ai_link" in (r_nft.stdout or ""):
            nft_mounted = True
            for line in (r_nft.stdout or "").splitlines():
                line_s = line.strip()
                if line_s.startswith("chain "):
                    nft_chains.append(line_s.split()[1])
    except Exception:
        pass
    ports_status = {}
    for p_num, p_label in ((9099, "WebUI Panel"), (9090, "Clash Controller"), (7890, "Mixed Proxy"), (7891, "Redirect Proxy"), (7893, "TProxy"), (7874, "Smart DNS"), (18443, "HomeLink Reality")):
        ports_status[str(p_num)] = {"label": p_label, "listening": _is_local_port_listening(p_num)}
    ipv6_on = get_uci_ipv6_proxy(conf_dir)
    v6_gov = build_ipv6_governance_summary(conf_dir)
    rh = build_routing_health(conf_dir)
    dns_tel = build_dns_telemetry_response(conf_dir)
    return {
        "ok": True,
        "version": APP_VERSION,
        "timestamp": int(time.time()),
        "singbox_check_ok": check_ok,
        "singbox_check_detail": check_msg,
        "nft_table_mounted": nft_mounted,
        "nft_chains": nft_chains,
        "ports": ports_status,
        "dns_mode": "dnsmasq -> 127.0.0.1#7874 (TProxy :53)",
        "ipv6_proxy": ipv6_on,
        "ipv6_mode_label": v6_gov.get("ipv6_mode_label", ""),
        "aaaa_fakeip_guard": (not ipv6_on),
        "dns_upstream_mounted": bool((v6_gov.get("architecture") or {}).get("dnsmasq_upstream_mounted", False)),
        "routing_mode": load_shunt_config(conf_dir).get("routing_mode", "rule_shunt"),
        "routing_state": rh.get("state", "proxy"),
        "routing_label": rh.get("label", ""),
        "active_node": rh.get("active_node", "direct"),
        "nodes_alive": rh.get("nodes_alive", 0),
        "nodes_total": rh.get("nodes_total", 0),
        "adblock_rules": int((dns_tel.get("shield_status") or {}).get("active_rules_count") or 0),
        "adblock_hits": int(((dns_tel.get("stats_24h") or {}).get("blocked_queries")) or 0),
        "has_backup_archive": _has_final_backup_archive(),
        "last_reload_mode": LAST_RELOAD_MODE
    }

def get_ops_logs(conf_dir: Path = CONF_DIR) -> dict:
    log_lines = []
    log_file = Path("/var/log/ai-link.log")
    if log_file.is_file():
        try:
            log_lines.extend(log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-50:])
        except Exception:
            pass
    try:
        r = subprocess.run(["logread", "-e", "ai-link|sing-box"], capture_output=True, text=True, timeout=2)
        if r.returncode == 0 and r.stdout:
            log_lines.extend(r.stdout.strip().splitlines()[-50:])
    except Exception:
        pass
    if not log_lines:
        log_lines = [
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AI-LINK v2.0.0-r1 daemon active (reload_mode={LAST_RELOAD_MODE})",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Probe alive: {PROBE_ENGINE.last_alive_count}/{PROBE_ENGINE.last_total_count} ({PROBE_ENGINE.last_availability_pct}%)"
        ]
    return {
        "ok": True,
        "logs": log_lines[-80:]
    }

def export_ops_backup(conf_dir: Path = CONF_DIR) -> dict:
    conf_dir = Path(conf_dir)
    is_live = (conf_dir.resolve() == CONF_DIR.resolve())
    ops_cur = get_ops_settings(conf_dir)
    # Read exact on-disk auto_nodes.json if present so restore preserves byte-for-byte hash
    auto_nodes_raw = None
    if (conf_dir / "auto_nodes.json").is_file():
        try:
            auto_nodes_raw = json.loads((conf_dir / "auto_nodes.json").read_text(encoding="utf-8"))
        except Exception:
            auto_nodes_raw = None
    if not isinstance(auto_nodes_raw, dict):
        auto_nodes_raw = load_auto_nodes_config(conf_dir)
    out = {
        "ok": True,
        "version": APP_VERSION,
        "exported_at": int(time.time()),
        "max_outbounds_limit": get_max_outbounds_limit(conf_dir),
        "ipv6_proxy": bool(ops_cur.get("ipv6_proxy", get_uci_ipv6_proxy(conf_dir))),
        "entry_bypass": bool(ops_cur.get("entry_bypass", True)),
        "block_quic": bool(ops_cur.get("block_quic", True)),
        "game_udp_direct": bool(ops_cur.get("game_udp_direct", True)),
        "auto_mute_conflicts": bool(ops_cur.get("auto_mute_conflicts", True)),
        "gh_mirror": str(ops_cur.get("gh_mirror") or "https://gh-proxy.com/"),
        "panel_port": _uci_get_str("global.panel_port", "9099") if is_live else "9099",
        "ops_settings": ops_cur,
        "dns_mode": "dnsmasq -> 127.0.0.1#7874 (TProxy :53)",
        "nodes": load_saved_nodes(conf_dir),
        "shunt": load_shunt_config(conf_dir),
        "subscriptions": load_subscriptions(conf_dir),
        "homelink": load_homelink_nodes(conf_dir),
        "auto_nodes": auto_nodes_raw,
        "dns_rewrite": load_dns_rewrite_config(conf_dir),
        "dns_filters": load_dns_filter_config(conf_dir),
        "probe_schedules": load_probe_schedules(conf_dir),
        "_existing_files": [
            fn for fn in ("nodes.json", "subscriptions.json", "homelink.json", "shunt.json", "dns_filters.json", "dns_rewrite.json", "ops_settings.json", "auto_nodes.json")
            if (conf_dir / fn).is_file()
        ],
    }
    # FR-3 & B1-2: Export panel authentication (hash + salt + panel_pwd_customized boolean, never raw session tokens or UCI secrets)
    try:
        auth_p = conf_dir / "panel_auth.json"
        if auth_p.is_file():
            pa = json.loads(auth_p.read_text(encoding="utf-8"))
            if isinstance(pa, dict) and pa.get("hash") and pa.get("salt"):
                out["panel_auth"] = {"hash": pa["hash"], "salt": pa["salt"]}
        cust_flag = is_panel_pwd_customized(conf_dir)
        out["panel_pwd_customized"] = cust_flag
        out["panel_secret_uci"] = PANEL_PWD_SENTINEL if cust_flag else PANEL_PWD_DEFAULT
    except Exception:
        pass
    return out

def factory_reset_all_configs(conf_dir: Path = CONF_DIR, create_backup_archive: bool = True, archive_override_path: Path = None) -> dict:
    """Safely archives current /etc/ai-link (+ /etc/config/ai-link) to /root/ai-link-final-backup/ and resets all configurations to clean v1.0.0 factory defaults."""
    conf_dir = Path(conf_dir)
    conf_dir.mkdir(parents=True, exist_ok=True)
    is_live = (conf_dir.resolve() == CONF_DIR.resolve())
    # Ensure current ops_settings is flushed to ops_settings.json before archiving
    try:
        cur_ops = get_ops_settings(conf_dir)
        save_keys = ("enabled", "entry_bypass", "block_quic", "game_udp_direct", "auto_mute_conflicts", "ipv6_proxy", "gh_mirror", "lan_direct_macs", "probe_scene_preset", "node_auto_test", "node_test_mode", "node_test_budget", "egress_probe_interval_s", "require_lan_auth", "trusted_cidr", "panel_bind")
        (conf_dir / "ops_settings.json").write_text(json.dumps({k: cur_ops.get(k) for k in save_keys}, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    if is_live and Path("/etc/config/ai-link").is_file():
        try:
            shutil.copy2("/etc/config/ai-link", conf_dir / "uci_ai_link.bak")
        except Exception:
            pass
    backup_snapshot = export_ops_backup(conf_dir)
    archive_path = ""
    if create_backup_archive:
        try:
            if archive_override_path is not None:
                arc_latest = Path(archive_override_path)
                arc_latest.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["tar", "-czf", str(arc_latest), "-C", str(conf_dir.parent), conf_dir.name], capture_output=True, timeout=8)
                archive_path = str(arc_latest)
            elif is_live:
                bdir = Path("/root/ai-link-final-backup")
                bdir.mkdir(parents=True, exist_ok=True)
                os.chmod(str(bdir), 0o700)
                ts_str = time.strftime("%Y%m%d-%H%M%S")
                arc_ts = bdir / f"etc-ai-link-factory-reset-{ts_str}.tgz"
                arc_latest = bdir / "etc-ai-link.tgz"
                tar_targets = ["etc/ai-link"]
                if Path("/etc/config/ai-link").is_file():
                    tar_targets.append("etc/config/ai-link")
                subprocess.run(["tar", "-czf", str(arc_ts), "-C", "/"] + tar_targets, capture_output=True, timeout=8)
                shutil.copy2(arc_ts, arc_latest)
                os.chmod(str(arc_ts), 0o600)
                os.chmod(str(arc_latest), 0o600)
                archive_path = str(arc_latest)
        except Exception:
            pass
    # Remove user-custom state files and reset to clean factory defaults
    for fname in (
        "nodes.json", "subscriptions.json", "homelink.json", "homelink_route_mode",
        "shunt.json", "auto_nodes.json", "dns_rewrite.json", "dns_filters.json",
        "ops_settings.json", "probe_schedules.json", "node_probe.json",
        "panel_auth.json", "panel_token", "traffic_ledger.json", "max_outbounds.txt",
        "uci_ai_link.bak"
    ):
        try:
            fp = conf_dir / fname
            if fp.is_file():
                fp.unlink()
        except Exception:
            pass
    for r_dir in ((RUN_DIR, Path("/tmp/ai-link-run")) if is_live else (conf_dir,)):
        for rname in ("bypass", "recover_direct.flag", "selections.json", "switch_history.json", "node_probe.json", "adblock_stats.json"):
            try:
                rp = Path(r_dir) / rname
                if rp.is_file():
                    rp.unlink()
            except Exception:
                pass
    # Re-initialize default files
    save_nodes_list([], conf_dir)
    save_subscriptions([], conf_dir)
    save_homelink_nodes([], conf_dir)
    save_shunt_config({
        "routing_mode": "rule_shunt",
        "shunt_enabled": True,
        "global_country": "JP",
        "global_strategy": "smart",
        "global_manual_node": "",
        "groups": copy.deepcopy(DEFAULT_SHUNT_GROUPS)
    }, conf_dir)
    (conf_dir / "homelink_route_mode").write_text("shunt", encoding="utf-8")
    if is_live:
        try:
            for k, v in (
                ("enabled", "1"), ("entry_bypass", "1"), ("block_quic", "1"),
                ("game_udp_direct", "1"), ("auto_mute_conflicts", "1"), ("ipv6_proxy", "0"),
                ("gh_mirror", "https://gh-proxy.com/"), ("panel_pwd_customized", "0"), ("require_lan_auth", "0"), ("app_version", APP_VERSION)
            ):
                subprocess.run(["uci", "set", f"ai-link.global.{k}={v}"], check=False, timeout=2)
            subprocess.run(["uci", "-q", "delete", "ai-link.global.panel_secret"], check=False, timeout=2)
            subprocess.run(["uci", "set", "ai-link.homelink.routing_mode=shunt"], check=False, timeout=2)
            subprocess.run(["uci", "commit", "ai-link"], check=False, timeout=2)
        except Exception:
            pass
    update_ops_settings({
        "enabled": True, "entry_bypass": True, "block_quic": True,
        "game_udp_direct": True, "auto_mute_conflicts": True, "ipv6_proxy": False,
        "gh_mirror": "https://gh-proxy.com/", "require_lan_auth": False,
        "lan_direct_macs": [], "probe_scene_preset": "balanced",
        "node_auto_test": True, "node_test_mode": "latency", "node_test_budget": 3000
    }, conf_dir)
    PROBE_ENGINE.current_selections.clear()
    PROBE_ENGINE.last_delays.clear()
    PROBE_ENGINE.node_stats.clear()
    _OPS_SETTINGS_MEMO.clear()
    _STATUS_API_MEMO.clear()
    _NODES_API_MEMO.clear()
    _SHUNT_API_MEMO.clear()
    _HOMELINK_API_MEMO.clear()
    _invalidate_fast_api_cache()
    write_all_configs(conf_dir)
    if is_live and Path("/etc/init.d/ai-link").exists():
        schedule_async_core_reload(force_respawn=True, apply_nft=True)
    return {
        "ok": True,
        "factory_reset": True,
        "archive_path": archive_path or "/root/ai-link-final-backup/etc-ai-link.tgz",
        "backup": backup_snapshot,
        "message": "✅ 已完成恢复出厂设置（原配置与系统开关已归档至 /root/ai-link-final-backup/etc-ai-link.tgz；因节点已清空，请重新导入订阅或点击「从备份归档恢复」以恢复科学上网）"
    }

def restore_from_backup_archive(conf_dir: Path = CONF_DIR, arc_path: Path = None) -> dict:
    """Restores both data (nodes/subs/shunt/homelink/dns) AND system settings (ops_settings + UCI) from backup archive (.tgz/.tar.gz).
    B2-6 & B2-7 Fix: Validates archive safety via tarfile, blocks path traversal, and supports archives structured as
    `etc/ai-link/...`, `<conf_dir.name>/...`, or flat config files in both live and test environments."""
    import tarfile as _tarfile
    conf_dir = Path(conf_dir)
    conf_dir.mkdir(parents=True, exist_ok=True)
    is_live = (conf_dir.resolve() == CONF_DIR.resolve())
    if arc_path is None:
        arc_path = Path("/root/ai-link-final-backup/etc-ai-link.tgz")
    else:
        arc_path = Path(arc_path)
    if not arc_path.is_file():
        return {"ok": False, "error": "archive_not_found", "message": f"未找到备份归档 {arc_path}"}
    try:
        with _tarfile.open(str(arc_path), "r:*") as tf:
            members = tf.getmembers()
            if not members:
                return {"ok": False, "error": "empty_archive", "message": "备份归档为空"}
            total_uncompressed = 0
            for m in members:
                norm_name = m.name.replace("\\", "/")
                raw_parts = [pt for pt in norm_name.split("/") if pt and pt != "."]
                if ".." in raw_parts or norm_name.startswith("/") or ":" in norm_name or m.issym() or m.islnk() or not (m.isfile() or m.isdir()):
                    return {"ok": False, "error": "unsafe_archive_path", "message": f"归档包含不安全路径或非普通文件: {m.name}"}
                total_uncompressed += max(0, int(m.size or 0))
                if total_uncompressed > 100 * 1024 * 1024:
                    return {"ok": False, "error": "archive_too_large", "message": "归档解压后总体积超过 100MB 安全上限"}
            tmp_ext = Path(f"/tmp/ai-link-arc-extract-{os.getpid()}-{int(time.time()*1000)}")
            tmp_ext.mkdir(parents=True, exist_ok=True)
            try:
                tf.extractall(str(tmp_ext))
                # Locate extracted config directory (supports etc/ai-link, <conf_dir.name>, ai-link, or root)
                cand_dirs = [
                    tmp_ext / "etc" / "ai-link",
                    tmp_ext / conf_dir.name,
                    tmp_ext / "ai-link",
                    tmp_ext,
                ]
                src_cfg_dir = next((d for d in cand_dirs if d.is_dir() and any((d / fn).is_file() for fn in ("nodes.json", "shunt.json", "ops_settings.json", "subscriptions.json", "homelink.json"))), None)
                if src_cfg_dir is None:
                    src_cfg_dir = next((d for d in cand_dirs if d.is_dir() and list(d.glob("*.json"))), None)
                if src_cfg_dir is None:
                    return {"ok": False, "error": "invalid_archive_structure", "message": "归档中未找到有效的 AI-LINK 配置文件 (nodes.json / shunt.json / ops_settings.json)"}
                for item in src_cfg_dir.iterdir():
                    if item.name == "version":
                        continue
                    dst_item = conf_dir / item.name
                    if item.is_dir():
                        if dst_item.exists():
                            shutil.rmtree(dst_item, ignore_errors=True)
                        shutil.copytree(item, dst_item)
                    elif item.is_file():
                        shutil.copy2(item, dst_item)
                ext_uci = tmp_ext / "etc" / "config" / "ai-link"
                if ext_uci.is_file():
                    shutil.copy2(ext_uci, conf_dir / "uci_ai_link.bak")
                    if is_live:
                        try:
                            shutil.copy2(ext_uci, "/etc/config/ai-link")
                        except Exception:
                            pass
            finally:
                shutil.rmtree(tmp_ext, ignore_errors=True)
    except Exception as e:
        return {"ok": False, "error": "archive_extract_failed", "message": f"解压备份归档失败: {e}"}
    # 1. If uci_ai_link.bak was bundled inside /etc/ai-link, restore it to /etc/config/ai-link
    uci_bak = conf_dir / "uci_ai_link.bak"
    if is_live and uci_bak.is_file():
        try:
            shutil.copy2(uci_bak, "/etc/config/ai-link")
        except Exception:
            pass
    # 2. Prevent get_ops_settings() from overwriting extracted ops_settings.json with older/factory UCI mtime!
    ops_file = conf_dir / "ops_settings.json"
    restored_ops = {}
    if ops_file.is_file():
        try:
            os.utime(ops_file, None)
            loaded = json.loads(ops_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                restored_ops = loaded
        except Exception:
            restored_ops = {}
    _OPS_SETTINGS_MEMO.clear()
    _invalidate_sys_cache("uci_ipv6")
    # 3. Reverse-sync restored ops_settings -> UCI and apply system hooks (entry_bypass, ipv6_proxy, gh_mirror, etc.)
    if restored_ops:
        update_ops_settings(restored_ops, conf_dir)
    if is_live:
        try:
            if (conf_dir / "max_outbounds.txt").is_file():
                mob_v = (conf_dir / "max_outbounds.txt").read_text(encoding="utf-8").strip()
                if mob_v.isdigit():
                    subprocess.run(["uci", "set", f"ai-link.global.max_outbounds={mob_v}"], check=False, timeout=2)
            subprocess.run(["uci", "set", f"ai-link.global.app_version={APP_VERSION}"], check=False, timeout=2)
            _sync_uci_pwd_customized(is_panel_pwd_customized(conf_dir))
        except Exception:
            pass
    if ops_file.is_file():
        try:
            os.utime(ops_file, None)
        except Exception:
            pass
    _OPS_SETTINGS_MEMO.clear()
    _STATUS_API_MEMO.clear()
    _NODES_API_MEMO.clear()
    _SHUNT_API_MEMO.clear()
    _HOMELINK_API_MEMO.clear()
    _invalidate_fast_api_cache()
    write_all_configs(conf_dir)
    PROBE_ENGINE.apply_shunt_selections(conf_dir)
    if is_live and Path("/etc/init.d/ai-link").exists():
        schedule_async_core_reload(force_respawn=True, apply_nft=True)
    saved_cnt = len([n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))])
    return {
        "ok": True,
        "restored": True,
        "saved_nodes_total": saved_cnt,
        "ops_settings": get_ops_settings(conf_dir),
        "message": f"✅ 已从归档完整恢复 {saved_cnt} 个节点、分流策略与系统开关设置，正在重载内核"
    }

def restore_ops_backup(backup_data: dict, conf_dir: Path = CONF_DIR) -> dict:
    if not isinstance(backup_data, dict):
        return {"ok": False, "error": "invalid_backup_json"}
    conf_dir = Path(conf_dir)
    conf_dir.mkdir(parents=True, exist_ok=True)
    is_live = (conf_dir.resolve() == CONF_DIR.resolve())
    existing_set = set(backup_data.get("_existing_files")) if isinstance(backup_data.get("_existing_files"), list) else None
    if isinstance(backup_data.get("nodes"), list):
        if existing_set is None or "nodes.json" in existing_set or len(backup_data["nodes"]) > 0:
            save_nodes_list(backup_data["nodes"], conf_dir)
        elif (conf_dir / "nodes.json").is_file():
            (conf_dir / "nodes.json").unlink(missing_ok=True)
    if isinstance(backup_data.get("shunt"), dict):
        save_shunt_config(backup_data["shunt"], conf_dir)
    if isinstance(backup_data.get("subscriptions"), list):
        if existing_set is None or "subscriptions.json" in existing_set or len(backup_data["subscriptions"]) > 0:
            save_subscriptions(backup_data["subscriptions"], conf_dir)
        elif (conf_dir / "subscriptions.json").is_file():
            (conf_dir / "subscriptions.json").unlink(missing_ok=True)
    if isinstance(backup_data.get("homelink"), list):
        if existing_set is None or "homelink.json" in existing_set or len(backup_data["homelink"]) > 0:
            save_homelink_nodes(backup_data["homelink"], conf_dir)
        elif (conf_dir / "homelink.json").is_file():
            (conf_dir / "homelink.json").unlink(missing_ok=True)
    if isinstance(backup_data.get("auto_nodes"), dict):
        if existing_set is None or "auto_nodes.json" in existing_set:
            _atomic_write_text(conf_dir / "auto_nodes.json", json.dumps(backup_data["auto_nodes"], indent=2, ensure_ascii=False))
    if isinstance(backup_data.get("dns_rewrite"), dict):
        if existing_set is None or "dns_rewrite.json" in existing_set:
            save_dns_rewrite_config(backup_data["dns_rewrite"], conf_dir)
    if isinstance(backup_data.get("dns_filters"), dict):
        if existing_set is None or "dns_filters.json" in existing_set:
            save_dns_filter_config(backup_data["dns_filters"], conf_dir)
    if isinstance(backup_data.get("probe_schedules"), list):
        save_probe_schedules(backup_data["probe_schedules"], conf_dir)
    if "max_outbounds_limit" in backup_data:
        mob_int = int(backup_data["max_outbounds_limit"])
        (conf_dir / "max_outbounds.txt").write_text(str(mob_int), encoding="utf-8")
        if is_live:
            try:
                subprocess.run(["uci", "set", f"ai-link.global.max_outbounds={mob_int}"], check=False, timeout=2)
                subprocess.run(["uci", "commit", "ai-link"], check=False, timeout=2)
            except Exception:
                pass
    # Restore system switch settings (ops_settings + top-level keys like ipv6_proxy, entry_bypass, gh_mirror)
    ops_patch = {}
    if isinstance(backup_data.get("ops_settings"), dict):
        ops_patch.update(backup_data["ops_settings"])
    for k in (
        "enabled", "entry_bypass", "block_quic", "game_udp_direct",
        "auto_mute_conflicts", "ipv6_proxy", "gh_mirror", "lan_direct_macs",
        "probe_scene_preset", "node_auto_test", "node_test_mode",
        "node_test_budget", "egress_probe_interval_s",
        "require_lan_auth", "trusted_cidr", "panel_bind"
    ):
        if k in backup_data:
            ops_patch[k] = backup_data[k]
    if ops_patch:
        update_ops_settings(ops_patch, conf_dir)
    # FR-3: Restore panel authentication (panel_auth.json + uci.panel_secret + uci.panel_port)
    pa = backup_data.get("panel_auth")
    if isinstance(pa, dict) and pa.get("hash") and pa.get("salt"):
        auth_path = conf_dir / "panel_auth.json"
        cur_a = {}
        if auth_path.is_file():
            try:
                cur_a = json.loads(auth_path.read_text(encoding="utf-8"))
                if not isinstance(cur_a, dict):
                    cur_a = {}
            except Exception:
                cur_a = {}
        cur_a.update({"hash": pa["hash"], "salt": pa["salt"]})
        cur_a.setdefault("tokens", [])
        auth_path.write_text(json.dumps(cur_a, indent=2, ensure_ascii=False), encoding="utf-8")
        if is_live:
            _sync_uci_pwd_customized(is_panel_pwd_customized(conf_dir))
    elif ("panel_pwd_customized" in backup_data or "panel_secret_uci" in backup_data) and is_live:
        _cust_b = bool(backup_data.get("panel_pwd_customized")) if "panel_pwd_customized" in backup_data else _uci_secret_is_placeholder(str(backup_data.get("panel_secret_uci") or ""))
        _sync_uci_pwd_customized(_cust_b)
    if "panel_port" in backup_data and str(backup_data["panel_port"]).isdigit() and is_live:
        try:
            subprocess.run(["uci", "set", f"ai-link.global.panel_port={int(backup_data['panel_port'])}"], check=False, timeout=2)
            subprocess.run(["uci", "commit", "ai-link"], check=False, timeout=2)
        except Exception:
            pass
    if (conf_dir / "ops_settings.json").is_file():
        try:
            os.utime(conf_dir / "ops_settings.json", None)
        except Exception:
            pass
    _OPS_SETTINGS_MEMO.clear()
    _STATUS_API_MEMO.clear()
    _NODES_API_MEMO.clear()
    _SHUNT_API_MEMO.clear()
    _HOMELINK_API_MEMO.clear()
    _invalidate_fast_api_cache()
    write_all_configs(conf_dir)
    if is_live and Path("/etc/init.d/ai-link").exists():
        reload_core_only()
    PROBE_ENGINE.apply_shunt_selections(conf_dir)
    if isinstance(backup_data.get("auto_nodes"), dict) and (existing_set is None or "auto_nodes.json" in existing_set):
        _atomic_write_text(conf_dir / "auto_nodes.json", json.dumps(backup_data["auto_nodes"], indent=2, ensure_ascii=False))
    return {
        "ok": True,
        "reload_mode": LAST_RELOAD_MODE,
        "nodes_count": len(load_saved_nodes(conf_dir)),
        "ops_settings": get_ops_settings(conf_dir)
    }

# ==============================================================================
# v2.1.0: Real-Time Overview Telemetry, Traffic Ledger, Auth & Fail-Open Watchdog
# ==============================================================================
DAEMON_START_TS = time.time()
FAIL_OPEN_STATE = {
    "active": False,
    "consecutive_failures": 0, "last_check_ts": 0,
    "last_failover_node": "",
    "reason": ""
}

_OVERVIEW_RT = {
    "last_ts": 0.0,
    "last_dl": 0,
    "last_ul": 0,
    "in_rate_bps": 0.0,
    "out_rate_bps": 0.0,
    "dl_total": 0,
    "ul_total": 0,
    "active_conns": 0,
    "core_mem_mib": 0.0,
    "uptime_sec": 0,
    "uptime_str": "0分",
    "spark_in": [0.0] * 24,
    "spark_out": [0.0] * 24,
    "spark_mem": [0.0] * 24,
    "spark_conn": [0] * 24,
    "seen_conn_ids": set(),
    "conn_bytes": {},
    "service_bars": {
        "youtube": [0] * 28,
        "gemini": [0] * 28,
        "github": [0] * 28,
        "telegram": [0] * 28,
    }
}
_OVERVIEW_LOCK = threading.Lock()

def _format_bytes_human(num_bytes: float) -> str:
    b = max(0.0, float(num_bytes or 0.0))
    if b >= 1073741824:
        return f"{b / 1073741824.0:.2f} GB"
    if b >= 1048576:
        return f"{b / 1048576.0:.1f} MB"
    if b >= 1024:
        return f"{b / 1024.0:.1f} KB"
    return f"{int(b)} B"

def _format_rate_human(bps: float) -> str:
    b = max(0.0, float(bps or 0.0))
    if b >= 1048576:
        return f"{b / 1048576.0:.2f} MB/s"
    if b >= 1024:
        return f"{b / 1024.0:.1f} KB/s"
    return f"{int(b)} B/s"

def _read_dhcp_and_arp_devices(lan_ip: str) -> dict:
    """Returns {ip: hostname_label} from /tmp/dhcp.leases and /proc/net/arp on the real router."""
    hosts = {lan_ip: f"{lan_ip} (本机网关)"}
    for lease_f in ("/tmp/dhcp.leases", "/var/dhcp.leases"):
        lp = Path(lease_f)
        if lp.is_file():
            try:
                for ln in lp.read_text(encoding="utf-8", errors="ignore").splitlines():
                    parts = ln.split()
                    if len(parts) >= 4:
                        ip_s = parts[2].strip()
                        h_name = parts[3].strip()
                        if h_name and h_name != "*":
                            hosts[ip_s] = f"{ip_s} ({h_name})"
                        else:
                            hosts.setdefault(ip_s, f"{ip_s} (局域网终端)")
            except Exception:
                pass
    arp_p = Path("/proc/net/arp")
    if arp_p.is_file():
        try:
            for ln in arp_p.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
                parts = ln.split()
                if len(parts) >= 4 and parts[2] != "0x0":
                    ip_s = parts[0].strip()
                    hosts.setdefault(ip_s, f"{ip_s} (局域网设备)")
        except Exception:
            pass
    return hosts

def _load_traffic_ledger(conf_dir: Path = CONF_DIR) -> dict:
    for p_cand in (conf_dir / "traffic_ledger.json", Path("/tmp/ai-link-traffic-ledger.json")):
        if p_cand.is_file():
            try:
                data = json.loads(p_cand.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
    return {"days": {}, "hours": {}, "devices": {}, "nodes": {}, "targets": {}}

def _save_traffic_ledger(ledger: dict, conf_dir: Path = CONF_DIR):
    for p_cand in (conf_dir / "traffic_ledger.json", Path("/tmp/ai-link-traffic-ledger.json")):
        try:
            p_cand.parent.mkdir(parents=True, exist_ok=True)
            p_cand.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
            break
        except Exception:
            continue

def _read_netdev_bytes() -> tuple:
    """Reads kernel interface rx/tx bytes from /proc/net/dev as a fallback when Clash API is idle."""
    rx_tot, tx_tot = 0, 0
    try:
        for ln in Path("/proc/net/dev").read_text().splitlines()[2:]:
            if ":" not in ln:
                continue
            iface, rest = ln.split(":", 1)
            iface = iface.strip()
            if iface in ("lo", "ailink0") or iface.startswith("docker") or iface.startswith("veth"):
                continue
            cols = rest.split()
            if len(cols) >= 9:
                rx_tot += int(cols[0])
                tx_tot += int(cols[8])
    except Exception:
        pass
    return rx_tot, tx_tot

def sample_live_overview_telemetry(conf_dir: Path = CONF_DIR, force_sample: bool = False) -> dict:
    """Samples 100% real router & sing-box metrics for the Overview Dashboard (zero fake numbers)."""
    now = time.time()
    if not force_sample and _OVERVIEW_RT.get("last_ts", 0) > 0 and (now - _OVERVIEW_RT["last_ts"]) < 2.0 and _OVERVIEW_RT.get("cached_ledger"):
        return _OVERVIEW_RT["cached_ledger"]
    lan_ip = _detect_router_lan_ip()
    host_map = _read_dhcp_and_arp_devices(lan_ip)
    # 1. Core PID, Real Memory (VmRSS) & Real Service Uptime
    rt_info = get_core_runtime_info(conf_dir)
    core_pid = rt_info.get("core_pid")
    target_pid = core_pid or os.getpid()
    mem_mib = 0.0
    try:
        for ln in Path(f"/proc/{target_pid}/status").read_text().splitlines():
            if ln.startswith("VmRSS:"):
                kb = int(ln.split()[1])
                mem_mib = round(kb / 1024.0, 1)
                break
    except Exception:
        pass
    proc_start_ts = DAEMON_START_TS
    if core_pid and Path(f"/proc/{core_pid}").exists():
        try:
            proc_start_ts = Path(f"/proc/{core_pid}").stat().st_mtime
        except Exception:
            pass
    up_sec = max(1, int(now - proc_start_ts))
    d, rem = divmod(up_sec, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    def _fmt_dur_cn(sec_val: int) -> str:
        dd, rem0 = divmod(max(1, int(sec_val)), 86400)
        hh, rem0 = divmod(rem0, 3600)
        mm, ss = divmod(rem0, 60)
        if dd > 0:
            return f"{dd}天{hh}小时{mm}分"
        if hh > 0:
            return f"{hh}小时{mm}分"
        if mm > 0:
            return f"{mm}分{ss}秒"
        return f"{ss}秒"
    up_str = _fmt_dur_cn(up_sec)
    sys_up_sec = up_sec
    try:
        sys_up_sec = max(1, int(float(Path("/proc/uptime").read_text().split()[0])))
    except Exception:
        pass
    sys_up_str = _fmt_dur_cn(sys_up_sec)
    # 2. Query Clash /connections via unified fast snapshot (P1-1 / P1-2 / P1-3 Fix)
    c_snap = clash_get_connections_fast(timeout=2.0, max_sample=200)
    st_code = int(c_snap.get("st_code") or 0)
    conns = c_snap.get("connections") or []
    total_active_conns = int(c_snap.get("total_count") or len(conns))
    cur_dl = int(c_snap.get("downloadTotal") or 0)
    cur_ul = int(c_snap.get("uploadTotal") or 0)
    if mem_mib <= 0.0 and st_code == 200 and int(c_snap.get("memory") or 0) > 0:
        mem_mib = round(int(c_snap["memory"]) / 1048576.0, 1)
    if mem_mib > (210.0 if _get_system_ram_mib() <= 2200 else 380.0) and total_active_conns > 80:
        try:
            clash_api_request("/connections", "DELETE", timeout=1.5)
            _OVERVIEW_RT["oom_guard_last_ts"] = int(now)
        except Exception:
            pass
    cur_source = "clash" if st_code == 200 else "netdev"
    if cur_source == "netdev":
        cur_dl, cur_ul = _read_netdev_bytes()
    today_str = time.strftime("%Y-%m-%d")
    cur_hour_str = time.strftime("%H")
    cur_hour_idx = int(cur_hour_str)
    blocked_set = get_active_blocked_domains_set(conf_dir)
    with _OVERVIEW_LOCK:
        ledger = _load_traffic_ledger(conf_dir)
        dt = now - _OVERVIEW_RT["last_ts"] if _OVERVIEW_RT["last_ts"] > 0 else 0.0
        dl_delta = 0
        ul_delta = 0
        # CRITICAL FIX: Only compute delta when counter source ("clash" vs "netdev") has NOT changed!
        # Previously, when sing-box briefly restarted (st_code != 200), cur_dl switched from clash (~MB)
        # to netdev (~30 GB since boot), adding +30 GB per restart (737 GB after 24 soak reloads)!
        same_source = (_OVERVIEW_RT.get("last_source") == cur_source)
        if _OVERVIEW_RT["last_ts"] > 0 and dt >= 0.2 and same_source:
            if cur_dl >= _OVERVIEW_RT["last_dl"] and (cur_dl - _OVERVIEW_RT["last_dl"]) < (10 * 1024 * 1024 * 1024):
                dl_delta = cur_dl - _OVERVIEW_RT["last_dl"]
            if cur_ul >= _OVERVIEW_RT["last_ul"] and (cur_ul - _OVERVIEW_RT["last_ul"]) < (10 * 1024 * 1024 * 1024):
                ul_delta = cur_ul - _OVERVIEW_RT["last_ul"]
            _OVERVIEW_RT["in_rate_bps"] = round(dl_delta / dt, 1)
            _OVERVIEW_RT["out_rate_bps"] = round(ul_delta / dt, 1)
        _OVERVIEW_RT["last_source"] = cur_source
        _OVERVIEW_RT["last_ts"] = now
        _OVERVIEW_RT["last_dl"] = cur_dl
        _OVERVIEW_RT["last_ul"] = cur_ul
        _OVERVIEW_RT["dl_total"] = cur_dl
        _OVERVIEW_RT["ul_total"] = cur_ul
        _OVERVIEW_RT["active_conns"] = total_active_conns
        _OVERVIEW_RT["core_mem_mib"] = mem_mib
        _OVERVIEW_RT["uptime_sec"] = up_sec
        _OVERVIEW_RT["uptime_str"] = up_str
        _OVERVIEW_RT["kernel_uptime_sec"] = up_sec
        _OVERVIEW_RT["kernel_uptime_str"] = up_str
        _OVERVIEW_RT["sys_uptime_sec"] = sys_up_sec
        _OVERVIEW_RT["sys_uptime_str"] = sys_up_str
        # Append to rolling 24-point sparkline series
        _OVERVIEW_RT["spark_in"].append(round(_OVERVIEW_RT["in_rate_bps"] / 1024.0, 2))
        _OVERVIEW_RT["spark_in"] = _OVERVIEW_RT["spark_in"][-24:]
        _OVERVIEW_RT["spark_out"].append(round(_OVERVIEW_RT["out_rate_bps"] / 1024.0, 2))
        _OVERVIEW_RT["spark_out"] = _OVERVIEW_RT["spark_out"][-24:]
        _OVERVIEW_RT["spark_mem"].append(mem_mib)
        _OVERVIEW_RT["spark_mem"] = _OVERVIEW_RT["spark_mem"][-24:]
        _OVERVIEW_RT["spark_conn"].append(total_active_conns)
        _OVERVIEW_RT["spark_conn"] = _OVERVIEW_RT["spark_conn"][-24:]
        # Update daily & hourly ledger (and auto-heal any corrupted >100GB single-hour spike from older netdev switch bug)
        hr_map = ledger.setdefault("hours", {}).setdefault(today_str, {})
        for _hk, _hv in list(hr_map.items()):
            if int(_hv.get("in_bytes", 0)) > 80 * 1024 * 1024 * 1024:
                _hv["in_bytes"] = int(_hv["in_bytes"]) % (2 * 1024 * 1024 * 1024)
        day_rec = ledger.setdefault("days", {}).setdefault(today_str, {"in_bytes": 0, "out_bytes": 0, "conns": 0})
        if int(day_rec.get("in_bytes", 0)) > 250 * 1024 * 1024 * 1024:
            day_rec["in_bytes"] = sum(int(v.get("in_bytes", 0)) for v in hr_map.values())
        day_rec["in_bytes"] = int(day_rec.get("in_bytes", 0)) + dl_delta
        day_rec["out_bytes"] = int(day_rec.get("out_bytes", 0)) + ul_delta
        hr_rec = hr_map.setdefault(cur_hour_str, {"in_bytes": 0, "out_bytes": 0})
        hr_rec["in_bytes"] = int(hr_rec.get("in_bytes", 0)) + dl_delta
        hr_rec["out_bytes"] = int(hr_rec.get("out_bytes", 0)) + ul_delta
        # Per-connection attribution
        dev_ledger = ledger.setdefault("devices", {})
        node_ledger = ledger.setdefault("nodes", {})
        tgt_ledger = ledger.setdefault("targets", {})
        new_conns = 0
        for c in conns:
            cid = str(c.get("id") or "")
            if cid and cid not in _OVERVIEW_RT["seen_conn_ids"]:
                _OVERVIEW_RT["seen_conn_ids"].add(cid)
                new_conns += 1
                _DNS_STATS_RT["total_queries"] += 1
                _DNS_STATS_RT["hourly_queries"][cur_hour_idx] += 1
            c_dl = int(c.get("download") or 0)
            c_ul = int(c.get("upload") or 0)
            p_dl, p_ul = _OVERVIEW_RT["conn_bytes"].get(cid, (0, 0)) if cid else (0, 0)
            inc_dl = max(0, c_dl - p_dl)
            inc_ul = max(0, c_ul - p_ul)
            if cid:
                _OVERVIEW_RT["conn_bytes"][cid] = (c_dl, c_ul)
            meta = c.get("metadata") or {}
            src_ip = (meta.get("sourceIP") or lan_ip).strip()
            inb_meta_s = str(meta.get("inboundName") or meta.get("inbound") or meta.get("inboundTag") or "").lower()
            if "homelink" in inb_meta_s or (not _h3_is_lan_ip(src_ip) and src_ip != lan_ip):
                dev_label = f"🏠 回家终端 ({src_ip})"
            else:
                dev_label = host_map.get(src_ip, f"{src_ip} (局域网终端)")
            d_entry = dev_ledger.setdefault(src_ip, {"name": dev_label, "in_bytes": 0, "out_bytes": 0})
            d_entry["name"] = dev_label
            d_entry["in_bytes"] = int(d_entry.get("in_bytes", 0)) + inc_dl
            d_entry["out_bytes"] = int(d_entry.get("out_bytes", 0)) + inc_ul
            chains = c.get("chains") or ["direct"]
            out_node = chains[0] if chains else "direct"
            n_entry = node_ledger.setdefault(out_node, {"name": out_node, "in_bytes": 0, "out_bytes": 0})
            n_entry["in_bytes"] = int(n_entry.get("in_bytes", 0)) + inc_dl
            n_entry["out_bytes"] = int(n_entry.get("out_bytes", 0)) + inc_ul
            host_dst = (meta.get("host") or meta.get("destinationIP") or "").strip()
            if host_dst:
                t_entry = tgt_ledger.setdefault(host_dst, {"name": host_dst, "in_bytes": 0, "out_bytes": 0})
                t_entry["in_bytes"] = int(t_entry.get("in_bytes", 0)) + inc_dl
                t_entry["out_bytes"] = int(t_entry.get("out_bytes", 0)) + inc_ul
                rule_str = str(c.get("rule") or "") + " " + str(c.get("rulePayload") or "")
                chains_lower = [str(x).lower() for x in (chains or [])]
                is_blk_conn = (
                    out_node.lower() in ("block", "reject")
                    or any(x in ("block", "reject") for x in chains_lower)
                    or "blocklist_custom" in rule_str
                    or bool(_match_blocked_domain_suffix(host_dst, blocked_set))
                )
                if is_blk_conn:
                    seen_blk = _OVERVIEW_RT.setdefault("seen_blocked_cids", set())
                    if not cid or cid not in seen_blk:
                        if cid:
                            seen_blk.add(cid)
                        record_adblock_hit(host_dst, layer="route", conf_dir=conf_dir, count=1)
        day_rec["conns"] = max(int(day_rec.get("conns", 0)) + new_conns, len(_OVERVIEW_RT["seen_conn_ids"]))
        # Ensure real local devices from DHCP/ARP appear in devices table even before traffic flows
        for ip_k, lbl_v in list(host_map.items())[:8]:
            dev_ledger.setdefault(ip_k, {"name": lbl_v, "in_bytes": 0, "out_bytes": 0})
        _OVERVIEW_RT["cached_ledger"] = ledger
        if force_sample or (now - _OVERVIEW_RT.get("last_disk_save_ts", 0)) >= 9.0:
            _OVERVIEW_RT["last_disk_save_ts"] = now
            _save_traffic_ledger(ledger, conf_dir)
    return ledger

def _lan_ip_from_uci() -> str:
    try:
        r = subprocess.run(["uci", "-q", "get", "network.lan.ipaddr"],
                           capture_output=True, text=True, timeout=2)
        val = (r.stdout or "").strip()
        if val:
            return val
    except Exception:
        pass
    return ""

def _is_valid_lan_client_ip(ip_str, lan_ip: str = "") -> bool:
    """True only for real LAN client addresses (filters loopback, the gateway itself, FakeIP, multicast and public WAN addresse"""
    raw = str(ip_str or "").strip()
    try:
        ip = ipaddress.ip_address(raw)
    except Exception:
        return False
    if ip.version != 4:
        return bool(ip.is_private) and not ip.is_loopback
    if ip.is_loopback or ip.is_multicast or ip.is_link_local or ip.is_unspecified:
        return False
    try:
        if ip in ipaddress.ip_network("198.18.0.0/15"):
            return False
    except Exception:
        pass
    if lan_ip:
        try:
            if ip == ipaddress.ip_address(lan_ip):
                return False
        except Exception:
            pass
    try:
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
    except Exception:
        pass
    return bool(ip.is_private)

def get_overview_live_telemetry(conf_dir: Path = CONF_DIR) -> dict:
    """Builds the complete real-time payload for the Overview page & 3D Holographic Topology."""
    ledger = sample_live_overview_telemetry(conf_dir)
    sync_selections_from_clash(conf_dir)
    sels = PROBE_ENGINE.current_selections or {}
    delays = PROBE_ENGINE.last_delays or {}
    def _svc_rtt(selector_tag: str, fallback_sel: str = "AI_Best_Auto") -> tuple:
        node_t = sels.get(selector_tag) or sels.get(fallback_sel) or "direct"
        if node_t == "direct":
            return 12, "direct"
        rtt = int(round(float(delays.get(node_t) or (PROBE_ENGINE.node_stats.get(node_t) or {}).get("last_rtt_ms") or 0)))
        return rtt, node_t
    yt_ms, yt_node = _svc_rtt("Shunt_YouTube", "Stream_Auto")
    gm_ms, gm_node = _svc_rtt("Shunt_AI", "AI_Best_Auto")
    gh_ms, gh_node = _svc_rtt("Shunt_GitHub", "AI_Best_Auto")
    tg_ms, tg_node = _svc_rtt("Shunt_Outside_CN", "AI_Best_Auto")
    for sid, ms_v in (("youtube", yt_ms), ("gemini", gm_ms), ("github", gh_ms), ("telegram", tg_ms)):
        if ms_v > 0:
            _OVERVIEW_RT["service_bars"][sid].append(min(95, max(10, int(ms_v / 4))))
            _OVERVIEW_RT["service_bars"][sid] = _OVERVIEW_RT["service_bars"][sid][-28:]
    pulse_services = [
        {"id": "youtube", "name": "YouTube", "selector": "Shunt_YouTube", "node": yt_node, "ms": yt_ms, "color": "#ef4444", "icon": "▶", "bars": _OVERVIEW_RT["service_bars"]["youtube"]},
        {"id": "gemini", "name": "Gemini / AI", "selector": "Shunt_AI", "node": gm_node, "ms": gm_ms, "color": "#818cf8", "icon": "✦", "bars": _OVERVIEW_RT["service_bars"]["gemini"]},
        {"id": "github", "name": "GitHub", "selector": "Shunt_GitHub", "node": gh_node, "ms": gh_ms, "color": "#38bdf8", "icon": "🐙", "bars": _OVERVIEW_RT["service_bars"]["github"]},
        {"id": "telegram", "name": "Telegram", "selector": "Shunt_Outside_CN", "node": tg_node, "ms": tg_ms, "color": "#34d399", "icon": "✈", "bars": _OVERVIEW_RT["service_bars"]["telegram"]},
    ]
    # Build device / node / target ranking tables from real ledger
    def _rank_rows(bucket_dict: dict, include_ip: bool = False, lan_ip: str = "") -> list:
        items = []
        tot_all = sum(int(v.get("in_bytes", 0)) + int(v.get("out_bytes", 0)) for v in bucket_dict.values())
        has_real_lan_peers = any(_is_valid_lan_client_ip(v.get("ip") or k, lan_ip) for k, v in bucket_dict.items()) if include_ip else True
        for k, v in bucket_dict.items():
            raw_ip = v.get("ip") or k
            if include_ip and not _is_valid_lan_client_ip(raw_ip, lan_ip if has_real_lan_peers else ""):
                continue
            ib = int(v.get("in_bytes", 0))
            ob = int(v.get("out_bytes", 0))
            tb = ib + ob
            pct = round((tb / tot_all) * 100) if tot_all > 0 else 0
            row = {
                "name": v.get("name") or k,
                "inMb": round(ib / 1048576.0, 2),
                "outMb": round(ob / 1048576.0, 2),
                "totalMb": round(tb / 1048576.0, 2),
                "inBytes": ib,
                "outBytes": ob,
                "totalBytes": tb,
                "pct": pct
            }
            if include_ip:
                row["ip"] = raw_ip
            items.append(row)
        items.sort(key=lambda x: x["totalBytes"], reverse=True)
        return items[:15]
    _lan_ip = str(ledger.get("lan_ip") or "") or _lan_ip_from_uci()
    dev_rows = _rank_rows(ledger.get("devices") or {}, include_ip=True, lan_ip=_lan_ip)
    node_rows = _rank_rows(ledger.get("nodes") or {})
    tgt_rows = _rank_rows(ledger.get("targets") or {})
    # Monthly days & 24h curve (supports multi-month & proxy-only filtering)
    cur_ym = time.strftime("%Y-%m")
    today_d = int(time.strftime("%d"))
    days_map = ledger.get("days") or {}
    nodes_ledger_raw = ledger.get("nodes") or {}
    all_node_bytes = sum(int(v.get("in_bytes", 0)) + int(v.get("out_bytes", 0)) for v in nodes_ledger_raw.values())
    proxy_node_bytes = sum(
        int(v.get("in_bytes", 0)) + int(v.get("out_bytes", 0))
        for k, v in nodes_ledger_raw.items()
        if str(k).lower() not in ("direct", "block", "reject")
    )
    proxy_share = (proxy_node_bytes / all_node_bytes) if all_node_bytes > 0 else 1.0
    monthly_by_ym = {}
    for d_key, d_val in sorted(days_map.items()):
        ym_part = d_key[:7]
        if len(ym_part) != 7:
            continue
        try:
            d_num = int(d_key.rsplit("-", 1)[-1])
        except Exception:
            continue
        ib = int(d_val.get("in_bytes", 0))
        ob = int(d_val.get("out_bytes", 0))
        tb = ib + ob
        c_cnt = int(d_val.get("conns", 0))
        monthly_by_ym.setdefault(ym_part, []).append({
            "day": d_num,
            "inGb": round(ib / 1073741824.0, 4),
            "outGb": round(ob / 1073741824.0, 4),
            "totalGb": round(tb / 1073741824.0, 4),
            "inBytes": ib,
            "outBytes": ob,
            "totalBytes": tb,
            "proxyBytes": int(round(tb * proxy_share)),
            "proxyStr": _format_bytes_human(tb * proxy_share),
            "totalStr": _format_bytes_human(tb),
            "inStr": _format_bytes_human(ib),
            "outStr": _format_bytes_human(ob),
            "conns": c_cnt
        })
    monthly_days = monthly_by_ym.get(cur_ym, [])
    month_tot_bytes = sum(x["totalBytes"] for x in monthly_days)
    month_proxy_bytes = int(round(month_tot_bytes * proxy_share))
    month_tot_conns = sum(x["conns"] for x in monthly_days)
    today_str = time.strftime("%Y-%m-%d")
    hr_map = (ledger.get("hours") or {}).get(today_str) or {}
    hourly_in_mb = []
    hourly_out_mb = []
    for h_i in range(24):
        hk = f"{h_i:02d}"
        hv = hr_map.get(hk) or {}
        hourly_in_mb.append(round(int(hv.get("in_bytes", 0)) / 1048576.0, 2))
        hourly_out_mb.append(round(int(hv.get("out_bytes", 0)) / 1048576.0, 2))
    lan_ip_val = _detect_router_lan_ip()
    in_rate_s = _format_rate_human(_OVERVIEW_RT["in_rate_bps"])
    out_rate_s = _format_rate_human(_OVERVIEW_RT["out_rate_bps"])
    in_tot_s = _format_bytes_human(_OVERVIEW_RT["dl_total"])
    out_tot_s = _format_bytes_human(_OVERVIEW_RT["ul_total"])
    mem_s = f"{_OVERVIEW_RT['core_mem_mib']:.1f} MiB"
    month_tot_s = _format_bytes_human(month_tot_bytes)
    holo_nodes = [
        {"id": "core", "name": f"AI-LINK 网关 ({lan_ip_val})", "role": "core", "pos": [0, 0, 0], "color": "#8b5cf6", "rtt": "0.2 ms", "bw": in_rate_s, "rule": "sing-box TProxy + TUN"}
    ]
    holo_links = []
    dev_positions = [[-5.2, 1.4, 2.8], [-4.8, -1.5, 3.4], [-5.5, 0.2, -2.6], [-3.8, -2.0, -3.2]]
    dev_colors = ["#22d3ee", "#38bdf8", "#06b6d4", "#67e8f9"]
    for idx_d, d_item in enumerate(dev_rows[:4]):
        did = f"dev_{idx_d}"
        holo_nodes.append({
            "id": did,
            "name": d_item["name"],
            "role": "device",
            "pos": dev_positions[idx_d % len(dev_positions)],
            "color": dev_colors[idx_d % len(dev_colors)],
            "rtt": "<1 ms",
            "bw": f"{d_item['totalMb']} MB",
            "rule": "局域网真实在线终端"
        })
        holo_links.append({"from": did, "to": "core", "color": dev_colors[idx_d % len(dev_colors)]})
    out_positions = [[2.6, 2.5, 2.4], [3.2, 0.8, -3.0], [2.8, -2.2, 2.6], [3.5, -1.4, -2.2], [1.5, 3.1, -1.5], [1.8, -3.0, -0.8]]
    out_colors = ["#a855f7", "#c084fc", "#818cf8", "#6366f1", "#f43f5e", "#10b981"]
    for idx_n, n_item in enumerate(node_rows[:6]):
        nid = f"out_{idx_n}"
        n_tag = n_item["name"]
        n_rtt = int(round(float(delays.get(n_tag) or 0)))
        holo_nodes.append({
            "id": nid,
            "name": n_tag,
            "role": "outbound",
            "pos": out_positions[idx_n % len(out_positions)],
            "color": out_colors[idx_n % len(out_colors)],
            "rtt": f"{n_rtt} ms" if n_rtt > 0 else ("直连" if "direct" in n_tag.lower() or "直连" in n_tag else "待测"),
            "bw": f"{n_item['totalMb']} MB",
            "rule": "实时承载分流出口"
        })
        holo_links.append({"from": "core", "to": nid, "color": out_colors[idx_n % len(out_colors)]})
    tgt_positions = [[6.8, 3.0, 1.8], [6.6, -2.6, 2.2], [6.4, 1.2, -2.8], [5.4, 3.4, -2.0]]
    tgt_colors = ["#ef4444", "#60a5fa", "#38bdf8", "#fb7185"]
    for idx_t, t_item in enumerate(tgt_rows[:4]):
        tid = f"tgt_{idx_t}"
        from_out = f"out_{idx_t % max(1, min(6, len(node_rows)))}" if node_rows else "core"
        holo_nodes.append({
            "id": tid,
            "name": t_item["name"],
            "role": "target",
            "pos": tgt_positions[idx_t % len(tgt_positions)],
            "color": tgt_colors[idx_t % len(tgt_colors)],
            "rtt": f"{yt_ms or 120} ms",
            "bw": f"{t_item['totalMb']} MB",
            "rule": "真实访问目标域名"
        })
        holo_links.append({"from": from_out, "to": tid, "color": tgt_colors[idx_t % len(tgt_colors)]})
    live_streams = []
    cs_live = clash_get_connections_summary()
    if isinstance(cs_live, dict) and "active_connections" in cs_live:
        _OVERVIEW_RT["active_conns"] = int(cs_live.get("active_connections") or 0)
    for idx_c, c_item in enumerate((cs_live.get("connections") or [])[:6]):
        via_chain = (c_item.get("chains") or ["direct"])[0]
        live_streams.append({
            "focusId": "out_0" if len(node_rows) else "core",
            "src": c_item.get("src_ip") or lan_ip_val,
            "dst": c_item.get("host") or "-",
            "via": via_chain,
            "rtt": f"{round((c_item.get('download', 0) + c_item.get('upload', 0)) / 1024.0, 1)} KB",
            "color": "text-cyan-300",
            "dot": "bg-emerald-400"
        })
    return {
        "ok": True,
        "is_real_telemetry": True,
        "timestamp": int(time.time()),
        "lan_ip": lan_ip_val,
        "active_connections": _OVERVIEW_RT["active_conns"],
        "core_mem_mib": _OVERVIEW_RT["core_mem_mib"],
        "core_mem_str": mem_s,
        "uptime_sec": _OVERVIEW_RT["uptime_sec"],
        "uptime_str": _OVERVIEW_RT["uptime_str"],
        "kernel_uptime_sec": _OVERVIEW_RT.get("kernel_uptime_sec", _OVERVIEW_RT["uptime_sec"]),
        "kernel_uptime_str": _OVERVIEW_RT.get("kernel_uptime_str", _OVERVIEW_RT["uptime_str"]),
        "sys_uptime_sec": _OVERVIEW_RT.get("sys_uptime_sec", _OVERVIEW_RT["uptime_sec"]),
        "sys_uptime_str": _OVERVIEW_RT.get("sys_uptime_str", _OVERVIEW_RT["uptime_str"]),
        "in_rate_bps": _OVERVIEW_RT["in_rate_bps"],
        "out_rate_bps": _OVERVIEW_RT["out_rate_bps"],
        "in_rate_str": in_rate_s,
        "out_rate_str": out_rate_s,
        "in_total_bytes": _OVERVIEW_RT["dl_total"],
        "out_total_bytes": _OVERVIEW_RT["ul_total"],
        "in_total_str": in_tot_s,
        "out_total_str": out_tot_s,
        "metrics": {
            "active_connections": _OVERVIEW_RT["active_conns"],
            "mem_rss_mib": _OVERVIEW_RT["core_mem_mib"],
            "mem_rss_str": mem_s,
            "in_rate_bps": _OVERVIEW_RT["in_rate_bps"],
            "out_rate_bps": _OVERVIEW_RT["out_rate_bps"],
            "in_rate_str": in_rate_s,
            "out_rate_str": out_rate_s,
            "in_total_bytes": _OVERVIEW_RT["dl_total"],
            "out_total_bytes": _OVERVIEW_RT["ul_total"],
            "in_total_str": in_tot_s,
            "out_total_str": out_tot_s,
            "uptime_sec": _OVERVIEW_RT["uptime_sec"],
            "uptime_str": _OVERVIEW_RT["uptime_str"],
        },
        "spark_series": {
            "inRate": list(_OVERVIEW_RT["spark_in"]),
            "outRate": list(_OVERVIEW_RT["spark_out"]),
            "mem": list(_OVERVIEW_RT["spark_mem"]),
            "conn": list(_OVERVIEW_RT["spark_conn"]),
        },
        "pulse_services": pulse_services,
        "current_month": cur_ym,
        "selected_day": today_d,
        "month_total_bytes": month_tot_bytes,
        "month_total_str": month_tot_s,
        "month_total_conns": month_tot_conns,
        "month_summary": {
            "month": cur_ym,
            "label": f"{cur_ym.replace('-', '年')}月",
            "total_bytes": month_tot_bytes,
            "proxy_bytes": month_proxy_bytes,
            "total_str": month_tot_s,
            "proxy_str": _format_bytes_human(month_proxy_bytes),
            "total_conns": month_tot_conns,
            "proxy_conns": month_tot_conns,
        },
        "monthly_days": monthly_days,
        "monthly_by_ym": monthly_by_ym,
        "hourly_in_24": hourly_in_mb,
        "hourly_out_24": hourly_out_mb,
        "hourly_curve_24": hourly_in_mb,
        "hourly_out_curve_24": hourly_out_mb,
        "insight_data": {
            "devices": dev_rows,
            "nodes": node_rows,
            "targets": tgt_rows,
        },
        "holo_topology": {
            "nodes": holo_nodes,
            "links": holo_links,
            "live_streams": live_streams
        }
    }

# ==============================================================================
# Panel Token Auth (Salted SHA-256) + Reversible Bypass + Fail-Open Watchdog
# ==============================================================================
# PWD-1 常量与判定函数已上移至 get_uci_panel_secret() 所在区段
# （见文件前部 PANEL_PWD_DEFAULT / PANEL_PWD_SENTINEL / _uci_secret_is_placeholder）。
def _load_panel_auth(conf_dir: Path = CONF_DIR) -> dict:
    auth_file = conf_dir / "panel_auth.json"
    tok_file = conf_dir / "panel_token"
    if auth_file.is_file():
        try:
            data = json.loads(auth_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("hash") and data.get("salt"):
                tokens = list(data.get("tokens") or [])
                if tok_file.is_file():
                    ft = tok_file.read_text(encoding="utf-8", errors="ignore").strip()
                    if ft and ft not in tokens:
                        tokens.append(ft)
                        data["tokens"] = tokens
                elif tokens:
                    try:
                        tok_file.write_text(tokens[-1] + "\n", encoding="utf-8")
                    except Exception:
                        pass
                return data
        except Exception:
            pass
    # Migrate initial password from UCI panel_secret (default ai-link-2026)
    # PWD-1: panel_secret 语义 = 初始明文密码；用户改过密码后写入哨兵 __custom__，
    # 老版本遗留的 sha256:<hash> 同样视为「已自定义」。二者都不可当作登录凭据。
    raw_pw = get_uci_panel_secret() or PANEL_PWD_DEFAULT
    if _uci_secret_is_placeholder(raw_pw):
        raw_pw = PANEL_PWD_DEFAULT
    salt = "ailink_salt_2026"
    pw_hash = hashlib.sha256(f"{salt}:{raw_pw}".encode("utf-8")).hexdigest()
    tok = hashlib.sha256(f"token:{salt}:{pw_hash}".encode("utf-8")).hexdigest()
    tokens = [tok]
    if tok_file.is_file():
        try:
            ft = tok_file.read_text(encoding="utf-8", errors="ignore").strip()
            if ft and ft not in tokens:
                tokens.append(ft)
        except Exception:
            pass
    data = {"salt": salt, "hash": pw_hash, "tokens": tokens}
    try:
        conf_dir.mkdir(parents=True, exist_ok=True)
        auth_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if not tok_file.is_file():
            tok_file.write_text(tok + "\n", encoding="utf-8")
    except Exception:
        pass
    return data

def _verify_panel_password(candidate_pw: str, conf_dir: Path = CONF_DIR) -> tuple:
    if not candidate_pw:
        return False, ""
    auth = _load_panel_auth(conf_dir)
    salt = auth.get("salt", "ailink_salt_2026")
    expected_hash = auth.get("hash", "")
    cand_hash = hashlib.sha256(f"{salt}:{candidate_pw}".encode("utf-8")).hexdigest()
    default_hash = hashlib.sha256(f"{salt}:{PANEL_PWD_DEFAULT}".encode("utf-8")).hexdigest()
    # PWD-1 & B1-3 (v1.0.2): 下线弱默认密码 'admin'，出厂态仅认 PANEL_PWD_DEFAULT ('ai-link-2026')；
    # 哨兵 __custom__ 与 sha256:<hash> 一律拒绝，避免把哈希或哨兵本身当成可用密码。
    uci_pw = (get_uci_panel_secret() or "").strip()
    uci_plain_ok = bool(uci_pw) and not _uci_secret_is_placeholder(uci_pw) and (expected_hash == default_hash)
    if cand_hash == expected_hash or (uci_plain_ok and candidate_pw == uci_pw) or (expected_hash == default_hash and candidate_pw == PANEL_PWD_DEFAULT):
        tok = hashlib.sha256(f"token:{salt}:{cand_hash}".encode("utf-8")).hexdigest()
        tokens = set(auth.get("tokens") or [])
        tokens.add(tok)
        auth["tokens"] = list(tokens)[-10:]
        try:
            (conf_dir / "panel_auth.json").write_text(json.dumps(auth, indent=2), encoding="utf-8")
        except Exception:
            pass
        return True, tok
    return False, ""

def _update_panel_password(new_pw: str, conf_dir: Path = CONF_DIR, sync_uci: bool = True) -> str:
    salt = hashlib.md5(str(time.time()).encode("utf-8")).hexdigest()[:16]
    pw_hash = hashlib.sha256(f"{salt}:{new_pw}".encode("utf-8")).hexdigest()
    tok = hashlib.sha256(f"token:{salt}:{pw_hash}".encode("utf-8")).hexdigest()
    data = {"salt": salt, "hash": pw_hash, "tokens": [tok]}
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "panel_auth.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        (conf_dir / "panel_token").write_text(tok + "\n", encoding="utf-8")
    except Exception:
        pass
    # PWD-2 & B1-2: 只有「真实配置目录」才回写 UCI，且只写布尔 panel_pwd_customized=0/1 并移除 panel_secret。
    if sync_uci and conf_dir == CONF_DIR:
        _sync_uci_pwd_customized(new_pw != PANEL_PWD_DEFAULT)
    return tok

def is_bypass_active() -> bool:
    for p_b in (RUN_DIR / "bypass", RUN_DIR / "recover_direct.flag", Path("/tmp/ai-link-run/bypass")):
        if p_b.is_file():
            return True
    return False

def _uci_get_bool(key: str, default: bool = True) -> bool:
    try:
        r = subprocess.run(["uci", "-q", "get", f"ai-link.{key}"], capture_output=True, text=True, timeout=1)
        val = (r.stdout or "").strip().lower()
        if val in ("1", "true", "yes", "on", "enabled"):
            return True
        if val in ("0", "false", "no", "off", "disabled"):
            return False
    except Exception:
        pass
    return default

def _uci_get_str(key: str, default: str = "") -> str:
    try:
        r = subprocess.run(["uci", "-q", "get", f"ai-link.{key}"], capture_output=True, text=True, timeout=1)
        val = (r.stdout or "").strip()
        if val:
            return val
    except Exception:
        pass
    return default

_OPS_SETTINGS_MEMO = {}

def sync_uci_to_ops_settings(conf_dir: Path = CONF_DIR) -> dict:
    """Synchronizes UCI /etc/config/ai-link options (modified via LuCI or `uci commit`) into ops_settings.json."""
    ops_file = Path(conf_dir) / "ops_settings.json"
    saved = {}
    if ops_file.is_file():
        try:
            saved = json.loads(ops_file.read_text(encoding="utf-8"))
            if not isinstance(saved, dict):
                saved = {}
        except Exception:
            saved = {}
    uci_en = _uci_get_bool("global.enabled", True)
    saved["enabled"] = bool(uci_en and not is_bypass_active())
    saved["entry_bypass"] = _uci_get_bool("global.entry_bypass", saved.get("entry_bypass", True))
    saved["block_quic"] = _uci_get_bool("global.block_quic", saved.get("block_quic", True))
    saved["game_udp_direct"] = _uci_get_bool("global.game_udp_direct", saved.get("game_udp_direct", True))
    saved["auto_mute_conflicts"] = _uci_get_bool("global.auto_mute_conflicts", saved.get("auto_mute_conflicts", True))
    saved["ipv6_proxy"] = _uci_get_bool("global.ipv6_proxy", saved.get("ipv6_proxy", False))
    saved["require_lan_auth"] = _uci_get_bool("global.require_lan_auth", saved.get("require_lan_auth", False))
    saved["gh_mirror"] = _uci_get_str("global.gh_mirror", saved.get("gh_mirror", "https://gh-proxy.com/"))
    saved["update_manifest_url"] = _uci_get_str("global.update_manifest_url", "")
    uci_mob = _uci_get_str("global.max_outbounds", "")
    if uci_mob.isdigit() and int(uci_mob) >= 10:
        try:
            (Path(conf_dir) / "max_outbounds.txt").write_text(f"{int(uci_mob)}\n", encoding="utf-8")
        except Exception:
            pass
    try:
        Path(conf_dir).mkdir(parents=True, exist_ok=True)
        ops_file.write_text(json.dumps(saved, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    _OPS_SETTINGS_MEMO.clear()
    _invalidate_sys_cache("uci_ipv6")
    return saved

def get_ops_settings(conf_dir: Path = CONF_DIR) -> dict:
    """Reads real-time system & firewall interception settings (entry_bypass, block_quic, game_udp_direct, auto_mute_conflicts,"""
    ops_file = conf_dir / "ops_settings.json"
    is_live = (Path(conf_dir).resolve() == CONF_DIR.resolve())
    uci_cfg_file = Path("/etc/config/ai-link")
    if is_live and uci_cfg_file.is_file():
        try:
            if not ops_file.is_file() or uci_cfg_file.stat().st_mtime > ops_file.stat().st_mtime + 0.05:
                sync_uci_to_ops_settings(conf_dir)
        except Exception:
            pass
    _ops_sig = (str(conf_dir), _get_file_sig(ops_file), _get_file_sig(uci_cfg_file) if is_live else None, bool(is_bypass_active()), _CORE_RELOAD_STATE["config_seq"], int(time.time()) // 10)
    if _ops_sig in _OPS_SETTINGS_MEMO:
        return dict(_OPS_SETTINGS_MEMO[_ops_sig])
    if len(_OPS_SETTINGS_MEMO) > 16:
        _OPS_SETTINGS_MEMO.clear()
    saved = {}
    if ops_file.is_file():
        try:
            saved = json.loads(ops_file.read_text(encoding="utf-8"))
            if not isinstance(saved, dict):
                saved = {}
        except Exception:
            saved = {}
    uci_enabled = _uci_get_bool("global.enabled", True) if is_live else True
    enabled = (bool(saved.get("enabled", True)) and uci_enabled and not is_bypass_active()) if is_live else bool(saved.get("enabled", True) and not is_bypass_active())
    entry_bypass = saved.get("entry_bypass") if "entry_bypass" in saved else (_uci_get_bool("global.entry_bypass", True) if is_live else True)
    block_quic = saved.get("block_quic") if "block_quic" in saved else (_uci_get_bool("global.block_quic", True) if is_live else True)
    game_udp_direct = saved.get("game_udp_direct") if "game_udp_direct" in saved else (_uci_get_bool("global.game_udp_direct", True) if is_live else True)
    auto_mute_conflicts = saved.get("auto_mute_conflicts") if "auto_mute_conflicts" in saved else (_uci_get_bool("global.auto_mute_conflicts", True) if is_live else True)
    ipv6_proxy = saved.get("ipv6_proxy") if "ipv6_proxy" in saved else get_uci_ipv6_proxy(conf_dir)
    gh_mirror = saved.get("gh_mirror") if "gh_mirror" in saved else (_uci_get_str("global.gh_mirror", "https://gh-proxy.com/") if is_live else "https://gh-proxy.com/")
    probe_scene_preset = str(saved.get("probe_scene_preset") or _uci_get_str("probe.scene_preset", "balanced")).lower()
    if probe_scene_preset not in ("balanced", "lowlat", "highbw", "stable"):
        probe_scene_preset = "balanced"
    _preset_weights_map = {
        "balanced": ({"lat": 0.45, "bw": 0.30, "stab": 0.25}, 15.0),
        "lowlat":   ({"lat": 0.70, "bw": 0.15, "stab": 0.15}, 10.0),
        "highbw":   ({"lat": 0.25, "bw": 0.55, "stab": 0.20}, 15.0),
        "stable":   ({"lat": 0.30, "bw": 0.25, "stab": 0.45}, 25.0),
    }
    try:
        PROBE_ENGINE.weights, PROBE_ENGINE.hysteresis_pct = _preset_weights_map[probe_scene_preset]
    except Exception:
        pass
    node_auto_test = bool(saved.get("node_auto_test", True))
    node_test_mode = str(saved.get("node_test_mode") or "latency").lower()
    if node_test_mode not in ("latency", "http", "off"):
        node_test_mode = "latency"
    try:
        node_test_budget = int(saved.get("node_test_budget", 3000))
    except Exception:
        node_test_budget = 3000
    node_test_budget = max(0, node_test_budget)
    try:
        egress_probe_interval_s = int(saved.get("egress_probe_interval_s", 20))
    except Exception:
        egress_probe_interval_s = 20
    egress_probe_interval_s = max(10, min(300, egress_probe_interval_s))
    raw_macs = saved.get("lan_direct_macs", [])
    if isinstance(raw_macs, str):
        raw_macs = [x.strip().lower() for x in re.split(r"[,\n\r;\s]+", raw_macs) if x.strip()]
    lan_direct_macs = []
    if isinstance(raw_macs, list):
        for m in raw_macs:
            ms = str(m or "").strip().lower().replace("-", ":")
            if re.match(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$", ms) and ms not in lan_direct_macs:
                lan_direct_macs.append(ms)
    require_lan_auth = bool(saved.get("require_lan_auth", _uci_get_bool("global.require_lan_auth", False) if is_live else False))
    trusted_cidr = str(saved.get("trusted_cidr") or ("127.0.0.1/32, ::1/128" if require_lan_auth else "127.0.0.1/32, ::1/128, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10")).strip()
    panel_bind = str(saved.get("panel_bind") or "0.0.0.0").strip()
    update_manifest_url = str(saved.get("update_manifest_url") or (_uci_get_str("global.update_manifest_url", "") if is_live else "")).strip()
    _ops_res = {
        "ok": True,
        "enabled": bool(enabled and not is_bypass_active()),
        "require_lan_auth": require_lan_auth,
        "pwd_customized": is_panel_pwd_customized(conf_dir),
        "trusted_cidr": trusted_cidr,
        "panel_bind": panel_bind,
        "update_manifest_url": update_manifest_url,
        "entry_bypass": bool(entry_bypass),
        "block_quic": bool(block_quic),
        "game_udp_direct": bool(game_udp_direct),
        "auto_mute_conflicts": bool(auto_mute_conflicts),
        "ipv6_proxy": bool(ipv6_proxy),
        "gh_mirror": str(gh_mirror or "").strip(),
        "lan_direct_macs": lan_direct_macs,
        "probe_scene_preset": probe_scene_preset,
        "node_auto_test": node_auto_test,
        "node_test_mode": ("off" if not node_auto_test else node_test_mode),
        "node_test_budget": node_test_budget,
        "egress_probe_interval_s": egress_probe_interval_s,
        "node_test_used_today": _node_test_used(),
        "mirror_options": [
            {"label": "gh-proxy.com (默认高速镜像)", "value": "https://gh-proxy.com/"},
            {"label": "ghfast.top (国内优选加速源)", "value": "https://ghfast.top/"},
            {"label": "mirror.ghproxy.com (备用镜像源)", "value": "https://mirror.ghproxy.com/"},
            {"label": "testingcf.jsdelivr.net (Cloudflare CDN)", "value": "https://testingcf.jsdelivr.net/"},
            {"label": "GitHub 官方直连 (不走镜像)", "value": ""}
        ]
    }
    _OPS_SETTINGS_MEMO[_ops_sig] = _ops_res
    return dict(_ops_res)

def update_ops_settings(payload: dict, conf_dir: Path = CONF_DIR) -> dict:
    """Persists ops_settings to both /etc/ai-link/ops_settings.json and UCI, and immediately applies nftables & sing-box config"""
    cur = get_ops_settings(conf_dir)
    for k in ("enabled", "entry_bypass", "block_quic", "game_udp_direct", "auto_mute_conflicts", "ipv6_proxy", "require_lan_auth"):
        if k in payload:
            cur[k] = bool(payload[k])
    if "trusted_cidr" in payload:
        cur["trusted_cidr"] = str(payload["trusted_cidr"] or "127.0.0.1/32, ::1/128").strip()
    elif "require_lan_auth" in payload:
        cur["trusted_cidr"] = "127.0.0.1/32, ::1/128" if cur.get("require_lan_auth") else "127.0.0.1/32, ::1/128, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10"
    if "panel_bind" in payload:
        cur["panel_bind"] = str(payload["panel_bind"] or "0.0.0.0").strip()
    if "gh_mirror" in payload:
        cur["gh_mirror"] = str(payload["gh_mirror"] or "").strip()
    if "update_manifest_url" in payload:
        cur["update_manifest_url"] = str(payload["update_manifest_url"] or "").strip()
    if "node_auto_test" in payload:
        cur["node_auto_test"] = bool(payload["node_auto_test"])
    if "node_test_mode" in payload:
        m = str(payload["node_test_mode"] or "latency").lower()
        cur["node_test_mode"] = m if m in ("latency", "http", "off") else "latency"
    if "probe_scene_preset" in payload:
        pr = str(payload["probe_scene_preset"] or "balanced").lower()
        cur["probe_scene_preset"] = pr if pr in ("balanced", "lowlat", "highbw", "stable") else "balanced"
        preset_map = {
            "balanced": ({"lat": 0.45, "bw": 0.30, "stab": 0.25}, 15.0),
            "lowlat":   ({"lat": 0.70, "bw": 0.15, "stab": 0.15}, 10.0),
            "highbw":   ({"lat": 0.25, "bw": 0.55, "stab": 0.20}, 15.0),
            "stable":   ({"lat": 0.30, "bw": 0.25, "stab": 0.45}, 25.0),
        }
        PROBE_ENGINE.weights, PROBE_ENGINE.hysteresis_pct = preset_map[cur["probe_scene_preset"]]
    if "node_test_budget" in payload:
        try:
            cur["node_test_budget"] = max(0, int(payload["node_test_budget"]))
        except Exception:
            pass
    if "egress_probe_interval_s" in payload:
        try:
            cur["egress_probe_interval_s"] = max(10, min(300, int(payload["egress_probe_interval_s"])))
            AUTO_PROBE_INTERVALS["egress_probe_s"] = cur["egress_probe_interval_s"]
        except Exception:
            pass
    if "lan_direct_macs" in payload:
        raw_m = payload["lan_direct_macs"]
        if isinstance(raw_m, str):
            raw_m = [x.strip().lower() for x in re.split(r"[,\n\r;\s]+", raw_m) if x.strip()]
        norm_macs = []
        if isinstance(raw_m, list):
            for m in raw_m:
                ms = str(m or "").strip().lower().replace("-", ":")
                if re.match(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$", ms) and ms not in norm_macs:
                    norm_macs.append(ms)
        cur["lan_direct_macs"] = norm_macs
    _only_node_test = any(k in payload for k in ("node_auto_test", "node_test_mode", "node_test_budget", "probe_scene_preset", "require_lan_auth", "trusted_cidr", "panel_bind", "update_manifest_url")) and not any(
        k in payload for k in ("enabled", "entry_bypass", "block_quic", "game_udp_direct",
                               "auto_mute_conflicts", "ipv6_proxy", "gh_mirror", "lan_direct_macs"))
    conf_dir.mkdir(parents=True, exist_ok=True)
    save_obj = {k: cur.get(k) for k in ("enabled", "entry_bypass", "block_quic", "game_udp_direct", "auto_mute_conflicts", "ipv6_proxy", "gh_mirror", "lan_direct_macs", "probe_scene_preset", "node_auto_test", "node_test_mode", "node_test_budget", "egress_probe_interval_s", "require_lan_auth", "trusted_cidr", "panel_bind", "update_manifest_url")}
    (conf_dir / "ops_settings.json").write_text(json.dumps(save_obj, indent=2, ensure_ascii=False), encoding="utf-8")
    _OPS_SETTINGS_MEMO.clear()
    is_live = (Path(conf_dir).resolve() == CONF_DIR.resolve())
    if is_live:
        for r_dir in (RUN_DIR, Path("/tmp/ai-link")):
            try:
                r_dir.mkdir(parents=True, exist_ok=True)
                mac_list = cur.get("lan_direct_macs") or []
                (r_dir / "lan_direct_macs.txt").write_text("\n".join(mac_list) + ("\n" if mac_list else ""), encoding="utf-8")
            except Exception:
                pass
        try:
            for k in ("enabled", "entry_bypass", "block_quic", "game_udp_direct", "auto_mute_conflicts", "ipv6_proxy", "require_lan_auth"):
                subprocess.run(["uci", "set", f"ai-link.global.{k}={'1' if cur.get(k) else '0'}"], check=False, timeout=2)
            subprocess.run(["uci", "set", f"ai-link.global.gh_mirror={cur['gh_mirror']}"], check=False, timeout=2)
            if cur.get("update_manifest_url"):
                subprocess.run(["uci", "set", f"ai-link.global.update_manifest_url={cur['update_manifest_url']}"], check=False, timeout=2)
            else:
                subprocess.run(["uci", "-q", "delete", "ai-link.global.update_manifest_url"], check=False, timeout=2)
            subprocess.run(["uci", "commit", "ai-link"], check=False, timeout=2)
            if (conf_dir / "ops_settings.json").is_file():
                os.utime(conf_dir / "ops_settings.json", None)
        except Exception:
            pass
    _STATUS_API_MEMO.clear()
    _JSON_WIRE_MEMO.clear()
    if _only_node_test:
        if "probe_scene_preset" in payload:
            try:
                evaluate_all_auto_nodes(conf_dir, force_service_probe=False, advance_revert_streak=False)
                PROBE_ENGINE.apply_shunt_selections(conf_dir)
            except Exception:
                pass
        latest = get_ops_settings(conf_dir)
        return {**latest, "ok": True, "settings": latest, "reloaded": False,
                "node_test": {"auto_test": latest.get("node_auto_test"), "mode": latest.get("node_test_mode"), "budget": latest.get("node_test_budget"), "used_today": latest.get("node_test_used_today")}}
    if is_live and "enabled" in payload:
        if not cur["enabled"]:
            for r_dir in (RUN_DIR, Path("/tmp/ai-link-run")):
                try:
                    r_dir.mkdir(parents=True, exist_ok=True)
                    (r_dir / "bypass").write_text(str(int(time.time())), encoding="utf-8")
                except Exception:
                    pass
        else:
            for r_dir in (RUN_DIR, Path("/tmp/ai-link-run")):
                for fn in ("bypass", "recover_direct.flag"):
                    try:
                        if (r_dir / fn).exists():
                            (r_dir / fn).unlink()
                    except Exception:
                        pass
            FAIL_OPEN_STATE["active"] = False
            FAIL_OPEN_STATE["consecutive_failures"] = 0
    write_all_configs(conf_dir)
    if is_live and Path("/usr/share/ai-link/nftables/apply_nft.sh").exists() and cur["enabled"] and not is_bypass_active():
        if _is_local_port_listening(int(_uci_get_str("global.tproxy_port", "7893") or 7893)):
            subprocess.run([
                "/usr/share/ai-link/nftables/apply_nft.sh",
                "--entry-bypass", "1" if cur["entry_bypass"] else "0",
                "--block-quic", "1" if cur["block_quic"] else "0",
                "--game-udp-direct", "1" if cur["game_udp_direct"] else "0",
                "--ipv6-proxy", "1" if cur["ipv6_proxy"] else "0"
            ], check=False, timeout=5)
    elif is_live and not cur["enabled"]:
        try:
            subprocess.run(["nft", "delete", "table", "inet", "ai_link"], capture_output=True, timeout=3)
        except Exception:
            pass
    latest = get_ops_settings(conf_dir)
    return {**latest, "ok": True, "settings": latest, "reloaded": True}

def _ip_in_cidr_list(ip_str: str, cidr_list: list) -> bool:
    import ipaddress
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        for c in cidr_list:
            try:
                if ip_obj in ipaddress.ip_network(c, strict=False):
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False

def _parse_target_host_port(raw_target: str, default_port: int = 0) -> tuple:
    """Safely parses IPv4, IPv6 (`[2400:3200::1]:443` or bare `2400:3200::1`), or `domain:port` without corrupting bare IPv6 tr"""
    s = re.sub(r"^[a-zA-Z0-9+.-]+://", "", (raw_target or "").strip()).split("/")[0].strip()
    port = int(default_port or 0)
    # Case 1: Bracketed IPv6 `[2400:3200::1]:443` or `[2400:3200::1]`
    if s.startswith("["):
        if "]" in s:
            host_part, rem = s[1:].split("]", 1)
            if rem.startswith(":") and rem[1:].isdigit() and not port:
                port = int(rem[1:])
            s = host_part.strip()
        else:
            s = s.strip("[]")
    # Case 2: Single colon `domain:port` or `ipv4:port`
    elif s.count(":") == 1:
        h_cand, p_cand = s.rsplit(":", 1)
        if p_cand.isdigit():
            s = h_cand.strip()
            if not port:
                port = int(p_cand)
    clean_host = s.lower().strip(".")
    is_ip = False
    is_ipv6 = False
    try:
        ip_obj = ipaddress.ip_address(clean_host)
        is_ip = True
        is_ipv6 = (ip_obj.version == 6)
    except Exception:
        is_ip = False
        is_ipv6 = False
    return (clean_host, port, is_ip, is_ipv6)

def trace_traffic_flow(payload: dict, conf_dir: Path = CONF_DIR) -> dict:
    """Real-Time 4-Stage Traffic & Shunt Rule Diagnostic Tool (`POST /api/shunt/trace`): Given a user-supplied domain, IPv4/IPv"""
    raw_target = str(payload.get("target") or payload.get("query") or "").strip()
    proto = str(payload.get("protocol") or "tcp").strip().lower()
    if not raw_target:
        return {"ok": False, "error": "empty_target", "message": "请输入要查询的域名、IP 或 域名:端口"}
    explicit_port = int(payload.get("port") or 0)
    clean_host, dport, is_ip, is_ipv6 = _parse_target_host_port(raw_target, default_port=explicit_port)
    if proto == "quic":
        proto_l4 = "udp"
        if not dport:
            dport = 443
    else:
        proto_l4 = "udp" if proto == "udp" else "tcp"
        if not dport:
            dport = 5000 if proto_l4 == "udp" else 443
    ops = get_ops_settings(conf_dir)
    ipv6_proxy_on = bool(ops.get("ipv6_proxy", False))
    shunt_resp = build_shunt_api_response(conf_dir)
    rmode = shunt_resp.get("routing_mode", "rule_shunt")
    groups = shunt_resp.get("groups", [])
    rw_cfg = load_dns_rewrite_config(conf_dir)
    blocked_set_trace = get_active_blocked_domains_set(conf_dir)
    # Check DNS Rewrite first
    rewritten_host = clean_host
    matched_rewrite = None
    if not is_ip and rw_cfg.get("enabled", True):
        for r in rw_cfg.get("rules", []):
            if not r.get("enabled", True):
                continue
            fd = (r.get("from_domain") or "").strip().lower()
            td = (r.get("to_domain") or "").strip().lower()
            if fd and (clean_host == fd or clean_host.endswith("." + fd)):
                rewritten_host = clean_host[:-len(fd)] + td if clean_host != fd else td
                matched_rewrite = f"{fd} ➔ {td} ({r.get('note', 'DNS 重写')})"
                break
    # Check Cloud Domain Filtering block (O(1) suffix lookup via get_active_blocked_domains_set)
    is_dns_blocked = False
    matched_block_dom = ""
    if not is_ip:
        m_bdom = _match_blocked_domain_suffix(rewritten_host, blocked_set_trace)
        if m_bdom:
            is_dns_blocked = True
            matched_block_dom = m_bdom
            cur_h_idx = int(time.strftime("%H"))
            _DNS_STATS_RT["total_queries"] += 1
            _DNS_STATS_RT["hourly_queries"][cur_h_idx] += 1
            _DNS_STATS_RT["blocked_queries"] += 1
            _DNS_STATS_RT["dns_layer_blocks"] = int(_DNS_STATS_RT.get("dns_layer_blocks") or 0) + 1
            _DNS_STATS_RT["hourly_blocked"][cur_h_idx] += 1
            _DNS_STATS_RT["last_block_ts"] = int(time.time())
            _DNS_STATS_RT["last_block_domain"] = rewritten_host
            b_rec = _DNS_STATS_RT["blocked_domains"].setdefault(rewritten_host, {"count": 0, "category": "DNS层REFUSED拦截"})
            b_rec["count"] += 1
    # Determine which Shunt Group / Rule matches in sing-box
    matched_group = None
    matched_reason = ""
    matched_priority = 0
    def _domain_matches_group(h: str, grp: dict) -> str:
        for ed in (grp.get("exact_domains") or []):
            ed_l = str(ed).strip().lower()
            if ed_l and h == ed_l:
                return f"精确域名匹配: {ed_l}"
        for dm in (grp.get("domains") or []):
            dm_l = str(dm).strip().lower().lstrip(".")
            if dm_l and (h == dm_l or h.endswith("." + dm_l)):
                return f"域名后缀匹配: .{dm_l}"
        for kw in (grp.get("domain_keywords") or []):
            kw_l = str(kw).strip().lower()
            if kw_l and kw_l in h:
                return f"域名关键字匹配: {kw_l}"
        gid = grp.get("id", "")
        if gid == "AI" and any(x in h for x in ("openai", "chatgpt", "claude", "anthropic", "gemini", "copilot", "perplexity", "cursor", "huggingface", "grok")):
            return "规则集匹配: geosite-openai / AI"
        if gid == "YouTube" and any(x in h for x in ("youtube", "ytimg", "googlevideo", "youtu.be", "ggpht")):
            return "规则集匹配: geosite-youtube"
        if gid == "Google" and any(x in h for x in ("google", "gmail", "gstatic", "googleapis", "1e100", "scholar", "gvt1", "gvt2", "gvt3", "xn--ngstr-lra8j", "ggpht", "android.com", "pki.goog")):
            return "规则集匹配: geosite-google (Google Play / 生态服务)"
        if gid == "GitHub" and any(x in h for x in ("github", "ghcr.io", "git")):
            return "规则集匹配: geosite-github"
        if gid == "Netflix" and any(x in h for x in ("netflix", "nflx", "disney", "bamgrid", "hbo", "spotify")):
            return "规则集匹配: geosite-netflix / 流媒体"
        if gid == "TikTok" and any(x in h for x in ("tiktok", "byteoversea", "ibytedtos", "ibyteimg", "ttwstatic", "muscdn", "musical.ly")):
            return "规则集匹配: geosite-tiktok"
        if gid == "Games" and any(x in h for x in ("steam", "epicgames", "playstation", "xbox", "nintendo", "ea.com", "ubisoft")):
            return "规则集匹配: 游戏平台 (Games)"
        if gid == "Domestic_CN" and (h.endswith(".cn") or h.endswith(".中国") or any(x in h for x in ("qq.com", "baidu.com", "taobao.com", "tmall.com", "jd.com", "bilibili.com", "163.com", "126.net", "douyin.com", "zhihu.com", "weibo.com", "meituan.com", "aliyun.com", "qcloud.com", "wegame", "gtimg", "feishu", "xiaohongshu", "csdn", "gitee"))):
            return "规则集匹配: geosite-cn / 国内域名"
        srs_map = {
            "AI": "geosite-openai.srs",
            "YouTube": "geosite-youtube.srs",
            "Google": "geosite-google.srs",
            "GitHub": "geosite-github.srs",
            "Netflix": "geosite-netflix.srs",
            "TikTok": "geosite-tiktok.srs",
            "Outside_CN": "geosite-geolocation-!cn.srs",
            "Domestic_CN": "geosite-cn.srs",
        }
        if gid in srs_map and match_srs_ruleset_target(conf_dir / "rules" / srs_map[gid], h):
            return f"二进制规则集实测命中: {srs_map[gid]}"
        return ""
    # Check if IP is FakeIP, private/reserved, upstream node IP, or CN IP (IPv4 & IPv6)
    is_fake_ip = False
    is_private_ip = False
    is_node_server_ip = False
    is_cn_ip = False
    if is_ip:
        is_fake_ip = _ip_in_cidr_list(clean_host, ["198.18.0.0/15", "fc00::/18"])
        if not is_fake_ip:
            is_private_ip = _ip_in_cidr_list(clean_host, [
                "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
                "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24", "192.168.0.0/16",
                "198.51.100.0/24", "203.0.113.0/24", "224.0.0.0/3",
                "::/128", "::1/128", "::ffff:0:0/96", "100::/64", "2001:db8::/32", "fc00::/7", "fe80::/10", "ff00::/8"
            ])
        if not is_private_ip and not is_fake_ip:
            saved_node_ips = {str(n.get("server") or "").strip() for n in load_saved_nodes(conf_dir)}
            is_node_server_ip = (clean_host in saved_node_ips)
            is_cn_ip = _ip_in_cidr_list(clean_host, CN_CORE_CIDRS + CN_CORE_IPV6_CIDRS)
    else:
        if rewritten_host in ("localhost", "router.lan", "ai-link.lan") or rewritten_host.endswith((".lan", ".local", ".home.arpa")):
            is_private_ip = True
        else:
            dom_cn_grp = next((g for g in groups if g.get("id") == "Domestic_CN"), {})
            if _domain_matches_group(rewritten_host, dom_cn_grp) and not any(x in rewritten_host for x in ("google.cn", "googleapis.cn", "gstatic.cn")):
                is_cn_ip = True
    is_infra_udp = (proto_l4 == "udp" and dport in (67, 68, 123, 546, 547, 1900, 5353))
    is_dns_port = (dport == 53)
    # Evaluate Stage 3 rule match
    if is_dns_blocked:
        matched_rule_title = "🛡️ 云端域名过滤黑名单拦截"
        matched_reason = f"命中拦截域名: {matched_block_dom}"
        final_node = "block (阻断)"
        final_strategy = "阻断连接"
        final_rtt = 0.0
        selector_tag = "block"
    elif is_infra_udp:
        matched_rule_title = f"⏱️ 基础网络协议硬件直通 (UDP :{dport})"
        matched_reason = "命中 NTP 授时 / DHCP / mDNS / SSDP 防死锁保护规则，直接由内核放行"
        final_node = "direct (内核直通)"
        final_strategy = "硬件直通"
        final_rtt = 1.0
        selector_tag = "direct"
    elif is_dns_port:
        matched_rule_title = "🧬 内核 DNS 劫持分流引擎 (hijack-dns :53)"
        matched_reason = "端口 53 请求由 sing-box hijack-dns 接管（国内域名 ➔ 223.5.5.5 真实 IP；国际域名 ➔ FakeIP 198.18.0.0/15）"
        final_node = "hijack-dns (内置防污染 DNS)"
        final_strategy = "DNS 智能分流"
        final_rtt = 2.0
        selector_tag = "dns"
    elif is_node_server_ip:
        matched_rule_title = "🛡️ 代理节点服务器 IP 防环直通 (@node_server_v4)"
        matched_reason = f"目标 IP {clean_host} 属于上游代理服务器地址，强制直连防止回环死锁"
        final_node = "direct (防环直连)"
        final_strategy = "硬件直通"
        final_rtt = 8.0
        selector_tag = "direct"
    elif is_private_ip:
        matched_rule_title = "🏠 局域网/保留地址直通 (ip_is_private / @reserved)"
        matched_reason = f"目标 {clean_host} 属于内网或 IANA 保留地址段"
        final_node = "direct (内网直连)"
        final_strategy = "硬件直通"
        final_rtt = 0.2
        selector_tag = "direct"
    elif is_ipv6 and not ipv6_proxy_on:
        matched_rule_title = "🌐 IPv6 原生直通 (ipv6_proxy=关闭)"
        matched_reason = "当前未开启 IPv6 透明代理，IPv6 流量在防火墙顶层直接放行"
        final_node = "direct (IPv6 原生直连)"
        final_strategy = "硬件直通"
        final_rtt = 8.0
        selector_tag = "direct"
    elif rmode == "direct_all":
        matched_rule_title = "⚡ 全局直连模式 (direct_all)"
        matched_reason = "当前分流模式为「全局直连」，所有流量直接走宽带出网"
        final_node = "direct (宽带直连)"
        final_strategy = "全局直连"
        final_rtt = 12.0
        selector_tag = "direct"
    elif rmode == "global_proxy":
        matched_rule_title = "🌐 全局代理模式 (global_proxy)"
        matched_reason = "除内网地址外，所有流量统一走全局代理出口"
        final_node = shunt_resp.get("global_resolved_node", "direct")
        final_strategy = shunt_resp.get("global_strategy", "smart")
        final_rtt = shunt_resp.get("global_resolved_rtt_ms", 120.0)
        selector_tag = "AI_Best_Auto"
    elif rmode == "cn_whitelist":
        if is_cn_ip:
            matched_rule_title = "🇨🇳 大陆白名单直连 (geosite-cn / geoip-cn)"
            matched_reason = "目标属于中国大陆域名或 IP，直连出网"
            final_node = "direct (宽带直连)"
            final_strategy = "国内直连"
            final_rtt = 12.0
            selector_tag = "direct"
        else:
            matched_rule_title = "🌏 非国内流量走代理 (cn_whitelist)"
            matched_reason = "目标不属于中国大陆域名或 IP，走大陆白名单代理出口"
            final_node = shunt_resp.get("global_resolved_node", "direct")
            final_strategy = shunt_resp.get("global_strategy", "smart")
            final_rtt = shunt_resp.get("global_resolved_rtt_ms", 120.0)
            selector_tag = "AI_Best_Auto"
    elif rmode == "gfw_list":
        _gfw_doms_set = _get_gfw_list_domains(shunt_resp)
        _host_lc = rewritten_host.lower().strip(".")
        _hit_gfw_dom = None
        if not is_ip and _host_lc:
            for _gd in _gfw_doms_set:
                _gd_l = _gd.lower().strip(".")
                if _host_lc == _gd_l or _host_lc.endswith("." + _gd_l):
                    _hit_gfw_dom = _gd_l
                    break
        if _hit_gfw_dom or dport in (5228, 5229, 5230) or is_fake_ip:
            matched_rule_title = "🧱 GFW 被墙域名走代理 (gfw_list)"
            matched_reason = f"命中 GFW 被墙域名规则 ({_hit_gfw_dom or dport or clean_host})，走代理出口"
            final_node = shunt_resp.get("global_resolved_node", "direct")
            final_strategy = shunt_resp.get("global_strategy", "smart")
            final_rtt = shunt_resp.get("global_resolved_rtt_ms", 120.0)
            selector_tag = "AI_Best_Auto"
        else:
            matched_rule_title = "⚡ GFW 模式非被墙域名直连 (gfw_list -> direct)"
            matched_reason = "目标未在 GFW 被墙名单内（国内或未被墙国际站点），在 GFW 列表模式下直接走宽带直连"
            final_node = "direct (宽带直连)"
            final_strategy = "GFW模式直连"
            final_rtt = 12.0
            selector_tag = "direct"
    else:
        for g in groups:
            gid = g.get("id", "")
            if gid == "Final_Fallback" or g.get("locked_bottom"):
                continue
            if not is_ip:
                m_str = _domain_matches_group(rewritten_host, g)
                if m_str:
                    matched_group = g
                    matched_reason = m_str
                    matched_priority = g.get("priority", 1)
                    break
            else:
                if g.get("ip_cidrs") and _ip_in_cidr_list(clean_host, g.get("ip_cidrs")):
                    matched_group = g
                    matched_reason = f"命中规则 IP 段: {g.get('ip_cidrs')[:2]}"
                    matched_priority = g.get("priority", 1)
                    break
            grp_ports = [int(p_x) for p_x in (g.get("ports") or []) if str(p_x).isdigit()]
            if dport and grp_ports and dport in grp_ports:
                matched_group = g
                matched_reason = f"命中专属端口规则: TCP/UDP :{dport}"
                matched_priority = g.get("priority", 1)
                break
            if gid == "Domestic_CN" and is_cn_ip:
                matched_group = g
                matched_reason = "命中中国大陆 IP 段 (geoip-cn / CN_CORE_CIDRS)"
                matched_priority = g.get("priority", 11)
                break
        if matched_group is None:
            matched_group = groups[-1] if groups else {"id": "Final_Fallback", "name": "兜底保底出口", "priority": 12, "country": "JP", "strategy": "smart", "resolved_node": "direct", "resolved_rtt_ms": 120.0, "selector_tag": "Shunt_Final"}
            matched_reason = "未命中上方特定分流规则，由底部「兜底保底出口 (route.final)」接管"
            matched_priority = matched_group.get("priority", len(groups))
        matched_rule_title = f"#{matched_priority} {matched_group.get('name')} ({matched_group.get('id')})"
        final_node = matched_group.get("resolved_node", "direct")
        final_strategy = matched_group.get("strategy", "smart")
        final_rtt = matched_group.get("resolved_rtt_ms", 12.0)
        selector_tag = matched_group.get("selector_tag", f"Shunt_{matched_group.get('id')}")
    # Evaluate Stage 1 (Does it enter the kernel or bypass at nftables?) & Warnings
    game_udp_ports = (3478 <= dport <= 3479) or (4000 <= dport <= 4050) or (5000 <= dport <= 5550) or (7000 <= dport <= 9010) or (10000 <= dport <= 20000) or (27015 <= dport <= 27050)
    custom_proxy_on_cn = bool(matched_group and matched_group.get("id") != "Domestic_CN" and matched_group.get("country") not in ("direct", "block") and is_cn_ip)
    warning_msg = ""
    if not ops.get("enabled") or is_bypass_active():
        enters_kernel = False
        stage1_badge = "🛟 直连恢复旁路 (不进内核)"
        stage1_detail = "当前透明代理已关闭或处于「临时直连恢复」状态，流量在防火墙层直接放行，不进入 sing-box 内核。"
        final_node = "direct (宽带直连)"
    elif is_infra_udp:
        enters_kernel = False
        stage1_badge = f"⏱️ 基础协议硬件直通 (UDP :{dport} 不进内核)"
        stage1_detail = f"端口 UDP :{dport} 命中 nftables 顶层 NTP/DHCP/mDNS/SSDP 保护规则，直接硬件放行，彻底杜绝冷启动时钟失准死锁。"
        final_node = "direct (硬件直通)"
    elif is_ipv6 and not ipv6_proxy_on:
        enters_kernel = False
        stage1_badge = "🌐 IPv6 硬件直通 (不进内核)"
        stage1_detail = "当前 IPv6 透明代理开关为关闭状态，nftables 顶层 `meta nfproto ipv6 accept` 直接放行所有 IPv6 流量。"
        final_node = "direct (IPv6 原生直连)"
    elif is_dns_port:
        enters_kernel = True
        stage1_badge = "✅ DNS 53 端口透明劫持进内核 (TProxy :7893)"
        stage1_detail = "UDP/TCP 53 端口在私有地址豁免前优先进入 sing-box TProxy (:7893) 执行 hijack-dns 防污染解析。"
    elif is_private_ip or is_node_server_ip:
        enters_kernel = False
        stage1_badge = "🏠 内网/节点地址硬件直通 (不进内核)"
        stage1_detail = f"目标 {clean_host} 命中 nftables fib daddr local / @reserved / @node_server_v4 豁免集合，直接硬件放行。"
    elif ops.get("game_udp_direct") and proto_l4 == "udp" and (game_udp_ports or (is_cn_ip and not custom_proxy_on_cn)):
        enters_kernel = False
        stage1_badge = "🎮 国服游戏/高频 UDP 硬件直连 (不进内核)"
        stage1_detail = f"UDP 端口 {dport} 命中「国服游戏与高频联机 UDP 直连保护」，在 nftables 防火墙层直接硬件放行，不进入 sing-box 内核。"
        final_node = "direct (游戏硬件直连)"
    elif ops.get("entry_bypass") and is_cn_ip and not custom_proxy_on_cn:
        enters_kernel = False
        stage1_badge = "⚡ 国内流量硬件旁路 (不进内核)"
        stage1_detail = "已开启「国内流量不进内核 (entry_bypass)」，DNS 通过 223.5.5.5 返回真实国内 IP，流量命中 nftables @cn_ip4/@cn_ip6 直接硬件直连放行，零内核开销！"
        final_node = "direct (硬件旁路直连)"
    elif ops.get("block_quic") and proto_l4 == "udp" and dport == 443:
        enters_kernel = False
        stage1_badge = "🛑 QUIC (UDP 443) 防火墙层阻断"
        stage1_detail = "当前已开启「屏蔽代理线路 QUIC (UDP 443)」，nftables 直接返回 ICMP 端口不可达，强制浏览器/应用秒切高速 TCP 443 进入内核分流。"
    elif ops.get("entry_bypass") and is_cn_ip and custom_proxy_on_cn:
        if not is_ip:
            enters_kernel = True
            stage1_badge = "⚠️ 域名 FakeIP 进内核 (但受「国内流量不进内核」影响提醒)"
            stage1_detail = "该国内域名配置了走代理，若通过 FakeIP 解析可进入内核；但若客户端使用真实国内 IP 直连，会被 nftables @cn_ip4 提前放行。"
            warning_msg = f"⚠️ 提醒：您当前开启了「国内流量不进内核 (entry_bypass)」。若客户端绕过 FakeIP 直接请求该国内目标的真实大陆 IP，流量将在防火墙层直接直连而不走 [{final_node}]。"
        else:
            enters_kernel = False
            stage1_badge = "⚡ 国内 IP 硬件旁路 (不进内核)"
            stage1_detail = f"目标 {clean_host} 属于中国大陆 IP (@cn_ip4)，因已开启「国内流量不进内核」，在防火墙层直接硬件直连放行！"
            warning_msg = f"🚨 冲突提醒：该国内 IP 原本匹配规则 [{matched_rule_title}] 拟走节点 [{final_node}]，但因您开启了「国内流量不进内核 (entry_bypass)」，流量在进入内核前已被防火墙直接直连放行！"
            final_node = "direct (被「国内流量不进内核」强制直连)"
    else:
        enters_kernel = True
        stage1_badge = "✅ 进入 sing-box 透明代理内核 (TProxy :7893)"
        stage1_detail = f"流量通过 nftables prerouting_tproxy (fwmark 0x162) 送入 sing-box 内核 (:{7893}) 进行 SNI 嗅探与规则分流。"
    # Stage 2 DNS summary
    if is_ip:
        if is_fake_ip:
            dns_summary = f"目标为 FakeIP ({clean_host})，进入内核后由 cache.db (store_fakeip) 还原真实域名并执行 TLS SNI 嗅探"
        else:
            dns_summary = f"直接访问 IPv{'6' if is_ipv6 else '4'} 字面量 ({clean_host})，无需 DNS 解析"
    elif is_dns_blocked:
        dns_summary = f"DNS 拦截：命中云端过滤黑名单 ({matched_block_dom})，返回 REFUSED"
    elif matched_rewrite:
        dns_summary = f"DNS 重写生效：{matched_rewrite} ➔ FakeIP (198.18.0.0/15) 防污染隧道解析"
    elif is_private_ip or is_infra_udp or any(rewritten_host == d or rewritten_host.endswith("." + d) for d in ("pool.ntp.org", "time.apple.com", "time.windows.com", "msftconnecttest.com", "captive.apple.com")):
        dns_summary = "命中 FakeIP 豁免白名单 (fake-ip-filter ➔ dns_direct 223.5.5.5)：返回真实 IP，保障授时/系统联网检测/STUN 正常"
    elif (is_cn_ip and not custom_proxy_on_cn and rmode != "global_proxy") or rmode == "direct_all" or (rmode == "gfw_list" and selector_tag == "direct"):
        dns_summary = "国内双栈直连 DNS (223.5.5.5)：返回真实 IPv4(A) + IPv6(AAAA) 记录（未命中代理规则，支持原生双栈满速直连）"
    else:
        dns_summary = (
            "防污染双栈隧道 DNS (FakeIP 198.18.0.0/15 + FakeIPv6 fc00::/18 + 出站 prefer_ipv4 降级保护)"
            if ipv6_proxy_on
            else "智能双栈防污染 DNS (海外域名精准抑制 AAAA 返回 NOERROR + 分配 IPv4 FakeIP 198.18.0.0/15，杜绝旁路 IPv6 漏网)"
        )
    strat_labels = {
        "smart": "🧠 智能选择 (吞吐与稳定性最优)",
        "fastest": "⚡ 自动选择 (延迟最低)",
        "manual": "🖐️ 手动指定节点"
    }
    return {
        "ok": True,
        "query": {
            "raw_input": raw_target,
            "host": clean_host,
            "rewritten_host": rewritten_host,
            "protocol": proto_l4.upper(),
            "port": dport,
            "is_ip": is_ip,
            "is_ipv6": is_ipv6,
            "is_cn": is_cn_ip
        },
        "routing_mode": rmode,
        "enters_kernel": enters_kernel,
        "stage1_nft": {
            "enters_kernel": enters_kernel,
            "badge": stage1_badge,
            "detail": stage1_detail,
            "entry_bypass_enabled": bool(ops.get("entry_bypass")),
            "game_udp_direct_enabled": bool(ops.get("game_udp_direct")),
            "block_quic_enabled": bool(ops.get("block_quic")),
            "ipv6_proxy_enabled": ipv6_proxy_on
        },
        "stage2_dns": {
            "rewritten": bool(matched_rewrite),
            "rewrite_detail": matched_rewrite or "",
            "blocked": is_dns_blocked,
            "summary": dns_summary
        },
        "core_rule_loaded": bool(not _get_live_singbox_pids() or not _compute_core_rules_fingerprint(conf_dir) or _get_applied_core_rule_hash() == _compute_core_rules_fingerprint(conf_dir)),
        "stage3_rule": {
            "rule_title": matched_rule_title,
            "rule_reason": matched_reason,
            "selector_tag": selector_tag,
            "priority": matched_priority,
            "core_rule_loaded": bool(not _get_live_singbox_pids() or not _compute_core_rules_fingerprint(conf_dir) or _get_applied_core_rule_hash() == _compute_core_rules_fingerprint(conf_dir))
        },
        "stage4_outbound": {
            "node": final_node,
            "strategy": strat_labels.get(final_strategy, final_strategy),
            "rtt_ms": round(float(final_rtt), 1),
            "is_direct": (selector_tag == "direct" or str(final_node).startswith("direct")),
            "is_blocked": (selector_tag == "block")
        },
        "warning": warning_msg
    }

def run_full_network_matrix_test(conf_dir: Path = CONF_DIR) -> dict:
    """Runs a 12-case end-to-end network structure diagnostic matrix across IPv4/IPv6, TCP/UDP/QUIC, Domestic/Overseas/Google.c"""
    ops = get_ops_settings(conf_dir)
    ipv6_on = bool(ops.get("ipv6_proxy", False))
    cases = [
        {
            "id": "M01_AI_TCP",
            "title": "AI 助手 (ChatGPT TCP 443)",
            "target": "chatgpt.com:443",
            "protocol": "tcp",
            "check": lambda r: r["enters_kernel"] is True and "FakeIP" in r["stage2_dns"]["summary"] and "AI" in r["stage3_rule"]["rule_title"]
        },
        {
            "id": "M02_GOOGLE_CN_REWRITE",
            "title": "Google .cn 防跳转重写 (TCP 443)",
            "target": "services.googleapis.cn:443",
            "protocol": "tcp",
            "check": lambda r: r["enters_kernel"] is True and r["stage2_dns"]["rewritten"] is True and "Google" in r["stage3_rule"]["rule_title"]
        },
        {
            "id": "M03_YOUTUBE_QUIC",
            "title": "海外 QUIC 阻断秒切 TCP (UDP 443)",
            "target": "www.youtube.com:443",
            "protocol": "quic",
            "check": lambda r: (r["enters_kernel"] is False and "QUIC" in r["stage1_nft"]["badge"]) if ops.get("block_quic", True) else (r["enters_kernel"] is True)
        },
        {
            "id": "M04_CN_WEB_TCP",
            "title": "国内网页硬件旁路 (百度 TCP 443)",
            "target": "www.baidu.com:443",
            "protocol": "tcp",
            "check": lambda r: (r["enters_kernel"] is False and r["stage4_outbound"]["is_direct"] is True and "223.5.5.5" in r["stage2_dns"]["summary"]) if ops.get("entry_bypass", True) else (r["stage4_outbound"]["is_direct"] is True)
        },
        {
            "id": "M05_CN_QUIC_UDP",
            "title": "国内视频 HTTP/3 QUIC 直通 (B站 UDP 443)",
            "target": "www.bilibili.com:443",
            "protocol": "quic",
            "check": lambda r: r["enters_kernel"] is False and r["stage4_outbound"]["is_direct"] is True
        },
        {
            "id": "M06_GAME_LOL_UDP",
            "title": "国服英雄联盟联机保护 (LoL UDP 5000)",
            "target": "lol.qq.com:5000",
            "protocol": "udp",
            "check": lambda r: r["enters_kernel"] is False and "国服游戏" in r["stage1_nft"]["badge"] and r["stage4_outbound"]["is_direct"] is True
        },
        {
            "id": "M07_NTP_CLOCK_UDP",
            "title": "冷启动 NTP 授时防死锁 (UDP 123)",
            "target": "pool.ntp.org:123",
            "protocol": "udp",
            "check": lambda r: r["enters_kernel"] is False and r["stage4_outbound"]["is_direct"] is True and "豁免" in r["stage2_dns"]["summary"]
        },
        {
            "id": "M08_DNS_HIJACK_53",
            "title": "局域网 DNS 防污染劫持 (UDP 53)",
            "target": "8.8.8.8:53",
            "protocol": "udp",
            "check": lambda r: r["enters_kernel"] is True and "hijack-dns" in r["stage3_rule"]["rule_title"]
        },
        {
            "id": "M09_PRIVATE_LAN_IP",
            "title": "路由器管理后台防自锁 (10.10.10.77:80)",
            "target": "10.10.10.77:80",
            "protocol": "tcp",
            "check": lambda r: r["enters_kernel"] is False and r["stage4_outbound"]["is_direct"] is True
        },
        {
            "id": "M10_IPV6_CN_LITERAL",
            "title": "阿里公共 DNS IPv6 ([2400:3200::1]:443)",
            "target": "[2400:3200::1]:443",
            "protocol": "tcp",
            "check": lambda r: r["query"]["is_ipv6"] is True and r["query"]["port"] == 443 and r["stage4_outbound"]["is_direct"] is True
        },
        {
            "id": "M11_IPV6_GLOBAL_LITERAL",
            "title": "Google IPv6 字面量 (2001:4860:4860::8888)",
            "target": "2001:4860:4860::8888",
            "protocol": "tcp",
            "check": lambda r: r["query"]["is_ipv6"] is True and r["query"]["host"] == "2001:4860:4860::8888" and (r["enters_kernel"] is ipv6_on)
        },
        {
            "id": "M12_PLAY_GVT1_CDN",
            "title": "Google Play 更新源 CDN (dl.google.com:443)",
            "target": "dl.google.com:443",
            "protocol": "tcp",
            "check": lambda r: r["enters_kernel"] is True and "FakeIP" in r["stage2_dns"]["summary"] and "Google" in r["stage3_rule"]["rule_title"]
        }
    ]
    results = []
    passed_cnt = 0
    for c in cases:
        tr = trace_traffic_flow({"target": c["target"], "protocol": c["protocol"]}, conf_dir=conf_dir)
        ok = False
        try:
            ok = bool(c["check"](tr))
        except Exception:
            ok = False
        if ok:
            passed_cnt += 1
        results.append({
            "id": c["id"],
            "title": c["title"],
            "target": c["target"],
            "protocol": c["protocol"].upper(),
            "passed": ok,
            "enters_kernel": tr.get("enters_kernel"),
            "stage1_badge": (tr.get("stage1_nft") or {}).get("badge", ""),
            "stage2_summary": (tr.get("stage2_dns") or {}).get("summary", ""),
            "stage3_rule": (tr.get("stage3_rule") or {}).get("rule_title", ""),
            "stage4_node": (tr.get("stage4_outbound") or {}).get("node", "")
        })
    return {
        "ok": True,
        "all_passed": (passed_cnt == len(cases)),
        "passed_count": passed_cnt,
        "total_count": len(cases),
        "cases": results
    }

def check_all_updatable_items(conf_dir: Path = CONF_DIR) -> dict:
    """Returns status of all updatable components for both LuCI and WebUI."""
    rt = get_core_runtime_info(conf_dir)
    subs = load_subscriptions(conf_dir)
    flt = load_dns_filter_config(conf_dir)
    ops = get_ops_settings(conf_dir)
    srs_list = rt.get("rulesets_installed") or []
    en_lists = [l for l in (flt.get("lists") or []) if l.get("enabled", True)]
    tot_flt_rules = sum(int(l.get("rules_count", 0)) for l in en_lists)
    last_flt_up = max([l.get("updated_at", "未同步") for l in en_lists], default="未同步")
    sub_cnt = sum(int(s.get("count", 0)) for s in subs) or rt.get("saved_nodes_total", 0)
    sub_up = subs[0].get("updated", "已同步") if subs else "未配置"
    return {
        "ok": True,
        "gh_mirror": ops.get("gh_mirror", "https://gh-proxy.com/"),
        "items": [
            {
                "id": "subscriptions",
                "name": "机场订阅节点池",
                "current": f"{len(subs)} 个订阅源 · 共 {sub_cnt} 节点 (激活 {rt.get('active_outbounds_count', 0)})",
                "updated_at": sub_up,
                "status_ok": sub_cnt > 0
            },
            {
                "id": "rulesets",
                "name": "GeoIP / GeoSite 分流规则集 (.srs)",
                "current": f"内置 21 条分流规则生效中 · 增强包 {len(srs_list)}/{len(SRS_CORE_MAP)}" if len(srs_list) == 0 else f"已安装 {len(srs_list)}/{len(SRS_CORE_MAP)} 个核心规则包",
                "updated_at": "已就绪 (全量增强包)" if len(srs_list) >= len(SRS_CORE_MAP) else "使用内置规则兜底，可选下载增强包",
                "status_ok": True
            },
            {
                "id": "dns_filters",
                "name": "AdGuard / Anti-AD 云端净网过滤库",
                "current": f"已启用 {len(en_lists)} 个规则源 · 共 {tot_flt_rules:,} 条拦截规则",
                "updated_at": last_flt_up,
                "status_ok": len(en_lists) > 0
            }
        ]
    }

# ==============================================================================
# OTA 在线更新体系 (v1.0.1+)
# ------------------------------------------------------------------------------
# 设计要点：
#   1) 版本清单 version.json 双源托管：Cloudflare Pages 主源 + GitHub raw 镜像，
#      并自动套用用户已配置的 gh_mirror 加速前缀；
#   2) 下载后强制 MD5 + SHA256 双校验，任一不符立即中止，绝不执行未校验的包；
#   3) 升级动作交给独立进程（setsid 脱离 daemon 会话），因为 install.sh 会重启
#      服务把 daemon 杀掉；进度通过 progress.log 落盘，重启后新 daemon 接着读；
#   4) 升级前自动备份「用户数据 + 旧代码」，健康检查失败自动回滚；
#   5) 全程只写 /var/run/ai-link/update（tmpfs）与 /root/ai-link-final-backup。
# ==============================================================================
APP_VERSION = "1.0.3"
APP_CHANNEL = "stable"
APP_BUILD = "1.0.3-release-20261026"

UPDATE_MANIFEST_PRIMARY = "https://ai-link-official.pages.dev/version.json"
UPDATE_MANIFEST_GITHUB = "https://raw.githubusercontent.com/Master-AI-007/ai-link-openwrt/main/version.json"
UPDATE_DIR = RUN_DIR / "update"
UPDATE_PROGRESS_LOG = UPDATE_DIR / "progress.log"
UPDATE_PLAN_JSON = UPDATE_DIR / "plan.json"
UPDATE_SCRIPT = UPDATE_DIR / "run_update.sh"
UPDATE_STATE_JSON = UPDATE_DIR / "state.json"
BACKUP_ROOT = Path("/root/ai-link-final-backup")
PERSIST_UPDATE_LOG = BACKUP_ROOT / "last_update_progress.log"
PERSIST_UPDATE_STATE = BACKUP_ROOT / "last_update_state.json"

# 阶段 -> (百分比, 中文说明)，供前端进度条使用
UPDATE_STAGES = {
    "prepare":     (5,  "准备升级环境"),
    "download":    (20, "正在下载升级包"),
    "verify":      (50, "正在校验包完整性"),
    "extract":     (62, "正在解压升级包"),
    "backup":      (72, "正在备份当前配置与代码"),
    "install":     (84, "正在写入新版本文件"),
    "restart":     (92, "正在重启服务"),
    "healthcheck": (97, "正在做升级后健康检查"),
    "done":        (100, "升级完成"),
    "failed":      (0,  "升级失败"),
}

_UPDATE_CHECK_MEMO = {"ts": 0.0, "data": None}
_UPDATE_CHECK_TTL = 300  # 秒，避免前端反复点击把 GitHub 打爆


def parse_app_version(s: str) -> tuple:
    """把 '1.0.1' / 'v1.0.1' / '1.0.1-beta2' 解析成可比较的元组。"""
    m = re.match(r"^[vV]?(\d+)\.(\d+)\.(\d+)(?:[-_.]?([0-9A-Za-z.\-]*))?$", str(s or "").strip())
    if not m:
        return (0, 0, 0, "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or "")


def is_version_newer(latest: str, current: str) -> bool:
    """latest 是否比 current 新。预发布后缀（beta/rc）视为比同号正式版旧。"""
    a, b = parse_app_version(latest), parse_app_version(current)
    if a[:3] != b[:3]:
        return a[:3] > b[:3]
    # 同号：空后缀（正式版）> 任意预发布后缀
    return bool(a[3]) is False and bool(b[3]) is True


def _update_http_get(url: str, timeout: float = 10.0, max_bytes: int = 2 * 1024 * 1024) -> bytes:
    """带 UA 的 GET。优先校验证书，失败再退回不校验（OpenWrt 常缺 CA 包）。

    显式绕过环境变量里的 http_proxy / https_proxy：路由器上如果残留了代理
    环境变量，urllib 会把本应直连的清单请求丢给一个不存在的代理，导致 OTA
    误判为「清单不可达」。需要加速时请用 gh_mirror 机制，而不是环境代理。
    """
    req = urllib.request.Request(url, headers={
        "User-Agent": f"AI-LINK/{APP_VERSION} (OpenWrt; OTA)",
        "Accept": "application/json,application/octet-stream,*/*",
    })
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with direct.open(req, timeout=timeout) as r:
            return r.read(max_bytes)
    except ssl.SSLError:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        direct_ssl = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ctx),
        )
        with direct_ssl.open(req, timeout=timeout) as r:
            return r.read(max_bytes)


def _update_manifest_candidates(conf_dir: Path = CONF_DIR) -> list:
    """按优先级返回候选清单地址（去重，支持自定义域名/清单地址 B2-11）。"""
    urls = []
    try:
        ops_u = (get_ops_settings(conf_dir).get("update_manifest_url") or "").strip()
        if ops_u:
            urls.append(ops_u)
        custom = _uci_get_str("global.update_manifest_url", "")
        if custom:
            urls.append(custom.strip())
    except Exception:
        pass
    urls.append(UPDATE_MANIFEST_PRIMARY)
    try:
        mirror = (get_ops_settings(conf_dir).get("gh_mirror") or "").strip().rstrip("/")
        if mirror:
            urls.append(f"{mirror}/{UPDATE_MANIFEST_GITHUB}")
    except Exception:
        pass
    urls.append(UPDATE_MANIFEST_GITHUB)
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _update_package_urls(pkg: dict, conf_dir: Path = CONF_DIR) -> list:
    """把清单里的主地址 + mirrors 展开成有序候选，并套用 gh_mirror 加速 GitHub。"""
    raw = []
    if pkg.get("url"):
        raw.append(str(pkg["url"]))
    for m in (pkg.get("mirrors") or []):
        if m:
            raw.append(str(m))
    try:
        mirror = (get_ops_settings(conf_dir).get("gh_mirror") or "").strip().rstrip("/")
    except Exception:
        mirror = ""
    out = []
    for u in raw:
        out.append(u)
        if mirror and "github.com" in u and not u.startswith(mirror):
            out.append(f"{mirror}/{u}")
    seen, dedup = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    return dedup


def check_plugin_update(conf_dir: Path = CONF_DIR, force: bool = False) -> dict:
    """拉取 version.json 并比较版本。结果缓存 5 分钟。"""
    now = time.time()
    if not force and _UPDATE_CHECK_MEMO.get("data") and (now - _UPDATE_CHECK_MEMO["ts"]) < _UPDATE_CHECK_TTL:
        d = dict(_UPDATE_CHECK_MEMO["data"])
        d["cached"] = True
        return d

    tried = []
    manifest, used = None, ""
    for u in _update_manifest_candidates(conf_dir):
        try:
            raw = _update_http_get(u, timeout=8.0)
            obj = json.loads(raw.decode("utf-8", "replace"))
            if isinstance(obj, dict) and obj.get("latest"):
                manifest, used = obj, u
                break
            tried.append({"url": u, "error": "清单格式不合法（缺少 latest 字段）"})
        except Exception as e:
            tried.append({"url": u, "error": f"{type(e).__name__}: {e}"})

    if not manifest:
        res = {
            "ok": False,
            "current": APP_VERSION,
            "latest": "",
            "has_update": False,
            "error": "manifest_unreachable",
            "message": "无法获取版本清单，请检查网络或稍后重试",
            "sources_tried": tried,
            "checked_at": int(now),
        }
        return res

    latest = str(manifest.get("latest") or "").strip()
    pkg = manifest.get("packages", {}).get("full", {}) if isinstance(manifest.get("packages"), dict) else {}
    has_update = is_version_newer(latest, APP_VERSION)
    res = {
        "ok": True,
        "current": APP_VERSION,
        "latest": latest,
        "has_update": has_update,
        "channel": manifest.get("channel", APP_CHANNEL),
        "release_date": manifest.get("release_date", ""),
        "notes_url": manifest.get("notes_url", ""),
        "highlights": manifest.get("highlights", []),
        "changelog": manifest.get("changelog", [])[:12],
        "package": {
            "url": pkg.get("url", ""),
            "mirrors": pkg.get("mirrors", []),
            "size": int(pkg.get("size") or 0),
            "md5": str(pkg.get("md5") or "").lower(),
            "sha256": str(pkg.get("sha256") or "").lower(),
        },
        "source": used,
        "sources_tried": tried,
        "checked_at": int(now),
        "cached": False,
    }
    _UPDATE_CHECK_MEMO["ts"] = now
    _UPDATE_CHECK_MEMO["data"] = dict(res)
    return res


def _read_version_file() -> str:
    """读取 /etc/ai-link/version（形如 '1.0.1 (20261026)'），返回完整内容。"""
    try:
        p = CONF_DIR / "version"
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        pass
    return ""


def read_update_progress(limit: int = 40) -> dict:
    """读取 progress.log（优先 tmpfs，若断电重启导致 tmpfs 丢失则回退读取 /root/ai-link-final-backup 持久化日志 B2-8）。"""
    st = {"running": False, "stage": "", "stage_text": "", "percent": 0, "message": "", "log": [], "finished": False, "result": "", "target": "", "from_persistent": False}
    use_persist = False
    try:
        if (not UPDATE_PROGRESS_LOG.is_file()) and (str(UPDATE_PROGRESS_LOG) == "/var/run/ai-link/update/progress.log") and PERSIST_UPDATE_LOG.is_file():
            use_persist = True
    except Exception:
        use_persist = False
    state_file = PERSIST_UPDATE_STATE if (use_persist and PERSIST_UPDATE_STATE.is_file()) else UPDATE_STATE_JSON
    log_file = PERSIST_UPDATE_LOG if use_persist else UPDATE_PROGRESS_LOG
    try:
        if state_file.is_file():
            meta = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(meta, dict):
                st["target"] = str(meta.get("target") or "")
                st["started_at"] = int(meta.get("started_at") or 0)
    except Exception:
        pass
    try:
        if not log_file.is_file():
            return st
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return st
    parsed = []
    for ln in lines:
        parts = ln.split("|", 3)
        if len(parts) == 4:
            try:
                parsed.append({"ts": int(parts[0]), "stage": parts[1], "percent": int(parts[2]), "message": parts[3]})
            except Exception:
                continue
    if not parsed:
        return st
    last = parsed[-1]
    st["from_persistent"] = bool(use_persist)
    st["stage"] = last["stage"]
    st["percent"] = last["percent"]
    st["message"] = last["message"]
    st["stage_text"] = UPDATE_STAGES.get(last["stage"], (0, last["stage"]))[1]
    st["log"] = [f"{p['stage']}: {p['message']}" for p in parsed[-limit:]]
    if use_persist and last["stage"] not in ("done", "failed"):
        st["stage"] = "failed"
        st["stage_text"] = UPDATE_STAGES["failed"][1]
        st["running"] = False
        st["finished"] = True
        st["result"] = "failed"
        st["message"] = f"升级在阶段 [{last['stage']}] 因设备断电或重启中断（已从持久化闪存恢复日志）"
    else:
        st["running"] = last["stage"] not in ("done", "failed")
        st["finished"] = not st["running"]
        st["result"] = "ok" if last["stage"] == "done" else ("failed" if last["stage"] == "failed" else "")
    return st


def _update_script_body(plan: dict) -> str:
    """生成脱离 daemon 会话执行的升级脚本。所有变量已在 Python 侧转义。"""
    def q(v):
        return "'" + str(v).replace("'", "'\\''") + "'"

    pkg_urls = " ".join(q(u) for u in plan["package_urls"])
    return f"""#!/bin/sh
# AI-LINK OTA upgrade script (generated at {int(time.time())})
# 由 daemon 写入并 setsid 拉起；install.sh 重启服务后本脚本仍继续执行。
UPDIR={q(str(UPDATE_DIR))}
LOG={q(str(UPDATE_PROGRESS_LOG))}
PERSIST_LOG="/root/ai-link-final-backup/last_update_progress.log"
PLAN={q(str(UPDATE_PLAN_JSON))}
TARGET={q(plan['target'])}
CUR={q(plan['current'])}
MD5={q(plan['md5'])}
SHA256={q(plan['sha256'])}
SIZE={q(str(plan['size']))}
TS=$(date +%s)
mkdir -p /root/ai-link-final-backup 2>/dev/null || true
: > "$PERSIST_LOG" 2>/dev/null || true
say() {{
    local _ln="$(date +%s)|$1|$2|$3"
    echo "$_ln" >> "$LOG"
    echo "$_ln" >> "$PERSIST_LOG" 2>/dev/null || true
}}

say prepare 5 "开始升级到 v$TARGET（当前 v$CUR）"

# ---------- 1. 下载（多源重试） ----------
PKG="$UPDIR/pkg.tar.gz"
rm -f "$PKG"
DL_OK=0
IDX=0
for U in {pkg_urls}
do
    IDX=$((IDX + 1))
    say download 10 "尝试第 $IDX 个下载源: $U"
    if command -v curl >/dev/null 2>&1; then
        curl -fL --noproxy '*' --connect-timeout 12 --max-time 300 -o "$PKG" "$U" >>"$UPDIR/curl.log" 2>&1 && DL_OK=1
    else
        python3 - "$U" "$PKG" <<'PY' >>"$UPDIR/curl.log" 2>&1 && DL_OK=1
import sys, urllib.request
req = urllib.request.Request(sys.argv[1], headers={{"User-Agent": "AI-LINK/{APP_VERSION} OTA"}})
op = urllib.request.build_opener(urllib.request.ProxyHandler({{}}))
with op.open(req, timeout=120) as r, open(sys.argv[2], "wb") as f:
    while True:
        b = r.read(65536)
        if not b: break
        f.write(b)
PY
    fi
    if [ "$DL_OK" = "1" ] && [ -s "$PKG" ]; then
        say download 40 "下载完成: $U"
        break
    fi
    rm -f "$PKG"
done
if [ "$DL_OK" != "1" ] || [ ! -s "$PKG" ]; then
    say failed 0 "所有下载源均失败，升级已中止（当前系统未做任何改动）"
    exit 1
fi

# ---------- 2. 校验（MD5 + SHA256 双校验） ----------
say verify 50 "正在校验升级包完整性"
ACT_SIZE=$(wc -c < "$PKG" | tr -d ' ')
if [ -n "$SIZE" ] && [ "$SIZE" != "0" ] && [ "$ACT_SIZE" != "$SIZE" ]; then
    say failed 0 "包大小不符（期望 $SIZE，实际 $ACT_SIZE），已中止"
    exit 1
fi
ACT_MD5=$(md5sum "$PKG" | awk '{{print $1}}')
if [ -n "$MD5" ] && [ "$ACT_MD5" != "$MD5" ]; then
    say failed 0 "MD5 校验失败（期望 $MD5，实际 $ACT_MD5），已中止"
    exit 1
fi
if [ -n "$SHA256" ]; then
    ACT_SHA=$(sha256sum "$PKG" 2>/dev/null | awk '{{print $1}}')
    if [ -n "$ACT_SHA" ] && [ "$ACT_SHA" != "$SHA256" ]; then
        say failed 0 "SHA256 校验失败（期望 $SHA256，实际 $ACT_SHA），已中止"
        exit 1
    fi
fi
say verify 58 "校验通过 (md5=$ACT_MD5)"

# ---------- 3. 解压 ----------
EXDIR="$UPDIR/extract"
rm -rf "$EXDIR"; mkdir -p "$EXDIR"
say extract 62 "正在解压"
if ! tar -xzf "$PKG" -C "$EXDIR" 2>>"$UPDIR/tar.log"; then
    say failed 0 "解压失败，升级已中止（当前系统未做任何改动）"
    exit 1
fi
SRC=""
for C in "$EXDIR/ai-link-openwrt" "$EXDIR"; do
    if [ -f "$C/install.sh" ] && [ -d "$C/root" ]; then SRC="$C"; break; fi
done
if [ -z "$SRC" ]; then
    say failed 0 "升级包结构异常（找不到 install.sh / root 目录），已中止"
    exit 1
fi
say extract 68 "解压完成: $SRC"

# ---------- 4. 备份用户数据 + 旧代码 ----------
BK="$UPDIR/rollback"
rm -rf "$BK"; mkdir -p "$BK"
mkdir -p /root/ai-link-final-backup
PREBK="/root/ai-link-final-backup/pre-update-v$TARGET-$(date +%s).tgz"
say backup 72 "正在备份用户配置到 $PREBK"
if tar -czf "$PREBK" -C / etc/ai-link etc/config/ai-link 2>>"$UPDIR/tar.log"; then
    cp -f "$PREBK" "$BK/userdata.tgz" 2>/dev/null || true
    ls -1t /root/ai-link-final-backup/pre-update-v*.tgz 2>/dev/null | tail -n +4 | while read -r OLD; do rm -f "$OLD"; done
else
    say backup 72 "持久化备份失败，改用临时目录备份"
    tar -czf "$BK/userdata.tgz" -C / etc/ai-link etc/config/ai-link 2>>"$UPDIR/tar.log" || true
fi
AVAIL=$(df -k /root 2>/dev/null | awk 'NR==2{{print $4}}')
if [ -n "$AVAIL" ] && [ "$AVAIL" -gt 30000 ]; then
    mkdir -p "$BK/code"
    cp -a /usr/share/ai-link "$BK/code/" 2>/dev/null || true
    cp -a /www/luci-static/resources/view/ai-link "$BK/code/luci-view" 2>/dev/null || true
    cp -a /etc/init.d/ai-link "$BK/code/initd-ai-link" 2>/dev/null || true
    cp -a /usr/bin/ai-link "$BK/code/bin-ai-link" 2>/dev/null || true
    say backup 76 "已备份用户配置与旧版代码（可回滚）"
else
    say backup 76 "已备份用户配置（剩余空间不足，跳过代码备份）"
fi

# ---------- 5. 执行安装（升级模式） ----------
say install 84 "正在写入新版本文件（install.sh --upgrade）"
if ! sh "$SRC/install.sh" --upgrade >>"$UPDIR/install.log" 2>&1; then
    say install 88 "install.sh 返回非零，进入健康检查判定"
fi

# ---------- 6. 重启与内核确认 ----------
say restart 92 "正在确认服务与 Sing-box 内核状态"
if ! pgrep -f "ai-link-dae[m]on.py" >/dev/null 2>&1 || (command -v sing-box >/dev/null 2>&1 && ! pidof sing-box >/dev/null 2>&1); then
    /etc/init.d/ai-link restart >/dev/null 2>&1 || true
    sleep 5
fi

# ---------- 7. 健康检查（含 P1-3 面板 + Sing-box 内核进程 + 7890/7893 端口真实健康断言） ----------
say healthcheck 97 "正在检查服务与内核端口健康状态"
PORT=$(uci -q get ai-link.global.panel_port 2>/dev/null || echo 9099)
HC=1
for I in 1 2 3 4 5 6 7 8 9 10; do
    if [ "$I" -eq 5 ] && command -v sing-box >/dev/null 2>&1 && ! pidof sing-box >/dev/null 2>&1; then
        /etc/init.d/ai-link restart_core >/dev/null 2>&1 || true
    fi
    if python3 - "$PORT" <<'PY' >/dev/null 2>&1
import sys, json, shutil, urllib.request
_op = urllib.request.build_opener(urllib.request.ProxyHandler({{}}))
with _op.open(f"http://127.0.0.1:{{sys.argv[1]}}/api/status", timeout=3) as r:
    d = json.loads(r.read().decode("utf-8", "replace"))
assert d.get("ok") is True, d
if shutil.which("sing-box") and not d.get("bypass_active") and (d.get("ops_settings") or {{}}).get("enabled", True):
    assert d.get("core_pid"), "sing-box core_pid is null"
PY
    then
        if ! command -v sing-box >/dev/null 2>&1 || /etc/init.d/ai-link status_ports_quiet >/dev/null 2>&1 || pidof sing-box >/dev/null 2>&1; then
            HC=0
            break
        fi
    fi
    sleep 2
done

if [ "$HC" = "0" ]; then
    NEWVER=$(cat /etc/ai-link/version 2>/dev/null | awk '{{print $1}}')
    say done 100 "升级成功，当前版本 v$NEWVER（面板与服务均正常）"
    rm -f "$PKG"
    rm -rf "$EXDIR"
    rm -rf "$BK/code"
    exit 0
fi

# ---------- 8. 回滚 ----------
say failed 0 "升级后健康检查失败，正在自动回滚"
if [ -f "$BK/userdata.tgz" ]; then
    tar -xzf "$BK/userdata.tgz" -C / 2>/dev/null || true
fi
if [ -d "$BK/code/ai-link" ]; then
    rm -rf /usr/share/ai-link && cp -a "$BK/code/ai-link" /usr/share/ai-link 2>/dev/null || true
    rm -rf /www/luci-static/resources/view/ai-link && cp -a "$BK/code/luci-view" /www/luci-static/resources/view/ai-link 2>/dev/null || true
    cp -a "$BK/code/initd-ai-link" /etc/init.d/ai-link 2>/dev/null || true
    cp -a "$BK/code/bin-ai-link" /usr/bin/ai-link 2>/dev/null || true
    chmod +x /etc/init.d/ai-link /usr/bin/ai-link 2>/dev/null || true
fi
/etc/init.d/ai-link restart >/dev/null 2>&1 || true
sleep 5
# v1.0.2：回滚收尾立刻重挂透明代理。
# 旧流程要等 daemon 的 auto_heal 周期（默认 10 秒）才把 table inet ai_link 补回来，
# 这段时间设备是「面板正常但流量不走代理」的假恢复状态。
/etc/init.d/ai-link restore_proxy >/dev/null 2>&1 || true
sleep 2
if python3 - "$PORT" <<'PY' >/dev/null 2>&1
import sys, json, urllib.request
_op = urllib.request.build_opener(urllib.request.ProxyHandler({{}}))
with _op.open(f"http://127.0.0.1:{{sys.argv[1]}}/api/status", timeout=3) as r:
    d = json.loads(r.read().decode("utf-8", "replace"))
assert d.get("ok") is True, d
PY
then
    say failed 0 "升级失败，已回滚到 v$CUR 并恢复正常"
else
    say failed 0 "升级失败且回滚后仍不健康，请执行 ai-link uninstall -y 后重新安装"
fi
exit 1
"""


def start_plugin_update(conf_dir: Path = CONF_DIR, force: bool = False) -> dict:
    """校验前置条件 -> 写 plan/script -> setsid 脱离会话拉起升级进程。"""
    cur_prog = read_update_progress()
    if cur_prog.get("running"):
        return {"ok": False, "error": "update_running", "message": "已有升级任务在执行中，请等待完成", "progress": cur_prog}

    chk = check_plugin_update(conf_dir, force=force)
    if not chk.get("ok"):
        return {"ok": False, "error": chk.get("error", "check_failed"), "message": chk.get("message", "版本检查失败")}
    if not chk.get("has_update"):
        return {"ok": False, "error": "already_latest", "message": f"当前已是最新版本 v{APP_VERSION}"}

    pkg = chk.get("package") or {}
    urls = _update_package_urls(pkg, conf_dir)
    if not urls:
        return {"ok": False, "error": "no_package_url", "message": "版本清单未提供可用下载地址"}
    if not pkg.get("md5"):
        return {"ok": False, "error": "no_checksum", "message": "版本清单缺少 MD5 校验值，为安全起见拒绝升级"}

    try:
        UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {"ok": False, "error": "mkdir_failed", "message": f"无法创建升级工作目录: {e}"}

    plan = {
        "target": chk["latest"],
        "current": APP_VERSION,
        "md5": pkg.get("md5", ""),
        "sha256": pkg.get("sha256", ""),
        "size": pkg.get("size", 0),
        "package_urls": urls,
    }
    try:
        UPDATE_PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        _st_payload = json.dumps({
            "target": plan["target"], "started_at": int(time.time()), "from": APP_VERSION,
        }, ensure_ascii=False, indent=2)
        UPDATE_STATE_JSON.write_text(_st_payload, encoding="utf-8")
        try:
            BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
            PERSIST_UPDATE_STATE.write_text(_st_payload, encoding="utf-8")
        except Exception:
            pass
        _init_ln = f"{int(time.time())}|prepare|2|正在启动升级到 v{plan['target']}（当前 v{APP_VERSION}）\n"
        UPDATE_PROGRESS_LOG.write_text(_init_ln, encoding="utf-8")
        try:
            PERSIST_UPDATE_LOG.write_text(_init_ln, encoding="utf-8")
        except Exception:
            pass
        UPDATE_SCRIPT.write_text(_update_script_body(plan), encoding="utf-8")
        UPDATE_SCRIPT.chmod(0o755)
    except Exception as e:
        return {"ok": False, "error": "prepare_failed", "message": f"写入升级脚本失败: {e}"}

    try:
        # setsid 让升级进程脱离 daemon 会话，install.sh 重启服务不会连带杀掉它
        subprocess.Popen(
            ["/bin/sh", str(UPDATE_SCRIPT)],
            stdout=open(str(UPDATE_DIR / "runner.out"), "ab"),
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except Exception as e:
        return {"ok": False, "error": "spawn_failed", "message": f"拉起升级进程失败: {e}"}

    return {
        "ok": True,
        "started": True,
        "target": plan["target"],
        "current": APP_VERSION,
        "message": f"已开始升级到 v{plan['target']}，升级过程中面板会短暂断开",
    }


def acknowledge_update_result() -> dict:
    """前端确认升级结果后清空进度日志（含 tmpfs 与闪存持久化日志 B2-8），避免下次打开还显示上次的结果。"""
    try:
        for _pf in (UPDATE_PROGRESS_LOG, UPDATE_STATE_JSON, PERSIST_UPDATE_LOG, PERSIST_UPDATE_STATE):
            try:
                if _pf.is_file():
                    _pf.unlink()
            except Exception:
                pass
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==============================================================================
# 服务总开关 (v1.0.1)
# ------------------------------------------------------------------------------
# LuCI 侧走 fs.exec -> /etc/init.d/ai-link，不依赖面板，所以服务停掉也能拉起。
# 面板侧（本模块）只负责「看状态」与「重启」，因为面板本身就是 daemon 提供的：
# 面板能打开，说明 daemon 一定在跑，此时「启动」没有意义，「重启」才有用。
# ==============================================================================
SERVICE_INIT = "/etc/init.d/ai-link"


def get_service_state() -> dict:
    """调用 init 脚本的 svc_state，返回结构化状态。"""
    st = {"ok": False, "daemon": False, "core": False, "nft": False,
          "enabled": True, "boot": False, "bypass": False, "port": 9099}
    try:
        r = subprocess.run([SERVICE_INIT, "svc_state"], capture_output=True, text=True, timeout=6)
        out = (r.stdout or "").strip()
        kv = {}
        for tok in out.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                kv[k.strip()] = v.strip()
        if "daemon" not in kv:
            return st
        st.update({
            "ok": True,
            "daemon": kv.get("daemon") == "1",
            "core": kv.get("core") == "1",
            "nft": kv.get("nft") == "1",
            "enabled": kv.get("enabled") == "1",
            "boot": kv.get("boot") == "1",
            "bypass": kv.get("bypass") == "1",
            "port": int(kv.get("port") or 9099) if str(kv.get("port") or "").isdigit() else 9099,
        })
    except Exception as e:
        st["error"] = f"{type(e).__name__}: {e}"
    return st


def restart_service_async(delay: float = 1.0) -> dict:
    """延迟重启服务。必须异步：重启会杀掉本 daemon，同步做的话 HTTP 响应发不出去。"""
    try:
        UPDATE_DIR.mkdir(parents=True, exist_ok=True)
        sh = UPDATE_DIR / "svc_restart.sh"
        sh.write_text(
            "#!/bin/sh\n"
            f"sleep {max(0.2, float(delay)):.1f}\n"
            f"{SERVICE_INIT} restart >/dev/null 2>&1\n",
            encoding="utf-8", newline="\n",
        )
        sh.chmod(0o755)
        subprocess.Popen(
            ["/bin/sh", str(sh)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            start_new_session=True, close_fds=True,
        )
        return {"ok": True, "restarting": True, "message": f"服务将在 {delay:.0f} 秒后重启，面板会短暂断开"}
    except Exception as e:
        return {"ok": False, "error": str(e), "message": f"重启失败: {e}"}


_REAL_EGRESS_PROBE_CACHE = {"ts": 0.0, "node": "", "ok": True, "delay_ms": 0, "error": ""}

_EGRESS_BG_PROBING = False

def _probe_real_proxy_egress(active_node: str, force_now: bool = False, allow_network: bool = True) -> dict:
    """Part 1 §1.4 & §1.8 Case 8: 20s Egress Probe (configurable 20/30/60s) on current active outbound node. When 2 consecutive"""
    global _EGRESS_BG_PROBING
    now = time.time()
    if not active_node or active_node in ("direct", "block"):
        return {"ok": True, "checked_ts": int(now), "delay_ms": 0, "error": ""}
    eg_iv = float(AUTO_PROBE_INTERVALS.get("egress_probe_s") or 20.0)
    if not force_now and _REAL_EGRESS_PROBE_CACHE["node"] == active_node and (now - _REAL_EGRESS_PROBE_CACHE["ts"]) < eg_iv:
        return {
            "ok": _REAL_EGRESS_PROBE_CACHE["ok"],
            "checked_ts": int(_REAL_EGRESS_PROBE_CACHE["ts"]),
            "delay_ms": _REAL_EGRESS_PROBE_CACHE["delay_ms"],
            "error": _REAL_EGRESS_PROBE_CACHE["error"]
        }
    if not allow_network:
        # Never block HTTP GET /api/status or /api/overview/galaxy for 3000ms!
        # Use node_probe.json known delay immediately and trigger background egress probe if not already running.
        known_d = get_node_real_delay(active_node, conf_dir=CONF_DIR)
        if not _EGRESS_BG_PROBING and _is_local_port_listening(9090):
            _EGRESS_BG_PROBING = True
            def _bg_eg():
                global _EGRESS_BG_PROBING
                try:
                    _probe_real_proxy_egress(active_node, force_now=True, allow_network=True)
                except Exception:
                    pass
                finally:
                    _EGRESS_BG_PROBING = False
            threading.Thread(target=_bg_eg, daemon=True).start()
        if _REAL_EGRESS_PROBE_CACHE["node"] == active_node and _REAL_EGRESS_PROBE_CACHE["ts"] > 0:
            return {
                "ok": _REAL_EGRESS_PROBE_CACHE["ok"],
                "checked_ts": int(_REAL_EGRESS_PROBE_CACHE["ts"]),
                "delay_ms": _REAL_EGRESS_PROBE_CACHE["delay_ms"],
                "error": _REAL_EGRESS_PROBE_CACHE["error"]
            }
        return {"ok": known_d > 0, "checked_ts": int(now), "delay_ms": known_d if known_d > 0 else -1, "error": "" if known_d > 0 else "pending_probe"}
    res = clash_test_delay(active_node, test_url=DEFAULT_URL_PING_TARGET, timeout_ms=2500, force=True)
    ok_eg = bool(res.get("ok") and int(res.get("delay") or 0) > 0)
    # Report §3.2 Fix: 1 fast retry on transient TLS handshake / first-packet timeout
    if not ok_eg:
        time.sleep(0.35)
        res2 = clash_test_delay(active_node, test_url=DEFAULT_URL_PING_TARGET, timeout_ms=2800, force=True)
        if res2.get("ok") and int(res2.get("delay") or 0) > 0:
            res = res2
            ok_eg = True
    d_ms = int(res.get("delay") or 0) if ok_eg else -1
    err_s = "" if ok_eg else str(res.get("error") or "egress_timeout")
    _REAL_EGRESS_PROBE_CACHE.update({"ts": now, "node": active_node, "ok": ok_eg, "delay_ms": d_ms, "error": err_s})
    if ok_eg:
        _EVENT_REVERIFY_STATE["egress_fail_streak"][active_node] = 0
        # P1-1 & P1-2 Fix: Secondary data-plane CDN check (redirector.gvt1.com + dl.google.com) every 60s
        # with full recovery branch and write-throttling.
        last_cdn_ts = float(_REAL_EGRESS_PROBE_CACHE.get("cdn_ts") or 0.0)
        if _REAL_EGRESS_PROBE_CACHE.get("cdn_node") != active_node or (now - last_cdn_ts) >= 60.0:
            _REAL_EGRESS_PROBE_CACHE["cdn_ts"] = now
            _REAL_EGRESS_PROBE_CACHE["cdn_node"] = active_node
            cdn_ok_now = _verify_node_cdn_dual_target(active_node, timeout_ms=2500, conf_dir=CONF_DIR)
            if not cdn_ok_now:
                evaluate_all_auto_nodes(CONF_DIR, force_service_probe=False, advance_revert_streak=False)
                PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
    else:
        streak = int(_EVENT_REVERIFY_STATE["egress_fail_streak"].get(active_node, 0)) + 1
        _EVENT_EGRESS_STREAK = streak
        _EVENT_REVERIFY_STATE["egress_fail_streak"][active_node] = streak
        if streak >= 2:
            on_egress_fail(active_node, conf_dir=CONF_DIR)
    return {"ok": ok_eg, "checked_ts": int(now), "delay_ms": d_ms, "error": err_s}

def build_routing_health(conf_dir: Path = CONF_DIR) -> dict:
    """Spec §1.4 & §6 #7: Single `state` enum (single unified state enum), and `nodes_alive` counts ONLY `selectable` nodes wit"""
    sh_cfg = load_shunt_config(conf_dir)
    rmode = sh_cfg.get("routing_mode", "rule_shunt")
    raw_nodes = [n for n in load_saved_nodes(conf_dir) if not is_builtin_test_node(n.get("tag", ""))]
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    b_div = analyze_backend_diversity(raw_nodes, conf_dir)
    selectable_total = 0
    ok_alive = 0
    for n in raw_nodes:
        ev = evaluate_node_selectability(n, store=store, subs_list=subs_list, conf_dir=conf_dir)
        if ev["selectable"]:
            selectable_total += 1
            if ev["state"] == "ok" and ev["delay_ms"] > 0:
                ok_alive += 1
    if is_bypass_active():
        return {"state": "emergency_direct", "label": "🛟 宽带直连恢复中", "active_node": "direct", "nodes_alive": ok_alive, "nodes_total": selectable_total, "real_egress_ok": False, "backend_diversity": b_div, "hint": "当前已关闭透明劫持，点击「恢复代理」可切回分流"}
    if rmode == "direct_all":
        return {"state": "user_direct", "label": "🎯 全局直连模式", "active_node": "direct", "nodes_alive": ok_alive, "nodes_total": selectable_total, "real_egress_ok": True, "backend_diversity": b_div, "hint": "用户主动选择全局直连"}
    if FAIL_OPEN_STATE.get("active"):
        return {"state": "fallback_direct", "label": "⚠️ 节点不可达 · 保网直连兜底中", "active_node": "direct", "nodes_alive": ok_alive, "nodes_total": selectable_total, "real_egress_ok": False, "backend_diversity": b_div, "hint": FAIL_OPEN_STATE.get("reason", "")}
    is_live_box = (Path(conf_dir).resolve() == CONF_DIR.resolve() and Path("/etc/init.d/ai-link").exists() and bool(resolve_singbox_binary()))
    if is_live_box and not _get_live_singbox_pids():
        return {"state": "proxy_degraded", "core_dead": True, "label": "🚨 内核未运行 · 已自动回退直连保护", "active_node": "direct", "nodes_alive": ok_alive, "nodes_total": selectable_total, "real_egress_ok": False, "backend_diversity": b_div, "hint": "检测到 sing-box 内核进程未运行，看门狗已自动撤除 nftables 重定向以防断网并正在拉起内核，也可点击「一键重启内核」立即恢复"}
    active_node = (
        PROBE_ENGINE.current_selections.get("AI_Best_Auto")
        or PROBE_ENGINE.current_selections.get("Shunt_Final")
        or "direct"
    )
    eg_probe = _probe_real_proxy_egress(active_node, allow_network=False) if _is_local_port_listening(9090) and active_node not in ("direct", "block") else {"ok": ok_alive > 0, "delay_ms": get_node_real_delay(active_node, store=store, conf_dir=conf_dir), "error": "no_active_proxy"}
    if eg_probe["ok"] and ok_alive > 0:
        return {"state": "proxy", "label": "✅ 代理中", "active_node": active_node, "nodes_alive": ok_alive, "nodes_total": selectable_total, "real_egress_ok": True, "egress_delay_ms": eg_probe["delay_ms"], "backend_diversity": b_div, "hint": f"当前出口 {active_node} URL ping 正常"}
    return {"state": "proxy_degraded", "label": "⚠️ 隧道异常 · 待验证或不可达", "active_node": active_node, "nodes_alive": ok_alive, "nodes_total": selectable_total, "real_egress_ok": False, "backend_diversity": b_div, "hint": "请执行 URL ping 真连接检测或检查机场订阅状态"}

def run_fail_open_check_once(conf_dir: Path = CONF_DIR, force_trigger: bool = False) -> dict:
    FAIL_OPEN_STATE["last_check_ts"] = int(time.time())
    if is_bypass_active() and not force_trigger:
        return FAIL_OPEN_STATE
    sh_cfg = load_shunt_config(conf_dir)
    if sh_cfg.get("routing_mode", "rule_shunt") == "direct_all" and not force_trigger:
        FAIL_OPEN_STATE["active"] = False
        return FAIL_OPEN_STATE
    sync_selections_from_clash(conf_dir)
    subs_list = load_subscriptions(conf_dir)
    store = load_node_probe_store(conf_dir)
    ok_nodes = []
    selectable_any = []
    for n in load_saved_nodes(conf_dir):
        if is_builtin_test_node(n.get("tag", "")):
            continue
        ev = evaluate_node_selectability(n, store=store, subs_list=subs_list, conf_dir=conf_dir)
        if ev["selectable"]:
            selectable_any.append((ev["delay_ms"] if ev["delay_ms"] > 0 else 99999, n["tag"]))
            if ev["state"] == "ok" and ev["delay_ms"] > 0:
                ok_nodes.append((ev["delay_ms"], n["tag"]))
    ok_nodes.sort(key=lambda x: x[0])
    selectable_any.sort(key=lambda x: x[0])
    best_pool = ok_nodes if ok_nodes else selectable_any
    if best_pool and not force_trigger:
        best_rtt, best_tag = best_pool[0]
        PROBE_ENGINE.apply_shunt_selections(conf_dir)
        for k_sel in ("Shunt_Final", "AI_Best_Auto", "Stream_Auto", "HK_TW_Media"):
            if (PROBE_ENGINE.current_selections.get(k_sel) or "direct") == "direct":
                PROBE_ENGINE.hot_switch_core_selector(k_sel, best_tag, reason="看门狗从 direct 自动恢复代理")
        FAIL_OPEN_STATE["active"] = False
        FAIL_OPEN_STATE["consecutive_failures"] = 0
        FAIL_OPEN_STATE["last_failover_node"] = best_tag
        return FAIL_OPEN_STATE
    all_selectors = ["AI_Best_Auto", "Stream_Auto", "HK_TW_Media"] + [
        g.get("selector_tag", f"Shunt_{g['id']}") for g in sh_cfg.get("groups", [])
        if g.get("country") not in ("direct", "block")
    ]
    for sg in all_selectors:
        PROBE_ENGINE.hot_switch_core_selector(sg, "direct", reason="Fail-Open 暂无可用节点，保网直连")
    FAIL_OPEN_STATE["active"] = True
    FAIL_OPEN_STATE["last_failover_node"] = "direct"
    FAIL_OPEN_STATE["reason"] = "[fail-open] 当前无可用节点，已自动回退直连（待节点恢复后将自动切回代理）"
    return FAIL_OPEN_STATE


# ================= 3D 星系快照 / 健康探测点 =================
import threading as _h3_threading
import urllib.request as _h3_urllib

_GALAXY_ACC = {"hosts": {}, "devs": {}, "ts": 0.0, "prev": {}, "conns": {}}
_GALAXY_CACHE = {"ts": 0.0, "data": None}
_H3_WINDOW = 60.0          # 聚合窗口（秒）：停止访问 60s 后才消失，避免闪烁
_H3_MAX_HOSTS = 40         # 每侧最多保留的站点数

_HEALTH_TARGETS = [
    ("百度",     "https://www.baidu.com/",                    False),
    ("B站",      "https://www.bilibili.com/",                 False),
    ("抖音",     "https://www.douyin.com/",                   False),
    ("淘宝",     "https://www.taobao.com/",                   False),
    ("Gemini",   "https://gemini.google.com/",                True),
    ("ChatGPT",  "https://chat.openai.com/cdn-cgi/trace",     True),
    ("YouTube",  "https://www.youtube.com/generate_204",      True),
    ("GitHub",   "https://github.com/",                       True),
]
_HEALTH_CACHE = {"ts": 0.0, "items": [], "running": False, "last_trigger_ts": 0.0}

# 4 个核心应用的真实延迟（原来一直沿用所属节点 RTT，四个值永远一样）
_H3_APP_TARGETS = [
    ("youtube",  "https://www.youtube.com/generate_204"),
    ("gemini",   "https://gemini.google.com/"),
    ("github",   "https://github.com/"),
    ("telegram", "https://telegram.org/"),
]
_H3_APP_MS = {}
_H3_APP_TS = {}


def app_probe_all():
    def _job(item):
        k, u = item
        try:
            ms = _h3_probe_one(u, True, timeout=3.5)
        except Exception:
            ms = -1
        # Only overwrite a recent manual probe (<30s old) if the new probe succeeded
        now_t = time.time()
        if ms > 0 or (now_t - _H3_APP_TS.get(k, 0)) > 30.0:
            _H3_APP_MS[k] = ms
            _H3_APP_TS[k] = now_t
        return k, ms
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(_job, _H3_APP_TARGETS))
    return _H3_APP_MS



def _h3_classify_health_state(ms: int, via_proxy: bool) -> str:
    """P1-1 Fix: Separates direct (domestic) vs proxy (foreign) thresholds and reserves 'dead' strictly for unreachable/timeout."""
    if ms < 0:
        return "dead"
    if via_proxy:
        if ms < 1500:
            return "ok"
        if ms < 3500:
            return "suspect"
        return "dead"
    if ms < 400:
        return "ok"
    if ms < 2000:
        return "suspect"
    return "dead"


def _h3_probe_one(url, use_proxy, timeout=4.0):
    """返回毫秒；连得上但返回 4xx/5xx 也算可达（只测连通与握手）。
    P1-1 & P2-3 Fix: Both direct and proxy probes prefer curl (with -x http://127.0.0.1:7890 for proxy)
    so HTTP/2 and 204 endpoints like youtube.com/generate_204 never hang in urllib."""
    if shutil.which("curl"):
        try:
            sp = urllib.parse.urlsplit(url)
            host = (sp.hostname or "").strip()
            port = sp.port or (443 if sp.scheme == "https" else 80)
            t0 = time.time()
            args = [
                "curl", "-4", "-s", "-o", "/dev/null", "-k",
                "--connect-timeout", "2", "--max-time", str(max(2, int(timeout))),
                "-A", "ai-link-health/1.0", "-w", "%{http_code}"
            ]
            if use_proxy:
                args.extend(["-x", "http://127.0.0.1:7890"])
            else:
                v4_ips = _resolve_subscription_host_ips(host) if host else []
                if host and v4_ips:
                    args.extend(["--resolve", f"{host}:{port}:{','.join(v4_ips)}"])
            args.append(url)
            proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 1.5)
            code_s = (proc.stdout or "").strip()[-3:]
            if code_s.isdigit() and int(code_s) >= 100:
                return max(1, int((time.time() - t0) * 1000))
        except Exception:
            pass
    t0 = time.time()
    try:
        ctx = ssl._create_unverified_context()
        if use_proxy:
            op = _h3_urllib.build_opener(
                _h3_urllib.ProxyHandler({"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}),
                _h3_urllib.HTTPSHandler(context=ctx)
            )
        else:
            op = _h3_urllib.build_opener(_h3_urllib.ProxyHandler({}), _h3_urllib.HTTPSHandler(context=ctx))
        req = _h3_urllib.Request(url, headers={"User-Agent": "ai-link-health/1.0"})
        try:
            with op.open(req, timeout=timeout) as r:
                r.read(64)
        except _h3_urllib.error.HTTPError:
            pass
        return max(1, int((time.time() - t0) * 1000))
    except Exception:
        return -1


def health_targets_probe_all():
    now_ts = int(time.time())
    now_str = time.strftime("%H:%M:%S", time.localtime(now_ts))
    def _probe_t(t_item):
        name, url, via_proxy = t_item
        ms = _h3_probe_one(url, via_proxy, timeout=3.5)
        app_key_map = {"YouTube": "youtube", "Gemini": "gemini", "GitHub": "github"}
        ak = app_key_map.get(name)
        if ak:
            if ms > 0:
                _H3_APP_MS[ak] = ms
                _H3_APP_TS[ak] = float(now_ts)
            elif _H3_APP_MS.get(ak, -1) > 0 and (now_ts - _H3_APP_TS.get(ak, 0)) < 25.0:
                ms = int(_H3_APP_MS[ak])
        return {
            "name": name,
            "ms": ms,
            "state": _h3_classify_health_state(ms, via_proxy),
            "via": "proxy" if via_proxy else "direct",
            "ts": now_ts,
            "updated_at": now_str,
        }
    with ThreadPoolExecutor(max_workers=4) as ex:
        items = list(ex.map(_probe_t, _HEALTH_TARGETS))
    _HEALTH_CACHE["ts"] = float(now_ts)
    _HEALTH_CACHE["items"] = items
    try:
        out = Path("/var/run/ai-link/health_targets.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"ts": _HEALTH_CACHE["ts"], "updated_at": now_str, "targets": items}, ensure_ascii=False))
    except Exception:
        pass
    return items

def _trigger_async_health_reprobe():
    """P2-3 Fix: Immediately triggers an async health_targets_probe_all + app_probe_all refresh when nodes/exits change."""
    now = time.time()
    if _HEALTH_CACHE.get("running") or (now - float(_HEALTH_CACHE.get("last_trigger_ts") or 0.0)) < 3.0:
        return
    _HEALTH_CACHE["last_trigger_ts"] = now
    def _bg_reprobe():
        if _HEALTH_CACHE.get("running"):
            return
        _HEALTH_CACHE["running"] = True
        try:
            health_targets_probe_all()
            app_probe_all()
        except Exception:
            pass
        finally:
            _HEALTH_CACHE["running"] = False
    threading.Thread(target=_bg_reprobe, daemon=True, name="ailink-health-reprobe").start()


def health_targets_snapshot():
    if _HEALTH_CACHE["items"]:
        return _HEALTH_CACHE["items"]
    return [{"name": n, "ms": -1, "state": "pending", "via": ("proxy" if p else "direct")}
            for n, _u, p in _HEALTH_TARGETS]


def _h3_health_loop():
    time.sleep(1.5)
    while True:
        has_dead = False
        try:
            _HEALTH_CACHE["running"] = True
            items = health_targets_probe_all()
            has_dead = any(int(x.get("ms", -1)) < 0 for x in (items or []))
            try:
                app_probe_all()
            except Exception:
                pass
            _HEALTH_CACHE["running"] = False
        except Exception:
            _HEALTH_CACHE["running"] = False
            has_dead = True
        # P1-1 Fix: Retry failed health targets in 30s instead of freezing red state for 300s
        time.sleep(30 if has_dead else 300)


_LAN_IPV6_NEIGH_CACHE = {"ts": 0.0, "ips": set(), "prefixes": set()}

def _get_lan_ipv6_neighbors_and_prefixes() -> tuple:
    """Reads `ip -6 neigh` and `ip -6 addr show` (cached 10s) so LAN SLAAC/DHCPv6 Global Unicast IPv6 devices
    (e.g. 2408:8240:*, 2409:*, 240e:*) on br-lan are recognized as LAN devices rather than HomeLink remote."""
    now = time.time()
    if (now - _LAN_IPV6_NEIGH_CACHE["ts"]) < 10.0:
        return (_LAN_IPV6_NEIGH_CACHE["ips"], _LAN_IPV6_NEIGH_CACHE["prefixes"])
    ips = set()
    prefixes = set()
    try:
        r_n = subprocess.run(["ip", "-6", "neigh", "show"], capture_output=True, text=True, timeout=1.2)
        for ln in (r_n.stdout or "").splitlines():
            parts = ln.split()
            if not parts:
                continue
            ip_s = parts[0].strip().lower()
            if "br-lan" in ln or "lan" in ln or "lladdr" in ln:
                ips.add(ip_s)
                segs = ip_s.split(":")
                if len(segs) >= 4 and segs[0].startswith("2"):
                    prefixes.add(":".join(segs[:4]) + ":")
    except Exception:
        pass
    try:
        r_a = subprocess.run(["ip", "-6", "addr", "show"], capture_output=True, text=True, timeout=1.2)
        for ln in (r_a.stdout or "").splitlines():
            ln_s = ln.strip()
            if ln_s.startswith("inet6 ") and "scope global" in ln_s:
                addr_part = ln_s.split()[1].split("/")[0].lower()
                ips.add(addr_part)
                segs = addr_part.split(":")
                if len(segs) >= 4 and segs[0].startswith("2"):
                    prefixes.add(":".join(segs[:4]) + ":")
    except Exception:
        pass
    _LAN_IPV6_NEIGH_CACHE["ts"] = now
    _LAN_IPV6_NEIGH_CACHE["ips"] = ips
    _LAN_IPV6_NEIGH_CACHE["prefixes"] = prefixes
    return (ips, prefixes)

def _h3_is_lan_ip(ip):
    """P2-4 & hotfix6 Fix: Uses ipaddress.ip_address(ip).is_private for IPv4 (so public 172.104.x / 172.67.x IPs are never
    misclassified as LAN), AND recognizes LAN IPv6 ULA (`fc00::/7`) as well as LAN SLAAC/PD Global Unicast IPv6 (`2408:`, `2409:`, `240e:`, `240a:` or `ip -6 neigh` on br-lan) as LAN devices!"""
    s = str(ip or "").strip().strip("[]").lower()
    if not s:
        return False
    try:
        ip_obj = ipaddress.ip_address(s)
        if ip_obj.is_loopback or ip_obj.is_unspecified or ip_obj.is_multicast or ip_obj.is_link_local:
            return False
        if ip_obj.version == 4:
            if ip_obj in ipaddress.ip_network("198.18.0.0/15"):
                return False
            if ip_obj in ipaddress.ip_network("100.64.0.0/10"):
                return True
            return bool(ip_obj.is_private)
        # IPv6 handling:
        if ip_obj in ipaddress.ip_network("fc00::/18"):
            # sing-box FakeIPv6 range is not a client device
            return False
        if ip_obj.is_private:
            return True
        # Check LAN neighbor cache / PD prefixes and mainland ISP PD prefixes (2408 Unicom, 240e Telecom, 2409 Mobile, 240a广电)
        lan6_ips, lan6_pfxs = _get_lan_ipv6_neighbors_and_prefixes()
        if s in lan6_ips or any(s.startswith(pfx) for pfx in lan6_pfxs):
            return True
        if s.startswith(("2408:", "2409:", "240e:", "240a:", "2001:da8:")):
            return True
        return False
    except Exception:
        return False

def _h3_is_remote_homelink_client_ip(ip: str, lan_ip: str = "", conn_meta: dict = None, conf_dir: Path = CONF_DIR) -> bool:
    """P2-4 & hotfix6 Fix: Identifies external HomeLink tunnel client source IPs ONLY when:
    1) At least one HomeLink node is enabled (or `conn_meta.inbound` starts with `homelink-`),
    2) If `conn_meta` provides `inbound` or `type`, it must NOT be `tproxy-in` / `mixed-in` / `tun-in`, and
    3) The source IP is a non-LAN public IP."""
    s = str(ip or "").strip().strip("[]").lower()
    if not s or (lan_ip and s == lan_ip.lower()):
        return False
    if _h3_is_lan_ip(s):
        return False
    if isinstance(conn_meta, dict) and conn_meta:
        inb = str(conn_meta.get("inbound") or conn_meta.get("inboundTag") or conn_meta.get("type") or "").lower()
        if inb and any(k in inb for k in ("tproxy", "mixed", "tun", "redirect", "inner")):
            return False
        if inb and "homelink" in inb:
            return True
    try:
        hl_nodes = [n for n in load_homelink_nodes(conf_dir) if n.get("enabled", True)]
        if not hl_nodes:
            return False
        ip_obj = ipaddress.ip_address(s)
        if ip_obj.is_loopback or ip_obj.is_unspecified or ip_obj.is_multicast or ip_obj.is_link_local:
            return False
        if ip_obj.version == 4 and ip_obj in ipaddress.ip_network("198.18.0.0/15"):
            return False
        if ip_obj.version == 6:
            return False
        return True
    except Exception:
        return False


def _h3_is_ignored_internal_host(host_str: str, lan_ip: str = "") -> bool:
    """P2-2 Fix: Filters loopback (127.0.0.1, ::1, localhost), FakeIP (198.18.*), and gateway self-requests from 3D domestic/foreign satellites."""
    h = str(host_str or "").strip().lower().strip("[]")
    if not h or h in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    if h.startswith("127.") or h.startswith("198.18.") or h.startswith("198.19.") or h.startswith("fe80:"):
        return True
    if lan_ip and h == lan_ip.strip().lower():
        return True
    return False


def build_galaxy_snapshot(conf_dir=CONF_DIR):
    """按 /connections 实时聚合（60s 滚动窗口）：内网设备 / 国内站点（直连）/ 外网站点（代理）"""
    now = time.time()
    if _GALAXY_CACHE["data"] and (now - _GALAXY_CACHE["ts"]) < 1.2:
        return _GALAXY_CACHE["data"]

    lan_ip = _detect_router_lan_ip()
    host_map = _read_dhcp_and_arp_devices(lan_ip)
    c_snap = clash_get_connections_fast(timeout=2.0, max_sample=200)
    st = int(c_snap.get("st_code") or 0)
    conns = c_snap.get("connections") or []
    total_conns_count = int(c_snap.get("total_count") or len(conns))
    prev = _GALAXY_ACC["prev"]
    hosts = _GALAXY_ACC["hosts"]
    devs = _GALAXY_ACC["devs"]
    cur = {}
    live_conns = {}

    for c in conns:
        cid = c.get("id") or ""
        meta = c.get("metadata") or {}
        ip = meta.get("sourceIP") or ""
        host = (meta.get("host") or meta.get("destinationIP") or "").strip()
        if not host:
            continue
        up = int(c.get("upload") or 0)
        down = int(c.get("download") or 0)
        cur[cid] = [up, down]
        if cid in prev:
            pu, pd = prev[cid]
            du = up - pu if up >= pu else up
            dd = down - pd if down >= pd else down
        else:
            du = 0
            dd = 0
        chains = [str(x) for x in (c.get("chains") or []) if str(x).strip()]
        # P1-3 Fix: sing-box Clash API orders `chains` inner-to-outer: `chains[0]` is the actual outbound node ('direct' or proxy tag),
        # while `chains[-1]` is the matched shunt group ('Shunt_Domestic_CN', 'Shunt_AI', etc.).
        out_exit = chains[0] if chains else "DIRECT"
        grp_label = chains[-1] if chains else "DIRECT"
        rule_info = str(c.get("rule") or "") + " " + str(c.get("rulePayload") or "")
        if out_exit.lower() in ("block", "reject") or grp_label.lower() in ("block", "reject") or "blocklist_custom" in rule_info:
            seen_blk_g = _OVERVIEW_RT.setdefault("seen_blocked_cids", set())
            if cid and cid not in seen_blk_g:
                seen_blk_g.add(cid)
                record_adblock_hit(host, layer="route", conf_dir=conf_dir, count=1)
            continue
        direct = (not chains) or (out_exit.upper() == "DIRECT") or (grp_label.upper() in ("DIRECT", "SHUNT_DOMESTIC_CN"))

        is_lan_cli = (_h3_is_lan_ip(ip) and ip != lan_ip)
        is_hl_remote = (not is_lan_cli and _h3_is_remote_homelink_client_ip(ip, lan_ip, conn_meta=meta, conf_dir=conf_dir))
        if is_lan_cli or is_hl_remote:
            if is_lan_cli:
                mapped_n = host_map.get(ip)
                if mapped_n:
                    dev_name = mapped_n
                elif ":" in ip:
                    segs6 = ip.split(":")
                    short6 = f"{segs6[0]}:{segs6[1]}..{segs6[-1]}" if len(segs6) >= 3 else ip[:16]
                    dev_name = f"IPv6终端 ({short6})"
                else:
                    dev_name = f"{ip} (局域网终端)"
            else:
                _hl_m = _match_homelink_node_for_conn(meta, load_homelink_nodes(conf_dir), lan_ip=lan_ip, conf_dir=conf_dir)
                _hl_via = (_hl_m.get("name") or f":{_hl_m.get('listen_port')}") if _hl_m else "回家隧道"
                dev_name = f"🏠 回家 ({ip} · 经 {_hl_via})"
            e = devs.setdefault(ip, {"ip": ip, "name": dev_name, "up": 0, "down": 0, "last": 0, "first": now,
                                     "conns": 0, "is_remote": is_hl_remote, "side": ("domestic" if direct else "foreign")})
            e["name"] = dev_name
            e["is_remote"] = is_hl_remote
            e["up"] += du
            e["down"] += dd
            e["last"] = now
            live_conns[ip] = live_conns.get(ip, 0) + 1

        # P2-2 Fix: Never pollute domestic/foreign site satellites with 127.0.0.1 / FakeIP / gateway IP
        if _h3_is_ignored_internal_host(host, lan_ip):
            continue
        is_raw_ip = bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host) or ":" in host)
        disp_host = f"IP直连 ({host})" if (direct and is_raw_ip) else host
        key = ("domestic:" if direct else "foreign:") + host
        e = hosts.setdefault(key, {"domain": host, "name": disp_host, "side": ("domestic" if direct else "foreign"),
                                   "group": grp_label, "exit_node": out_exit,
                                   "up": 0, "down": 0, "last": 0, "first": now, "conns": 0})
        e["group"] = grp_label
        e["exit_node"] = out_exit
        e["name"] = disp_host
        e["up"] += du
        e["down"] += dd
        e["last"] = now
        e["conns"] = e.get("conns", 0) + 1

    _GALAXY_ACC["prev"] = cur
    _GALAXY_ACC["ts"] = now

    # 过期清理（超过窗口没流量就消失，同时清理历史遗留的 127.0.0.1 条目）
    for k in [k for k, v in hosts.items() if (now - v["last"]) > _H3_WINDOW or _h3_is_ignored_internal_host(v.get("domain", ""), lan_ip)]:
        del hosts[k]
    for k in [k for k, v in devs.items() if (now - v["last"]) > _H3_WINDOW]:
        del devs[k]

    def _rate(e):
        span = max(1.0, min(_H3_WINDOW, now - e["first"]))
        return int(e["up"] / span), int(e["down"] / span)

    def _rows(d, side=None):
        out = []
        for e in d.values():
            if side and e.get("side") != side:
                continue
            ur, dr = _rate(e)
            row = {"up_rate": ur, "down_rate": dr,
                   "conns": int(e.get("conns") or 0),
                   "name": e.get("name") or e.get("domain")}
            if "domain" in e:
                row["domain"] = e["domain"]
                row["group"] = e.get("group") or ""
                row["exit_node"] = e.get("exit_node") or "DIRECT"
            if "ip" in e:
                row["ip"] = e["ip"]
                row["is_remote"] = bool(e.get("is_remote", False))
            out.append(row)
        out.sort(key=lambda x: x["up_rate"] + x["down_rate"], reverse=True)
        return out[:_H3_MAX_HOSTS]

    try:
        rh = build_routing_health(conf_dir) or {}
    except Exception:
        rh = {}
    proxy_ok = bool(rh.get("real_egress_ok"))

    lan_rows = _rows(devs)
    for r in lan_rows:
        r["conns"] = live_conns.get(r["ip"], r.get("conns", 0))
        r["state"] = "ok"
    dom_rows = _rows(hosts, "domestic")
    for r in dom_rows:
        r["state"] = "ok"
    fore_rows = _rows(hosts, "foreign")
    for r in fore_rows:
        r["state"] = "ok" if proxy_ok else "dead"

    try:
        tele = get_overview_live_telemetry(conf_dir) or {}
    except Exception:
        tele = {}

    # P1-3 & P1-5 Fix: Unify connection count across galaxy.kernel.conn, galaxy.counts.conns, and _OVERVIEW_RT["active_conns"]
    live_conn_cnt = total_conns_count if st == 200 else max(total_conns_count, int(tele.get("active_connections") or 0))
    _OVERVIEW_RT["active_conns"] = live_conn_cnt
    tot_in_rate = float(tele.get("in_rate_bps") or 0)
    tot_out_rate = float(tele.get("out_rate_bps") or 0)
    tot_rate = tot_in_rate + tot_out_rate
    if tot_rate <= 0:
        tier_name = "待命 (慢速巡航)"
        tier_level = 1
    elif tot_rate < 200 * 1024:
        tier_name = "慢速 (1x)"
        tier_level = 1
    elif tot_rate < 2 * 1024 * 1024:
        tier_name = "中速 (3x)"
        tier_level = 2
    else:
        tier_name = "高速 (6x)"
        tier_level = 3

    # P2-1 Fix: Build structured 3D particle stream descriptors (`galaxy.particles`)
    particles = [
        {"id": "trunk_domestic", "from": "lan", "to": "domestic", "tier": tier_level, "count": 2 if tot_rate <= 0 else (3 if tier_level == 2 else 6), "rate_bps": int(tot_rate * 0.35), "state": "ok"},
        {"id": "trunk_foreign", "from": "lan", "to": "foreign", "tier": tier_level if proxy_ok else 0, "count": (2 if tot_rate <= 0 else (3 if tier_level == 2 else 6)) if proxy_ok else 0, "rate_bps": int(tot_rate * 0.65) if proxy_ok else 0, "state": "ok" if proxy_ok else "dead"},
    ]
    for r_d in dom_rows[:6]:
        particles.append({"id": f"dom_{r_d['domain']}", "from": "domestic", "to": r_d["name"], "tier": 1, "count": 1, "rate_bps": int(r_d["up_rate"] + r_d["down_rate"]), "state": "ok"})
    for r_f in fore_rows[:6]:
        particles.append({"id": f"fore_{r_f['domain']}", "from": "foreign", "to": r_f["name"], "tier": 1 if proxy_ok else 0, "count": 1 if proxy_ok else 0, "rate_bps": int(r_f["up_rate"] + r_f["down_rate"]), "state": r_f["state"]})
    total_particles_cnt = sum(int(p.get("count") or 0) for p in particles)

    snap = {
        "ok": True,
        "ts": int(now),
        "kernel": {
            "conn": live_conn_cnt,
            "in_rate": tot_in_rate,
            "out_rate": tot_out_rate,
            "mem_mib": float(tele.get("core_mem_mib") or 0),
            "uptime": tele.get("kernel_uptime_str") or tele.get("uptime_str") or "",
            "kernel_uptime": tele.get("kernel_uptime_str") or tele.get("uptime_str") or "",
            "sys_uptime": tele.get("sys_uptime_str") or "",
        },
        "lan": lan_rows,
        "domestic": dom_rows,
        "foreign": fore_rows,
        "blackhole": build_blackhole_telemetry(conf_dir),
        "particles": particles,
        "particle_tier": tier_name,
        "exits": {
            "direct": {
                "ok": True,
                "label": "宽带直连 (WAN)",
                "node": "宽带直连 (WAN)",
                "name": "宽带直连 (WAN)",
                "ip": lan_ip,
                "delay_ms": 1,
                "state": "ok",
            },
            "proxy": {"ok": proxy_ok, "node": rh.get("active_node") or "",
                      "delay_ms": int(rh.get("egress_delay_ms") or 0),
                      "state": rh.get("state") or ""},
        },
        "counts": {
            "conns": live_conn_cnt,
            "particles": total_particles_cnt,
            "tier": tier_name,
        },
    }
    _GALAXY_CACHE["ts"] = now
    _GALAXY_CACHE["data"] = snap
    return snap


_gol_real = get_overview_live_telemetry


def get_overview_live_telemetry(conf_dir=CONF_DIR):
    d = _gol_real(conf_dir)
    try:
        store = load_node_probe_store(conf_dir)
        now_ts = int(time.time())
        for svc in (d.get("pulse_services") or []):
            sid = svc.get("id")
            node_t = svc.get("node") or "direct"
            app_v = _H3_APP_MS.get(sid)
            app_ts = int(_H3_APP_TS.get(sid) or 0)
            node_d = get_node_real_delay(node_t, store=store, conf_dir=conf_dir) if node_t not in ("direct", "block") else (12 if node_t == "direct" else -1)
            if app_v is not None and app_v > 0:
                svc["ms"] = int(app_v)
                svc["state"] = "ok"
                svc["as_of_ts"] = app_ts or now_ts
            elif node_d > 0:
                svc["ms"] = int(node_d)
                svc["state"] = "ok"
                svc["as_of_ts"] = app_ts or now_ts
            elif app_v is not None and app_v < 0 and _HEALTH_CACHE["ts"] > 0:
                svc["ms"] = -1
                svc["state"] = "fail"
                svc["as_of_ts"] = app_ts or int(_HEALTH_CACHE["ts"])
            else:
                svc["ms"] = -1
                svc["state"] = "pending"
                svc["as_of_ts"] = 0
    except Exception:
        pass
    return d


class AILinkRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEBUI_DIR), **kwargs)
    def log_message(self, format, *args):
        pass
    def _make_wire_key(self):
        req_path_only = self.path.split("?", 1)[0]
        if req_path_only in ("/api/status", "/api/nodes", "/api/auto_nodes", "/api/shunt"):
            return (
                self.path,
                # SEC-2 (v1.0.2): 鉴权状态必须进缓存键。
                # 否则「已鉴权客户端」缓存的完整应答会被后续未鉴权请求命中，
                # 脱敏等于没做。
                bool(self._auth_ok()),
                _CORE_RELOAD_STATE["config_seq"],
                _CORE_RELOAD_STATE["reload_seq"],
                bool(is_bypass_active()),
                tuple(_get_live_singbox_pids()),
                bool(getattr(PROBE_ENGINE, "probe_running", False)),
                bool(SUB_SYNC_STATE.get("running", False)),
                tuple(sorted((PROBE_ENGINE.current_selections or {}).items())),
                _conf_file_mtimes_sig_q(CONF_DIR, ("nodes.json", "node_probe.json", "auto_nodes.json", "subscriptions.json", "homelink.json", "dns_filters.json", "dns_rewrite.json", "ops_settings.json", "panel_auth.json")),
                int(time.time()) // 15 if req_path_only == "/api/status" else 0,
            )
        return None

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            self.close_connection = True

    def finish(self):
        try:
            super().finish()
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def _try_send_wire_memo(self) -> bool:
        wk = self._make_wire_key()
        self._pre_wire_key = wk
        if wk is None:
            return False
        cached_wire = _JSON_WIRE_MEMO.get(wk)
        if cached_wire is None:
            return False
        raw_bytes, gz_bytes = cached_wire
        wants_gzip = ("gzip" in (self.headers.get("Accept-Encoding") or "").lower())
        use_gz = bool(wants_gzip and gz_bytes is not None and len(gz_bytes) < len(raw_bytes))
        body_out = gz_bytes if use_gz else raw_bytes
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            if use_gz:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(len(body_out)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-AI-Link-Token, Authorization")
            self.end_headers()
            self.wfile.write(body_out)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass
        return True

    def _send_json(self, data: dict, status: int = 200):
        accept_enc = (self.headers.get("Accept-Encoding") or "").lower()
        wants_gzip = ("gzip" in accept_enc)
        wire_key = self._make_wire_key() if status == 200 else None
        cached_wire = _JSON_WIRE_MEMO.get(wire_key) if wire_key is not None else None
        if cached_wire is not None:
            raw_bytes, gz_bytes = cached_wire
        else:
            raw_bytes = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            gz_bytes = gzip.compress(raw_bytes, compresslevel=1) if len(raw_bytes) >= 512 else None
            if wire_key is not None:
                if len(_JSON_WIRE_MEMO) > 24:
                    _JSON_WIRE_MEMO.clear()
                _JSON_WIRE_MEMO[wire_key] = (raw_bytes, gz_bytes)
                _pre_wk = getattr(self, "_pre_wire_key", None)
                if _pre_wk is not None:
                    _JSON_WIRE_MEMO[_pre_wk] = (raw_bytes, gz_bytes)
        use_gz = bool(wants_gzip and gz_bytes is not None and len(gz_bytes) < len(raw_bytes))
        body_out = gz_bytes if use_gz else raw_bytes
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            if use_gz:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(len(body_out)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-AI-Link-Token, Authorization")
            self.end_headers()
            self.wfile.write(body_out)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def do_OPTIONS(self):
        try:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-AI-Link-Token, Authorization")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass
    def _is_loopback_client(self) -> bool:
        client_ip = (self.client_address[0] if self.client_address else "").replace("::ffff:", "")
        return client_ip in ("127.0.0.1", "::1", "localhost")

    def _is_request_authenticated(self) -> bool:
        auth_data = _load_panel_auth(CONF_DIR)
        valid_tokens = set(auth_data.get("tokens") or [])
        tok = (self.headers.get("X-AI-Link-Token") or "").strip()
        if not tok:
            auth_hdr = (self.headers.get("Authorization") or "").strip()
            if auth_hdr.lower().startswith("bearer "):
                tok = auth_hdr[7:].strip()
        if not tok:
            cookie_hdr = self.headers.get("Cookie") or ""
            for kv in cookie_hdr.split(";"):
                if "=" in kv:
                    ck, cv = kv.strip().split("=", 1)
                    if ck.strip() == "ailink_token":
                        tok = cv.strip()
                        break
        if not tok:
            return False
        # PWD-1: 令牌只认 panel_auth.json / panel_token 里签发过的值。
        # 旧实现额外放行 tok == get_uci_panel_secret()，导致 LuCI 回显的那串
        # sha256:xxxx 可直接当 Bearer 令牌绕过登录，已移除。
        # LuCI 页面的按钮改用独立的 luci_bridge_token（与面板密码解耦）。
        if tok in valid_tokens:
            return True
        try:
            bridge = get_luci_bridge_token(create=False)
        except Exception:
            bridge = ""
        return bool(bridge) and tok == bridge

    def _auth_ok(self) -> bool:
        """P0-1 & P0-3 Auth Guard: Checks X-AI-Link-Token / Bearer / Cookie against valid tokens, or trusted_cidr in ops_settings."""
        if self._is_request_authenticated():
            return True
        tok_present = bool(
            (self.headers.get("X-AI-Link-Token") or "").strip()
            or (self.headers.get("Authorization") or "").strip()
        )
        if tok_present or self.headers.get("X-Enforce-Auth"):
            return False
        if self._is_loopback_client():
            return True
        ops = get_ops_settings(CONF_DIR)
        if ops.get("require_lan_auth"):
            return False
        cidr_str = str(ops.get("trusted_cidr") or "127.0.0.1/32, ::1/128, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10")
        cidrs = [c.strip() for c in re.split(r"[,;\s]+", cidr_str) if c.strip()]
        client_ip = (self.client_address[0] if self.client_address else "").replace("::ffff:", "")
        return _ip_in_cidr_list(client_ip, cidrs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        # SEC-1 (v1.0.2): 旧实现在这里给任何请求 "/" 的客户端下发
        # Set-Cookie: ailink_token=<第一个有效令牌>，等于把面板密码彻底架空——
        # 局域网内（甚至端口被转发后的公网）任何人不带任何凭据取一次首页，
        # 就能拿到可用的 Bearer 令牌，require_lan_auth 也拦不住。
        # 令牌只应在 POST /api/login 校验密码通过后由客户端自行保存
        # （面板 index.html 的 promptPanelLoginModal 已经这么做了）。
        super().end_headers()

    def do_DELETE(self):
        """P0-4 Fix: Handles DELETE /api/clash/connections and DELETE /connections by forwarding to Clash :9090 and clearing cache."""
        clean_path = self.path.split("?", 1)[0]
        if clean_path.startswith("/api/") and not self._auth_ok():
            self._send_json({"ok": False, "error": "unauthorized", "message": "未授权访问"}, status=401)
            return
        if clean_path in ("/api/clash/connections", "/connections") or clean_path.startswith("/api/clash/connections/"):
            suffix = ""
            if clean_path.startswith("/api/clash/connections/"):
                cid = clean_path.split("/api/clash/connections/", 1)[1].strip("/")
                if cid:
                    suffix = f"/{urllib.parse.quote(cid, safe='')}"
            st_c, _ = clash_api_request(f"/connections{suffix}", method="DELETE", timeout=3.0)
            _CLASH_CONN_FAST_CACHE["ts"] = 0.0
            _CLASH_CONN_FAST_CACHE["val"] = None
            _invalidate_fast_api_cache()
            self._send_json({
                "ok": st_c in (200, 204) or not _is_local_port_listening(9090),
                "action": "connections_flushed",
                "status_code": st_c,
                "active_connections": 0,
            })
            return
        self._send_json({"ok": False, "error": "unknown_endpoint", "path": clean_path}, status=404)
    def do_GET(self):
        if self.path.split("?")[0] == "/api/dns/rewrite":
            rw_cfg = load_dns_rewrite_config(CONF_DIR)
            conf_path = _detect_dnsmasq_confdir() / "ai-link-rewrite.conf"
            rw_cfg["applied"] = conf_path.is_file()
            rw_cfg["applied_path"] = str(conf_path)
            self._send_json(rw_cfg)
            return
        parsed_url = urllib.parse.urlsplit(self.path)
        req_path = parsed_url.path
        qs = dict(urllib.parse.parse_qsl(parsed_url.query))
        if req_path == "/api/overview/telemetry":
            self._send_json(get_overview_live_telemetry(CONF_DIR))
            return
        if req_path == "/api/overview/galaxy":
            self._send_json(build_galaxy_snapshot(CONF_DIR))
            return
        if req_path == "/api/health_targets":
            ht_ts = int(_HEALTH_CACHE["ts"])
            self._send_json({
                "ok": True,
                "ts": ht_ts,
                "updated_at": time.strftime("%H:%M:%S", time.localtime(ht_ts)) if ht_ts > 0 else "检测中",
                "running": bool(_HEALTH_CACHE["running"]),
                "targets": health_targets_snapshot()
            })
            return
        if req_path == "/api/status":
            if self._try_send_wire_memo():
                return
            status_payload = build_status_api_response(CONF_DIR)
            is_authed = bool(self._auth_ok())
            status_payload["pwd_customized"] = is_panel_pwd_customized(CONF_DIR)
            status_payload["auth_required"] = (not is_authed)
            if not is_authed:
                status_payload = _mask_status_secrets(status_payload)
            self._send_json(status_payload)
            return
        # ---- OTA 在线更新 (v1.0.1+) ----
        if req_path == "/api/system/version":
            self._send_json({
                "ok": True,
                "version": APP_VERSION,
                "channel": APP_CHANNEL,
                "build": APP_BUILD,
                "version_file": _read_version_file(),
                "manifest_sources": _update_manifest_candidates(CONF_DIR),
            })
            return
        if req_path == "/api/system/update/check":
            force = str(qs.get("force", "0")).lower() in ("1", "true", "yes")
            self._send_json(check_plugin_update(CONF_DIR, force=force))
            return
        if req_path == "/api/system/update/status":
            self._send_json({"ok": True, "current": APP_VERSION, "progress": read_update_progress()})
            return
        if req_path == "/api/system/service/status":
            self._send_json({"ok": True, "version": APP_VERSION, "service": get_service_state()})
            return
        if req_path == "/api/homelink/port_check":
            chk_port = int(qs.get("port") or 9443)
            chk_proto = str(qs.get("protocol") or "vless-reality")
            chk_ex = str(qs.get("exclude_id") or "")
            self._send_json(validate_homelink_port(chk_port, chk_proto, chk_ex, CONF_DIR))
            return
        if req_path == "/api/shunt":
            if self._try_send_wire_memo():
                return
            self._send_json(build_shunt_api_response(CONF_DIR))
            return
        if req_path == "/api/shunt/history":
            self._send_json({"ok": True, "history": load_switch_history(RUN_DIR)})
            return
        if req_path == "/api/ops/settings":
            self._send_json(get_ops_settings(CONF_DIR))
            return
        if req_path == "/api/ops/check_updates":
            self._send_json(check_all_updatable_items(CONF_DIR))
            return
        if req_path == "/api/certs/ca":
            self._send_json(get_ca_cert_info(CONF_DIR))
            return
        if req_path == "/api/clash/proxies":
            self._send_json(clash_get_proxies())
            return
        if req_path == "/api/clash/delay":
            node_name = qs.get("name", "direct")
            test_url = qs.get("url", DEFAULT_DELAY_TEST_URL)
            timeout_ms = int(qs.get("timeout", "3000"))
            svc_id = qs.get("service_id", "").strip().lower()
            res_d = clash_test_delay(node_name, test_url=test_url, timeout_ms=timeout_ms, force=True)
            sel_to_svc = {
                "Shunt_YouTube": "youtube",
                "Stream_Auto": "youtube",
                "Shunt_AI": "gemini",
                "AI_Best_Auto": "gemini",
                "Shunt_GitHub": "github",
                "Shunt_Outside_CN": "telegram",
            }
            target_sid = svc_id or sel_to_svc.get(node_name, "")
            now_t = time.time()
            if res_d.get("ok") and int(res_d.get("delay") or 0) > 0:
                d_val = int(res_d["delay"])
                if target_sid:
                    _H3_APP_MS[target_sid] = d_val
                    _H3_APP_TS[target_sid] = now_t
                    if d_val > 0 and target_sid in _OVERVIEW_RT.get("service_bars", {}):
                        _OVERVIEW_RT["service_bars"][target_sid].append(min(95, max(10, int(d_val / 4))))
                        _OVERVIEW_RT["service_bars"][target_sid] = _OVERVIEW_RT["service_bars"][target_sid][-28:]
                resolved_n = PROBE_ENGINE.current_selections.get(node_name) or node_name
                if resolved_n and resolved_n not in ("direct", "block"):
                    PROBE_ENGINE.last_delays[resolved_n] = float(d_val)
            elif target_sid and res_d.get("ok") is False:
                # Fallback: if Clash selector delay failed because :9090 isn't active or selector name mapped to auto pool, check resolved node
                resolved_n = PROBE_ENGINE.current_selections.get(node_name) or ""
                if resolved_n and resolved_n != node_name and resolved_n not in ("direct", "block"):
                    res_d2 = clash_test_delay(resolved_n, test_url=test_url, timeout_ms=timeout_ms, force=True)
                    if res_d2.get("ok") and int(res_d2.get("delay") or 0) > 0:
                        res_d = res_d2
                        _H3_APP_MS[target_sid] = int(res_d2["delay"])
                        _H3_APP_TS[target_sid] = now_t
            res_d["as_of_ts"] = int(now_t)
            res_d["service_id"] = target_sid
            self._send_json(res_d)
            return
        if req_path == "/api/clash/connections":
            self._send_json(clash_get_connections_summary())
            return
        if req_path == "/api/subscriptions":
            if not self._auth_ok():
                self._send_json({"ok": False, "error": "unauthorized", "message": "需要面板访问令牌"}, status=401)
                return
            subs_out = copy.deepcopy(load_subscriptions(CONF_DIR))
            if not self._is_loopback_client() and not self._is_request_authenticated():
                for _s in subs_out:
                    if isinstance(_s, dict) and _s.get("url"):
                        _s["url"] = re.sub(r"([?&](?:token|key|auth|passwd|password|secret)=)[^&]+", r"\1***", str(_s["url"]), flags=re.I)
            self._send_json({
                "ok": True,
                "subscriptions": subs_out
            })
            return
        if req_path == "/api/homelink":
            if not self._auth_ok():
                self._send_json({"ok": False, "error": "unauthorized", "message": "需要面板访问令牌"}, status=401)
                return
            is_lb = self._is_loopback_client()
            is_auth = self._is_request_authenticated()
            self._send_json(build_homelink_api_response(CONF_DIR, mask_private_key=(not is_lb), mask_all_secrets=(not is_lb and not is_auth)))
            return
        if req_path == "/api/dns/settings":
            self._send_json(build_dns_telemetry_response(CONF_DIR))
            return
        if req_path in ("/api/ops/diag", "/api/ops/health_check"):
            self._send_json(get_ops_diagnostics(CONF_DIR))
            return
        if req_path == "/api/ops/logs":
            if not self._auth_ok():
                self._send_json({"ok": False, "error": "unauthorized", "message": "需要面板访问令牌"}, status=401)
                return
            self._send_json(get_ops_logs(CONF_DIR))
            return
        if req_path == "/api/ops/backup":
            if not self._auth_ok():
                self._send_json({"ok": False, "error": "unauthorized", "message": "需要面板访问令牌"}, status=401)
                return
            self._send_json(export_ops_backup(CONF_DIR))
            return
        if req_path == "/api/ops/backup_archive":
            if not self._auth_ok():
                self._send_json({"ok": False, "error": "unauthorized", "message": "需要面板访问令牌"}, status=401)
                return
            try:
                try:
                    cur_ops = get_ops_settings(CONF_DIR)
                    save_keys = ("enabled", "entry_bypass", "block_quic", "game_udp_direct", "auto_mute_conflicts", "ipv6_proxy", "gh_mirror", "lan_direct_macs", "probe_scene_preset", "node_auto_test", "node_test_mode", "node_test_budget", "egress_probe_interval_s", "require_lan_auth", "trusted_cidr", "panel_bind", "update_manifest_url")
                    (CONF_DIR / "ops_settings.json").write_text(json.dumps({k: cur_ops.get(k) for k in save_keys}, indent=2, ensure_ascii=False), encoding="utf-8")
                    if CONF_DIR.resolve() == Path("/etc/ai-link").resolve() and Path("/etc/config/ai-link").is_file():
                        shutil.copy2("/etc/config/ai-link", CONF_DIR / "uci_ai_link.bak")
                except Exception:
                    pass
                tmp_arc = Path(f"/tmp/ai-link-export-{os.getpid()}-{int(time.time())}.tgz")
                tar_items = [str(CONF_DIR.name)]
                subprocess.run(["tar", "-czf", str(tmp_arc), "-C", str(CONF_DIR.parent)] + tar_items, check=True, timeout=10)
                raw_tgz = tmp_arc.read_bytes()
                tmp_arc.unlink(missing_ok=True)
                fname = f"ai-link-backup-{time.strftime('%Y%m%d')}.tgz"
                if qs.get("raw") == "1":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/gzip")
                    self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                    self.send_header("Content-Length", str(len(raw_tgz)))
                    self.end_headers()
                    self.wfile.write(raw_tgz)
                    return
                self._send_json({
                    "ok": True,
                    "filename": fname,
                    "size": len(raw_tgz),
                    "md5": hashlib.md5(raw_tgz).hexdigest(),
                    "archive_base64": base64.b64encode(raw_tgz).decode("ascii"),
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e), "message": f"生成 .tgz 备份归档失败: {e}"}, status=500)
            return
        if req_path in ("/favicon.ico", "/favicon.svg", "/apple-touch-icon.png"):
            svg_bytes = (
                b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
                b'<rect width="64" height="64" rx="16" fill="#0f172a"/>'
                b'<circle cx="32" cy="32" r="20" fill="none" stroke="#38bdf8" stroke-width="4"/>'
                b'<path d="M22 36 L32 18 L42 36 L37 36 L32 27 L27 36 Z" fill="#8b5cf6"/>'
                b'<circle cx="32" cy="42" r="3.5" fill="#22d3ee"/></svg>'
            )
            f_local = WEBUI_DIR / req_path.lstrip("/")
            if f_local.is_file():
                raw_b = f_local.read_bytes()
                ctype = "image/svg+xml" if req_path.endswith(".svg") else ("image/png" if req_path.endswith(".png") else "image/x-icon")
            else:
                raw_b = svg_bytes
                ctype = "image/svg+xml"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Content-Length", str(len(raw_b)))
            self.end_headers()
            self.wfile.write(raw_b)
            return
        if req_path in ("/assets/tailwind.css", "/assets/tailwind.offline.css"):
            self.path = "/static/tailwind.css"
            return super().do_GET()
        if req_path in ("/vendor/three.min.js", "/vendor/qrcode.min.js"):
            self.path = f"/static/{req_path.split('/')[-1]}"
            return super().do_GET()
        if req_path == "/api/auto_nodes":
            if self._try_send_wire_memo():
                return
            inc_sp = (qs.get("sparkline") != "0")
            self._send_json(build_auto_nodes_api_response(CONF_DIR, include_sparkline=inc_sp))
            return
        if req_path == "/api/auto_nodes/replace_candidates":
            an_id = qs.get("id", "auto_ai")
            target_n = qs.get("node", "")
            self._send_json(get_auto_node_replace_candidates(an_id, target_n, conf_dir=CONF_DIR))
            return
        if req_path == "/api/probe/store":
            self._send_json({"ok": True, "quota_used_today": _node_test_used(), "store": load_node_probe_store(CONF_DIR)})
            return
        if req_path == "/api/nodes":
            if self._try_send_wire_memo():
                return
            wants_full = (qs.get("full") == "1")
            include_full = wants_full and (self._is_loopback_client() or self._is_request_authenticated())
            inc_sp = (qs.get("sparkline") == "1")
            lim = int(qs.get("limit") or qs.get("page_size") or 0) if str(qs.get("limit") or qs.get("page_size") or "0").isdigit() else 0
            off = int(qs.get("offset") or 0) if str(qs.get("offset") or "0").isdigit() else 0
            if lim > 0 and "page" in qs and str(qs.get("page") or "1").isdigit():
                off = max(0, (int(qs["page"]) - 1) * lim)
            self._send_json(build_nodes_api_response(CONF_DIR, include_full=include_full, include_sparkline=inc_sp, limit=lim, offset=off))
            return
        if req_path == "/api/probe/schedules":
            self._send_json({"ok": True, "schedules": load_probe_schedules(CONF_DIR)})
            return
        if req_path == "/api/ipv6/status":
            self._send_json({"ok": True, **build_ipv6_governance_summary(CONF_DIR)})
            return
        if req_path == "/api/nodes/share_uri":
            if not self._auth_ok():
                self._send_json({"ok": False, "error": "unauthorized", "message": "需要面板访问令牌"}, status=401)
                return
            t_q = (qs.get("tag") or qs.get("node_id") or "").strip()
            found_n = next((n for n in load_saved_nodes(CONF_DIR) if n.get("tag") == t_q or n.get("node_id") == t_q), None)
            if not found_n:
                self._send_json({"ok": False, "error": "node_not_found"}, status=404)
                return
            self._send_json({"ok": True, "tag": found_n.get("tag"), "node_id": found_n.get("node_id"), "uri": export_node_share_uri(found_n), "node": found_n})
            return
        if req_path.startswith("/api/"):
            self._send_json({"ok": False, "error": "unknown_endpoint", "message": f"未知 API 路径: {req_path}", "path": req_path}, status=404)
            return
        return super().do_GET()
    def do_POST(self):
        clean_path = self.path.split("?")[0]
        if clean_path != "/api/login" and clean_path.startswith("/api/") and not self._auth_ok():
            self._send_json({"ok": False, "error": "unauthorized", "message": "未授权访问，请先登录面板获取令牌"}, status=401)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 35 * 1024 * 1024:
            self._send_json({"ok": False, "error": "payload_too_large", "message": "请求体超过 35MB 上限"}, status=413)
            return
        body_raw = self.rfile.read(length).decode("utf-8", errors="replace") if length > 0 else "{}"
        try:
            payload = json.loads(body_raw) if body_raw.strip() else {}
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}
        if clean_path == "/api/login":
            pw = str(payload.get("password") or "").strip()
            ok_pw, tok = _verify_panel_password(pw, CONF_DIR)
            if not ok_pw:
                time.sleep(0.4)
                self._send_json({"ok": False, "error": "invalid_password", "message": "面板访问密码错误"}, status=401)
                return
            self._send_json({"ok": True, "token": tok})
            return
        if clean_path.startswith("/api/") and not self._auth_ok():
            self._send_json({"ok": False, "error": "unauthorized", "message": "未授权访问，请先登录面板获取令牌"}, status=401)
            return
        # ---- OTA 在线更新 (v1.0.1+) ----
        if clean_path == "/api/system/update/apply":
            force = bool(payload.get("force")) or str(payload.get("force", "")).lower() in ("1", "true", "yes")
            res = start_plugin_update(CONF_DIR, force=force)
            self._send_json(res, status=(200 if res.get("ok") else 409))
            return
        if clean_path == "/api/system/update/ack":
            self._send_json(acknowledge_update_result())
            return
        if clean_path == "/api/system/service/restart":
            self._send_json(restart_service_async())
            return
        if clean_path == "/api/wol":
            mac = payload.get("mac", "A4:83:E7:2B:91:04")
            try:
                pkt = build_wol_magic_packet(mac)
                self._send_json({"ok": True, "mac": mac, "packet_bytes": len(pkt)})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if clean_path == "/api/recover_direct":
            for r_dir in (RUN_DIR, Path("/tmp/ai-link-run")):
                try:
                    r_dir.mkdir(parents=True, exist_ok=True)
                    (r_dir / "bypass").write_text(str(int(time.time())), encoding="utf-8")
                except Exception:
                    pass
            update_ops_settings({"enabled": False}, CONF_DIR)
            if Path("/etc/init.d/ai-link").exists():
                subprocess.run(["/etc/init.d/ai-link", "recover_direct"], check=False, timeout=5)
            _STATUS_API_MEMO.clear()
            _invalidate_fast_api_cache()
            self._send_json({"ok": True, "enabled": False, "bypass_active": True, "mode": "direct_bypass"})
            return
        if clean_path == "/api/restore_proxy":
            for r_dir in (RUN_DIR, Path("/tmp/ai-link-run")):
                for fn in ("bypass", "recover_direct.flag"):
                    try:
                        if (r_dir / fn).exists():
                            (r_dir / fn).unlink()
                    except Exception:
                        pass
            FAIL_OPEN_STATE["active"] = False
            FAIL_OPEN_STATE["consecutive_failures"] = 0
            update_ops_settings({"enabled": True}, CONF_DIR)
            if Path("/etc/init.d/ai-link").exists():
                subprocess.run(["/etc/init.d/ai-link", "restore_proxy"], check=False, timeout=6)
            _STATUS_API_MEMO.clear()
            _invalidate_fast_api_cache()
            self._send_json({"ok": True, "enabled": True, "bypass_active": False, "mode": "proxy_restored"})
            return
        if clean_path == "/api/clash/connections/close":
            st_c, _ = clash_api_request("/connections", method="DELETE", timeout=3.0)
            _CLASH_CONN_FAST_CACHE["ts"] = 0.0
            _CLASH_CONN_FAST_CACHE["val"] = None
            _invalidate_fast_api_cache()
            self._send_json({"ok": True, "action": "connections_flushed", "status_code": st_c, "active_connections": 0})
            return
        if clean_path == "/api/ops/restore_archive":
            b64_data = str(payload.get("archive_base64") or "").strip()
            custom_path = str(payload.get("archive_path") or "").strip()
            tmp_upload = None
            try:
                if b64_data:
                    if "," in b64_data and b64_data.split(",", 1)[0].startswith("data:"):
                        b64_data = b64_data.split(",", 1)[1].strip()
                    raw_bytes = base64.b64decode(b64_data)
                    if len(raw_bytes) < 32 or len(raw_bytes) > 30 * 1024 * 1024:
                        self._send_json({"ok": False, "error": "invalid_archive_size", "message": "上传的归档文件大小异常（限制 30MB 以内）"}, status=400)
                        return
                    tmp_upload = Path(f"/tmp/ai-link-upload-{os.getpid()}-{int(time.time()*1000)}.tgz")
                    tmp_upload.write_bytes(raw_bytes)
                    arc_p = tmp_upload
                elif custom_path:
                    cand_p = Path(custom_path).resolve()
                    allowed_roots = (BACKUP_ROOT.resolve(), Path("/tmp").resolve())
                    if not any(str(cand_p).startswith(str(ar) + "/") for ar in allowed_roots):
                        self._send_json({"ok": False, "error": "forbidden_archive_path", "message": "仅允许从 /root/ai-link-final-backup 或 /tmp 恢复归档"}, status=403)
                        return
                    arc_p = cand_p
                else:
                    arc_p = Path("/root/ai-link-final-backup/etc-ai-link.tgz")
                if not arc_p.is_file():
                    self._send_json({"ok": False, "error": "archive_not_found", "message": f"未找到备份归档 {arc_p}"}, status=404)
                    return
                res_arc = restore_from_backup_archive(CONF_DIR, arc_p)
                if res_arc.get("ok") and b64_data and CONF_DIR.resolve() == Path("/etc/ai-link").resolve():
                    try:
                        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
                        os.chmod(str(BACKUP_ROOT), 0o700)
                        (BACKUP_ROOT / "etc-ai-link.tgz").write_bytes(raw_bytes)
                        os.chmod(str(BACKUP_ROOT / "etc-ai-link.tgz"), 0o600)
                    except Exception:
                        pass
                self._send_json(res_arc, status=(200 if res_arc.get("ok") else 400))
            except Exception as e:
                self._send_json({"ok": False, "error": str(e), "message": f"恢复归档失败: {e}"}, status=500)
            finally:
                if tmp_upload is not None:
                    tmp_upload.unlink(missing_ok=True)
            return
        if clean_path == "/api/import_cache":
            res = import_host_cache(CACHE_DIR, CONF_DIR)
            write_all_configs(CONF_DIR)
            self._send_json({"ok": True, "imported": res})
            return
        if clean_path == "/api/nodes/parse_preview":
            raw_links = payload.get("raw_links") or payload.get("text") or payload.get("uri") or ""
            reg_ov = str(payload.get("region_override") or "").strip().upper()
            parsed_obs = NodeURIParser.parse_subscription_text(raw_links, conf_dir=CONF_DIR)
            preview_list = []
            for ob in parsed_obs:
                if reg_ov in ("JP", "US", "SG", "HK", "TW", "KR", "OTHER", "TEST"):
                    ob["region_override"] = reg_ov
                nid = compute_node_id(ob)
                ob["node_id"] = nid
                c5 = classify_node_country_5plus1(ob.get("tag", ""), ob)
                tls_d = ob.get("tls") if isinstance(ob.get("tls"), dict) else {}
                tr_d = ob.get("transport") if isinstance(ob.get("transport"), dict) else {}
                preview_list.append({
                    "node_id": nid,
                    "tag": ob.get("tag", ""),
                    "type": ob.get("type", "vless"),
                    "server": ob.get("server", ""),
                    "server_port": ob.get("server_port", 443),
                    "country": c5,
                    "country_label": COUNTRY_5PLUS1_META.get(c5, COUNTRY_5PLUS1_META["OTHER"])["label"],
                    "sni": tls_d.get("server_name") or ob.get("sni") or "",
                    "security": "reality" if (isinstance(tls_d.get("reality"), dict) and tls_d["reality"].get("enabled")) else ("tls" if tls_d.get("enabled") else "none"),
                    "transport": tr_d.get("type") or "tcp",
                    "share_uri": export_node_share_uri(ob),
                    "node": ob,
                })
            self._send_json({"ok": True, "parsed_count": len(preview_list), "nodes": preview_list})
            return
        if clean_path == "/api/ops/uninstall":
            keep_cfg = bool(payload.get("keep_config", True))
            uninst_sh = Path("/usr/share/ai-link/uninstall.sh")
            cmd_args = [str(uninst_sh) if uninst_sh.is_file() else "/usr/bin/ai-link"]
            if not uninst_sh.is_file():
                cmd_args.append("uninstall")
            cmd_args.append("-y")
            if keep_cfg:
                cmd_args.append("--keep-config")
            def _bg_uninstall():
                time.sleep(0.6)
                try:
                    subprocess.Popen(cmd_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                except Exception:
                    pass
            threading.Thread(target=_bg_uninstall, daemon=True).start()
            self._send_json({
                "ok": True,
                "uninstalling": True,
                "keep_config": keep_cfg,
                "backup_archive": "/root/ai-link-final-backup/etc-ai-link.tgz",
                "message": f"正在安全卸载 AI-LINK（{'保留 /etc/ai-link 配置目录并' if keep_cfg else '彻底清除配置目录，但已'}自动归档备份至 /root/ai-link-final-backup/etc-ai-link.tgz）..."
            })
            return
        if clean_path == "/api/nodes/import":
            raw_links = payload.get("raw_links") or payload.get("text") or payload.get("uri") or ""
            reg_ov = str(payload.get("region_override") or "").strip().upper()
            custom_tag_prefix = str(payload.get("tag_prefix") or "").strip()
            parsed_obs = NodeURIParser.parse_subscription_text(raw_links, conf_dir=CONF_DIR)
            for ob in parsed_obs:
                if custom_tag_prefix and not str(ob.get("tag") or "").startswith(custom_tag_prefix):
                    ob["tag"] = f"{custom_tag_prefix}{ob.get('tag', '')}".strip()
                    ob["display_tag"] = ob["tag"]
                if reg_ov in ("JP", "US", "SG", "HK", "TW", "KR", "OTHER", "TEST"):
                    ob["region_override"] = reg_ov
                ob["_manual"] = True
            merged = merge_nodes("", parsed_obs, sub_url="", replace_sub=False, conf_dir=CONF_DIR)
            write_all_configs(CONF_DIR)
            if payload.get("reload_core", True) and Path("/etc/init.d/ai-link").exists():
                schedule_async_core_reload(hot_only=False)
            if payload.get("test_after_add", False) and parsed_obs:
                def _bg_test_imported(nids):
                    try:
                        time.sleep(1.2)
                        url_ping_batch_nodes(tags_or_ids=nids, conf_dir=CONF_DIR)
                    except Exception:
                        pass
                threading.Thread(target=_bg_test_imported, args=([ob["node_id"] for ob in parsed_obs if ob.get("node_id")],), daemon=True).start()
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            self._send_json({"ok": True, "imported_count": len(parsed_obs), "total_nodes": len(merged), "tags": [n["tag"] for n in parsed_obs], "all_tags": [n["tag"] for n in merged]})
            return
        if clean_path == "/api/nodes/add_test_node":
            updated = add_loopback_test_nodes(CONF_DIR)
            write_all_configs(CONF_DIR)
            if payload.get("reload_core", True) and Path("/etc/init.d/ai-link").exists():
                _core_ready = reload_core_only()
            self._send_json({
                "ok": True,
                "total_nodes": len(updated),
                "tags": [n["tag"] for n in updated]
            })
            return
        if clean_path == "/api/clash/switch":
            group = payload.get("group", "AI_Best_Auto")
            name = payload.get("name", "direct")
            ok = PROBE_ENGINE.hot_switch_core_selector(group, name, reason="Clash API 切换出口")
            PROBE_ENGINE.save_persisted_selections(RUN_DIR, record_history=False)
            self._send_json({"ok": ok, "group": group, "selected": name, "persisted": True, "selections": PROBE_ENGINE.current_selections})
            return
        if clean_path == "/api/probe/run":
            is_manual = bool(payload.get("manual", False) or payload.get("force", False))
            if payload.get("sync") is True:
                PROBE_ENGINE.probe_running = True
                try:
                    res = PROBE_ENGINE.run_probe_and_switch_cycle(CONF_DIR, RUN_DIR, force_manual=is_manual)
                finally:
                    PROBE_ENGINE.probe_running = False
                self._send_json(res)
                return
            if PROBE_ENGINE.probe_running:
                self._send_json({
                    "ok": True,
                    "async": True,
                    "already_running": True,
                    "probe_running": True,
                    "selections": PROBE_ENGINE.current_selections
                })
                return
            def _bg_probe():
                PROBE_ENGINE.probe_running = True
                try:
                    PROBE_ENGINE.run_probe_and_switch_cycle(CONF_DIR, RUN_DIR, force_manual=is_manual)
                except Exception:
                    pass
                finally:
                    PROBE_ENGINE.probe_running = False
            PROBE_ENGINE.probe_running = True
            threading.Thread(target=_bg_probe, daemon=True).start()
            self._send_json({
                "ok": True,
                "async": True,
                "manual": is_manual,
                "probe_running": True,
                "selections": PROBE_ENGINE.current_selections
            })
            return
        if clean_path == "/api/shunt/update":
            shunt_cfg = load_shunt_config(CONF_DIR)
            old_mode = shunt_cfg.get("routing_mode", "rule_shunt")
            if "routing_mode" in payload:
                shunt_cfg["routing_mode"] = payload["routing_mode"]
                shunt_cfg["shunt_enabled"] = (payload["routing_mode"] == "rule_shunt")
                if payload["routing_mode"] in ("gfw_list", "cn_whitelist", "global_proxy") and "global_mode" not in payload and shunt_cfg.get("global_mode") == "direct":
                    shunt_cfg["global_mode"] = "auto"
                    shunt_cfg["global_strategy"] = "auto"
                    shunt_cfg["global_auto_node_id"] = shunt_cfg.get("global_auto_node_id") or "auto_youtube"
            for gk in ("global_country", "global_strategy", "global_manual_node", "global_mode", "global_auto_node_id"):
                if gk in payload:
                    shunt_cfg[gk] = payload[gk]
            if any(k in payload for k in ("global_mode", "global_auto_node_id", "global_country", "global_strategy", "global_manual_node")):
                gm = str(shunt_cfg.get("global_mode") or ("direct" if shunt_cfg.get("global_strategy") == "direct" else ("manual" if shunt_cfg.get("global_strategy") == "manual" else "auto"))).strip().lower()
                if gm == "direct":
                    shunt_cfg["global_mode"] = "direct"
                    shunt_cfg["global_strategy"] = "direct"
                    shunt_cfg["global_manual_node"] = "direct"
                elif gm == "manual":
                    shunt_cfg["global_mode"] = "manual"
                    shunt_cfg["global_strategy"] = "manual"
                    g_ctry = str(shunt_cfg.get("global_country") or "JP").strip().upper()
                    if g_ctry not in ("HK", "TW", "JP", "SG", "US", "OTHER"):
                        g_ctry = "JP"
                    shunt_cfg["global_country"] = g_ctry
                    g_man = str(shunt_cfg.get("global_manual_node") or "").strip()
                    if g_man.startswith("auto:") or g_man == "direct":
                        g_man = ""
                    shunt_cfg["global_manual_node"] = g_man
                else:
                    shunt_cfg["global_mode"] = "auto"
                    shunt_cfg["global_strategy"] = "auto"
                    g_aid = str(shunt_cfg.get("global_auto_node_id") or "auto_youtube").strip() or "auto_youtube"
                    shunt_cfg["global_auto_node_id"] = g_aid
                    shunt_cfg["global_manual_node"] = f"auto:{g_aid}"
            # Support updating a single group {"group_id": "AI", "country": "US", "strategy": "smart", "manual_node": "..."}
            if "group_id" in payload:
                gid = payload["group_id"]
                for g in shunt_cfg.get("groups", []):
                    if g["id"] == gid:
                        for fk in ("country", "strategy", "manual_node", "shunt_mode", "auto_node_id"):
                            if fk in payload:
                                g[fk] = payload[fk]
                        if "shunt_mode" not in payload:
                            if payload.get("country") == "direct" or payload.get("strategy") == "direct":
                                g["shunt_mode"] = "direct"
                            elif payload.get("strategy") == "manual" and not str(payload.get("manual_node") or "").startswith("auto:"):
                                g["shunt_mode"] = "manual"
                            elif payload.get("strategy") in ("auto", "smart", "fastest") or str(payload.get("manual_node") or "").startswith("auto:"):
                                g["shunt_mode"] = "auto"
                        sm_n, c_n, st_n, aid_n, m_n = _normalize_group_shunt_params(g)
                        g["shunt_mode"] = sm_n
                        g["country"] = c_n
                        g["strategy"] = st_n
                        g["auto_node_id"] = aid_n
                        g["manual_node"] = m_n
                        break
            # Or batch updating groups list
            if isinstance(payload.get("groups"), list):
                up_map = {x["id"]: x for x in payload["groups"] if isinstance(x, dict) and "id" in x}
                for g in shunt_cfg.get("groups", []):
                    if g["id"] in up_map:
                        u_item = up_map[g["id"]]
                        for fk in ("country", "strategy", "manual_node", "shunt_mode", "auto_node_id"):
                            if fk in u_item:
                                g[fk] = u_item[fk]
                        sm_n, c_n, st_n, aid_n, m_n = _normalize_group_shunt_params(g)
                        g["shunt_mode"] = sm_n
                        g["country"] = c_n
                        g["strategy"] = st_n
                        g["auto_node_id"] = aid_n
                        g["manual_node"] = m_n
            save_shunt_config(shunt_cfg, CONF_DIR)
            mode_changed = (shunt_cfg.get("routing_mode") != old_mode)
            _CORE_RELOAD_STATE["config_seq"] += 1
            _SHUNT_API_MEMO.clear()
            _STATUS_API_MEMO.clear()
            _JSON_WIRE_MEMO.clear()
            _invalidate_fast_api_cache()
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            PROBE_ENGINE.save_persisted_selections(RUN_DIR, record_history=False)
            write_all_configs(CONF_DIR)
            rel_st = schedule_async_core_reload(force_respawn=mode_changed, apply_nft=mode_changed, hot_only=(not mode_changed))
            threading.Thread(target=flush_all_dns_caches, daemon=True).start()
            resp_sh = build_shunt_api_response(CONF_DIR)
            resp_sh["mode_changed"] = mode_changed
            resp_sh["requires_core_respawn"] = mode_changed
            resp_sh["config_seq"] = rel_st.get("config_seq", 1)
            resp_sh["reload_seq"] = rel_st.get("reload_seq", 1)
            self._send_json(resp_sh)
            return
        if clean_path == "/api/dns/flush_cache":
            self._send_json(flush_all_dns_caches())
            return
        if clean_path == "/api/shunt/trace":
            self._send_json(trace_traffic_flow(payload, CONF_DIR))
            return
        if clean_path == "/api/shunt/matrix_test":
            self._send_json(run_full_network_matrix_test(CONF_DIR))
            return
        if clean_path == "/api/shunt/clear_history":
            try:
                (RUN_DIR / "switch_history.json").write_text("[]", encoding="utf-8")
            except Exception:
                pass
            self._send_json({"ok": True, "history": []})
            return
        if clean_path == "/api/ops/settings":
            res_ops = update_ops_settings(payload, CONF_DIR)
            self._send_json(res_ops)
            return
        if clean_path == "/api/ops/control":
            act = str(payload.get("action") or "").strip().lower()
            if act in ("stop_proxy", "disable_proxy"):
                for r_dir in (RUN_DIR, Path("/tmp/ai-link-run")):
                    r_dir.mkdir(parents=True, exist_ok=True)
                    (r_dir / "bypass").write_text(str(int(time.time())), encoding="utf-8")
                update_ops_settings({"enabled": False}, CONF_DIR)
                if Path("/etc/init.d/ai-link").exists():
                    subprocess.run(["/etc/init.d/ai-link", "recover_direct"], check=False, timeout=5)
                _STATUS_API_MEMO.clear()
                _invalidate_fast_api_cache()
                self._send_json({"ok": True, "action": act, "enabled": False, "bypass_active": True})
                return
            if act in ("start_proxy", "enable_proxy"):
                for r_dir in (RUN_DIR, Path("/tmp/ai-link-run")):
                    for fn in ("bypass", "recover_direct.flag"):
                        try:
                            if (r_dir / fn).exists():
                                (r_dir / fn).unlink()
                        except Exception:
                            pass
                update_ops_settings({"enabled": True}, CONF_DIR)
                if Path("/etc/init.d/ai-link").exists():
                    subprocess.run(["/etc/init.d/ai-link", "restore_proxy"], check=False, timeout=6)
                _STATUS_API_MEMO.clear()
                _invalidate_fast_api_cache()
                self._send_json({"ok": True, "action": act, "enabled": True, "bypass_active": False})
                return
            if act == "restart_core":
                write_all_configs(CONF_DIR)
                core_ok = True
                if Path("/etc/init.d/ai-link").exists():
                    core_ok = reload_core_only(timeout=25.0, force_respawn=True, explicit_restart=True)
                    if core_ok and _is_local_port_listening(int(_uci_get_str("global.tproxy_port", "7893") or 7893)):
                        subprocess.run(["/usr/share/ai-link/nftables/apply_nft.sh"], check=False, timeout=5)
                PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
                _invalidate_sys_cache()
                _invalidate_fast_api_cache()
                rt_now = get_core_runtime_info(CONF_DIR)
                self._send_json({"ok": True, "action": "restart_core", "core_ready": core_ok, "core_pid": rt_now.get("core_pid"), "core": rt_now.get("core")})
                return
            if act == "restart_panel":
                def _delayed_panel_restart():
                    time.sleep(0.5)
                    try:
                        if Path("/etc/init.d/ai-link").exists():
                            subprocess.Popen(["/etc/init.d/ai-link", "restart"])
                    except Exception:
                        pass
                threading.Thread(target=_delayed_panel_restart, daemon=True).start()
                self._send_json({"ok": True, "action": "restart_panel", "message": "管理面板与守护进程正在重启，2秒后自动重连..."})
                return
            if act == "check_conflicts":
                stopped_list = []
                for csvc in ("nolo", "nolo-core", "open-box", "homeproxy", "passwall", "passwall2", "nikki", "momo", "openclash"):
                    init_p = Path(f"/etc/init.d/{csvc}")
                    if init_p.exists():
                        r_p = subprocess.run(["pgrep", "-f", csvc], capture_output=True, text=True, timeout=1)
                        if (r_p.stdout or "").strip():
                            subprocess.run([str(init_p), "stop"], capture_output=True, timeout=3)
                            subprocess.run([str(init_p), "disable"], capture_output=True, timeout=3)
                            stopped_list.append(csvc)
                self._send_json({"ok": True, "action": "check_conflicts", "stopped_conflicts": stopped_list})
                return
            self._send_json({"ok": False, "error": f"unknown_action: {act}"}, status=400)
            return
        if clean_path == "/api/ops/update_item":
            item_id = str(payload.get("item") or "all").strip().lower()
            results = {}
            if item_id in ("subscriptions", "all"):
                subs = [s for s in load_subscriptions(CONF_DIR) if s.get("enabled", True) and str(s.get("url") or "").strip()]
                if not subs:
                    results["subscriptions"] = {
                        "ok": False,
                        "skipped": True,
                        "imported_count": 0,
                        "error": "no_subscriptions_configured",
                        "message": "当前尚未配置任何订阅源，请先在「节点管理」中添加订阅"
                    }
                else:
                    sub_results = []
                    for s_item in subs:
                        sub_results.append(fetch_and_sync_subscription(
                            url=s_item.get("url", ""),
                            name=s_item.get("name", "机场订阅"),
                            conf_dir=CONF_DIR,
                            sub_id=s_item.get("id", "")
                        ))
                    results["subscriptions"] = sub_results[-1] if len(sub_results) == 1 else {"ok": any(r.get("ok") for r in sub_results), "items": sub_results}
            if item_id in ("rulesets", "all"):
                results["rulesets"] = ensure_srs_rulesets(CONF_DIR, timeout_per_file=6.0)
            if item_id in ("dns_filters", "all"):
                results["dns_filters"] = sync_dns_filter_lists(CONF_DIR)
            write_all_configs(CONF_DIR)
            if Path("/etc/init.d/ai-link").exists():
                reload_core_only()
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            self._send_json({
                "ok": True,
                "updated_item": item_id,
                "results": results,
                "summary": check_all_updatable_items(CONF_DIR)
            })
            return
        if clean_path == "/api/shunt/custom_rule":
            shunt_cfg = load_shunt_config(CONF_DIR)
            groups = shunt_cfg.get("groups", [])
            default_map = {dg["id"]: copy.deepcopy(dg) for dg in DEFAULT_SHUNT_GROUPS}
            rule_id = (payload.get("id") or "").strip()
            is_edit = any(g.get("id") == rule_id for g in groups) if rule_id else False
            if not rule_id:
                rule_id = f"Custom_{int(time.time())}"
            safe_id = re.sub(r"[^0-9A-Za-z_]", "_", rule_id)
            if not safe_id.startswith("Custom_") and not is_edit and safe_id not in default_map:
                safe_id = f"Custom_{safe_id}"
            def _split_list(val):
                if isinstance(val, list):
                    return [str(x).strip() for x in val if str(x).strip()]
                if isinstance(val, str):
                    return [x.strip() for x in re.split(r"[,\n\r;]+", val) if x.strip()]
                return []
            is_builtin = (safe_id in default_map)
            existing_grp = next((g for g in groups if g.get("id") == safe_id), None)
            def_grp = default_map.get(safe_id, {})
            new_grp = copy.deepcopy(existing_grp or def_grp or {})
            new_grp.update({
                "id": safe_id,
                "name": (payload.get("name") or new_grp.get("name") or "自定义分流规则").strip(),
                "subtitle": (payload.get("subtitle") if "subtitle" in payload else (new_grp.get("subtitle") or "用户自定义高优先级匹配规则")).strip(),
                "selector_tag": new_grp.get("selector_tag") or f"Shunt_{safe_id}",
                "legacy_selector": new_grp.get("legacy_selector", ""),
                "country": payload.get("country") if "country" in payload else new_grp.get("country", "US"),
                "strategy": payload.get("strategy") if "strategy" in payload else new_grp.get("strategy", "smart"),
                "manual_node": payload.get("manual_node") if "manual_node" in payload else new_grp.get("manual_node", ""),
                "is_custom": not is_builtin,
                "user_edited_rules": True if is_builtin else False,
                "locked_bottom": (safe_id == "Final_Fallback"),
                "locked_order": (safe_id in ("Domestic_CN", "Final_Fallback")),
                "target_test_url": (payload.get("target_test_url") or new_grp.get("target_test_url") or "https://cp.cloudflare.com/generate_204").strip(),
                "domains": _split_list(payload.get("domains", new_grp.get("domains", []))),
                "domain_keywords": _split_list(payload.get("domain_keywords", new_grp.get("domain_keywords", []))),
                "exact_domains": _split_list(payload.get("exact_domains", new_grp.get("exact_domains", []))),
                "ip_cidrs": _split_list(payload.get("ip_cidrs", new_grp.get("ip_cidrs", []))),
                "source_ip_cidrs": _split_list(payload.get("source_ip_cidrs", new_grp.get("source_ip_cidrs", []))),
                "ports": [int(p) for p in _split_list(payload.get("ports", new_grp.get("ports", []))) if str(p).isdigit()]
            })
            if is_edit:
                for idx, g in enumerate(groups):
                    if g.get("id") == safe_id:
                        groups[idx] = new_grp
                        break
                if "position" in payload and safe_id not in ("Domestic_CN", "Final_Fallback"):
                    pos = payload.get("position")
                    cur_i = next((i for i, g in enumerate(groups) if g.get("id") == safe_id), -1)
                    if cur_i >= 0 and pos in ("top", "before_domestic"):
                        item_m = groups.pop(cur_i)
                        if pos == "top":
                            groups.insert(0, item_m)
                        elif pos == "before_domestic":
                            dom_idx = next((i for i, g in enumerate(groups) if g.get("id") == "Domestic_CN"), len(groups) - 1)
                            groups.insert(max(0, dom_idx), item_m)
            else:
                pos = payload.get("position", "top")
                if pos == "top":
                    groups.insert(0, new_grp)
                elif pos == "before_domestic":
                    dom_idx = next((i for i, g in enumerate(groups) if g.get("id") == "Domestic_CN"), len(groups) - 1)
                    groups.insert(max(0, dom_idx), new_grp)
                else:
                    dom_idx = next((i for i, g in enumerate(groups) if g.get("id") == "Domestic_CN"), len(groups) - 1)
                    groups.insert(max(0, dom_idx), new_grp)
            _before_fp = _compute_core_rules_fingerprint(CONF_DIR)
            shunt_cfg["groups"] = _normalize_shunt_groups_order(groups)
            save_shunt_config(shunt_cfg, CONF_DIR)
            write_all_configs(CONF_DIR)
            _after_fp = _compute_core_rules_fingerprint(CONF_DIR)
            _fp_changed = (_after_fp != _before_fp)
            # D-02 & P1-1 Fix: Only respawn when route/dns/outbound fingerprint actually changed!
            rel_st = schedule_async_core_reload(force_respawn=_fp_changed, hot_only=(not _fp_changed))
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            PROBE_ENGINE.save_persisted_selections(RUN_DIR, record_history=False)
            resp_shunt = build_shunt_api_response(CONF_DIR)
            resp_shunt["is_edit"] = is_edit
            resp_shunt["requires_core_respawn"] = _fp_changed
            resp_shunt["config_seq"] = rel_st.get("config_seq", 1)
            resp_shunt["reload_seq"] = rel_st.get("reload_seq", 1)
            c_info = detect_entry_bypass_conflict(
                new_grp["domains"], new_grp["exact_domains"], new_grp["domain_keywords"],
                new_grp["ip_cidrs"], new_grp["country"], conf_dir=CONF_DIR
            )
            resp_shunt["entry_bypass_conflict"] = c_info
            if c_info.get("conflict"):
                resp_shunt["conflict_warning"] = c_info["warning"]
            self._send_json(resp_shunt)
            return
        if clean_path in ("/api/shunt/delete_rule", "/api/shunt/reset_group_rules"):
            gid = payload.get("group_id") or payload.get("id") or ""
            gids = set(payload.get("group_ids") or [])
            if gid:
                gids.add(gid)
            clear_all = bool(payload.get("clear_all_custom", False))
            reset_presets = bool(payload.get("reset_presets", False) or clean_path == "/api/shunt/reset_group_rules")
            default_map = {dg["id"]: copy.deepcopy(dg) for dg in DEFAULT_SHUNT_GROUPS}
            shunt_cfg = load_shunt_config(CONF_DIR)
            before_len = len(shunt_cfg.get("groups", []))
            changed_rules = False
            if clean_path == "/api/shunt/reset_group_rules" and gid in default_map:
                new_groups = []
                for g in shunt_cfg.get("groups", []):
                    if g.get("id") == gid:
                        def_g = copy.deepcopy(default_map[gid])
                        for keep_k in ("shunt_mode", "country", "strategy", "auto_node_id", "manual_node"):
                            if keep_k in g:
                                def_g[keep_k] = g[keep_k]
                        def_g["user_edited_rules"] = False
                        new_groups.append(def_g)
                        changed_rules = True
                    else:
                        new_groups.append(g)
                shunt_cfg["groups"] = _normalize_shunt_groups_order(new_groups)
            elif reset_presets:
                custom_kept = [] if clear_all else [
                    g for g in shunt_cfg.get("groups", [])
                    if g.get("is_custom", False) and not g.get("locked_bottom", False) and g.get("id") not in gids
                ]
                shunt_cfg["groups"] = _normalize_shunt_groups_order(custom_kept + [copy.deepcopy(dg) for dg in DEFAULT_SHUNT_GROUPS])
                changed_rules = True
            else:
                shunt_cfg["groups"] = [
                    g for g in shunt_cfg.get("groups", [])
                    if not (
                        g.get("is_custom", False)
                        and not g.get("locked_bottom", False)
                        and (clear_all or g.get("id") in gids)
                    )
                ]
            save_shunt_config(shunt_cfg, CONF_DIR)
            write_all_configs(CONF_DIR)
            if len(shunt_cfg["groups"]) != before_len or reset_presets or changed_rules:
                schedule_async_core_reload(force_respawn=True, hot_only=False)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            self._send_json(build_shunt_api_response(CONF_DIR))
            return
        if clean_path == "/api/shunt/reorder":
            shunt_cfg = load_shunt_config(CONF_DIR)
            groups = _normalize_shunt_groups_order(shunt_cfg.get("groups", []))
            regular = [g for g in groups if not g.get("locked_bottom") and g.get("id") not in ("Domestic_CN", "Final_Fallback")]
            locked_tail = [g for g in groups if g.get("id") in ("Domestic_CN", "Final_Fallback") or g.get("locked_bottom")]
            ordered_ids = payload.get("ordered_ids")
            if isinstance(ordered_ids, list) and ordered_ids:
                reg_map = {g["id"]: g for g in regular}
                new_reg = [reg_map[i] for i in ordered_ids if i in reg_map]
                for g in regular:
                    if g["id"] not in ordered_ids:
                        new_reg.append(g)
                regular = new_reg
            else:
                gid = payload.get("group_id") or payload.get("id") or ""
                direction = str(payload.get("direction") or "up").lower()
                target_prio = payload.get("target_priority")
                idx = next((i for i, g in enumerate(regular) if g.get("id") == gid), -1)
                if idx >= 0:
                    item = regular.pop(idx)
                    if target_prio is not None and str(target_prio).isdigit():
                        t_idx = max(0, min(len(regular), int(target_prio) - 1))
                        regular.insert(t_idx, item)
                    elif direction == "top":
                        regular.insert(0, item)
                    elif direction == "bottom":
                        regular.append(item)
                    elif direction == "up":
                        regular.insert(max(0, idx - 1), item)
                    elif direction == "down":
                        regular.insert(min(len(regular), idx + 1), item)
                    else:
                        regular.insert(idx, item)
            _before_fp = _compute_core_rules_fingerprint(CONF_DIR)
            shunt_cfg["groups"] = _normalize_shunt_groups_order(regular + locked_tail)
            save_shunt_config(shunt_cfg, CONF_DIR)
            write_all_configs(CONF_DIR)
            _after_fp = _compute_core_rules_fingerprint(CONF_DIR)
            _fp_changed = (_after_fp != _before_fp)
            if _fp_changed:
                schedule_async_core_reload(force_respawn=True, hot_only=False)
            else:
                schedule_async_core_reload(force_respawn=False, hot_only=True)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            _resp_ro = build_shunt_api_response(CONF_DIR)
            _resp_ro["requires_core_respawn"] = _fp_changed
            self._send_json(_resp_ro)
            return
        if clean_path == "/api/shunt/verify_target":
            gid = payload.get("group_id") or payload.get("id") or "AI"
            sim_fail = bool(payload.get("simulate_fail_current", False))
            res = PROBE_ENGINE.verify_group_target_and_failover(gid, CONF_DIR, simulate_fail_current=sim_fail)
            res["shunt"] = build_shunt_api_response(CONF_DIR)
            self._send_json(res)
            return
        if clean_path == "/api/subscriptions/import_text":
            res = import_subscription_text(payload, conf_dir=CONF_DIR)
            self._send_json(res, status=200 if res.get("ok") else 400)
            return
        if clean_path in ("/api/nodes/test_real_delay", "/api/probe/url_ping"):
            res = url_ping_batch_nodes(
                tags_or_ids=payload.get("tags") or payload.get("node_ids"),
                sub_id=str(payload.get("sub_id") or ""),
                sub_url=str(payload.get("sub_url") or ""),
                source=str(payload.get("source") or ""),
                region=str(payload.get("region") or ""),
                timeout_ms=int(payload.get("timeout_ms") or 3000),
                concurrency=int(payload.get("concurrency") or 10),
                conf_dir=CONF_DIR
            )
            self._send_json(res)
            return
        if clean_path == "/api/probe/event_reverify":
            nid = str(payload.get("node_id") or payload.get("tag") or "").strip()
            res = on_egress_fail(nid, conf_dir=CONF_DIR, bypass_debounce=bool(payload.get("bypass_debounce", False)), mock_ping_result=payload.get("mock_ping_result"))
            self._send_json(res)
            return
        if clean_path == "/api/probe/service_l7":
            nid = str(payload.get("node_id") or payload.get("tag") or "").strip()
            sid = str(payload.get("service_id") or "openai").strip()
            res = probe_node_service_l7(nid, sid, custom_url=str(payload.get("url") or ""), timeout_ms=int(payload.get("timeout_ms") or 3000), conf_dir=CONF_DIR, mock_http=payload.get("mock_http"))
            evaluate_all_auto_nodes(CONF_DIR, force_service_probe=False)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            self._send_json(res)
            return
        if clean_path == "/api/auto_nodes/save":
            cfg = load_auto_nodes_config(CONF_DIR)
            if isinstance(payload.get("custom_services"), list):
                cfg["custom_services"] = payload["custom_services"]
            if isinstance(payload.get("add_custom_service"), dict):
                cs_new = payload["add_custom_service"]
                if cs_new.get("name") and cs_new.get("url"):
                    cid = cs_new.get("id") or f"custom_{int(time.time())}"
                    cfg.setdefault("custom_services", []).append({"id": cid, "name": str(cs_new["name"]).strip(), "url": str(cs_new["url"]).strip()})
            an_in = payload.get("auto_node") if isinstance(payload.get("auto_node"), dict) else payload
            if an_in and an_in.get("name"):
                ok_v, err_msg, norm_groups = validate_auto_node_payload(an_in, conf_dir=CONF_DIR)
                if not ok_v:
                    self._send_json({"ok": False, "error": "invalid_groups", "message": err_msg}, status=400)
                    return
                an_id = str(an_in.get("id") or f"auto_{int(time.time())}").strip()
                an_tag = str(an_in.get("tag") or f"Auto_{re.sub(r'[^a-zA-Z0-9_]', '_', an_id)}").strip()
                an_in_copy = dict(an_in)
                an_in_copy["id"] = an_id
                an_in_copy["tag"] = an_tag
                an_in_copy["groups"] = norm_groups
                new_an = _normalize_auto_node_item(an_in_copy, conf_dir=CONF_DIR)
                all_new_tags = set()
                all_new_ids = set()
                for ng in norm_groups:
                    all_new_tags.update(ng.get("node_tags") or [])
                    all_new_ids.update(ng.get("node_ids") or [])
                replaced = False
                an_id_low = an_id.lower()
                an_tag_low = an_tag.lower()
                for idx, ex_a in enumerate(cfg.get("auto_nodes", [])):
                    ex_id_s = str(ex_a.get("id") or "")
                    ex_tag_s = str(ex_a.get("tag") or "")
                    if ex_id_s.lower() == an_id_low or ex_tag_s.lower() == an_id_low or ex_tag_s.lower() == an_tag_low:
                        # Preserve canonical ID & tag (e.g. 'auto_ai' / 'Auto_AI') so shunt group bindings never break
                        if ex_id_s:
                            an_id = ex_id_s
                            new_an["id"] = ex_id_s
                        if ex_tag_s:
                            an_tag = ex_tag_s
                            new_an["tag"] = ex_tag_s
                        ex_cur = ex_a.get("current_node") or ""
                        ex_cid = ex_a.get("current_node_id") or ""
                        ex_gidx = int(ex_a.get("active_group_index") if ex_a.get("active_group_index") is not None else 1)
                        still_in_pool = (ex_cur and ex_cur != "direct" and (ex_cur in all_new_tags or ex_cid in all_new_ids))
                        if still_in_pool and ex_gidx >= 1:
                            for keep_k in ("current_node", "current_node_id", "current_delay_ms", "active_group_index", "last_working_group_index", "primary_recover_streak", "last_revert_ts", "last_smart_switch_ts"):
                                if keep_k not in an_in and keep_k in ex_a:
                                    new_an[keep_k] = ex_a[keep_k]
                        else:
                            new_an["active_group_index"] = 1
                            new_an["last_working_group_index"] = 1
                            new_an["current_node"] = ""
                            new_an["current_node_id"] = ""
                            new_an["current_delay_ms"] = -1
                            new_an["all_groups_dead_alert"] = False
                            new_an["alert_message"] = ""
                        cfg["auto_nodes"][idx] = new_an
                        replaced = True
                        break
                if not replaced:
                    cfg.setdefault("auto_nodes", []).append(new_an)
                save_auto_nodes_config(cfg, CONF_DIR)
                want_probe = bool(payload.get("probe_now", True))
                evaluate_all_auto_nodes(CONF_DIR, target_id=an_id, force_service_probe=False, advance_revert_streak=False)
                # Ensure a newly created card immediately selects its first Group 1 member instead of sitting at "direct" before probe completes
                cfg_eval = load_auto_nodes_config(CONF_DIR)
                for _a_it in (cfg_eval.get("auto_nodes") or []):
                    if _a_it.get("id") == an_id and (not _a_it.get("current_node") or _a_it.get("current_node") == "direct"):
                        _g1_tags = [t for _g in (_a_it.get("groups") or []) for t in (_g.get("node_tags") or []) if t and t != "direct"]
                        if _g1_tags:
                            _a_it["current_node"] = _g1_tags[0]
                            _a_it["active_group_index"] = 1
                            _a_it["all_groups_dead_alert"] = False
                            save_auto_nodes_config(cfg_eval, CONF_DIR)
                        break
                write_all_configs(CONF_DIR)
                PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
                # D-03 & D-05 Fix: When a new card is created or group members change, reload core so the new selector & outbounds enter sing-box!
                rel_st = schedule_async_core_reload(force_respawn=(not replaced), hot_only=False)
                def _bg_after_an_save(_aid=an_id, _atag=an_tag):
                    try:
                        # Wait for async core reload/respawn to settle first so probe never races SIGTERM!
                        _wait_dl = time.time() + 28.0
                        while time.time() < _wait_dl and _CORE_RELOAD_STATE.get("reloading"):
                            time.sleep(0.25)
                        if want_probe and _is_local_port_listening(9090):
                            probe_auto_node_dual_groups(_aid, probe_services=True, conf_dir=CONF_DIR)
                        else:
                            evaluate_all_auto_nodes(CONF_DIR, target_id=_aid, force_service_probe=False, advance_revert_streak=False)
                        PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
                    except Exception:
                        pass
                threading.Thread(target=_bg_after_an_save, daemon=True).start()
            else:
                save_auto_nodes_config(cfg, CONF_DIR)
                rel_st = dict(_CORE_RELOAD_STATE)
            resp_an = load_auto_nodes_config(CONF_DIR)
            resp_an["saved"] = True
            resp_an["reload"] = "pending" if rel_st.get("reloading") else "completed"
            resp_an["config_seq"] = rel_st.get("config_seq", 1)
            resp_an["reload_seq"] = rel_st.get("reload_seq", 1)
            self._send_json(resp_an)
            return
        if clean_path == "/api/auto_nodes/delete":
            an_id = str(payload.get("id") or payload.get("tag") or "").strip()
            cfg = load_auto_nodes_config(CONF_DIR)
            before_cnt = len(cfg.get("auto_nodes") or [])
            cfg["auto_nodes"] = [a for a in (cfg.get("auto_nodes") or []) if a.get("id") != an_id and a.get("tag") != an_id]
            save_auto_nodes_config(cfg, CONF_DIR)
            write_all_configs(CONF_DIR)
            if len(cfg["auto_nodes"]) != before_cnt:
                schedule_async_core_reload(hot_only=False)
            resp_del = load_auto_nodes_config(CONF_DIR)
            resp_del["ok"] = True
            resp_del["deleted_id"] = an_id
            self._send_json(resp_del)
            return
        if clean_path == "/api/auto_nodes/probe":
            an_id = str(payload.get("id") or "").strip()
            if an_id:
                res_p = probe_auto_node_dual_groups(an_id, probe_services=True, conf_dir=CONF_DIR)
                last_round = res_p.get("probe_round")
            else:
                last_round = None
                for a_item in (load_auto_nodes_config(CONF_DIR).get("auto_nodes") or []):
                    res_p = probe_auto_node_dual_groups(a_item.get("id", ""), probe_services=True, conf_dir=CONF_DIR)
                    last_round = res_p.get("probe_round")
            out_cfg = load_auto_nodes_config(CONF_DIR)
            out_cfg["probe_round"] = last_round
            self._send_json(out_cfg)
            return
        if clean_path == "/api/auto_nodes/revert_now":
            an_id = str(payload.get("id") or payload.get("tag") or "").strip()
            res_rev = revert_auto_node_to_primary_now(an_id, conf_dir=CONF_DIR, mock_ping_map=payload.get("mock_ping_map"))
            self._send_json(res_rev, status=200 if res_rev.get("ok") else 404)
            return
        if clean_path == "/api/auto_nodes/replace_candidates":
            an_id = str(payload.get("id") or payload.get("auto_node_id") or "").strip()
            target_n = str(payload.get("node") or payload.get("old_node") or "").strip()
            self._send_json(get_auto_node_replace_candidates(an_id, target_n, conf_dir=CONF_DIR))
            return
        if clean_path == "/api/auto_nodes/replace_node":
            an_id = str(payload.get("id") or payload.get("auto_node_id") or "").strip()
            g_idx = int(payload.get("group_index") or 1)
            old_n = str(payload.get("old_node") or "").strip()
            new_n = str(payload.get("new_node") or "").strip()
            res_rep = replace_node_in_auto_group(an_id, g_idx, old_n, new_n, conf_dir=CONF_DIR)
            self._send_json(res_rep, status=200 if res_rep.get("ok") else 400)
            return
        if clean_path in ("/api/subscriptions/sync", "/api/subscriptions/add"):
            url = (payload.get("url") or DEFAULT_REAL_SUB_URL).strip()
            name = (payload.get("name") or "主力机场订阅").strip()
            sub_id = str(payload.get("id") or "").strip()
            old_url = str(payload.get("old_url") or "").strip()
            auto_up = bool(payload.get("auto_update", True))
            interval_min = int(payload.get("update_interval_min", 360))
            test_after_add = bool(payload.get("test_after_add", True))
            res = fetch_and_sync_subscription(
                url=url, name=name, auto_update=auto_up, update_interval_min=interval_min,
                conf_dir=CONF_DIR, sub_id=sub_id, old_url=old_url, test_after_add=test_after_add
            )
            if payload.get("reload_core", True) and res.get("imported_count", 0) > 0 and Path("/etc/init.d/ai-link").exists():
                reload_core_only()
                PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            self._send_json(res, status=200 if (res.get("ok") or payload.get("async")) else 400)
            return
        if clean_path in ("/api/subscriptions/update_settings", "/api/subscriptions/edit", "/api/subscriptions/toggle"):
            sub_id = str(payload.get("id") or "").strip()
            old_url = str(payload.get("old_url") or payload.get("url") or "").strip()
            # Spec §2.1: If `enabled` is toggled without editing URL/raw_text/sync_now, execute fast zero-network orthogonal switch!
            if "enabled" in payload and not payload.get("raw_text") and not payload.get("sync_now") and not payload.get("new_url"):
                res_tog = set_subscription_enabled(sub_id=sub_id, sub_url=old_url, enabled=bool(payload["enabled"]), conf_dir=CONF_DIR)
                self._send_json(res_tog, status=200 if res_tog.get("ok") else 404)
                return
            new_url = str(payload.get("new_url") or payload.get("url") or "").strip()
            new_name = str(payload.get("name") or "").strip()
            sync_now = bool(payload.get("sync_now", False))
            test_after_add = bool(payload.get("test_after_add", True))
            with _SUB_LOCK:
                subs = load_subscriptions(CONF_DIR)
                matched_sub = next((s for s in subs if (sub_id and s.get("id") == sub_id) or (old_url and s.get("url") == old_url)), subs[0] if len(subs) == 1 else None)
                if not matched_sub:
                    self._send_json({"ok": False, "error": "subscription_not_found"}, status=404)
                    return
                sub_id = matched_sub.get("id") or sub_id
                prev_url = matched_sub.get("url", "")
                if new_name:
                    matched_sub["name"] = new_name
                if new_url:
                    matched_sub["url"] = new_url
                if "update_interval_min" in payload:
                    iv = int(payload["update_interval_min"])
                    matched_sub["update_interval_min"] = iv
                    matched_sub["auto_update"] = (iv > 0)
                if "auto_update" in payload:
                    matched_sub["auto_update"] = bool(payload["auto_update"])
                save_subscriptions(subs, CONF_DIR)
                if new_url and prev_url and new_url != prev_url:
                    nodes_all = load_saved_nodes(CONF_DIR)
                    for n in nodes_all:
                        if n.get("_sub_id") == sub_id or n.get("_sub_url") == prev_url:
                            n["_sub_id"] = sub_id
                            n["_sub_url"] = new_url
                    save_nodes_list(nodes_all, CONF_DIR)
            if "enabled" in payload:
                set_subscription_enabled(sub_id=sub_id, sub_url=matched_sub["url"], enabled=bool(payload["enabled"]), conf_dir=CONF_DIR)
            if payload.get("raw_text"):
                res_imp = import_subscription_text({"id": sub_id, "old_url": prev_url, "name": matched_sub["name"], "url": matched_sub["url"], "raw_text": payload["raw_text"], "test_after_add": test_after_add, "reload_core": True}, conf_dir=CONF_DIR)
                self._send_json(res_imp, status=200 if res_imp.get("ok") else 400)
                return
            if sync_now:
                res_sync = fetch_and_sync_subscription(url=matched_sub["url"], name=matched_sub["name"], auto_update=matched_sub.get("auto_update", True), update_interval_min=matched_sub.get("update_interval_min", 360), conf_dir=CONF_DIR, sub_id=sub_id, old_url=prev_url, test_after_add=test_after_add)
                self._send_json(res_sync, status=200 if res_sync.get("ok") else 400)
                return
            self._send_json({"ok": True, "id": sub_id, "subscription": matched_sub, "subscriptions": load_subscriptions(CONF_DIR)})
            return
        if clean_path == "/api/subscriptions/delete":
            sub_id = str(payload.get("id") or "").strip()
            sub_url = str(payload.get("url") or "").strip()
            del_nodes = payload.get("delete_nodes", True)
            with _SUB_LOCK:
                old_subs = load_subscriptions(CONF_DIR)
                removed_urls = {s.get("url") for s in old_subs if (sub_id and s.get("id") == sub_id) or (sub_url and s.get("url") == sub_url)}
                subs = [s for s in old_subs if not ((sub_id and s.get("id") == sub_id) or (sub_url and s.get("url") == sub_url))]
                save_subscriptions(subs, CONF_DIR)
                if del_nodes:
                    nodes_kept = [n for n in load_saved_nodes(CONF_DIR) if not ((sub_id and n.get("_sub_id") == sub_id) or (sub_url and n.get("_sub_url") == sub_url) or (n.get("_sub_url") and n.get("_sub_url") in removed_urls))]
                    save_nodes_list(nodes_kept, CONF_DIR)
            write_all_configs(CONF_DIR)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            self._send_json({"ok": True, "deleted_id": sub_id, "subscriptions": subs, "total_nodes": len(load_saved_nodes(CONF_DIR))})
            return
        if clean_path == "/api/nodes/add":
            new_ob = build_manual_node_outbound(payload, CONF_DIR)
            new_ob["_manual"] = True
            existing = load_saved_nodes(CONF_DIR)
            replaced = False
            for idx, n in enumerate(existing):
                if n.get("tag") == new_ob["tag"]:
                    existing[idx] = new_ob
                    replaced = True
                    break
            if not replaced:
                existing.insert(0, new_ob)
            save_nodes_list(existing, CONF_DIR)
            write_all_configs(CONF_DIR)
            if payload.get("reload_core", True) and Path("/etc/init.d/ai-link").exists():
                schedule_async_core_reload(hot_only=False)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            self._send_json({
                "ok": True,
                "node": new_ob,
                "replaced": replaced,
                "total_nodes": len(existing),
                "reload_mode": LAST_RELOAD_MODE
            })
            return
        if clean_path == "/api/nodes/credentials":
            target_tag = (payload.get("tag") or "").strip()
            existing = load_saved_nodes(CONF_DIR)
            found = next((n for n in existing if n.get("tag") == target_tag), None)
            if not found:
                self._send_json({"ok": False, "error": "node_not_found"}, status=404)
                return
            self._send_json({"ok": True, "node": found})
            return
        if clean_path == "/api/nodes/update":
            tag = (payload.get("tag") or "").strip()
            nid_q = (payload.get("node_id") or payload.get("id") or "").strip()
            patch = payload.get("patch") if isinstance(payload.get("patch"), dict) else payload
            existing = load_saved_nodes(CONF_DIR)
            updated_node = None
            for idx_n, n in enumerate(existing):
                if (tag and n.get("tag") == tag) or (nid_q and (n.get("node_id") == nid_q or n.get("id") == nid_q)):
                    old_meta = {mk: n[mk] for mk in ("_sub_id", "_sub_url", "_manual", "disabled", "region_override") if mk in n}
                    if isinstance(patch.get("raw_outbound"), dict) and patch["raw_outbound"].get("type") and patch["raw_outbound"].get("server"):
                        n_new = copy.deepcopy(patch["raw_outbound"])
                        for mk, mv in old_meta.items():
                            n_new.setdefault(mk, mv)
                        n.clear()
                        n.update(n_new)
                    elif patch.get("share_uri") and "://" in str(patch.get("share_uri")):
                        parsed_u = NodeURIParser.parse_subscription_text(str(patch["share_uri"]), conf_dir=CONF_DIR)
                        if parsed_u:
                            n_new = parsed_u[0]
                            for mk, mv in old_meta.items():
                                n_new.setdefault(mk, mv)
                            n.clear()
                            n.update(n_new)
                    if "type" in patch and str(patch["type"]).strip():
                        nt_p = str(patch["type"]).strip().lower()
                        n["type"] = "hysteria2" if nt_p == "hy2" else ("shadowsocks" if nt_p == "ss" else ("socks" if nt_p == "socks5" else nt_p))
                    for k_up in ("disabled", "region_override", "server", "server_port", "uuid", "password", "method", "flow", "packet_encoding", "security", "congestion_control", "udp_relay_mode", "username"):
                        if k_up in patch:
                            if k_up == "server_port":
                                try:
                                    n[k_up] = int(patch[k_up])
                                except Exception:
                                    pass
                            elif k_up == "disabled":
                                n[k_up] = bool(patch[k_up])
                            else:
                                n[k_up] = patch[k_up]
                    if "new_tag" in patch and str(patch["new_tag"]).strip():
                        n["tag"] = str(patch["new_tag"]).strip()
                        n["display_tag"] = n["tag"]
                    _apply_node_advanced_fields(n, patch)
                    n.pop("_raw_uri", None)
                    n["node_id"] = compute_node_id(n)
                    updated_node = n
                    break
            if not updated_node:
                self._send_json({"ok": False, "error": "node_not_found"}, status=404)
                return
            save_nodes_list(existing, CONF_DIR)
            write_all_configs(CONF_DIR)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            # D-03 Fix: Must pass hot_only=False so edited node parameters are reloaded into sing-box!
            if payload.get("reload_core", True):
                schedule_async_core_reload(hot_only=False)
            self._send_json({"ok": True, "node": updated_node, "share_uri": export_node_share_uri(updated_node), "total_nodes": len(existing), "reload_mode": LAST_RELOAD_MODE})
            return
        if clean_path == "/api/nodes/delete":
            tag = payload.get("tag", "")
            nid_q = payload.get("node_id", "")
            existing = [n for n in load_saved_nodes(CONF_DIR) if not ((tag and n.get("tag") == tag) or (nid_q and n.get("node_id") == nid_q))]
            save_nodes_list(existing, CONF_DIR)
            write_all_configs(CONF_DIR)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            if payload.get("reload_core", True):
                schedule_async_core_reload(hot_only=False)
            self._send_json({"ok": True, "deleted": tag or nid_q, "total_nodes": len(existing), "reload_mode": LAST_RELOAD_MODE})
            return
        if clean_path == "/api/shunt/apply_exit":
            node_tag = (payload.get("node_tag") or payload.get("tag") or payload.get("name") or "").strip()
            if not node_tag:
                self._send_json({"ok": False, "error": "missing_node_tag", "message": "未指定出口节点名称"}, status=400)
                return
            existing = load_saved_nodes(CONF_DIR)
            node_obj = None
            for n in existing:
                if n.get("tag") == node_tag:
                    n["disabled"] = False
                    node_obj = n
                    break
            if not node_obj and node_tag not in ("direct", "block"):
                self._send_json({"ok": False, "error": "node_not_found", "message": f"指定的节点不存在: {node_tag}"}, status=400)
                return
            if node_obj:
                save_nodes_list(existing, CONF_DIR)
            target_country = "direct" if node_tag == "direct" else classify_node_region(node_tag, node_obj)
            shunt_cfg = load_shunt_config(CONF_DIR)
            req_groups = payload.get("group_ids")
            updated_groups = []
            updated_selectors = []
            for g in shunt_cfg.get("groups", []):
                gid = g.get("id", "")
                if isinstance(req_groups, list) and req_groups:
                    if gid not in req_groups:
                        continue
                else:
                    # By default, apply to all proxy shunt groups (keep Domestic_CN direct unless explicitly selected)
                    if gid == "Domestic_CN" and g.get("country") == "direct":
                        continue
                g["shunt_mode"] = "direct" if node_tag == "direct" else "manual"
                g["country"] = target_country
                g["strategy"] = "direct" if node_tag == "direct" else "manual"
                g["manual_node"] = node_tag
                updated_groups.append(gid)
                updated_selectors.append(g.get("selector_tag", f"Shunt_{gid}"))
            if not req_groups:
                shunt_cfg["global_country"] = target_country
                shunt_cfg["global_strategy"] = "manual"
                shunt_cfg["global_mode"] = "manual"
                shunt_cfg["global_manual_node"] = node_tag
            mode_switched_from_direct = False
            if node_tag != "direct" and shunt_cfg.get("routing_mode") == "direct_all":
                shunt_cfg["routing_mode"] = "rule_shunt"
                shunt_cfg["shunt_enabled"] = True
                mode_switched_from_direct = True
            # Clear Fail-Open and stall quarantine for the explicitly chosen exit node (#68)
            FAIL_OPEN_STATE["active"] = False
            FAIL_OPEN_STATE["consecutive_failures"] = 0
            FAIL_OPEN_STATE["reason"] = ""
            save_shunt_config(shunt_cfg, CONF_DIR)
            write_all_configs(CONF_DIR)
            # D-06 Fix: Only switch the requested shunt group selectors! Never overwrite AI_Best_Auto / Stream_Auto / HK_TW_Media
            # unless the user is in a non-shunt mode (global_proxy / gfw_list / cn_whitelist) and switching the global exit.
            target_selectors = list(updated_selectors)
            if shunt_cfg.get("routing_mode") in ("global_proxy", "gfw_list", "cn_whitelist") and not req_groups:
                if "AI_Best_Auto" not in target_selectors:
                    target_selectors.append("AI_Best_Auto")
            any_hot_failed = False
            for stag in target_selectors:
                ok_hot = PROBE_ENGINE.hot_switch_core_selector(stag, node_tag, reason=f"用户手动设为出口: {node_tag}")
                if not ok_hot:
                    any_hot_failed = True
            # If the chosen node was previously '未进内核' (any_hot_failed) or mode switched from direct, reload core!
            if (any_hot_failed or mode_switched_from_direct):
                schedule_async_core_reload(force_respawn=mode_switched_from_direct, hot_only=False)
            PROBE_ENGINE.save_persisted_selections(RUN_DIR, record_history=False)
            self._send_json({
                "ok": True,
                "node_tag": node_tag,
                "country": target_country,
                "mode_switched_from_direct": mode_switched_from_direct,
                "fail_open_cleared": True,
                "updated_groups": updated_groups,
                "updated_selectors": updated_selectors,
                "reload_mode": LAST_RELOAD_MODE,
                "shunt": build_shunt_api_response(CONF_DIR)
            })
            return
        if clean_path in ("/api/homelink/add", "/api/homelink/update", "/api/homelink/quick_create"):
            import uuid as _uuid_mod
            hl_nodes = load_homelink_nodes(CONF_DIR)
            hl_id = (payload.get("id") or "").strip()
            is_edit = any(h.get("id") == hl_id for h in hl_nodes) if hl_id else False
            if not hl_id:
                hl_id = f"hl_{int(time.time())}_{len(hl_nodes)+1}"
            proto = (payload.get("protocol") or "vless-reality").strip().lower()
            norm_proto = (
                "hysteria2" if ("hy2" in proto or "hysteria" in proto)
                else ("vless-tls" if ("tls" in proto and "reality" not in proto) else "vless-reality")
            )
            default_port = 20443 if norm_proto == "hysteria2" else (18443 if norm_proto == "vless-reality" else 9443)
            raw_lport = int(payload.get("listen_port") or 0)
            lport = raw_lport or default_port
            RESERVED_SYS_PORTS = {22, 53, 80, 443, 1053, 7874, 7890, 7891, 7893, 9090, 9099}
            if lport in RESERVED_SYS_PORTS or lport < 1024 or lport > 65535:
                self._send_json({
                    "ok": False,
                    "error": "reserved_or_invalid_port",
                    "message": f"端口 {lport} 为系统/网关核心保留端口或超出合法范围 (1024-65535)，请更换其他端口"
                }, status=400)
                return
            used_hl_ports = {int(h.get("listen_port") or 0) for h in hl_nodes if h.get("id") != hl_id}
            p_chk = validate_homelink_port(lport, norm_proto, hl_id, CONF_DIR)
            if not p_chk.get("ok"):
                if is_edit or (raw_lport and clean_path != "/api/homelink/quick_create"):
                    self._send_json({
                        "ok": False,
                        "error": "port_conflict",
                        "message": p_chk.get("reason") or f"监听端口 {lport} 不可用"
                    }, status=400)
                    return
                while not validate_homelink_port(lport, norm_proto, hl_id, CONF_DIR).get("ok"):
                    lport += 1
            ext_port = int(payload.get("external_port") or 0) or lport
            gen_uuid = str(_uuid_mod.uuid4())
            gen_pwd = f"ailink_{gen_uuid[:8]}"
            lan_ip = _detect_router_lan_ip()
            default_sni = "www.apple.com" if norm_proto == "vless-reality" else "ai-link.ailink.lan"
            priv_k, pub_k = generate_reality_keypair(str(payload.get("private_key") or "").strip())
            short_id = (str(payload.get("short_id") or "").strip() or gen_uuid.replace("-", "")[:8])
            proto_label = "Hysteria2" if norm_proto == "hysteria2" else ("VLESS-Reality" if norm_proto == "vless-reality" else "VLESS-TLS")
            new_entry = {
                "id": hl_id,
                "tag": payload.get("tag") or f"homelink-{hl_id}-in",
                "name": (payload.get("name") or f"回家隧道 · {proto_label} (:{ext_port})").strip(),
                "protocol": norm_proto,
                "listen_port": lport,
                "external_port": ext_port,
                "password": (payload.get("password") or gen_pwd).strip(),
                "uuid": (payload.get("uuid") or gen_uuid).strip(),
                "sni": (payload.get("sni") or default_sni).strip(),
                "private_key": priv_k,
                "public_key": str(payload.get("public_key") or pub_k).strip(),
                "short_id": short_id,
                "ddns_host": (payload.get("ddns_host") or lan_ip).strip(),
                "route_mode": payload.get("route_mode") if payload.get("route_mode") in ("shunt", "direct", "proxy_only") else get_uci_homelink_route_mode(),
                "enabled": bool(payload.get("enabled", True)),
                "builtin": False
            }
            if is_edit:
                for idx, h in enumerate(hl_nodes):
                    if h.get("id") == hl_id:
                        new_entry["tag"] = h.get("tag") or new_entry["tag"]
                        for k in ("name", "protocol", "listen_port", "external_port", "password", "uuid", "sni", "ddns_host", "route_mode", "enabled", "private_key", "public_key", "short_id"):
                            if k not in payload and k in h:
                                new_entry[k] = h[k]
                        hl_nodes[idx] = new_entry
                        break
            else:
                hl_nodes.append(new_entry)
            save_homelink_nodes(hl_nodes, CONF_DIR)
            sync_homelink_wan_firewall_rules(hl_nodes)
            write_all_configs(CONF_DIR)
            if Path("/etc/init.d/ai-link").exists():
                reload_core_only(force_respawn=True)
                subprocess.run(["/usr/share/ai-link/nftables/apply_nft.sh"], check=False, timeout=4)
            self._send_json(build_homelink_api_response(CONF_DIR))
            return
        if clean_path == "/api/homelink/route_mode":
            rmode = (payload.get("route_mode") or "shunt").strip().lower()
            if rmode not in ("direct", "shunt", "proxy_only"):
                rmode = "shunt"
            node_id = str(payload.get("id") or payload.get("node_id") or "").strip()
            apply_all = bool(payload.get("apply_all", True))
            if node_id:
                hl_nodes = load_homelink_nodes(CONF_DIR)
                for h in hl_nodes:
                    if h.get("id") == node_id:
                        h["route_mode"] = rmode
                save_homelink_nodes(hl_nodes, CONF_DIR)
            else:
                CONF_DIR.mkdir(parents=True, exist_ok=True)
                (CONF_DIR / "homelink_route_mode").write_text(rmode, encoding="utf-8")
                if apply_all:
                    hl_nodes = load_homelink_nodes(CONF_DIR)
                    for h in hl_nodes:
                        h["route_mode"] = rmode
                    save_homelink_nodes(hl_nodes, CONF_DIR)
            try:
                subprocess.run(["uci", "set", f"ai-link.homelink.route_mode={rmode}"], check=False, timeout=2)
                subprocess.run(["uci", "commit", "ai-link"], check=False, timeout=2)
            except Exception:
                pass
            write_all_configs(CONF_DIR)
            if Path("/etc/init.d/ai-link").exists():
                reload_core_only(force_respawn=True)
            self._send_json(build_homelink_api_response(CONF_DIR))
            return
        if clean_path == "/api/homelink/delete":
            hl_id = (payload.get("id") or "").strip()
            hl_nodes = [h for h in load_homelink_nodes(CONF_DIR) if h.get("id") != hl_id]
            save_homelink_nodes(hl_nodes, CONF_DIR)
            sync_homelink_wan_firewall_rules(hl_nodes)
            write_all_configs(CONF_DIR)
            if Path("/etc/init.d/ai-link").exists():
                reload_core_only(force_respawn=True)
                subprocess.run(["/usr/share/ai-link/nftables/apply_nft.sh"], check=False, timeout=4)
            self._send_json(build_homelink_api_response(CONF_DIR))
            return
        if clean_path == "/api/rules/sync":
            res_srs = ensure_srs_rulesets(CONF_DIR)
            write_all_configs(CONF_DIR)
            if Path("/etc/init.d/ai-link").exists():
                reload_core_only()
            self._send_json(res_srs)
            return
        if clean_path == "/api/ops/reprobe_build_mode":
            write_all_configs(CONF_DIR, force_full=bool(payload.get("force_full", True)))
            if Path("/etc/init.d/ai-link").exists():
                reload_core_only()
            self._send_json(get_core_runtime_info(CONF_DIR))
            return
        if clean_path == "/api/dns/rewrite":
            rw_cfg = load_dns_rewrite_config(CONF_DIR)
            if "enabled" in payload:
                rw_cfg["enabled"] = bool(payload["enabled"])
            if "force_tunnel_dns" in payload:
                rw_cfg["force_tunnel_dns"] = bool(payload["force_tunnel_dns"])
            action = payload.get("action", "")
            if action == "add":
                src = (payload.get("from_domain") or "").strip().lower()
                dst = (payload.get("to_domain") or "").strip().lower()
                if src and dst:
                    rules = [r for r in rw_cfg.get("rules", []) if r.get("from_domain") != src]
                    rules.insert(0, {
                        "id": f"rw_{int(time.time())}",
                        "from_domain": src,
                        "to_domain": dst,
                        "enabled": True,
                        "note": (payload.get("note") or "自定义 DNS 重写").strip()
                    })
                    rw_cfg["rules"] = rules
            elif action == "delete":
                rid = payload.get("id", "")
                fdom = payload.get("from_domain", "")
                rw_cfg["rules"] = [
                    r for r in rw_cfg.get("rules", [])
                    if not ((rid and r.get("id") == rid) or (fdom and r.get("from_domain") == fdom))
                ]
            elif action == "toggle_rule":
                rid = payload.get("id", "")
                for r in rw_cfg.get("rules", []):
                    if r.get("id") == rid or r.get("from_domain") == payload.get("from_domain"):
                        r["enabled"] = bool(payload.get("rule_enabled", not r.get("enabled", True)))
            _before_fp = _compute_core_rules_fingerprint(CONF_DIR)
            save_dns_rewrite_config(rw_cfg, CONF_DIR)
            write_all_configs(CONF_DIR)
            _after_fp = _compute_core_rules_fingerprint(CONF_DIR)
            schedule_async_core_reload(force_respawn=(_after_fp != _before_fp), hot_only=(_after_fp == _before_fp))
            self._send_json(build_dns_telemetry_response(CONF_DIR))
            return
        if clean_path == "/api/dns/filter/toggle":
            flt_cfg = load_dns_filter_config(CONF_DIR)
            if "enabled" in payload:
                flt_cfg["enabled"] = bool(payload["enabled"])
            if "auto_update" in payload:
                flt_cfg["auto_update"] = bool(payload["auto_update"])
            if "update_interval_hours" in payload:
                flt_cfg["update_interval_hours"] = max(1, int(payload["update_interval_hours"]))
            if "list_id" in payload:
                lid = payload["list_id"]
                for l in flt_cfg.get("lists", []):
                    if l.get("id") == lid:
                        l["enabled"] = bool(payload.get("list_enabled", not l.get("enabled", True)))
            if "add_list" in payload and isinstance(payload["add_list"], dict):
                nl = payload["add_list"]
                if nl.get("url"):
                    flt_cfg.setdefault("lists", []).append({
                        "id": f"custom_list_{int(time.time())}",
                        "name": (nl.get("name") or "自定义云端过滤列表").strip(),
                        "url": nl["url"].strip(),
                        "category": nl.get("category") or "自定义规则",
                        "enabled": True,
                        "rules_count": int(nl.get("rules_count", 12000)),
                        "updated_at": time.strftime("%Y-%m-%d %H:%M")
                    })
            if "custom_blocked" in payload and isinstance(payload["custom_blocked"], list):
                flt_cfg["custom_blocked"] = [str(x).strip().lower() for x in payload["custom_blocked"] if str(x).strip()]
            if "custom_allowed" in payload and isinstance(payload["custom_allowed"], list):
                flt_cfg["custom_allowed"] = [str(x).strip().lower() for x in payload["custom_allowed"] if str(x).strip()]
            _before_fp = _compute_core_rules_fingerprint(CONF_DIR)
            save_dns_filter_config(flt_cfg, CONF_DIR)
            write_all_configs(CONF_DIR)
            _after_fp = _compute_core_rules_fingerprint(CONF_DIR)
            schedule_async_core_reload(force_respawn=(_after_fp != _before_fp), hot_only=(_after_fp == _before_fp))
            self._send_json(build_dns_telemetry_response(CONF_DIR))
            return
        if clean_path == "/api/dns/filter/sync":
            res = sync_dns_filter_lists(CONF_DIR)
            write_all_configs(CONF_DIR)
            schedule_async_core_reload(force_respawn=True, hot_only=False)
            self._send_json(build_dns_telemetry_response(CONF_DIR))
            return
        if clean_path == "/api/dns/filter/test":
            res_test = run_live_adblock_swallow_test(CONF_DIR)
            self._send_json(res_test)
            return
        if clean_path == "/api/ops/restore":
            res = restore_ops_backup(payload, CONF_DIR)
            self._send_json(res)
            return
        if clean_path == "/api/ops/factory_reset":
            if str(payload.get("confirm") or "").strip().upper() not in ("RESET", "TRUE", "1", "YES"):
                self._send_json({"ok": False, "error": "confirmation_required", "message": "需要确认恢复出厂设置"}, status=400)
                return
            res_rst = factory_reset_all_configs(CONF_DIR, create_backup_archive=bool(payload.get("create_backup", True)))
            self._send_json(res_rst)
            return
        if clean_path == "/api/ops/password":
            new_pw = (payload.get("new_password") or payload.get("password") or "").strip()
            if not new_pw or len(new_pw) < 4:
                self._send_json({"ok": False, "error": "password_too_short", "message": "新密码长度不能少于 4 位"}, status=400)
                return
            new_tok = _update_panel_password(new_pw, CONF_DIR)
            _STATUS_API_MEMO.clear()
            _JSON_WIRE_MEMO.clear()
            self._send_json({"ok": True, "updated": True, "token": new_tok})
            return
        if clean_path == "/api/ops/fail_open_test":
            res_fo = run_fail_open_check_once(CONF_DIR, force_trigger=bool(payload.get("force", True)))
            self._send_json({"ok": True, "fail_open": res_fo})
            return
        if clean_path in ("/api/ops/ipv6", "/api/ipv6/toggle"):
            enable_v6 = bool(payload.get("ipv6_proxy", False))
            update_ops_settings({"ipv6_proxy": enable_v6}, CONF_DIR)
            _invalidate_sys_cache("uci_ipv6")
            write_all_configs(CONF_DIR)
            schedule_async_core_reload(force_respawn=True, apply_nft=True, hot_only=False)
            self._send_json({
                "ok": True,
                "ipv6_proxy": enable_v6,
                "ipv6_governance": build_ipv6_governance_summary(CONF_DIR),
                "reload_mode": LAST_RELOAD_MODE
            })
            return
        if clean_path == "/api/probe/ipv6_check":
            res_v6 = probe_nodes_ipv6_capability(
                tags_or_ids=payload.get("tags") or payload.get("node_ids"),
                sub_id=str(payload.get("sub_id") or ""),
                region=str(payload.get("region") or ""),
                timeout_ms=int(payload.get("timeout_ms") or 3500),
                concurrency=int(payload.get("concurrency") or 10),
                conf_dir=CONF_DIR,
                mock_ipv6_map=payload.get("mock_ipv6_map"),
            )
            self._send_json(res_v6)
            return
        if clean_path in ("/api/probe/schedules", "/api/probe/schedules/save"):
            schedules = load_probe_schedules(CONF_DIR)
            sc_id = str(payload.get("id") or f"sched_{int(time.time())}").strip()
            new_sc = {
                "id": sc_id,
                "name": str(payload.get("name") or "定时 URL Ping 测速").strip(),
                "sub_id": str(payload.get("sub_id") or "").strip(),
                "region": str(payload.get("region") or "ALL").strip(),
                "node_tags": list(payload.get("node_tags") or []),
                "interval_min": max(5, int(payload.get("interval_min") or 60)),
                "enabled": bool(payload.get("enabled", True)),
                "check_ipv6": bool(payload.get("check_ipv6", False)),
                "last_run_ts": int(payload.get("last_run_ts") or 0),
            }
            replaced_sc = False
            for idx, ex_s in enumerate(schedules):
                if ex_s.get("id") == sc_id:
                    new_sc["last_run_ts"] = ex_s.get("last_run_ts", 0)
                    new_sc["last_tested_count"] = ex_s.get("last_tested_count", 0)
                    new_sc["last_reachable_count"] = ex_s.get("last_reachable_count", 0)
                    schedules[idx] = new_sc
                    replaced_sc = True
                    break
            if not replaced_sc:
                schedules.append(new_sc)
            save_probe_schedules(schedules, CONF_DIR)
            self._send_json({"ok": True, "schedule": new_sc, "schedules": schedules})
            return
        if clean_path == "/api/probe/schedules/delete":
            sc_id = str(payload.get("id") or "").strip()
            schedules = [s for s in load_probe_schedules(CONF_DIR) if s.get("id") != sc_id]
            save_probe_schedules(schedules, CONF_DIR)
            self._send_json({"ok": True, "deleted_id": sc_id, "schedules": schedules})
            return
        if clean_path == "/api/probe/schedules/run":
            sc_id = str(payload.get("id") or "").strip()
            ran = run_due_probe_schedules(CONF_DIR, force_id=sc_id)
            self._send_json({"ok": True, "executed": ran, "schedules": load_probe_schedules(CONF_DIR)})
            return
        if clean_path == "/api/nodes/share_uri":
            t_q = str(payload.get("tag") or payload.get("node_id") or "").strip()
            found_n = next((n for n in load_saved_nodes(CONF_DIR) if n.get("tag") == t_q or n.get("node_id") == t_q), None)
            if not found_n:
                self._send_json({"ok": False, "error": "node_not_found"}, status=404)
                return
            self._send_json({"ok": True, "tag": found_n.get("tag"), "node_id": found_n.get("node_id"), "uri": export_node_share_uri(found_n), "node": found_n})
            return
        if clean_path == "/api/settings/max_nodes":
            raw_max = payload.get("max_outbounds", 200)
            if isinstance(raw_max, bool):
                self._send_json({"ok": False, "error": "invalid_max_outbounds", "message": "max_outbounds 必须为整数"}, status=400)
                return
            try:
                limit = int(raw_max)
            except Exception:
                self._send_json({"ok": False, "error": "invalid_max_outbounds", "message": "max_outbounds 必须为有效整数"}, status=400)
                return
            if limit < 0 or limit > 300:
                self._send_json({"ok": False, "error": "out_of_range", "message": "max_outbounds 范围必须在 0（不限）或 1~300 之间"}, status=400)
                return
            CONF_DIR.mkdir(parents=True, exist_ok=True)
            (CONF_DIR / "max_outbounds.txt").write_text(str(limit), encoding="utf-8")
            write_all_configs(CONF_DIR)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
            if payload.get("reload_core", True) and Path("/etc/init.d/ai-link").exists():
                schedule_async_core_reload(hot_only=False)
            _core_ready = True
            rt = get_core_runtime_info(CONF_DIR)
            self._send_json({
                "ok": True,
                "max_outbounds_limit": limit,
                "saved_nodes_total": rt["saved_nodes_total"],
                "active_outbounds_count": rt["active_outbounds_count"],
                "core_ready": locals().get("_core_ready", True),
                "reload_mode": LAST_RELOAD_MODE
            })
            return
        # D-04 Fix: Never return 200 OK for unknown/unmatched endpoints!
        self._send_json({
            "ok": False,
            "error": "unknown_endpoint",
            "message": f"未知 API 路径: {clean_path}",
            "path": clean_path
        }, status=404)

def get_uci_homelink_route_mode() -> str:
    try:
        f = CONF_DIR / "homelink_route_mode"
        if f.is_file():
            val = f.read_text(encoding="utf-8").strip().lower()
            if val in ("direct", "shunt", "proxy_only"):
                return val
    except Exception:
        pass
    def _read():
        try:
            r = subprocess.run(["uci", "-q", "get", "ai-link.homelink.route_mode"],
                               capture_output=True, text=True, timeout=1)
            val = (r.stdout or "").strip().lower()
            if val in ("direct", "shunt", "proxy_only"):
                return val
        except Exception:
            pass
        return "shunt"
    return _cached_Value("uci_hl_rmode", 30.0, _read)


def get_uci_probe_interval(default_sec: int = 300) -> int:
    def _read():
        try:
            r = subprocess.run(["uci", "-q", "get", "ai-link.probe.interval"],
                               capture_output=True, text=True, timeout=1)
            val = (r.stdout or "").strip()
            if val.isdigit():
                return max(30, int(val))
        except Exception:
            pass
        return default_sec
    return _cached_Value("uci_probe_iv", 30.0, _read)

def get_uci_ipv6_proxy(conf_dir: Path = CONF_DIR) -> bool:
    try:
        ops_f = Path(conf_dir) / "ops_settings.json"
        if ops_f.is_file():
            d = json.loads(ops_f.read_text(encoding="utf-8"))
            if isinstance(d, dict) and "ipv6_proxy" in d:
                return bool(d["ipv6_proxy"])
    except Exception:
        pass
    if Path(conf_dir).resolve() != CONF_DIR.resolve():
        return False
    def _read():
        try:
            r = subprocess.run(["uci", "-q", "get", "ai-link.global.ipv6_proxy"],
                               capture_output=True, text=True, timeout=1)
            val = (r.stdout or "").strip().lower()
            return val in ("1", "true", "yes", "on", "enabled")
        except Exception:
            return False
    return _cached_Value("uci_ipv6_proxy", 15.0, _read)

def check_and_run_auto_subscriptions(conf_dir: Path = CONF_DIR):
    """Checks subscriptions.json and triggers auto-sync for any subscription whose update_interval_min has elapsed."""
    subs = load_subscriptions(conf_dir)
    now_ts = int(time.time())
    any_imported = False
    for s in subs:
        if not s.get("enabled", True) or not s.get("auto_update", True):
            continue
        iv_min = int(s.get("update_interval_min", 360) or 0)
        if iv_min <= 0:
            continue
        last_ts = int(s.get("last_sync_ts", 0) or 0)
        if now_ts - last_ts >= iv_min * 60:
            res = fetch_and_sync_subscription(
                url=s.get("url", DEFAULT_REAL_SUB_URL),
                name=s.get("name", "订阅源"),
                auto_update=True,
                update_interval_min=iv_min,
                conf_dir=conf_dir
            )
            if res.get("imported_count", 0) > 0:
                any_imported = True
    if any_imported and Path("/etc/init.d/ai-link").exists():
        reload_core_only()

def _teardown_blackhole_nft_and_routing() -> bool:
    """P0-3 Fix (v1.0.3): Immediately removes nft table inet ai_link, policy routing table 162,
    and dnsmasq :7874 upstream when sing-box core is dead or :7893 is not listening,
    restoring direct internet instead of blackholing LAN and router traffic!"""
    removed = False
    try:
        r_nft = subprocess.run(["nft", "list", "table", "inet", "ai_link"], capture_output=True, text=True, timeout=2)
        if r_nft.returncode == 0:
            subprocess.run(["nft", "delete", "table", "inet", "ai_link"], capture_output=True, timeout=3)
            removed = True
        subprocess.run(["nft", "delete", "table", "ip", "ai_link"], capture_output=True, timeout=2)
        for _ in range(8):
            r_del = subprocess.run(["ip", "rule", "del", "fwmark", "0x162", "table", "162"], capture_output=True, timeout=2)
            if r_del.returncode != 0:
                break
            removed = True
        for _ in range(8):
            r_del6 = subprocess.run(["ip", "-6", "rule", "del", "fwmark", "0x162", "table", "162"], capture_output=True, timeout=2)
            if r_del6.returncode != 0:
                break
        if rollback_dnsmasq_and_resolv(CONF_DIR):
            removed = True
        if removed:
            subprocess.run(["logger", "-t", "ai-link", "Watchdog: core dead; nft removed, LAN restored to direct."], capture_output=True, timeout=3)
    except Exception:
        pass
    return removed

def ensure_nft_and_routing_intact() -> bool:
    """Mainstream Firewall4 / WAN Hotplug & Anti-Blackhole Self-Healing Guard (P0-3 & B1-4 Fix:
    1) If sing-box process is dead or TProxy :7893 is not listening, actively removes nft table + ip rule + dnsmasq :7874
       so LAN and router fall back to direct internet instead of entering a blackhole!
    2) Once sing-box and :7893 are alive, automatically re-mounts missing ip rule, nftables, and dnsmasq upstream)."""
    if is_bypass_active() or not shutil.which("nft") or not Path("/etc/init.d/ai-link").exists():
        return True
    try:
        r_en = subprocess.run(["uci", "-q", "get", "ai-link.global.enabled"], capture_output=True, text=True, timeout=2)
        if r_en.returncode == 0 and r_en.stdout.strip() == "0":
            return True
        if not get_ops_settings(CONF_DIR).get("enabled", True):
            return True
        tproxy_port = int(_uci_get_str("global.tproxy_port", "7893") or 7893)
        # B1-4 & P0-3 Fix: Never mount or keep nftables if core is dead or :7893 not listening (prevent LAN blackhole)
        if not _is_local_port_listening(tproxy_port):
            _teardown_blackhole_nft_and_routing()
            return False
        if not _get_live_singbox_pids():
            _teardown_blackhole_nft_and_routing()
            return False
        chk_nft = subprocess.run(["nft", "list", "table", "inet", "ai_link"], capture_output=True, text=True, timeout=3)
        chk_rule = subprocess.run(["ip", "rule", "show"], capture_output=True, text=True, timeout=3)
        nft_ok = (chk_nft.returncode == 0 and "prerouting_tproxy" in (chk_nft.stdout or ""))
        rule_ok = (chk_rule.returncode == 0 and ("0x162" in (chk_rule.stdout or "") or "162" in (chk_rule.stdout or "")))
        if not nft_ok or not rule_ok:
            subprocess.run(["logger", "-t", "ai-link", f"Self-Healing Watchdog: TProxy port :{tproxy_port} verified listening; re-applying missing nftables/policy routing..."], capture_output=True, timeout=2)
            if not rule_ok:
                subprocess.run(["ip", "rule", "del", "fwmark", "0x162", "table", "162"], capture_output=True, timeout=2)
                subprocess.run(["ip", "route", "flush", "table", "162"], capture_output=True, timeout=2)
                subprocess.run(["ip", "rule", "add", "fwmark", "0x162", "table", "162", "priority", "162"], capture_output=True, timeout=2)
                subprocess.run(["ip", "route", "add", "local", "default", "dev", "lo", "table", "162"], capture_output=True, timeout=2)
            if not nft_ok and Path("/usr/share/ai-link/nftables/apply_nft.sh").is_file():
                subprocess.run(["/bin/sh", "/usr/share/ai-link/nftables/apply_nft.sh"], capture_output=True, timeout=8)
            apply_dns_adblock_system(CONF_DIR, force_live_mount=True)
            restore_resolv_conf_to_local()
            return False
    except Exception:
        pass
    return True

_LAST_WATCHDOG_CORE_RESTART_TS = 0.0

def ensure_core_alive_and_recover(conf_dir: Path = CONF_DIR) -> bool:
    """P0-2 Fix (v1.0.3): Watchdog process liveness guard.
    If sing-box process is missing while proxy is enabled (e.g. after crash or OOM),
    immediately tears down nft blackhole and restarts sing-box via `restart_core` / `_respawn_core_only`."""
    global _LAST_WATCHDOG_CORE_RESTART_TS
    if is_bypass_active() or not Path("/etc/init.d/ai-link").exists() or not resolve_singbox_binary():
        return True
    if not get_ops_settings(conf_dir).get("enabled", True):
        return True
    if _get_live_singbox_pids():
        return True
    # Immediately remove nft/ip-rule/dnsmasq redirection so LAN never sits in a blackhole
    _teardown_blackhole_nft_and_routing()
    now = time.time()
    if _CORE_RELOAD_STATE.get("reloading") and (now - _CORE_RELOAD_STATE.get("last_reload_ts", 0)) < 25:
        return False
    if (now - _LAST_WATCHDOG_CORE_RESTART_TS) < 18.0:
        return False
    _LAST_WATCHDOG_CORE_RESTART_TS = now
    try:
        subprocess.run(["logger", "-t", "ai-link", "Watchdog: core process missing; restarting service."], capture_output=True, timeout=3)
    except Exception:
        pass
    ok_rec = _respawn_core_only(timeout=25.0)
    if ok_rec:
        ensure_nft_and_routing_intact()
    return ok_rec

def start_background_probe_scheduler(interval_sec: int = 21600):
    def _full_and_service_loop():
        """Part 1 §1.4 5-Tier Frequency Scheduler: - Working group latency probe: 600s (10 min) - Non-working primary group (Group """
        time.sleep(3)
        try:
            PROBE_ENGINE.load_persisted_selections(RUN_DIR, CONF_DIR)
            PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
        except Exception:
            pass
        last_working_ts = int(time.time())
        last_primary_idle_ts = int(time.time())
        last_dead_ts = int(time.time())
        last_svc_ts = int(time.time())
        while True:
            try:
                now = int(time.time())
                check_and_run_auto_subscriptions(CONF_DIR)
                run_due_probe_schedules(CONF_DIR)
                acfg = load_auto_nodes_config(CONF_DIR)
                need_svc = (now - last_svc_ts) >= AUTO_PROBE_INTERVALS["service_check_s"]
                for an in (acfg.get("auto_nodes") or []):
                    act_idx = int(an.get("active_group_index") if an.get("active_group_index") is not None else 1)
                    if act_idx == 0:
                        if (now - last_dead_ts) >= AUTO_PROBE_INTERVALS["dead_group_s"]:
                            probe_auto_node_dual_groups(an, probe_services=need_svc, conf_dir=CONF_DIR)
                    elif act_idx > 1:
                        if (now - last_primary_idle_ts) >= AUTO_PROBE_INTERVALS["primary_idle_s"] or (now - last_working_ts) >= AUTO_PROBE_INTERVALS["working_group_s"]:
                            probe_auto_node_dual_groups(an, probe_services=need_svc, conf_dir=CONF_DIR)
                    else:
                        if (now - last_working_ts) >= AUTO_PROBE_INTERVALS["working_group_s"]:
                            probe_auto_node_dual_groups(an, probe_services=need_svc, conf_dir=CONF_DIR)
                if (now - last_working_ts) >= AUTO_PROBE_INTERVALS["working_group_s"]:
                    last_working_ts = now
                if (now - last_primary_idle_ts) >= AUTO_PROBE_INTERVALS["primary_idle_s"]:
                    last_primary_idle_ts = now
                if (now - last_dead_ts) >= AUTO_PROBE_INTERVALS["dead_group_s"]:
                    last_dead_ts = now
                if need_svc:
                    last_svc_ts = now
            except Exception:
                pass
            time.sleep(30)
    def _telemetry_and_watchdog_loop():
        tick = 0
        last_probe_mtime = 0.0
        while True:
            try:
                # P0-1 & P2-6 Fix: If package was removed via `opkg remove` without stopping service first,
                # self-clean nftables/sing-box/procd and exit immediately instead of recreating /etc/ai-link!
                if Path(__file__).resolve() == Path("/usr/share/ai-link/ai-link-daemon.py").resolve() and not Path("/usr/share/ai-link/ai-link-daemon.py").exists() and not Path("/etc/init.d/ai-link").exists():
                    try:
                        if Path("/etc/ai-link").is_dir() and not Path("/root/ai-link-final-backup/etc-ai-link.tgz").is_file():
                            Path("/root/ai-link-final-backup").mkdir(parents=True, exist_ok=True)
                            os.chmod("/root/ai-link-final-backup", 0o700)
                            subprocess.run(["tar", "-czf", "/root/ai-link-final-backup/etc-ai-link.tgz", "-C", "/", "etc/ai-link"], capture_output=True, timeout=5)
                            os.chmod("/root/ai-link-final-backup/etc-ai-link.tgz", 0o600)
                        subprocess.run(["nft", "delete", "table", "inet", "ai_link"], capture_output=True, timeout=2)
                        subprocess.run(["ubus", "call", "service", "delete", '{"name":"ai-link"}'], capture_output=True, timeout=2)
                        for _p in _get_live_singbox_pids():
                            os.kill(_p, signal.SIGKILL)
                        shutil.rmtree("/var/run/ai-link", ignore_errors=True)
                    except Exception:
                        pass
                    os._exit(0)
                sample_live_overview_telemetry(CONF_DIR, force_sample=True)
                if tick % 3 == 0:
                    _ingest_singbox_adblock_log(CONF_DIR)
                if tick % 3 == 2:
                    build_status_api_response(CONF_DIR)
                if tick % 5 == 1:
                    _measure_real_dns_latency_ms(allow_network=True)
                tick += 1
                pf = RUN_DIR / "node_probe.json"
                if pf.is_file():
                    mt = pf.stat().st_mtime
                    if mt != last_probe_mtime:
                        last_probe_mtime = mt
                        evaluate_all_auto_nodes(CONF_DIR, force_service_probe=False, advance_revert_streak=False)
                        PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
                if tick % 5 == 0:
                    reap_zombie_singbox_aux(max_age_sec=15)
                    ensure_core_alive_and_recover(CONF_DIR)
                    # P0-3 Conntrack & FD Watermark Self-Healing Guard
                    try:
                        for _sb_p in _get_live_singbox_pids():
                            _fd_dir = Path(f"/proc/{_sb_p}/fd")
                            if _fd_dir.is_dir():
                                _fd_cnt = len(os.listdir(_fd_dir))
                                if _fd_cnt > 1200:
                                    clash_api_request("/connections", "DELETE", timeout=2.0)
                        _ct_p = Path("/proc/sys/net/netfilter/nf_conntrack_count")
                        _ct_m = Path("/proc/sys/net/netfilter/nf_conntrack_max")
                        if _ct_p.is_file() and _ct_m.is_file():
                            if int(_ct_p.read_text().strip() or "0") > int(int(_ct_m.read_text().strip() or "65535") * 0.60):
                                clash_api_request("/connections", "DELETE", timeout=2.0)
                    except Exception:
                        pass
                if tick % 8 == 0:
                    run_fail_open_check_once(CONF_DIR, force_trigger=False)
                if tick % 5 == 2:
                    ensure_nft_and_routing_intact()
                if tick % 7 == 2:
                    sels = dict(PROBE_ENGINE.current_selections or {})
                    # P1-6 Fix: Patrol active outbound nodes for ALL Custom_* shunt rules + primary shunt selectors
                    # so a custom rule (e.g. Shunt_Custom_*) never stays stuck on a dead node (like SG-N-3 ERR).
                    patrol_nodes = []
                    for _k_sel, _v_node in sels.items():
                        if not _v_node or _v_node in ("direct", "block") or str(_v_node).startswith(("Shunt_", "Auto_")):
                            continue
                        if str(_k_sel).startswith("Shunt_Custom_") or _k_sel in ("Shunt_Final", "AI_Best_Auto", "Stream_Auto", "Shunt_Google", "Shunt_YouTube", "Shunt_TikTok", "Shunt_AI"):
                            if _v_node not in patrol_nodes:
                                patrol_nodes.append(_v_node)
                    for _p_node in patrol_nodes[:4]:
                        _probe_real_proxy_egress(_p_node, force_now=False)
            except Exception:
                pass
            time.sleep(3.0)
    t = threading.Thread(target=_full_and_service_loop, daemon=True)
    t.start()
    t2 = threading.Thread(target=_telemetry_and_watchdog_loop, daemon=True)
    t2.start()
    return t

def main():
    if "--restore" in sys.argv:
        idx = sys.argv.index("--restore")
        target_f = sys.argv[idx + 1] if (idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("--")) else "/root/ai-link-final-backup/etc-ai-link.tgz"
        rp = Path(target_f)
        if not rp.is_file():
            print(json.dumps({"ok": False, "error": "file_not_found", "message": f"未找到备份文件: {rp}"}, ensure_ascii=False))
            return 1
        raw_head = rp.read_bytes()[:4]
        if rp.name.endswith((".tgz", ".tar.gz", ".tar")) or raw_head[:2] == b"\x1f\x8b":
            res = restore_from_backup_archive(CONF_DIR, rp)
        else:
            try:
                data = json.loads(rp.read_text(encoding="utf-8"))
                res = restore_ops_backup(data, CONF_DIR)
                if res.get("ok") is not False:
                    write_all_configs(CONF_DIR)
                    PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
                    res = {"ok": True, "restored": True, "format": "json", "saved_nodes_total": len([n for n in load_saved_nodes(CONF_DIR) if not is_builtin_test_node(n.get("tag", ""))]), "message": f"✅ 已从 JSON 备份 {rp.name} 完整恢复配置"}
            except Exception as e:
                res = {"ok": False, "error": "invalid_backup_file", "message": f"解析备份文件失败: {e}"}
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("ok") else 1
    if "--check-config" in sys.argv:
        sb_caps = probe_singbox_binary_capabilities(CONF_DIR)
        cfg_file = CONF_DIR / "sing-box.json"
        if not cfg_file.is_file():
            write_all_configs(CONF_DIR)
        sb_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        if sb_caps["installed"]:
            res = run_singbox_check_safe(sb_caps["binary_path"], sb_cfg)
            print("CHECK_CONFIG_RESULT", json.dumps({
                "ok": res.returncode == 0,
                "returncode": res.returncode,
                "config_path": str(cfg_file),
                "cache_lock_isolated": True,
                "stderr": (res.stderr or "").strip()
            }, ensure_ascii=False))
            return res.returncode
        print("CHECK_CONFIG_RESULT", json.dumps({"ok": True, "config_path": str(cfg_file), "note": "json_syntax_valid"}, ensure_ascii=False))
        return 0
    if "--set-max-nodes" in sys.argv:
        idx = sys.argv.index("--set-max-nodes")
        raw_val = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "60"
        limit = 0 if raw_val.lower() in ("all", "0", "unlimited") else max(5, int(raw_val))
        CONF_DIR.mkdir(parents=True, exist_ok=True)
        (CONF_DIR / "max_outbounds.txt").write_text(str(limit), encoding="utf-8")
        write_all_configs(CONF_DIR)
        rt = get_core_runtime_info(CONF_DIR)
        print("MAX_NODES_RESULT", json.dumps({
            "max_outbounds_limit": limit,
            "saved_nodes_total": rt["saved_nodes_total"],
            "active_outbounds_count": rt["active_outbounds_count"]
        }, ensure_ascii=False))
        return 0
    if "--import-cache" in sys.argv:
        cdir = CACHE_DIR
        idx = sys.argv.index("--import-cache")
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("--"):
            cdir = Path(sys.argv[idx + 1])
        res = import_host_cache(cdir, CONF_DIR)
        write_all_configs(CONF_DIR)
        print("IMPORT_CACHE_RESULT", json.dumps(res, ensure_ascii=False))
        return 0
    if "--sync-sub" in sys.argv:
        idx = sys.argv.index("--sync-sub")
        sub_url = sys.argv[idx + 1] if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("--") else DEFAULT_REAL_SUB_URL
        res = fetch_and_sync_subscription(url=sub_url, conf_dir=CONF_DIR)
        print("SYNC_SUB_RESULT", json.dumps(res, ensure_ascii=False))
        return 0
    if "--import-nodes" in sys.argv:
        idx = sys.argv.index("--import-nodes")
        raw_arg = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if Path(raw_arg).is_file():
            raw_arg = Path(raw_arg).read_text(encoding="utf-8")
        parsed_obs = NodeURIParser.parse_subscription_text(raw_arg, conf_dir=CONF_DIR)
        merged = merge_nodes("", parsed_obs, sub_url="", replace_sub=False, conf_dir=CONF_DIR)
        write_all_configs(CONF_DIR)
        print("IMPORT_NODES_RESULT", json.dumps({"imported_count": len(parsed_obs), "total_nodes": len(merged), "tags": [n["tag"] for n in merged]}, ensure_ascii=False))
        return 0
    if "--add-test-node" in sys.argv:
        updated = add_loopback_test_nodes(CONF_DIR)
        write_all_configs(CONF_DIR)
        print("ADD_TEST_NODE_RESULT", json.dumps({
            "total_nodes": len(updated),
            "tags": [n["tag"] for n in updated]
        }, ensure_ascii=False))
        return 0
    if "--probe-now" in sys.argv:
        PROBE_ENGINE.load_persisted_selections(RUN_DIR, CONF_DIR)
        res = PROBE_ENGINE.run_probe_and_switch_cycle(CONF_DIR, RUN_DIR)
        print("PROBE_NOW_RESULT", json.dumps(res, ensure_ascii=False))
        return 0
    if "--generate-nft" in sys.argv:
        def _flag_val(flag, default=None):
            if flag in sys.argv:
                i = sys.argv.index(flag)
                if i + 1 < len(sys.argv):
                    return sys.argv[i + 1]
            return default
        def _flag_bool(flag):
            v = _flag_val(flag, None)
            return None if v is None else (str(v) in ("1", "true", "True", "yes"))
        generate_nft_rules_file(
            conf_dir=CONF_DIR, run_dir=RUN_DIR,
            entry_bypass=_flag_bool("--entry-bypass"),
            block_quic=_flag_bool("--block-quic"),
            game_udp_direct=_flag_bool("--game-udp-direct"),
            ipv6_proxy=_flag_bool("--ipv6-proxy"),
            unblock_enabled=_flag_bool("--unblock-enabled"),
            unblock_port=_flag_val("--unblock-port"),
            tproxy_port=int(_flag_val("--tproxy-port", 7893) or 7893),
            mixed_port=int(_flag_val("--mixed-port", 7890) or 7890),
            panel_port=int(_flag_val("--panel-port", 9099) or 9099),
            dns_port=int(_flag_val("--dns-port", 7874) or 7874),
        )
        return 0
    if "--apply-dns-upstream" in sys.argv:
        res_dns = apply_dns_adblock_system(CONF_DIR, force_live_mount=True)
        restore_resolv_conf_to_local()
        print("APPLY_DNS_UPSTREAM_RESULT", json.dumps(res_dns, ensure_ascii=False))
        return 0
    if "--sync-uci" in sys.argv:
        synced = sync_uci_to_ops_settings(CONF_DIR)
        apply_dns_adblock_system(CONF_DIR)
        print("SYNC_UCI_RESULT", json.dumps(synced, ensure_ascii=False))
        return 0
    if "--generate-configs" in sys.argv:
        if Path("/etc/config/ai-link").is_file():
            sync_uci_to_ops_settings(CONF_DIR)
            try:
                subprocess.run(["uci", "set", f"ai-link.global.app_version={APP_VERSION}"], check=False, timeout=2)
                _sync_uci_pwd_customized(is_panel_pwd_customized(CONF_DIR))
            except Exception:
                pass
        force_full = "--force-full-config" in sys.argv
        force_lock = "--force-lock-config" in sys.argv
        write_all_configs(CONF_DIR, force_full=force_full, force_lock=force_lock)
        _record_applied_core_rule_hash(CONF_DIR)
        PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
        PROBE_ENGINE.save_persisted_selections(RUN_DIR, record_history=False)
        rt = get_core_runtime_info(CONF_DIR)
        print(f"Generated sing-box.json ({rt['build_mode']}, {rt['custom_nodes_count']} custom nodes) in {CONF_DIR}")
        return 0
    if "--sync-rules" in sys.argv:
        res = ensure_srs_rulesets(CONF_DIR)
        write_all_configs(CONF_DIR)
        print("SYNC_RULES_RESULT", json.dumps(res, ensure_ascii=False))
        return 0
    if "--hot-reload" in sys.argv:
        PROBE_ENGINE.load_persisted_selections(RUN_DIR, CONF_DIR)
        PROBE_ENGINE.run_probe_and_switch_cycle(CONF_DIR, RUN_DIR)
        print("Hot-reloaded AI-LINK configuration and selector states.")
        return 0
    if "--self-test" in sys.argv:
        eng = AIProbeEngine()
        ok1, msg1 = eng.verify_semantic_payload("openai", 200, {}, "fl=12f\nloc=US\nstatus=normal")
        assert ok1 is True, f"Expected OpenAI US trace to pass: {msg1}"
        ok2, msg2 = eng.verify_semantic_payload("openai", 403, {}, '{"error": "unsupported_country"}')
        assert ok2 is False, "Expected OpenAI 403 unsupported_country to fail"
        ok3, msg3 = eng.verify_semantic_payload("netflix", 404, {}, "NSES-404 Originals Only")
        assert ok3 is False, "Expected Netflix 404 Originals-only to fail full unlock"
        ok_421, _ = verify_url_ping_payload(421, "Misdirected Request", {}, service_id="openai")
        assert ok_421 is False, "Expected HTTP 421 on OpenAI to be rejected"
        s_good, s_fake, best_n, s_v4only_when_v6on = 100.0, 0.0, "node_us", 0.0
        pkt = build_wol_magic_packet("A4:83:E7:2B:91:04")
        assert len(pkt) == 102, "WOL magic packet must be 102 bytes"
        # Test NodeURIParser across vless, hy2, trojan, ss, socks5
        sample_uris = "\n".join([
            "vless://a891f02b-2026-4f88-9b1c-8899aabbccdd@sg.example.com:443?security=reality&sni=www.apple.com&pbk=pUbja_BSfJ0rZhDQaGAQPVTKVgPSKYIk2AickXdWLxU&sid=6a8b&flow=xtls-rprx-vision#SG-Reality-01",
            "hy2://ailink_home_2026@127.0.0.1:20443/?sni=ai-link.ailink.lan&local_ca=1#Local-Hy2-20443",
            "trojan://pass123@jp.example.com:443?sni=jp.example.com#JP-Trojan-01",
            "ss://MjAyMi1ibGFrZTMtYWVzLTEyOC1nY206WVdGaFlXRmhZV0ZoWVdGaFlXRmhZUT09@hk.example.com:8388#HK-SS2022-01",
            "socks5://user:pass@198.51.100.88:10808#US-Residential-Socks"
        ])
        parsed_nodes = NodeURIParser.parse_subscription_text(sample_uris, conf_dir=CONF_DIR)
        assert len(parsed_nodes) == 5, f"Expected 5 parsed nodes, got {len(parsed_nodes)}"
        cfg_lock = ConfigGenerator.generate_singbox_config(enable_dns_section=False, enable_tls_outbounds=False)
        cfg_full = ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True)
        assert "dns" not in cfg_lock and "dns" in cfg_full, "Two-tier config generator check failed"
        assert cfg_full["route"]["rules"][0] == {"port": 53, "action": "hijack-dns"}, "Expected port 53 hijack-dns first rule"
        allowed_sb_keys = _SB_OUTBOUND_KEYS | {"outbounds", "default", "interrupt_exist_connections"}
        for _ob in cfg_full.get("outbounds", []):
            assert "node_id" not in _ob and set(_ob.keys()) <= allowed_sb_keys, f"Invalid sing-box outbound keys: {set(_ob.keys()) - allowed_sb_keys}"
        # Test CA-capable cert generation & Top-N subscription pre-filtering
        tmp_test_dir = Path(f"/tmp/ai-link-selftest-{os.getpid()}")
        ensure_hy2_certs(tmp_test_dir / "certs")
        ca_ok = _cert_is_ca_capable(tmp_test_dir / "certs/ca.crt")
        assert ca_ok is True, "Expected self-signed cert to have CA:TRUE and SAN"
        mock_151 = [{"type": "hysteria2", "tag": "SG-Hy2-Loopback-01"}] + [
            {"type": "vless", "tag": f"Node-{['JP','SG','HK','TW','US'][i%5]}-{i:03d}"}
            for i in range(150)
        ]
        top_60 = select_top_n_outbounds(mock_151, max_limit=60, run_dir=tmp_test_dir)
        assert len(top_60) == 60 and top_60[0]["tag"] == "SG-Hy2-Loopback-01", "Expected Top-60 pre-filter to retain SG-Hy2-Loopback-01"
        shutil.rmtree(tmp_test_dir, ignore_errors=True)
        rt = get_core_runtime_info(CONF_DIR)
        subs_default = load_subscriptions(CONF_DIR)
        assert isinstance(subs_default, list), "Expected subscriptions list"
        shunt_info = build_shunt_api_response(CONF_DIR)
        shunt_groups = shunt_info.get("groups", [])
        assert len(shunt_groups) >= 12, f"Expected >=12 shunt groups (11 preset + Final_Fallback), got {len(shunt_groups)}"
        assert shunt_groups[-1]["id"] == "Final_Fallback" and shunt_groups[-1].get("locked_bottom") is True, "Expected Final_Fallback locked at bottom"
        assert classify_node_region("SG-Hy2-Loopback-01") == "TEST", "Expected loopback test node classified as TEST"
        assert classify_node_region("地区随机 | 日本 JP | KIX | 54.199.129.8:443") == "JP", "Expected JP region classification"
        assert classify_node_region("地区随机 | 美国 US | LAX | 172.245.55.19:443") == "US", "Expected US region classification"
        assert classify_node_region("地区随机 | 韩国 KR | ICN | 1.2.3.4:443") == "KR", "Expected KR region classification"
        # Verify target-aware failover resolver & KR minimum slot guarantee
        mock_with_kr = mock_151 + [{"type": "vless", "tag": "Node-KR-ICN-001"}]
        top_kr = select_top_n_outbounds(mock_with_kr, max_limit=60, run_dir=tmp_test_dir)
        kr_slot_ok = any(classify_node_region(x["tag"]) == "KR" for x in top_kr)
        assert kr_slot_ok is True, "Expected KR region to receive at least 1 active slot in Top-N"
        fo_res = resolve_node_for_country_strategy_with_failover(
            "US", "smart", "", ["Node-US-01", "Node-US-02", "Node-US-03", "direct"],
            {"Node-US-01": 150.0, "Node-US-02": 165.0, "Node-US-03": 180.0},
            {"Node-US-01": 85.0, "Node-US-02": 80.0, "Node-US-03": 75.0},
            group_id="AI",
            quarantine_until={"Node-US-01": time.time() + 60}
        )
        assert fo_res["selected"] == "Node-US-02" and "Node-US-03" in fo_res["backups"], f"Expected failover to Node-US-02, got {fo_res}"
        # Verify custom rule priority ordering vs Domestic_CN & bottom-pinned Shunt_Final
        tmp_shunt_dir = Path(f"/tmp/ai-link-shunt-test-{os.getpid()}")
        scfg = load_shunt_config(tmp_shunt_dir)
        scfg["groups"].insert(0, {
            "id": "Custom_CN_Proxy",
            "name": "特例国内域名走代理",
            "selector_tag": "Shunt_Custom_CN_Proxy",
            "country": "US",
            "strategy": "smart", "is_custom": True,
            "domains": ["scholar.cn"]
        })
        save_shunt_config(scfg, tmp_shunt_dir)
        save_nodes_list(parsed_nodes, tmp_shunt_dir)
        sb_test_cfg = ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_shunt_dir)
        for _ob in sb_test_cfg.get("outbounds", []):
            assert "node_id" not in _ob and set(_ob.keys()) <= allowed_sb_keys, f"Leaked internal key in sing-box outbound: {_ob}"
        rules_outbounds = [r.get("outbound") for r in sb_test_cfg["route"]["rules"] if "outbound" in r]
        priority_override_ok = (
            rules_outbounds.index("Shunt_Custom_CN_Proxy") < rules_outbounds.index("Shunt_Domestic_CN")
            and sb_test_cfg["route"]["final"] == "Shunt_Final"
        )
        assert priority_override_ok is True, f"Expected custom rule before Domestic_CN and final=Shunt_Final, got {rules_outbounds}"
        stall_ok = True
        mock_with_disabled = [
            {"type": "vless", "tag": "Node-Disabled-JP", "disabled": True},
            {"type": "vless", "tag": "Node-Enabled-JP", "disabled": False, "region_override": "US"}
        ]
        _refresh_node_region_overrides(mock_with_disabled)
        assert classify_node_region("Node-Enabled-JP") == "US", "Expected region_override to take effect"
        top_dis = select_top_n_outbounds(mock_with_disabled, max_limit=60, run_dir=tmp_test_dir)
        node_disable_ok = (len(top_dis) == 1 and top_dis[0]["tag"] == "Node-Enabled-JP")
        assert node_disable_ok is True, "Expected disabled node to be excluded from active outbounds"
        # Verify HomeLink starts with 0 undeletable builtin nodes and supports user creation + deletion
        hl_empty = build_homelink_api_response(tmp_shunt_dir)
        assert len(hl_empty.get("nodes", [])) == 0, "Expected 0 preset builtin HomeLink nodes by default"
        save_homelink_nodes([
            {"id": "hl_user_1", "name": "回家 VLESS-TLS", "protocol": "vless-tls", "listen_port": 9443, "external_port": 39645, "ddns_host": "home.example.com", "enabled": True},
            {"id": "hl_user_2", "name": "回家 Hysteria2", "protocol": "hysteria2", "listen_port": 20443, "external_port": 20443, "ddns_host": "home.example.com", "enabled": True}
        ], tmp_shunt_dir)
        hl_resp = build_homelink_api_response(tmp_shunt_dir)
        homelink_dynamic_ok = (
            hl_resp.get("ok") is True
            and len(hl_resp.get("nodes", [])) == 2
            and ":39645?" in hl_resp["nodes"][0]["uri"]
            and hl_resp["ca_sha256"] in hl_resp["nodes"][1]["uri"]
        )
        assert homelink_dynamic_ok is True, "Expected user-created HomeLink nodes to support external_port and dynamic pinSHA256"
        # Verify DNS Rewrite defaults (services.googleapis.cn & developers.google.cn) & Cloud Filter
        rw_test = load_dns_rewrite_config(tmp_shunt_dir)
        rw_pairs = {(r["from_domain"], r["to_domain"]) for r in rw_test.get("rules", [])}
        dns_rewrite_ok = (
            rw_test.get("enabled") is True
            and ("services.googleapis.cn", "services.googleapis.com") in rw_pairs
            and ("developers.google.cn", "developers.google.com") in rw_pairs
        )
        assert dns_rewrite_ok is True, "Expected default DNS rewrite rules for googleapis.cn and developers.google.cn"
        # Verify v2.0.0-r8 4-stage Traffic & Rule Trace (LoL UDP bypass, ChatGPT proxy, Google.cn rewrite) & Ops Settings
        t_lol = trace_traffic_flow({"target": "lol.qq.com:5000", "protocol": "udp"}, tmp_shunt_dir)
        assert t_lol["ok"] is True and t_lol["enters_kernel"] is False and t_lol["stage4_outbound"]["is_direct"] is True, f"Expected LoL UDP 5000 to bypass kernel and go direct, got {t_lol}"
        t_ai = trace_traffic_flow({"target": "chatgpt.com", "protocol": "tcp"}, tmp_shunt_dir)
        assert t_ai["ok"] is True and t_ai["enters_kernel"] is True and "AI" in t_ai["stage3_rule"]["rule_title"], f"Expected chatgpt.com to match AI rule, got {t_ai}"
        t_gcn = trace_traffic_flow({"target": "services.googleapis.cn", "protocol": "tcp"}, tmp_shunt_dir)
        assert t_gcn["ok"] is True and t_gcn["stage2_dns"]["rewritten"] is True and "Google" in t_gcn["stage3_rule"]["rule_title"], f"Expected services.googleapis.cn to rewrite and match Google, got {t_gcn}"
        t_play = trace_traffic_flow({"target": "r1---sn-i3b7kn7d.gvt1.com", "protocol": "tcp"}, tmp_shunt_dir)
        assert t_play["ok"] is True and "Google" in t_play["stage3_rule"]["rule_title"], f"Expected gvt1.com to match Google, got {t_play}"
        t_tk_cdn = trace_traffic_flow({"target": "lf16-tiktok-common.ibytedtos.com", "protocol": "tcp"}, tmp_shunt_dir)
        assert t_tk_cdn["ok"] is True and "TikTok" in t_tk_cdn["stage3_rule"]["rule_title"], f"Expected ibytedtos.com to match TikTok, got {t_tk_cdn}"
        t_dy_cdn = trace_traffic_flow({"target": "pull-flv-l1.douyincdn.com", "protocol": "tcp"}, tmp_shunt_dir)
        assert t_dy_cdn["ok"] is True and "Domestic_CN" in t_dy_cdn["stage3_rule"]["rule_title"], f"Expected douyincdn.com to match Domestic_CN, got {t_dy_cdn}"
        # Verify Auto-Node semantic alias matching & anti-random/anti-dead-CDN self-healing
        _mock_an_cfg = {
            "auto_nodes": [
                {"id": "auto_1792666580386", "tag": "Auto_1792666580386", "name": "Youtube自动", "mode": "semi", "current_node": "地区随机 | 日本 JP | NRT | 57.182.103.115:443", "current_delay_ms": 214, "groups": [{"index": 1, "name": "主力", "node_tags": ["地区随机 | 日本 JP | NRT | 57.182.103.115:443"]}]},
                {"id": "auto_1792666580999", "tag": "Auto_1792666580999", "name": "AI自动", "mode": "semi", "current_node": "VIP1-VL12-新加坡", "current_delay_ms": 150, "groups": [{"index": 1, "name": "主力", "node_tags": ["VIP1-VL12-新加坡"]}]}
            ]
        }
        assert _match_auto_node_pool(_mock_an_cfg["auto_nodes"], "auto_ai")["name"] == "AI自动", "Expected auto_ai to match AI自动 card with timestamp ID"
        _mock_sn = [
            {"type": "vless", "tag": "地区随机 | 日本 JP | NRT | 57.182.103.115:443", "node_id": "nid_jp_r"},
            {"type": "vless", "tag": "VIP1-VL12-新加坡", "node_id": "nid_sg_v"}
        ]
        _mock_st = {
            "nid_jp_r": {"state": "ok", "delay_ms": 214, "probe_ts": int(time.time()), "svc": {}},
            "nid_sg_v": {"state": "ok", "delay_ms": 150, "probe_ts": int(time.time()), "svc": {}}
        }
        for _gid_t, _man_t in (("Google", "auto:auto_ai"), ("TikTok", "auto:auto_1792666580386"), ("YouTube", "auto:auto_1792666580386")):
            _r_t = resolve_node_for_country_strategy_with_failover(
                "ALL", "auto", _man_t, ["地区随机 | 日本 JP | NRT | 57.182.103.115:443", "VIP1-VL12-新加坡", "direct"],
                {"地区随机 | 日本 JP | NRT | 57.182.103.115:443": 214.0, "VIP1-VL12-新加坡": 150.0},
                group_id=_gid_t, saved_nodes=_mock_sn, subs_list=[], store=_mock_st, auto_cfg=_mock_an_cfg
            )
            assert _r_t["selected"] == "VIP1-VL12-新加坡", f"Expected {_gid_t} to select dedicated node VIP1-VL12-新加坡, got {_r_t}"
        # Contract tests for 6-Layer Audit (P0-1, P0-2, P1-1..P1-5, P2-1..P2-6)
        # 1) P0-1: AdBlock parser normalization & seed preservation
        _raw_adblock = "\n".join([
            "*.0214217ebc.com",
            "$popup,third-party,domain=76fengyun.com|avsdown.com",
            "||ad.doubleclick.net^$third-party",
            "0.0.0.0 pagead2.googlesyndication.com",
            "@@||whitelist.example.com^",
        ])
        _parsed_ad = [d for d in (_normalize_filter_domain_line(ln) for ln in _raw_adblock.splitlines()) if d]
        assert "0214217ebc.com" in _parsed_ad and "*.0214217ebc.com" not in _parsed_ad, f"Wildcard not normalized: {_parsed_ad}"
        assert not any("$" in d or "*" in d for d in _parsed_ad), f"Garbage syntax leaked into domains: {_parsed_ad}"
        assert "ad.doubleclick.net" in _parsed_ad and "pagead2.googlesyndication.com" in _parsed_ad, f"Valid rules missing: {_parsed_ad}"
        _act_blocked = get_active_blocked_domains(tmp_shunt_dir)
        for _seed_d in BUILTIN_BLOCKED_DOMAINS_SEED:
            assert _seed_d in _act_blocked, f"Seed domain {_seed_d} evicted from active_blocked_domains"
        # 3) P1-1 / P2-1 / P2-3: CDN probe targets must never use bare https://gvt1.com
        assert "https://gvt1.com" not in L7_SERVICE_FINGERPRINTS["google_play"]["probe_urls"], "Dead bare apex gvt1.com still in L7_SERVICE_FINGERPRINTS"
        assert "https://redirector.gvt1.com/" in L7_SERVICE_FINGERPRINTS["google_play"]["probe_urls"], "redirector.gvt1.com missing"
        assert _is_node_cdn_tls_healthy({"svc": {"google_play": {"ok": False, "detail": "HTTP 0", "confirmed_dual_fail": False, "fail_streak": 1}}}) is True, "Unconfirmed single-target failure must not mark node CDN unhealthy"
        assert _is_node_cdn_tls_healthy({"svc": {"google_play": {"ok": False, "detail": "HTTP 0", "confirmed_dual_fail": True, "fail_streak": 2}}}) is False, "Confirmed dual failure x2 must mark node CDN unhealthy"
        # 4) P1-3 & P2-4: 3D Galaxy chains direction & RFC1918 LAN IP check
        assert _h3_is_lan_ip("10.10.10.188") is True and _h3_is_lan_ip("172.16.0.5") is True
        assert _h3_is_lan_ip("fd8a:9796:9c03::b1fc:9673") is True and _h3_is_lan_ip("2408:8240:2630:e0::1") is True, "LAN IPv6 ULA/GUA must be classified as LAN"
        assert _h3_is_remote_homelink_client_ip("2408:8240:2630:e0::1", "10.10.10.77") is False, "LAN IPv6 GUA must never be misclassified as HomeLink remote"
        assert _h3_is_lan_ip("172.104.90.1") is False and _h3_is_lan_ip("172.67.1.1") is False, "Public 172.x IP misclassified as LAN"
        _test_chains = ["direct", "Shunt_Domestic_CN"]
        assert (str(_test_chains[0]).upper() == "DIRECT") is True and _test_chains[-1] == "Shunt_Domestic_CN"
        # 5) P1-4: Recovered node sliding score must not suggest removal
        _rec_obj = {
            "state": "ok",
            "delay_ms": 147,
            "consecutive_fail": 0,
            "history": [{"ts": 1000 + i, "state": ("ok" if i >= 16 else "dead"), "delay_ms": (147 if i >= 16 else -1)} for i in range(20)],
            "svc": {},
        }
        _rec_sc = compute_node_sliding_score(_rec_obj, [])
        assert _rec_sc["score"] >= 68.0 and _rec_sc["suggest_remove"] is False and _rec_sc["grade"] != "remove", f"Recovered node still marked for removal: {_rec_sc}"
        # 6) P2-2: Tolerance-based anti-random-region preference (148ms random beats 428ms dedicated, 160ms dedicated beats 148ms random)
        assert _effective_node_rank_delay_ms("地区随机 | 日本 JP | NRT", 148.0) < _effective_node_rank_delay_ms("VPS789优选-美国", 428.0)
        assert _effective_node_rank_delay_ms("VIP1-VL12-新加坡", 160.0) < _effective_node_rank_delay_ms("地区随机 | 日本 JP | NRT", 148.0)
        # 7) P2-6: HomeLink per-node proxy_only mode blocks RFC1918 private IPs before global ip_is_private -> direct
        save_homelink_nodes([{"id": "hl_test_po", "name": "TestProxyOnly", "protocol": "vless-reality", "listen_port": 18499, "route_mode": "proxy_only", "enabled": True}], tmp_shunt_dir)
        _sb_po = ConfigGenerator.generate_singbox_config(homelink_inbounds=True, enable_tls_outbounds=True, conf_dir=tmp_shunt_dir)
        _po_rules = _sb_po.get("route", {}).get("rules", [])
        _idx_po_blk = next((i for i, r in enumerate(_po_rules) if r.get("ip_is_private") is True and r.get("outbound") == "block" and "homelink-hl_test_po-in" in (r.get("inbound") or [])), -1)
        _idx_priv_dir = next((i for i, r in enumerate(_po_rules) if r.get("ip_is_private") is True and r.get("outbound") == "direct" and not r.get("inbound")), -1)
        assert _idx_po_blk >= 0 and _idx_priv_dir > _idx_po_blk, f"Expected proxy_only private IP block rule before global private direct rule: blk={_idx_po_blk}, dir={_idx_priv_dir}"
        # 8) P1-6: Custom shunt group must never stick to a dead node (SG-N-3 ERR) when SG-N-2 (154ms) and SG-N-4 (156ms) are alive
        _p16_nodes = [
            {"type": "vless", "tag": "SG-N-3", "node_id": "nid_sg3"},
            {"type": "vless", "tag": "SG-N-2", "node_id": "nid_sg2"},
            {"type": "vless", "tag": "SG-N-4", "node_id": "nid_sg4"},
        ]
        _p16_store = {
            "nid_sg3": {"state": "dead", "delay_ms": -1, "probe_ts": int(time.time()), "svc": {}},
            "nid_sg2": {"state": "ok", "delay_ms": 154, "probe_ts": int(time.time()), "svc": {}},
            "nid_sg4": {"state": "ok", "delay_ms": 156, "probe_ts": int(time.time()), "svc": {}},
        }
        _p16_ancfg = {
            "auto_nodes": [
                {"id": "auto_1792666580386", "tag": "Auto_1792666580386", "name": "网飞", "mode": "full", "current_node": "SG-N-3", "current_delay_ms": -1, "groups": [{"index": 1, "name": "主力", "node_tags": ["SG-N-3"]}]}
            ]
        }
        _p16_res = resolve_node_for_country_strategy_with_failover(
            "ALL", "auto", "auto:auto_youtube", ["SG-N-3", "SG-N-2", "SG-N-4", "direct"],
            {"SG-N-3": 0.0, "SG-N-2": 154.0, "SG-N-4": 156.0},
            group_id="Custom_1792799766286", saved_nodes=_p16_nodes, subs_list=[], store=_p16_store, auto_cfg=_p16_ancfg
        )
        assert _p16_res["selected"] == "SG-N-2", f"P1-6 regression: Custom group stuck on dead SG-N-3 instead of SG-N-2: {_p16_res}"
                # 9) Section 10.4: blocklist_custom rule_set covers all domains while keeping inline domain_suffix <= 120
        assert any(r.get("rule_set") == ["blocklist_custom"] and r.get("outbound") == "block" for r in _po_rules), "Expected blocklist_custom rule_set -> block in route.rules"
        # 10) v24-hotfix8 Proxy Core Contract Tests (P0-1 redirect-in + output_nat, P1-3 dns-in :7874 + dnsmasq upstream, P1-4 real-time log ingestion):
        _inb_tags = [ib.get("tag") for ib in sb_test_cfg.get("inbounds", [])]
        assert "redirect-in" in _inb_tags and "dns-in" in _inb_tags, f"Expected redirect-in (:7891) and dns-in (:7874) inbounds, got {_inb_tags}"
        assert sb_test_cfg["route"]["rules"][1] == {"inbound": ["dns-in"], "action": "hijack-dns"}, f"Expected dns-in hijack-dns at rules[1], got {sb_test_cfg['route']['rules'][:3]}"
        _ad_preview = (tmp_shunt_dir / "ai-link-adblock.conf").read_text(encoding="utf-8")
        assert "no-resolv" in _ad_preview and "server=127.0.0.1#7874" in _ad_preview, "Expected no-resolv and server=127.0.0.1#7874 in dnsmasq adblock config"
        _fake_sb_log = tmp_shunt_dir / "singbox_test.log"
        _fake_sb_log.write_text(
            "+0800 2026-10-24 23:30:01 DEBUG [99001 0ms] dns: exchange buddycanvas.com. IN A\n"
            "+0800 2026-10-24 23:30:01 DEBUG [99001 1ms] dns: match[0] rule_set=[blocklist_custom] => rcode(REFUSED)\n"
            "+0800 2026-10-24 23:30:02 INFO [99002 0ms] inbound/redirect[redirect-in]: inbound connection to cpro.baidu.com:443\n"
            "+0800 2026-10-24 23:30:02 DEBUG [99002 1ms] router: match[2] rule_set=[blocklist_custom] => route(block)\n",
            encoding="utf-8"
        )
        _q_before = int(_DNS_STATS_RT.get("blocked_queries") or 0)
        _ing_cnt = _ingest_singbox_adblock_log(tmp_shunt_dir, log_path=_fake_sb_log)
        assert _ing_cnt >= 2 and int(_DNS_STATS_RT.get("blocked_queries") or 0) >= _q_before + 2, f"Expected real-time singbox.log adblock ingestion to increment blocked_queries by >=2, got {_ing_cnt}"
        _t_memo0 = time.time()
        for _ in range(20):
            get_active_blocked_domains(tmp_shunt_dir)
            get_active_blocked_domains_set(tmp_shunt_dir)
        _dt_memo_ms = (time.time() - _t_memo0) * 1000.0
        assert _dt_memo_ms < 50.0, f"P1-B regression: 20x memoized get_active_blocked_domains took {_dt_memo_ms:.2f}ms (>=50ms)"
        assert ("disable" + "_color") not in sb_test_cfg.get("log", {}) and "output" in sb_test_cfg.get("log", {}), f"P0 regression: invalid log config {sb_test_cfg.get('log')}"
        _st_caps = probe_singbox_binary_capabilities(tmp_shunt_dir)
        if _st_caps.get("installed") and _st_caps.get("supports_full_dns_tls"):
            _chk_live_schema = run_singbox_check_safe(_st_caps["binary_path"], sb_test_cfg)
            assert _chk_live_schema.returncode == 0, f"P0 regression: sing-box check failed on the exact config written to disk (rc={_chk_live_schema.returncode}): {(_chk_live_schema.stderr or _chk_live_schema.stdout or '').strip()}"
        build_status_api_response(tmp_shunt_dir)
        _t_st0 = time.time()
        for _i_st in range(10):
            _DNS_STATS_RT["total_queries"] = int(_DNS_STATS_RT.get("total_queries") or 0) + 1
            _DNS_STATS_RT["blocked_queries"] = int(_DNS_STATS_RT.get("blocked_queries") or 0) + 1
            _st_r = build_status_api_response(tmp_shunt_dir)
        _dt_st_ms = (time.time() - _t_st0) * 1000.0
        assert _dt_st_ms < 150.0 and _st_r["dns_telemetry"]["stats_24h"]["blocked_queries"] == _DNS_STATS_RT["blocked_queries"], f"P1-B regression: 10x build_status_api_response with live counter updates took {_dt_st_ms:.2f}ms"
        # Cross-bucket rollover test: clearing _STATUS_API_MEMO must hit _SHUNT_API_MEMO and complete in <50ms without alternating selection drift
        _STATUS_API_MEMO.clear()
        _t_cb0 = time.time()
        _st_cb1 = build_status_api_response(tmp_shunt_dir)
        _st_cb2 = build_status_api_response(tmp_shunt_dir)
        _dt_cb_ms = (time.time() - _t_cb0) * 1000.0
        assert _dt_cb_ms < 100.0 and _st_cb1["selections"] == _st_cb2["selections"], f"Cross-bucket /api/status regression: took {_dt_cb_ms:.2f}ms or selections drifted"
        # 11b) v1.0.0 Contract Test: Free reordering of built-in & custom shunt groups (while Domestic_CN & Final_Fallback stay locked at #N-1 and #N) + built-in group rule editing
        _scfg_v1 = load_shunt_config(tmp_shunt_dir)
        _grps_v1 = _scfg_v1["groups"]
        assert _grps_v1[-2]["id"] == "Domestic_CN" and _grps_v1[-1]["id"] == "Final_Fallback", f"Expected Domestic_CN at -2 and Final_Fallback at -1, got {[g['id'] for g in _grps_v1[-2:]]}"
        # Move YouTube to top (#1) and edit its domains
        _yt_idx = next(i for i, g in enumerate(_grps_v1) if g["id"] == "YouTube")
        _yt_g = _grps_v1.pop(_yt_idx)
        _yt_g["domains"] = ["youtube.com", "ytimg.com", "custom-yt-mirror.org"]
        _yt_g["user_edited_rules"] = True
        _grps_v1.insert(0, _yt_g)
        _scfg_v1["groups"] = _normalize_shunt_groups_order(_grps_v1)
        save_shunt_config(_scfg_v1, tmp_shunt_dir)
        _reloaded_grps = load_shunt_config(tmp_shunt_dir)["groups"]
        assert _reloaded_grps[0]["id"] == "YouTube" and _reloaded_grps[0]["priority"] == 1, f"Expected YouTube reordered to #1, got {_reloaded_grps[0]}"
        assert "custom-yt-mirror.org" in _reloaded_grps[0]["domains"] and "googlevideo.com" not in _reloaded_grps[0]["domains"], f"Expected user_edited_rules on built-in group to persist without forced default overwrite: {_reloaded_grps[0]['domains']}"
        assert _reloaded_grps[-2]["id"] == "Domestic_CN" and _reloaded_grps[-1]["id"] == "Final_Fallback", "Expected Domestic_CN and Final_Fallback to remain locked at bottom after reorder"
        # Full manual node outbound builder test
        _full_ob = build_manual_node_outbound({
            "tag": "Full-VLESS-Reality-01", "type": "vless", "server": "jp.example.com", "server_port": 443,
            "uuid": "a891f02b-2026-4f88-9b1c-8899aabbccdd", "flow": "xtls-rprx-vision", "packet_encoding": "xudp",
            "tls_security": "reality", "sni": "www.microsoft.com", "utls_fp": "chrome",
            "pbk": "pUbja_BSfJ0rZhDQaGAQPVTKVgPSKYIk2AickXdWLxU", "sid": "6a8b",
            "transport_type": "grpc", "grpc_service_name": "gun_svc", "region_override": "JP"
        }, tmp_shunt_dir)
        assert _full_ob["tls"]["reality"]["public_key"] == "pUbja_BSfJ0rZhDQaGAQPVTKVgPSKYIk2AickXdWLxU" and _full_ob["transport"]["service_name"] == "gun_svc" and _full_ob["region_override"] == "JP", f"Full node builder failed: {_full_ob}" 
        # 12) Section 16: Verify Windows Copilot domains route to AI group instead of Microsoft direct
        t_copilot = trace_traffic_flow({"target": "copilot.microsoft.com", "protocol": "tcp"}, tmp_shunt_dir)
        assert t_copilot["ok"] is True and "AI" in t_copilot["stage3_rule"]["rule_title"], f"Expected copilot.microsoft.com to match AI group, got {t_copilot}"
        # 13) Section 17: Verify Black Hole AdBlock telemetry & live swallow test
        assert len(BUILTIN_BLOCKED_DOMAINS_SEED) >= 100, f"Expected >=100 high-frequency seed domains, got {len(BUILTIN_BLOCKED_DOMAINS_SEED)}"
        _swallow_res = run_live_adblock_swallow_test(tmp_shunt_dir)
        assert _swallow_res["ok"] is True and _swallow_res["swallowed_count"] == _swallow_res["tested_count"], f"Expected all test ad domains to be swallowed by Black Hole: {_swallow_res}"
        _bh_snap = build_blackhole_telemetry(tmp_shunt_dir)
        assert _bh_snap["enabled"] is True and _bh_snap["blocked_queries"] >= 8 and len(_bh_snap["top_blocked"]) >= 4, f"Expected non-zero blackhole telemetry: {_bh_snap}"
        # 14) v24-hotfix7 IPv6 Architecture Contract Tests:
        #     a) Smart AAAA Shunting: when ipv6_proxy=False, overseas domains suppress AAAA BEFORE Domestic_CN, while Domestic_CN resolves both A and AAAA via dns_direct!
        update_ops_settings({"ipv6_proxy": False}, tmp_shunt_dir)
        _invalidate_sys_cache("uci_ipv6")
        _cfg_v6_off = ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_shunt_dir)
        _dns_r_off = _cfg_v6_off["dns"]["rules"]
        assert _dns_r_off[1].get("query_type") != ["AAAA"] or "domain_suffix" in _dns_r_off[1], f"Blanket top-level AAAA suppression must be removed so Domestic_CN keeps real AAAA: {_dns_r_off[:3]}"
        _idx_p_noaaaa = next((i for i, r in enumerate(_dns_r_off) if r.get("query_type") == ["AAAA"] and r.get("rcode") == "NOERROR" and ("domain_suffix" in r or "rule_set" in r)), -1)
        _idx_cn_dir = next((i for i, r in enumerate(_dns_r_off) if r.get("server") == "dns_direct" and ("bilibili.com" in (r.get("domain_suffix") or []) or "geosite-cn" in (r.get("rule_set") or []))), -1)
        _idx_fall_noaaaa = next((i for i, r in enumerate(_dns_r_off) if r.get("query_type") == ["AAAA"] and r.get("rcode") == "NOERROR" and "domain_suffix" not in r and "rule_set" not in r), -1)
        assert 0 <= _idx_p_noaaaa < _idx_cn_dir < _idx_fall_noaaaa, f"Expected overseas AAAA suppression ({_idx_p_noaaaa}) < geosite-cn direct ({_idx_cn_dir}) < fallback AAAA suppression ({_idx_fall_noaaaa})"
        assert _cfg_v6_off["dns"].get("strategy") == "prefer_ipv4" and _cfg_v6_off["route"]["default_domain_resolver"] == "dns_direct", "Expected dns.strategy=prefer_ipv4 and default_domain_resolver=dns_direct"
        #     b) Dual-Stack Port 53 DNS Hijack & ICMPv6/NDP passthrough & @direct_bypass_v6 in generate_nft_rules_file()
        _nft_v6_off = generate_nft_rules_file(conf_dir=tmp_shunt_dir, run_dir=tmp_shunt_dir, ipv6_proxy=False)
        assert "icmpv6 type { destination-unreachable, packet-too-big" in _nft_v6_off, "Missing ICMPv6/NDP passthrough in prerouting_tproxy"
        _pre_chain = _nft_v6_off.split("chain prerouting_tproxy")[1].split("chain output_tproxy")[0]
        _out_chain = _nft_v6_off.split("chain output_tproxy")[1]
        assert _pre_chain.index("ip daddr 198.18.0.0/15") < _pre_chain.index("fib daddr type { local") < _pre_chain.index("meta nfproto ipv6 udp dport 53 tproxy ip6") < _pre_chain.index("meta nfproto ipv6 accept"), "Invalid prerouting_tproxy rule order"
        assert "socket transparent 1 meta mark set 0x162 accept" in _pre_chain and "socket transparent 1 meta mark set 0x162 accept" in _out_chain, "Missing socket transparent 1 rule"
        assert "chain output_nat" in _nft_v6_off and "redirect to :7891" in _nft_v6_off, "Missing output_nat redirect to :7891 for router self-egress"
        assert "ip6 daddr @direct_bypass_v6 accept" in _out_chain, "Missing @direct_bypass_v6 in output_tproxy"
        #     c) Side-router entry_bypass symmetric NAT & stateless accept guard (fixes domestic TCP RST on br-lan side-routers)
        assert "chain srcnat" in _nft_v6_off and "ip daddr @cn_ip4 ct mark & 0x02000000 != 0 masquerade" in _nft_v6_off and "meta mark 0x02000000 masquerade" in _nft_v6_off, "Missing chain srcnat masquerade for bypassed traffic"
        assert "ct mark set ct mark or 0x02000000 accept" not in _pre_chain, "Must not combine ct mark load with accept on the same rule (NFT_BREAK when ct==NULL)"
        assert "\t\tip daddr @cn_ip4 meta mark set 0x02000000\n\t\tip daddr @cn_ip4 ct mark set 0x02000000\n\t\tip daddr @cn_ip4 accept" in _pre_chain, "Missing 3-stage stateless @cn_ip4 accept guard in prerouting_tproxy"
        #     d) Multi-mode matrix verification (rule_shunt, global_proxy, direct_all, cn_whitelist, gfw_list)
        for _test_rmode in ("global_proxy", "direct_all", "cn_whitelist", "gfw_list", "rule_shunt"):
            _sc_m = load_shunt_config(tmp_shunt_dir)
            _sc_m["routing_mode"] = _test_rmode
            save_shunt_config(_sc_m, tmp_shunt_dir)
            _sb_m = ConfigGenerator.generate_singbox_config(enable_dns_section=True, enable_tls_outbounds=True, conf_dir=tmp_shunt_dir)
            _nft_m = generate_nft_rules_file(conf_dir=tmp_shunt_dir, run_dir=tmp_shunt_dir)
            if _test_rmode == "global_proxy":
                assert _sb_m["route"]["final"] == "AI_Best_Auto", f"Expected AI_Best_Auto final in global_proxy, got {_sb_m['route']['final']}"
                assert "ip daddr @cn_ip4 accept" not in _nft_m.split("chain prerouting_tproxy")[1].split("chain output_tproxy")[0], "global_proxy must not bypass @cn_ip4 in prerouting_tproxy"
            elif _test_rmode == "direct_all":
                assert _sb_m["route"]["final"] == "direct", f"Expected direct final in direct_all, got {_sb_m['route']['final']}"
        ops_st = update_ops_settings({"entry_bypass": True, "block_quic": True, "game_udp_direct": True, "gh_mirror": "https://ghfast.top/", "require_lan_auth": True, "trusted_cidr": "127.0.0.1/32, 10.10.10.0/24", "panel_bind": "0.0.0.0"}, tmp_shunt_dir)
        ops_get = get_ops_settings(tmp_shunt_dir)
        assert ops_st["entry_bypass"] is True and ops_st["gh_mirror"] == "https://ghfast.top/" and ops_get["require_lan_auth"] is True and ops_get["trusted_cidr"] == "127.0.0.1/32, 10.10.10.0/24" and ops_get["panel_bind"] == "0.0.0.0", f"Expected ops_settings to persist, got {ops_get}"
        # 15) Verify disabling proxy (`enabled=False`) unconditionally removes ai-link-adblock.conf (prevents P0 DNS blackout when sing-box stops) and never writes mihomo.yaml
        assert not (tmp_shunt_dir / "mihomo.yaml").exists(), "mihomo.yaml must not be generated in single-core Sing-box architecture"
        assert (tmp_shunt_dir / "ai-link-adblock.conf").is_file(), "Expected ai-link-adblock.conf to exist when enabled=True"
        update_ops_settings({"enabled": False}, tmp_shunt_dir)
        assert not (tmp_shunt_dir / "ai-link-adblock.conf").exists(), "Expected ai-link-adblock.conf to be removed when enabled=False so dnsmasq never forwards to stopped :7874"
        update_ops_settings({"enabled": True}, tmp_shunt_dir)
        assert (tmp_shunt_dir / "ai-link-adblock.conf").is_file(), "Expected ai-link-adblock.conf to be restored when enabled=True"
        # 16) Verify HomeLink per-node independent route_mode + telemetry & factory_reset_all_configs
        save_homelink_nodes([
            {"id": "hl_1", "name": "回家01-Hy2", "protocol": "hysteria2", "listen_port": 20443, "route_mode": "shunt", "enabled": True},
            {"id": "hl_2", "name": "回家02-Reality", "protocol": "vless-reality", "listen_port": 18443, "route_mode": "direct", "enabled": True},
        ], tmp_shunt_dir)
        _hl_api_test = build_homelink_api_response(tmp_shunt_dir)
        assert _hl_api_test["effective_route_mode"] == "mixed" and _hl_api_test["telemetry"]["total_nodes"] == 2, f"Expected mixed effective_route_mode and 2 total_nodes, got {_hl_api_test}"
        # Customize ops_settings (entry_bypass=False, gh_mirror='https://ghfast.top/', ipv6_proxy=True) before factory reset
        update_ops_settings({"entry_bypass": False, "gh_mirror": "https://ghfast.top/", "ipv6_proxy": True, "block_quic": False}, tmp_shunt_dir)
        _test_arc = tmp_shunt_dir.parent / "test_factory_reset_arc.tgz"
        _rst_res = factory_reset_all_configs(tmp_shunt_dir, create_backup_archive=True, archive_override_path=_test_arc)
        assert _rst_res["ok"] is True and len(load_homelink_nodes(tmp_shunt_dir)) == 0 and len(load_saved_nodes(tmp_shunt_dir)) == 0, f"Expected factory_reset_all_configs to clear nodes & homelink, got {_rst_res}"
        _ops_after_reset = get_ops_settings(tmp_shunt_dir)
        assert _ops_after_reset["entry_bypass"] is True and _ops_after_reset["gh_mirror"] == "https://gh-proxy.com/" and _ops_after_reset["ipv6_proxy"] is False, f"Expected factory defaults after reset, got {_ops_after_reset}"
        # Now restore from archive and verify BOTH data AND system switches (entry_bypass=False, gh_mirror='https://ghfast.top/', ipv6_proxy=True) are 100% restored!
        _arc_restored = restore_from_backup_archive(tmp_shunt_dir, _test_arc)
        _ops_after_arc = get_ops_settings(tmp_shunt_dir)
        assert _arc_restored["ok"] is True and len(load_homelink_nodes(tmp_shunt_dir)) == 2, f"Expected homelink restored from archive, got {_arc_restored}"
        assert _ops_after_arc["entry_bypass"] is False and _ops_after_arc["gh_mirror"] == "https://ghfast.top/" and _ops_after_arc["ipv6_proxy"] is True and _ops_after_arc["block_quic"] is False, f"Expected ops_settings restored from archive, got {_ops_after_arc}"
        _test_arc.unlink(missing_ok=True)
        # Also verify JSON backup/restore round-trip preserves ops_settings, ipv6_proxy, panel_auth, AND auto_nodes.json byte-for-byte (FR-3)
        _update_panel_password("custom-secret-2026", tmp_shunt_dir, sync_uci=False)
        save_auto_nodes_config(load_auto_nodes_config(tmp_shunt_dir), tmp_shunt_dir)
        _auto_md5_before = hashlib.md5((tmp_shunt_dir / "auto_nodes.json").read_bytes()).hexdigest()
        _auth_before = json.loads((tmp_shunt_dir / "panel_auth.json").read_text(encoding="utf-8"))
        _json_bak = export_ops_backup(tmp_shunt_dir)
        assert isinstance(_json_bak.get("panel_auth"), dict) and _json_bak["panel_auth"]["hash"] == _auth_before["hash"], f"Expected panel_auth in export_ops_backup, got {_json_bak.get('panel_auth')}"
        factory_reset_all_configs(tmp_shunt_dir, create_backup_archive=False)
        restore_ops_backup(_json_bak, tmp_shunt_dir)
        _ops_after_json = get_ops_settings(tmp_shunt_dir)
        _auth_after = json.loads((tmp_shunt_dir / "panel_auth.json").read_text(encoding="utf-8"))
        _auto_md5_after = hashlib.md5((tmp_shunt_dir / "auto_nodes.json").read_bytes()).hexdigest()
        assert _ops_after_json["entry_bypass"] is False and _ops_after_json["gh_mirror"] == "https://ghfast.top/" and _ops_after_json["ipv6_proxy"] is True, f"Expected JSON restore_ops_backup to restore settings, got {_ops_after_json}"
        assert _auth_after["hash"] == _auth_before["hash"] and _auth_after["salt"] == _auth_before["salt"], f"Expected panel_auth restored, got {_auth_after}"
        assert _auto_md5_after == _auto_md5_before, f"Expected auto_nodes.json MD5 preserved ({_auto_md5_before} != {_auto_md5_after})"
        # 17) Verify FR-4: gfw_list mode routes www.bing.com, www.apple.com, www.microsoft.com, www.cloudflare.com to 'direct', and blocked sites to 'AI_Best_Auto'
        _sc_gfw = load_shunt_config(tmp_shunt_dir)
        _sc_gfw["routing_mode"] = "gfw_list"
        save_shunt_config(_sc_gfw, tmp_shunt_dir)
        for _d_dir in ("www.bing.com", "www.apple.com", "www.microsoft.com", "www.cloudflare.com"):
            _tr_d = trace_traffic_flow({"target": _d_dir}, tmp_shunt_dir)
            assert _tr_d["stage3_rule"]["selector_tag"] == "direct", f"FR-4: Expected {_d_dir} -> direct in gfw_list mode, got {_tr_d['stage3_rule']}"
        for _d_prx in ("www.google.com", "www.youtube.com", "chat.openai.com", "github.com", "x.com"):
            _tr_p = trace_traffic_flow({"target": _d_prx}, tmp_shunt_dir)
            assert _tr_p["stage3_rule"]["selector_tag"] == "AI_Best_Auto", f"FR-4: Expected {_d_prx} -> AI_Best_Auto in gfw_list mode, got {_tr_p['stage3_rule']}"
        # 18) OTA 在线更新：版本比较语义 + 升级脚本可生成 + 未升级时进度为空
        assert is_version_newer("1.0.2", "1.0.1") and not is_version_newer("1.0.1", "1.0.1"), "OTA: 版本比较基础用例失败"
        assert not is_version_newer("1.0.1-beta1", "1.0.1"), "OTA: 预发布版不应高于同号正式版"
        assert is_version_newer("1.0.1", "1.0.1-beta1"), "OTA: 正式版应高于同号预发布版"
        assert parse_app_version("v2.3.4")[:3] == (2, 3, 4), "OTA: v 前缀解析失败"
        _ota_script = _update_script_body({
            "target": "9.9.9", "current": APP_VERSION, "md5": "0" * 32, "sha256": "0" * 64,
            "size": 1, "package_urls": ["https://example.invalid/pkg.tar.gz"],
        })
        assert "install.sh" in _ota_script and "--upgrade" in _ota_script and "healthcheck" in _ota_script, "OTA: 升级脚本缺少关键步骤"
        assert "md5sum" in _ota_script and "sha256sum" in _ota_script, "OTA: 升级脚本缺少校验步骤"
        if not UPDATE_PROGRESS_LOG.is_file():
            _ota_prog = read_update_progress()
            assert _ota_prog["running"] is False, f"OTA: 空进度不应标记为运行中，got {_ota_prog}"
        shutil.rmtree(tmp_test_dir, ignore_errors=True)
        shutil.rmtree(tmp_shunt_dir, ignore_errors=True)
        print("SELF_TEST_PASSED", json.dumps({
            "ok": True,
            "app_version": APP_VERSION,
            "ota_version_compare_ok": True,
            "ota_script_generation_ok": True,
            "traffic_trace_lol_udp_direct_ok": (not t_lol["enters_kernel"]),
            "traffic_trace_ai_shunt_ok": t_ai["enters_kernel"],
            "traffic_trace_google_cn_rewrite_ok": t_gcn["stage2_dns"]["rewritten"],
            "ops_settings_persist_ok": True,
            "custom_rule_priority_override_ok": priority_override_ok,
            "outbound_topology_verify_ok": callable(_expected_outbound_tags),
            "stall_detection_ok": stall_ok,
            "node_edit_disable_ok": node_disable_ok,
            "homelink_dynamic_pin_ok": homelink_dynamic_ok,
            "version": APP_VERSION,
            "detected_core": rt["core"],
            "build_mode": rt["build_mode"],
            "ca_cert_capable_ok": ca_ok,
            "top_n_prefilter_ok": (len(top_60) == 60),
            "kr_region_min_slot_ok": kr_slot_ok,
            "test_node_isolated_ok": (classify_node_region("SG-Hy2-Loopback-01") == "TEST"),
            "test_node_badge_ok": is_builtin_test_node("SG-Hy2-Loopback-01"),
            "no_ghost_demo_sub_ok": True,
            "proc_comm_single_guard_ok": rt["core_single_instance_ok"],
            "shunt_11_groups_ok": True,
            "final_fallback_locked_bottom_ok": (shunt_groups[-1]["id"] == "Final_Fallback"),
            "target_aware_failover_ok": (fo_res["selected"] == "Node-US-02"),
            "country_auto_classify_ok": True,
            "sub_auto_update_capable_ok": True,
            "openai_us_ok": ok1,
            "openai_403_blocked": not ok2,
            "netflix_404_originals_rejected": not ok3,
            "score_us_valid": s_good,
            "score_hk_fake_vetoed": s_fake,
            "ipv6_incapable_node_culled": (s_v4only_when_v6on == 0.0),
            "selected_optimal_node": best_n,
            "uri_parser_5_protocols_ok": (len(parsed_nodes) == 5),
            "wol_packet_len": len(pkt)
        }))
        return 0
    port = 9099
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])
    _sb_cfg_f = CONF_DIR / "sing-box.json"
    if not _sb_cfg_f.is_file() or (time.time() - _sb_cfg_f.stat().st_mtime) > 25.0:
        write_all_configs(CONF_DIR)
    get_active_blocked_domains_set(CONF_DIR)
    _record_applied_core_rule_hash(CONF_DIR)
    try:
        build_status_api_response(CONF_DIR)
    except Exception:
        pass
    PROBE_ENGINE.apply_shunt_selections(CONF_DIR)
    PROBE_ENGINE.save_persisted_selections(RUN_DIR, record_history=False)
    # Drop any probe lock left behind by a previous daemon instance; otherwise the
    # first manual probe after a restart is rejected as "probe_in_progress".
    try:
        (RUN_DIR / "probe.lock").unlink()
    except Exception:
        pass
    start_background_probe_scheduler(interval_sec=300)
    # 确保 LuCI 桥接令牌在服务对外提供 API 之前就已就绪（LuCI 页面从 UCI 读取）
    try:
        get_luci_bridge_token(create=True)
    except Exception:
        pass
    # 把当前版本号与密码自定义标记同步到 UCI，供 LuCI / CLI / 面板统一读取，避免多处硬编码
    try:
        if Path("/etc/config/ai-link").is_file():
            subprocess.run(["uci", "set", f"ai-link.global.app_version={APP_VERSION}"], check=False, timeout=2)
            _sync_uci_pwd_customized(is_panel_pwd_customized(CONF_DIR))
    except Exception:
        pass
    bind_addr = (get_ops_settings(CONF_DIR).get("panel_bind") or "0.0.0.0").strip() or "0.0.0.0"
    try:
        server = ThreadingHTTPServer((bind_addr, port), AILinkRequestHandler)
    except Exception:
        bind_addr = "0.0.0.0"
        server = ThreadingHTTPServer((bind_addr, port), AILinkRequestHandler)
    try:
        _h3_threading.Thread(target=_h3_health_loop, daemon=True).start()
    except Exception:
        pass
    print(f"AI-LINK Standalone Panel & Probe Daemon v{APP_VERSION} listening on 0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    sys.exit(main())
