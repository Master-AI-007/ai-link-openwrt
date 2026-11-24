# -*- coding: utf-8 -*-
"""AI-LINK Diagnostic, Sanitization & Pure-Function Submodule (OPT-275-01 / OPT-276-01 / OPT-277-04).

This module isolates pure diagnostic, schema validation, sanitization, adaptive
concurrency, and network posture checks from ai-link-daemon.py to reduce single-file
memory footprint on embedded OpenWrt routers while preserving 100% API compatibility.
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

DIAG_MODULE_VERSION = "2.8.6"

SENSITIVE_CREDENTIAL_KEYS = (
    "panel_secret",
    "panel_password",
    "token",
    "password",
    "uuid",
    "private_key",
    "short_id",
    "auth_token",
    "secret",
)

RESERVED_SYSTEM_PORTS = {
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

LEGACY_BACKUP_FIELD_MAP = {
    "proxy_enabled": ("ops_settings", "enabled"),
    "bypass_mode": ("ops_settings", "entry_bypass"),
    "lan_auth": ("ops_settings", "require_lan_auth"),
    "ipv6_enabled": ("ops_settings", "ipv6_proxy"),
    "dns_mode": ("dns_rewrite", "mode"),
    "nodes_list": ("nodes", None),
    "subs": ("subscriptions", None),
    "shunt_rules": ("shunt", "groups"),
}


def sanitize_singbox_outbound_tag(tag: str, max_bytes: int = 64) -> str:
    """OPT-275-03: UTF-8 safe byte-length truncation guard for sing-box outbound tags."""
    raw = str(tag or "").strip()
    raw = re.sub(r"[\x00-\x1f\x7f]", "", raw)
    enc = raw.encode("utf-8")
    if len(enc) <= max_bytes:
        return raw
    return enc[:max_bytes].decode("utf-8", errors="ignore").rstrip()


def deduplicate_outbound_tags(tags: list[str], max_bytes: int = 64) -> list[str]:
    """OPT-274-06: Deduplicate node tags deterministically while preserving UTF-8 limits."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for raw_tag in tags:
        clean = sanitize_singbox_outbound_tag(raw_tag, max_bytes=max_bytes) or "node"
        if clean not in seen:
            seen[clean] = 1
            out.append(clean)
        else:
            seen[clean] += 1
            suffix = f" #{seen[clean]}"
            stem = sanitize_singbox_outbound_tag(clean, max_bytes=max(8, max_bytes - len(suffix.encode("utf-8"))))
            candidate = f"{stem}{suffix}"
            while candidate in seen:
                seen[clean] += 1
                suffix = f" #{seen[clean]}"
                stem = sanitize_singbox_outbound_tag(clean, max_bytes=max(8, max_bytes - len(suffix.encode("utf-8"))))
                candidate = f"{stem}{suffix}"
            seen[candidate] = 1
            out.append(candidate)
    return out


def score_node_with_sub_priority(delay_ms: float, sub_priority: int = 1) -> float:
    """OPT-275-05: Weight node latency score by subscription priority (lower is better)."""
    base = max(1.0, float(delay_ms or 9999.0))
    prio_bonus = max(0, min(5, int(sub_priority or 1) - 1)) * 15.0
    return round(base + prio_bonus, 2)


def classify_probe_failure_reason(error_text: str = "", http_code: int = 0) -> dict[str, str]:
    """OPT-274-15: Categorize L7 probe failures into human-readable diagnostics."""
    msg = str(error_text or "").lower()
    if http_code in (403, 502, 503):
        return {"category": f"http_{http_code}", "label": f"HTTP {http_code} 拒绝/网关错误"}
    if "tls" in msg or "ssl" in msg or "handshake" in msg or "certificate" in msg:
        return {"category": "tls_handshake", "label": "TLS 握手超时或证书异常"}
    if "timeout" in msg or "timed out" in msg:
        return {"category": "timeout", "label": "TCP/HTTP 连接超时"}
    if "refused" in msg or "unreachable" in msg or "reset" in msg:
        return {"category": "tcp_unreachable", "label": "TCP 不可达或连接被重置"}
    return {"category": "probe_error", "label": "节点探测失败"}


def summarize_backup_redacted_fields(backup_obj: dict | None = None) -> dict[str, Any]:
    """OPT-275-06: List redacted credential fields before backup export/import."""
    obj = backup_obj if isinstance(backup_obj, dict) else {}
    redacted: list[str] = []
    for k in SENSITIVE_CREDENTIAL_KEYS:
        if k in obj or (isinstance(obj.get("ops_settings"), dict) and k in obj["ops_settings"]):
            redacted.append(k)
    return {"ok": True, "redacted_fields": redacted, "has_redacted": len(redacted) > 0}


def redact_sensitive_dict(data: Any, mask: str = "***") -> Any:
    """Recursively redact sensitive credential fields for diagnostic snapshots."""
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            kl = str(k).lower()
            if any(sk in kl for sk in ("secret", "password", "private_key", "token")) and isinstance(v, str) and v:
                out[k] = mask
            else:
                out[k] = redact_sensitive_dict(v, mask=mask)
        return out
    if isinstance(data, list):
        return [redact_sensitive_dict(item, mask=mask) for item in data]
    return data


def _parse_semver_tuple(raw_ver: Any) -> tuple[int, int, int]:
    """Parse version string like 'v2.5.1' or '2.7.7' into (major, minor, patch)."""
    s = str(raw_ver or "").strip().lstrip("vV")
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?", s)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0))


def validate_and_migrate_backup_schema(
    backup_data: dict[str, Any] | None,
    target_version: str = DIAG_MODULE_VERSION,
) -> dict[str, Any]:
    """OPT-277-08: Validate backup JSON schema_version and migrate pre-v2.6.0 backups safely."""
    if not isinstance(backup_data, dict):
        return {
            "ok": False,
            "error": "invalid_backup_json",
            "schema_version": "0.0.0",
            "migrated": False,
            "migration_changes": [],
            "data": {},
        }

    migrated_obj = copy.deepcopy(backup_data)
    raw_ver = migrated_obj.get("schema_version") or migrated_obj.get("version") or migrated_obj.get("app_version") or ""
    ver_tuple = _parse_semver_tuple(raw_ver)
    changes: list[str] = []
    needs_migration = (ver_tuple == (0, 0, 0)) or (ver_tuple < (2, 6, 0))

    if needs_migration:
        src_ver = str(raw_ver).strip() or "legacy(<2.6.0)"
        for old_key, (dst_section, dst_key) in LEGACY_BACKUP_FIELD_MAP.items():
            if old_key in migrated_obj:
                val = migrated_obj.pop(old_key)
                if dst_key is None:
                    if dst_section not in migrated_obj:
                        migrated_obj[dst_section] = val
                        changes.append(f"迁移顶层字段 {old_key} -> {dst_section}")
                else:
                    sec = migrated_obj.setdefault(dst_section, {})
                    if isinstance(sec, dict) and dst_key not in sec:
                        sec[dst_key] = val
                        changes.append(f"迁移字段 {old_key} -> {dst_section}.{dst_key}")

        ops = migrated_obj.get("ops_settings")
        if isinstance(ops, dict):
            if "require_lan_auth" not in ops:
                ops["require_lan_auth"] = True
                changes.append("补齐安全默认字段 ops_settings.require_lan_auth=true")
            if "topology_mode" not in ops:
                ops["topology_mode"] = "auto"
                changes.append("补齐默认字段 ops_settings.topology_mode=auto")

        shunt = migrated_obj.get("shunt")
        if isinstance(shunt, dict) and isinstance(shunt.get("groups"), list):
            for grp in shunt["groups"]:
                if isinstance(grp, dict) and "shunt_mode" not in grp:
                    st = str(grp.get("strategy") or "").lower()
                    grp["shunt_mode"] = "direct" if st == "direct" else ("manual" if st == "manual" else "auto")
                    changes.append(f"补齐分流组 {grp.get('id', '?')} 的 shunt_mode={grp['shunt_mode']}")

        migrated_obj["schema_version"] = target_version
        migrated_obj["migrated_from"] = src_ver
        if not changes:
            changes.append(f"升级 schema_version: {src_ver} -> {target_version}")
        return {
            "ok": True,
            "schema_version": target_version,
            "source_version": src_ver,
            "migrated": True,
            "migration_changes": changes,
            "data": migrated_obj,
        }

    norm_ver = f"{ver_tuple[0]}.{ver_tuple[1]}.{ver_tuple[2]}"
    migrated_obj.setdefault("schema_version", norm_ver)
    return {
        "ok": True,
        "schema_version": norm_ver,
        "source_version": norm_ver,
        "migrated": False,
        "migration_changes": [],
        "data": migrated_obj,
    }


def diagnose_auto_pool_scope_sources(
    pool_cfg: dict[str, Any] | None,
    subscriptions: list[dict[str, Any]] | None,
    nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """OPT-277-02: Detect deleted or empty subscription sources in auto-node pool scope_sources."""
    pool = pool_cfg if isinstance(pool_cfg, dict) else {}
    subs = [s for s in (subscriptions or []) if isinstance(s, dict)]
    node_list = [n for n in (nodes or []) if isinstance(n, dict)]

    raw_sources = pool.get("scope_sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        return {
            "ok": True,
            "scope_sources_empty": False,
            "missing_sources": [],
            "empty_sources": [],
            "matched_node_count": len(node_list),
            "empty_reason": "",
        }

    if "ALL" in raw_sources:
        return {
            "ok": True,
            "scope_sources_empty": False,
            "missing_sources": [],
            "empty_sources": [],
            "matched_node_count": len(node_list),
            "empty_reason": "",
        }

    sub_by_id = {str(s.get("id") or ""): s for s in subs if s.get("id")}
    sub_by_name = {str(s.get("name") or ""): s for s in subs if s.get("name")}

    missing_sources: list[str] = []
    empty_sources: list[str] = []
    matched_nodes = 0

    for src in raw_sources:
        s_key = str(src or "").strip()
        if not s_key:
            continue
        if s_key == "custom":
            custom_cnt = sum(
                1 for n in node_list
                if str(n.get("source") or n.get("sub_id") or "").lower() in ("custom", "manual", "")
            )
            matched_nodes += custom_cnt
            if custom_cnt == 0:
                empty_sources.append("custom")
            continue

        sub_obj = sub_by_id.get(s_key) or sub_by_name.get(s_key)
        if not sub_obj:
            missing_sources.append(s_key)
            continue

        sid = str(sub_obj.get("id") or "")
        sname = str(sub_obj.get("name") or "")
        cnt = sum(
            1 for n in node_list
            if str(n.get("_sub_id") or n.get("sub_id") or "") == sid
            or (sname and str(n.get("sub_name") or "") == sname)
        )
        matched_nodes += cnt
        if cnt == 0:
            empty_sources.append(sname or sid)

    is_empty = bool((missing_sources or empty_sources) and matched_nodes == 0)
    reason = ""
    if is_empty:
        if missing_sources and empty_sources:
            reason = f"所选订阅源已不存在或为空（缺失: {', '.join(missing_sources)}；空节点: {', '.join(empty_sources)}）"
        elif missing_sources:
            reason = f"所选订阅源已不存在（{', '.join(missing_sources)}），请重新选择订阅"
        else:
            reason = f"所选订阅源节点数为 0（{', '.join(empty_sources)}），请更新或重选订阅"

    return {
        "ok": not is_empty,
        "scope_sources_empty": is_empty,
        "missing_sources": missing_sources,
        "empty_sources": empty_sources,
        "matched_node_count": matched_nodes,
        "empty_reason": reason,
    }


def get_adaptive_probe_concurrency(
    requested_workers: int | None = None,
    cpu_count: int | None = None,
) -> int:
    """OPT-277-06: Scale probe concurrency safely by router CPU cores to avoid UI lag."""
    cores = cpu_count if isinstance(cpu_count, int) and cpu_count > 0 else (os.cpu_count() or 2)
    if cores <= 1:
        cap = 2
    elif cores == 2:
        cap = 4
    elif cores <= 4:
        cap = 6
    else:
        cap = 8

    if isinstance(requested_workers, int) and requested_workers > 0:
        return max(1, min(requested_workers, cap))
    return cap


def flush_dns_caches_atomic(
    reason: str = "dns_mode_switch",
    run_cmd=None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """OPT-277-05: Atomically flush dnsmasq and local DNS caches on mode/upstream switch."""
    t0 = time.monotonic()
    actions: list[str] = []
    errors: list[str] = []
    exec_fn = run_cmd or subprocess.run

    try:
        res = exec_fn(["killall", "-HUP", "dnsmasq"], capture_output=True, timeout=2)
        rc = getattr(res, "returncode", 0)
        actions.append(f"dnsmasq_sighup(rc={rc})")
    except FileNotFoundError:
        actions.append("dnsmasq_sighup(skipped_not_installed)")
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"dnsmasq_sighup:{exc}")

    if state_dir is not None:
        try:
            cache_file = Path(state_dir) / "dns_cache_epoch.json"
            payload = {"reason": str(reason), "flushed_at": int(time.time())}
            tmp_file = Path(state_dir) / f".dns_cache_epoch.{os.getpid()}.tmp"
            tmp_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp_file, cache_file)
            actions.append("dns_cache_epoch_updated")
        except OSError as exc:
            errors.append(f"epoch_write:{exc}")

    elapsed_ms = round((time.monotonic() - t0) * 1000.0, 2)
    return {
        "ok": len(errors) == 0,
        "reason": str(reason),
        "actions": actions,
        "errors": errors,
        "elapsed_ms": elapsed_ms,
    }


def _read_proc_net_ports(proto: str = "tcp") -> set[int]:
    """Read active listening ports from /proc/net/{tcp,tcp6,udp,udp6}."""
    ports: set[int] = set()
    files = ("/proc/net/udp", "/proc/net/udp6") if proto == "udp" else ("/proc/net/tcp", "/proc/net/tcp6")
    for fp in files:
        p = Path(fp)
        if not p.is_file():
            continue
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
                parts = line.strip().split()
                if len(parts) < 4:
                    continue
                local_addr, st_hex = parts[1], parts[3]
                if proto == "tcp" and st_hex != "0A":
                    continue
                if ":" in local_addr:
                    port_hex = local_addr.rsplit(":", 1)[1]
                    ports.add(int(port_hex, 16))
        except (OSError, ValueError):
            continue
    return ports


def check_homelink_port_conflict_summary(
    nodes: list[dict[str, Any]] | None,
    panel_port: int = 9099,
    live_tcp_ports: set[int] | None = None,
    live_udp_ports: set[int] | None = None,
) -> dict[str, Any]:
    """OPT-277-07: Real-time port conflict audit for HomeLink nodes vs panel/LuCI/live sockets."""
    hl_nodes = [n for n in (nodes or []) if isinstance(n, dict)]
    reserved = dict(RESERVED_SYSTEM_PORTS)
    reserved[int(panel_port or 9099)] = "AI-LINK Web 面板"
    reserved[80] = "uhttpd/LuCI HTTP"
    reserved[443] = "uhttpd/LuCI HTTPS"

    tcp_ports = live_tcp_ports if live_tcp_ports is not None else _read_proc_net_ports("tcp")
    udp_ports = live_udp_ports if live_udp_ports is not None else _read_proc_net_ports("udp")

    conflicts: list[dict[str, Any]] = []
    seen_ports: dict[int, str] = {}

    for n in hl_nodes:
        nid = str(n.get("id") or "")
        name = str(n.get("name") or nid or "HomeLink")
        proto = str(n.get("protocol") or "vless-reality").lower()
        try:
            lport = int(n.get("listen_port", 0) or 0)
        except (ValueError, TypeError):
            conflicts.append({"id": nid, "name": name, "port": n.get("listen_port"), "reason": "端口格式非法"})
            continue

        if lport < 1024 or lport > 65535:
            conflicts.append({"id": nid, "name": name, "port": lport, "reason": f"端口 {lport} 超出 1024-65535 安全范围"})
            continue

        if lport in reserved:
            conflicts.append({"id": nid, "name": name, "port": lport, "reason": f"与系统/面板端口冲突 ({reserved[lport]})"})
            continue

        if lport in seen_ports:
            conflicts.append({"id": nid, "name": name, "port": lport, "reason": f"与回家节点「{seen_ports[lport]}」端口重复"})
            continue
        seen_ports[lport] = name

        l4 = "udp" if ("hy" in proto or "tuic" in proto or "wg" in proto) else "tcp"
        active_set = udp_ports if l4 == "udp" else tcp_ports
        if not n.get("enabled", True) and lport in active_set:
            conflicts.append({"id": nid, "name": name, "port": lport, "reason": f"端口 {lport}/{l4.upper()} 已被其他进程占用"})

    return {
        "ok": len(conflicts) == 0,
        "checked_count": len(hl_nodes),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }


def check_bypass_ipv6_ra_ndp_conflict(
    ops: dict[str, Any] | None = None,
    dhcp_cfg_text: str | None = None,
) -> dict[str, Any]:
    """OPT-277-10: Detect IPv6 RA / NDP relay conflicts in single-arm bypass mode."""
    cfg = ops if isinstance(ops, dict) else {}
    ipv6_on = bool(cfg.get("ipv6_proxy", False))
    topo = str(cfg.get("topology_mode") or "auto").lower()

    if not ipv6_on or topo not in ("bypass", "onearm"):
        return {
            "ok": True,
            "checked": False,
            "has_conflict": False,
            "topology_mode": topo,
            "ipv6_proxy": ipv6_on,
            "ra_mode": "",
            "ndp_mode": "",
            "message": "",
        }

    raw_dhcp = dhcp_cfg_text
    if raw_dhcp is None:
        dhcp_path = Path("/etc/config/dhcp")
        raw_dhcp = dhcp_path.read_text(encoding="utf-8", errors="ignore") if dhcp_path.is_file() else ""

    ra_m = re.search(r"option\s+ra\s+['\"]?(\w+)['\"]?", raw_dhcp)
    ndp_m = re.search(r"option\s+ndp\s+['\"]?(\w+)['\"]?", raw_dhcp)
    dhcpv6_m = re.search(r"option\s+dhcpv6\s+['\"]?(\w+)['\"]?", raw_dhcp)

    ra_mode = ra_m.group(1).lower() if ra_m else ""
    ndp_mode = ndp_m.group(1).lower() if ndp_m else ""
    dhcpv6_mode = dhcpv6_m.group(1).lower() if dhcpv6_m else ""

    conflicts: list[str] = []
    if ra_mode in ("server", "hybrid"):
        conflicts.append(f"ra='{ra_mode}'")
    if ndp_mode in ("relay", "hybrid"):
        conflicts.append(f"ndp='{ndp_mode}'")
    if dhcpv6_mode in ("server", "hybrid"):
        conflicts.append(f"dhcpv6='{dhcpv6_mode}'")

    has_conflict = len(conflicts) > 0
    if has_conflict:
        msg = (
            f"旁路由单臂模式下检测到本机 LAN 开启了 IPv6 通告/中继 ({', '.join(conflicts)})，"
            "请核对主路由 RA 通告是否冲突，避免下发本机为重复 IPv6 默认网关。"
        )
    else:
        msg = "旁路由 IPv6 RA/NDP 配置未发现与主路由冲突；请确认主路由 RA 是否将本机通告为 IPv6 网关。"

    return {
        "ok": not has_conflict,
        "checked": True,
        "has_conflict": has_conflict,
        "topology_mode": topo,
        "ipv6_proxy": ipv6_on,
        "ra_mode": ra_mode,
        "ndp_mode": ndp_mode,
        "dhcpv6_mode": dhcpv6_mode,
        "message": msg,
    }


def check_storage_headroom_pure(target_dir: Path, min_free_mb: int = 16) -> dict[str, Any]:
    """Pure storage headroom check for flash / overlay safety."""
    p = Path(target_dir)
    probe_path = p if p.exists() else p.parent
    try:
        st = os.statvfs(str(probe_path))
        free_mb = round((st.f_bavail * st.f_frsize) / (1024 * 1024), 2)
    except OSError:
        free_mb = -1.0
    return {
        "ok": free_mb < 0 or free_mb >= float(min_free_mb),
        "free_mb": free_mb,
        "min_free_mb": min_free_mb,
        "path": str(probe_path),
    }


def is_port_listening_local(port: int, host: str = "127.0.0.1", timeout_s: float = 0.25) -> bool:
    """Lightweight TCP port check without spawning external processes."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_s):
            return True
    except OSError:
        return False


def build_diag_module_manifest() -> dict[str, Any]:
    """Return manifest of all exported pure diagnostic functions in ailink_diag."""
    return {
        "module": "ailink_diag",
        "version": DIAG_MODULE_VERSION,
        "functions": [
            "sanitize_singbox_outbound_tag",
            "deduplicate_outbound_tags",
            "score_node_with_sub_priority",
            "classify_probe_failure_reason",
            "summarize_backup_redacted_fields",
            "redact_sensitive_dict",
            "validate_and_migrate_backup_schema",
            "diagnose_auto_pool_scope_sources",
            "get_adaptive_probe_concurrency",
            "flush_dns_caches_atomic",
            "check_homelink_port_conflict_summary",
            "check_bypass_ipv6_ra_ndp_conflict",
            "check_storage_headroom_pure",
            "is_port_listening_local",
            "parse_and_validate_bulk_shunt_rules",
            "compute_subscription_usage_summary",
            "compute_next_schedule_preview",
            "check_bypass_multi_subnet_forwarding",
        ],
    }


def parse_and_validate_bulk_shunt_rules(raw_text: str, fmt: str = "auto") -> dict[str, Any]:
    """OPT-278-01: Parse and validate bulk shunt rules from JSON or plain domain/CIDR lines."""
    text = str(raw_text or "").strip()
    if not text:
        return {"ok": False, "error": "empty_input", "domains": [], "ip_cidrs": [], "invalid": []}

    domains: list[str] = []
    ip_cidrs: list[str] = []
    invalid: list[str] = []
    candidates: list[str] = []

    if fmt == "json" or (fmt == "auto" and text.startswith("{")):
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                candidates.extend(str(x) for x in (obj.get("domains") or []))
                candidates.extend(str(x) for x in (obj.get("ip_cidrs") or []))
            elif isinstance(obj, list):
                candidates.extend(str(x) for x in obj)
        except ValueError as exc:
            return {"ok": False, "error": f"invalid_json:{exc}", "domains": [], "ip_cidrs": [], "invalid": [text[:64]]}
    else:
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            candidates.append(s)

    dom_re = re.compile(r"^[a-zA-Z0-9*._-]+\.[a-zA-Z]{2,}$")
    cidr_re = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?$|^[0-9a-fA-F:]+(?:/\d{1,3})?$")
    for item in candidates:
        s = item.strip()
        if cidr_re.match(s) and ("." in s or ":" in s):
            if s not in ip_cidrs:
                ip_cidrs.append(s)
        elif dom_re.match(s) and " " not in s:
            if s not in domains:
                domains.append(s)
        else:
            invalid.append(s)

    return {
        "ok": len(invalid) == 0 and (len(domains) > 0 or len(ip_cidrs) > 0),
        "domains": domains,
        "ip_cidrs": ip_cidrs,
        "invalid": invalid,
        "total_valid": len(domains) + len(ip_cidrs),
    }


def compute_subscription_usage_summary(sub_obj: dict[str, Any] | None, now_ts: int | None = None) -> dict[str, Any]:
    """OPT-278-03: Compute remaining traffic percentage and expiration countdown days."""
    s = sub_obj if isinstance(sub_obj, dict) else {}
    now = int(now_ts if now_ts is not None else time.time())
    up = max(0, int(s.get("upload") or 0))
    down = max(0, int(s.get("download") or 0))
    total = max(0, int(s.get("total") or 0))
    expire = int(s.get("expire") or 0)

    used = up + down
    rem_pct = round(max(0.0, min(100.0, ((total - used) / total) * 100.0)), 1) if total > 0 else None
    days_left = max(0, int((expire - now) // 86400)) if expire > 0 else None
    return {
        "has_quota": total > 0,
        "used_bytes": used,
        "total_bytes": total,
        "remaining_pct": rem_pct,
        "expire_ts": expire,
        "days_left": days_left,
    }


def compute_next_schedule_preview(
    interval_hours: float = 6.0,
    last_run_ts: int = 0,
    now_ts: int | None = None,
) -> dict[str, Any]:
    """OPT-278-09: Preview next scheduled execution timestamp based on system clock."""
    now = int(now_ts if now_ts is not None else time.time())
    iv_s = max(60, int(float(interval_hours or 6.0) * 3600))
    base = int(last_run_ts or 0) if int(last_run_ts or 0) > 0 else now
    next_ts = base + iv_s
    while next_ts <= now:
        next_ts += iv_s
    return {
        "interval_hours": float(interval_hours or 6.0),
        "last_run_ts": int(last_run_ts or 0),
        "next_run_ts": next_ts,
        "in_seconds": max(0, next_ts - now),
        "ntp_synced": now >= 1700000000,
    }


def check_bypass_multi_subnet_forwarding(
    ops: dict[str, Any] | None = None,
    network_cfg_text: str | None = None,
) -> dict[str, Any]:
    """OPT-278-10: Detect multi-VLAN/Guest LAN interfaces in single-arm bypass mode."""
    cfg = ops if isinstance(ops, dict) else {}
    topo = str(cfg.get("topology_mode") or "auto").lower()
    if topo not in ("bypass", "onearm"):
        return {"ok": True, "checked": False, "multi_subnet": False, "subnets": [], "message": ""}

    raw_net = network_cfg_text
    if raw_net is None:
        net_p = Path("/etc/config/network")
        raw_net = net_p.read_text(encoding="utf-8", errors="ignore") if net_p.is_file() else ""

    ifaces = re.findall(r"config\s+interface\s+['\"]?([a-zA-Z0-9_]+)['\"]?", raw_net)
    lan_like = [i for i in ifaces if i.lower() not in ("loopback", "wan", "wan6")]
    multi = len(lan_like) > 1
    msg = (
        f"旁路由单臂模式下检测到多个局域网/Guest 子网接口 ({', '.join(lan_like)})，请核对防火墙区域转发（Forwarding）策略以确保跨网段放行。"
        if multi else ""
    )
    return {
        "ok": True,
        "checked": True,
        "multi_subnet": multi,
        "subnets": lan_like,
        "message": msg,
    }


# ---------------------------------------------------------------------------
# v2.7.9 (r54) OPT-279-01 .. OPT-279-10 Pure Diagnostic & Helper Functions
# ---------------------------------------------------------------------------
_SHUNT_UNDO_MEM_SNAPSHOT: dict[str, Any] = {"ts": 0.0, "shunt": None, "reason": ""}


def save_shunt_undo_snapshot(shunt_data: dict[str, Any], reason: str = "manual_change", now_ts: float | None = None) -> dict[str, Any]:
    """OPT-279-01: Save an in-memory 30s TTL undo snapshot before bulk/reset shunt changes."""
    import copy
    now = float(now_ts if now_ts is not None else time.time())
    _SHUNT_UNDO_MEM_SNAPSHOT["ts"] = now
    _SHUNT_UNDO_MEM_SNAPSHOT["shunt"] = copy.deepcopy(shunt_data) if isinstance(shunt_data, dict) else {}
    _SHUNT_UNDO_MEM_SNAPSHOT["reason"] = str(reason or "manual_change")
    return {"ok": True, "ts": now, "ttl_s": 30, "reason": _SHUNT_UNDO_MEM_SNAPSHOT["reason"]}


def restore_shunt_undo_snapshot(now_ts: float | None = None, ttl_s: float = 30.0) -> dict[str, Any]:
    """OPT-279-01: Restore the shunt snapshot if within the 30s undo window."""
    import copy
    now = float(now_ts if now_ts is not None else time.time())
    snap_ts = float(_SHUNT_UNDO_MEM_SNAPSHOT.get("ts") or 0.0)
    snap_data = _SHUNT_UNDO_MEM_SNAPSHOT.get("shunt")
    if not isinstance(snap_data, dict) or snap_ts <= 0:
        return {"ok": False, "error": "no_snapshot", "message": "暂无可撤销的分流规则快照"}
    age = now - snap_ts
    if age > float(ttl_s):
        return {"ok": False, "error": "snapshot_expired", "age_s": round(age, 1), "message": "分流规则撤销窗口（30秒）已过期"}
    restored = copy.deepcopy(snap_data)
    _SHUNT_UNDO_MEM_SNAPSHOT["ts"] = 0.0
    _SHUNT_UNDO_MEM_SNAPSHOT["shunt"] = None
    return {"ok": True, "age_s": round(age, 1), "shunt": restored, "reason": _SHUNT_UNDO_MEM_SNAPSHOT.get("reason", "")}


def evaluate_custom_doh_fallback(
    consecutive_timeouts: int = 0,
    custom_doh_url: str = "",
    threshold: int = 3,
) -> dict[str, Any]:
    """OPT-279-02: Trigger temporary fallback to trusted domestic DNS after >=3 custom DoH timeouts."""
    cnt = max(0, int(consecutive_timeouts or 0))
    active = bool(custom_doh_url and cnt >= int(threshold))
    fallback_dns = ["223.5.5.5", "119.29.29.29"] if active else []
    msg = (
        f"自定义 DoH 上游 ({custom_doh_url}) 连续 {cnt} 次解析超时，已临时降级至国内可信 DNS (223.5.5.5) 防断网。"
        if active else ""
    )
    return {
        "ok": True,
        "fallback_active": active,
        "consecutive_timeouts": cnt,
        "threshold": int(threshold),
        "custom_doh_url": str(custom_doh_url or ""),
        "fallback_dns": fallback_dns,
        "message": msg,
    }


def compute_node_jitter_stats(sparkline: list[dict[str, Any]] | None) -> dict[str, Any]:
    """OPT-279-03: Compute latency jitter (max - min) and avg over the latest 5 valid probe samples."""
    pts = [
        int(x.get("delay_ms"))
        for x in (sparkline or [])
        if isinstance(x, dict) and x.get("ok") and isinstance(x.get("delay_ms"), (int, float)) and int(x.get("delay_ms")) > 0
    ]
    recent = pts[-5:]
    if not recent:
        return {"samples": 0, "jitter_ms": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0, "high_jitter": False}
    mn, mx = min(recent), max(recent)
    jitter = mx - mn
    avg = round(sum(recent) / len(recent))
    return {
        "samples": len(recent),
        "jitter_ms": jitter,
        "avg_ms": avg,
        "min_ms": mn,
        "max_ms": mx,
        "high_jitter": jitter >= 80,
    }


def summarize_homelink_clients(peers: list[dict[str, Any]] | None, now_ts: int | None = None) -> dict[str, Any]:
    """OPT-279-04: Summarize online HomeLink remote clients and latest handshake timestamp."""
    now = int(now_ts if now_ts is not None else time.time())
    items = peers if isinstance(peers, list) else []
    online = []
    latest_hs = 0
    for p in items:
        if not isinstance(p, dict):
            continue
        hs = int(p.get("latest_handshake_ts") or p.get("last_handshake") or 0)
        is_on = bool(p.get("online")) or (hs > 0 and (now - hs) <= 180)
        if hs > latest_hs:
            latest_hs = hs
        if is_on:
            online.append({
                "name": str(p.get("name") or p.get("id") or "Remote-Peer"),
                "ip": str(p.get("ip") or ""),
                "latest_handshake_ts": hs,
            })
    return {
        "online_count": len(online),
        "total_peers": len(items),
        "latest_handshake_ts": latest_hs,
        "clients": online,
    }


def check_disk_quota_warning(
    paths: list[str] | None = None,
    threshold_pct: float = 85.0,
    usage_override: dict[str, float] | None = None,
) -> dict[str, Any]:
    """OPT-279-05: Warn when /etc/ai-link or /var/run/ai-link disk usage exceeds threshold_pct (default 85%)."""
    import shutil
    check_paths = paths or ["/etc/ai-link", "/var/run/ai-link"]
    warnings = []
    details = {}
    for p in check_paths:
        if isinstance(usage_override, dict) and p in usage_override:
            pct = float(usage_override[p])
        else:
            target = Path(p)
            probe = target if target.exists() else Path("/tmp")
            try:
                du = shutil.disk_usage(str(probe))
                pct = round((du.used / du.total) * 100.0, 1) if du.total > 0 else 0.0
            except OSError:
                pct = 0.0
        details[p] = pct
        if pct >= float(threshold_pct):
            warnings.append(f"{p} 磁盘使用率已达 {pct:.1f}%（>= {threshold_pct:.0f}%），建议清理旧 .srs 缓存或缩减日志。")
    return {
        "ok": len(warnings) == 0,
        "warning_active": len(warnings) > 0,
        "threshold_pct": float(threshold_pct),
        "usage_pct_by_path": details,
        "messages": warnings,
    }


def detect_flow_offloading_conflict(
    firewall_conf_text: str | None = None,
    data_plane_mode: str = "tproxy_redirect",
) -> dict[str, Any]:
    """OPT-279-06: Detect hardware/software flow_offloading or shortcut_fe conflicts with TProxy."""
    raw = firewall_conf_text
    if raw is None:
        fw_p = Path("/etc/config/firewall")
        raw = fw_p.read_text(encoding="utf-8", errors="ignore") if fw_p.is_file() else ""
    flow_on = bool(re.search(r"option\s+flow_offloading(_hw)?\s+[\x27\x22]?1[\x27\x22]?", raw))
    sfe_on = bool(re.search(r"(shortcut_fe|sfe)", raw, re.IGNORECASE)) and bool(re.search(r"[\x27\x22]?1[\x27\x22]?", raw))
    tproxy_active = "tproxy" in str(data_plane_mode or "tproxy_redirect").lower()
    conflict = (flow_on or sfe_on) and tproxy_active
    msg = (
        "检测到防火墙开启了硬件/软件流加速 (flow_offloading / SFE)，可能绕过 TProxy 透明代理导致分流失效，建议关闭流加速或切换全量 TUN 模式。"
        if conflict else ""
    )
    return {
        "ok": not conflict,
        "conflict": conflict,
        "flow_offloading": flow_on,
        "shortcut_fe": sfe_on,
        "data_plane_mode": str(data_plane_mode or ""),
        "message": msg,
    }


def format_watchdog_recovery_event(
    reason: str = "core_exit",
    downtime_s: float = 0.0,
    recovered_node: str = "",
    ts: int | None = None,
) -> dict[str, Any]:
    """OPT-279-08: Format structured watchdog self-healing recovery event for the notification center."""
    now = int(ts if ts is not None else time.time())
    dt = round(max(0.0, float(downtime_s or 0.0)), 1)
    node_str = str(recovered_node or "自动节点")
    rsn_str = str(reason or "core_exit")
    return {
        "ts": now,
        "reason": rsn_str,
        "downtime_s": dt,
        "recovered_node": node_str,
        "summary": f"看门狗自愈完成：原因={rsn_str}，中断时长={dt}s，当前恢复出口={node_str}",
    }


def detect_upstream_gateway_mac_change(
    current_gw_ip: str = "",
    current_gw_mac: str = "",
    saved_gw_mac: str = "",
) -> dict[str, Any]:
    """OPT-279-10: Detect upstream main-router gateway MAC address changes in bypass/onearm mode."""
    cur = str(current_gw_mac or "").strip().lower()
    prev = str(saved_gw_mac or "").strip().lower()
    changed = bool(cur and prev and cur != prev)
    msg = (
        f"检测到上游主路由 ({current_gw_ip or 'gateway'}) MAC 地址从 {prev} 变更为 {cur}，如遇断网请刷新 ARP 缓存并核对旁路由网关配置。"
        if changed else ""
    )
    return {
        "ok": not changed,
        "changed": changed,
        "gateway_ip": str(current_gw_ip or ""),
        "current_mac": cur,
        "saved_mac": prev,
        "message": msg,
    }


# ---------------------------------------------------------------------------
# v2.8.0 (r55) OPT-280-01 .. OPT-280-10 Pure Diagnostic & Helper Functions
# ---------------------------------------------------------------------------
def export_shunt_to_singbox_route_rules(shunt_data: dict[str, Any] | None) -> dict[str, Any]:
    """OPT-280-01: Export 5x3 shunt groups into native sing-box route.rules JSON snippet."""
    groups = (shunt_data or {}).get("groups") if isinstance(shunt_data, dict) else []
    rules = []
    for g in (groups or []):
        if not isinstance(g, dict):
            continue
        gid = str(g.get("id") or g.get("name") or "").strip()
        if not gid:
            continue
        outbound = f"Shunt_{gid}" if not gid.startswith("Shunt_") else gid
        domains = [str(d).strip() for d in (g.get("domains") or []) if str(d).strip()]
        cidrs = [str(c).strip() for c in (g.get("ip_cidr") or []) if str(c).strip()]
        rule: dict[str, Any] = {"outbound": outbound}
        if domains:
            rule["domain_suffix"] = domains[:50]
        if cidrs:
            rule["ip_cidr"] = cidrs[:50]
        if len(rule) > 1:
            rules.append(rule)
    return {"ok": True, "count": len(rules), "route": {"rules": rules}}


def build_dns_ecs_privacy_patch(ecs_strip_enabled: bool = True) -> dict[str, Any]:
    """OPT-280-02: Build EDNS0 Client Subnet (ECS) stripping privacy config."""
    strip = bool(ecs_strip_enabled)
    return {
        "ok": True,
        "ecs_strip_enabled": strip,
        "client_subnet": "0.0.0.0/0" if strip else "",
        "privacy_mode": "strict_no_ecs" if strip else "default",
    }


def compute_node_cooldown_progress(member: dict[str, Any] | None, now_ts: int | None = None, total_cooldown_s: int = 3600) -> dict[str, Any]:
    """OPT-280-03: Compute remaining failover cooldown seconds & progress percentage for UI."""
    now = int(now_ts if now_ts is not None else time.time())
    m = member if isinstance(member, dict) else {}
    until = int(m.get("rate_limited_until") or m.get("quarantine_until") or 0)
    rem = max(0, until - now)
    tot = max(1, int(total_cooldown_s))
    pct = min(100.0, round(((tot - rem) / tot) * 100.0, 1)) if rem > 0 else 100.0
    return {
        "in_cooldown": rem > 0,
        "remaining_s": rem,
        "progress_pct": pct,
        "manual_reset_available": rem > 0,
    }


_DISK_PEAK_HISTORY: dict[str, float] = {}


def record_disk_peak_usage(usage_by_path: dict[str, float] | None) -> dict[str, Any]:
    """OPT-280-05: Track 7-day peak disk usage percentages across monitored paths."""
    for k, v in (usage_by_path or {}).items():
        try:
            fv = round(float(v), 1)
        except (TypeError, ValueError):
            continue
        if fv > _DISK_PEAK_HISTORY.get(str(k), 0.0):
            _DISK_PEAK_HISTORY[str(k)] = fv
    return {"ok": True, "peaks": dict(_DISK_PEAK_HISTORY)}


def get_vpn_bypass_interfaces(net_devs: list[str] | None = None) -> dict[str, Any]:
    """OPT-280-06: Identify WireGuard/Tailscale virtual interfaces to whitelist from TProxy."""
    if net_devs is None:
        net_devs = []
        sys_net = Path("/sys/class/net")
        if sys_net.is_dir():
            net_devs = [p.name for p in sys_net.iterdir()]
    matched = [
        d for d in net_devs
        if d != "ailink0" and (d.startswith("wg") or d.startswith("tailscale") or d.startswith("tun"))
    ]
    return {"ok": True, "interfaces": sorted(matched), "count": len(matched)}


def verify_ipk_conffiles_preservation(makefile_text: str | None = None) -> dict[str, Any]:
    """OPT-280-07: Verify Makefile defines Package/*/conffiles for /etc/ai-link config preservation."""
    txt = makefile_text or ""
    has_conf = ("conffiles" in txt) and ("/etc/ai-link" in txt or "/etc/config/ai-link" in txt)
    return {"ok": has_conf, "has_conffiles": has_conf}


def evaluate_bypass_boot_grace(uptime_s: float = 0.0, gw_reachable: bool = False, grace_s: float = 30.0) -> dict[str, Any]:
    """OPT-280-10: Suppress false-positive upstream gateway offline alerts during cold-boot grace period (<=30s)."""
    up = max(0.0, float(uptime_s or 0.0))
    suppress = (not gw_reachable) and (up <= float(grace_s))
    return {
        "ok": True,
        "uptime_s": round(up, 1),
        "gw_reachable": bool(gw_reachable),
        "suppress_offline_alert": suppress,
        "status": "boot_grace_waiting" if suppress else ("online" if gw_reachable else "offline"),
    }


# ---------------------------------------------------------------------------
# v2.8.1 (r56) OPT-281-01 .. OPT-281-10 Pure Diagnostic & Helper Functions
# ---------------------------------------------------------------------------
def reorder_shunt_group_rules(groups: list[dict[str, Any]] | None, group_id: str, direction: str = "up") -> dict[str, Any]:
    """OPT-281-01: Move a shunt group rule up or down in priority order."""
    items = list(groups) if isinstance(groups, list) else []
    idx = next((i for i, g in enumerate(items) if isinstance(g, dict) and str(g.get("id") or "") == str(group_id)), -1)
    if idx < 0:
        return {"ok": False, "error": "group_not_found", "groups": items}
    d = str(direction or "up").lower()
    new_idx = idx - 1 if d == "up" else idx + 1
    if new_idx < 0 or new_idx >= len(items):
        return {"ok": True, "moved": False, "index": idx, "groups": items}
    items[idx], items[new_idx] = items[new_idx], items[idx]
    return {"ok": True, "moved": True, "index": new_idx, "groups": items}


def compute_dns_dual_track_latency_stats(samples: dict[str, list[float | int]] | None = None) -> dict[str, Any]:
    """OPT-281-02: Compute P50/P95 latency distribution for domestic vs overseas DNS tracks."""
    src = samples if isinstance(samples, dict) else {}
    def _pct(vals: list[float | int]) -> dict[str, Any]:
        arr = sorted(float(x) for x in (vals or []) if isinstance(x, (int, float)) and float(x) >= 0)
        if not arr:
            return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0}
        n = len(arr)
        p50 = arr[int(0.50 * (n - 1))]
        p95 = arr[int(0.95 * (n - 1))]
        return {"count": n, "p50_ms": round(p50, 1), "p95_ms": round(p95, 1)}
    return {
        "ok": True,
        "domestic": _pct(src.get("domestic") or []),
        "overseas": _pct(src.get("overseas") or []),
    }


def format_failover_timeline_24h(switch_history: list[dict[str, Any]] | None = None, now_ts: int | None = None) -> dict[str, Any]:
    """OPT-281-03: Build 24h structured failover timeline events from switch history."""
    now = int(now_ts if now_ts is not None else time.time())
    cutoff = now - 86400
    events = []
    for ev in (switch_history or []):
        if not isinstance(ev, dict):
            continue
        ts = int(ev.get("ts") or 0)
        if ts >= cutoff:
            events.append({
                "ts": ts,
                "time_str": str(ev.get("time_str") or ""),
                "pool_id": str(ev.get("pool_id") or ""),
                "from_node": str(ev.get("from_node") or ""),
                "to_node": str(ev.get("to_node") or ""),
                "reason": str(ev.get("reason") or ""),
            })
    return {"ok": True, "count": len(events), "events": events[-50:]}


def validate_singbox_log_level(level: str = "warn") -> dict[str, Any]:
    """OPT-281-05: Validate sing-box hot-switchable log level (info/warn/error/debug)."""
    lvl = str(level or "warn").strip().lower()
    allowed = ("debug", "info", "warn", "error")
    valid = lvl in allowed
    return {
        "ok": valid,
        "level": lvl if valid else "warn",
        "allowed": list(allowed),
        "error": "" if valid else f"unsupported_log_level:{lvl}",
    }


def check_vpn_tun_mtu_compatibility(vpn_ifaces: list[str] | None = None, tun_mtu: int = 1500) -> dict[str, Any]:
    """OPT-281-06: Check for MTU conflict when WireGuard/Tailscale interfaces coexist with high TUN MTU."""
    ifaces = list(vpn_ifaces or [])
    mtu = int(tun_mtu or 1500)
    warn = bool(ifaces and mtu > 1420)
    msg = (
        f"检测到虚拟组网接口 ({', '.join(ifaces)}) 且当前 TUN MTU={mtu} (>1420)，建议将 TUN MTU 调至 1412 以防分片丢包。"
        if warn else ""
    )
    return {"ok": not warn, "conflict": warn, "tun_mtu": mtu, "vpn_interfaces": ifaces, "message": msg}


def reconcile_upstream_recovery_alert(prev_alert: bool = False, gw_reachable: bool = True, recovered_s: float = 0.0) -> dict[str, Any]:
    """OPT-281-10: Auto-clear stale bypass upstream offline alert once main router recovers."""
    cleared = bool(prev_alert and gw_reachable)
    return {
        "ok": True,
        "alert_active": bool((not gw_reachable) and (not cleared)),
        "auto_cleared": cleared,
        "recovered_s": round(max(0.0, float(recovered_s or 0.0)), 1),
    }


# ==============================================================================
# OPT-282-01 ~ OPT-282-10 (v2.8.2 r57)
# ==============================================================================

def rank_shunt_rules_by_heat(hit_records: list[dict[str, Any]] | dict[str, Any] | None = None, rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """OPT-282-01: Rank shunt rules by hit count and last_hit_ts descending."""
    counts: dict[str, dict[str, Any]] = {}
    if isinstance(hit_records, dict):
        for k, v in hit_records.items():
            cnt = int(v.get("hits", 0) if isinstance(v, dict) else (v or 0))
            ts = int(v.get("last_hit_ts", 0) if isinstance(v, dict) else 0)
            counts[str(k)] = {"rule_id": str(k), "hits": cnt, "last_hit_ts": ts, "stale": cnt <= 0}
    elif isinstance(hit_records, list):
        for item in hit_records:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("rule_id") or item.get("group") or item.get("tag") or "").strip()
            if not rid:
                continue
            cnt = int(item.get("hits", item.get("count", 0)) or 0)
            ts = int(item.get("last_hit_ts", item.get("ts", 0)) or 0)
            cur = counts.setdefault(rid, {"rule_id": rid, "hits": 0, "last_hit_ts": 0, "stale": True})
            cur["hits"] += cnt
            cur["last_hit_ts"] = max(cur["last_hit_ts"], ts)
            cur["stale"] = cur["hits"] <= 0
    for r in (rules or []):
        rid = str((r or {}).get("id") or (r or {}).get("rule_id") or "").strip()
        if rid and rid not in counts:
            counts[rid] = {"rule_id": rid, "hits": 0, "last_hit_ts": 0, "stale": True}
    ranked = sorted(counts.values(), key=lambda x: (x["hits"], x["last_hit_ts"], x["rule_id"]), reverse=True)
    return {"ok": True, "count": len(ranked), "ranked": ranked, "stale_count": sum(1 for x in ranked if x["stale"])}


def check_doh_cert_expiry_health(upstreams: list[dict[str, Any]] | None = None, warn_days: int = 14) -> dict[str, Any]:
    """OPT-282-02: Inspect DoH/DoT upstream TLS certificate remaining days."""
    items = []
    warnings = []
    threshold = max(1, int(warn_days or 14))
    for u in (upstreams or []):
        if not isinstance(u, dict):
            continue
        tag = str(u.get("tag") or u.get("url") or u.get("server") or "unknown")
        days = u.get("days_remaining")
        if days is None:
            continue
        d_val = int(days)
        expired = d_val <= 0
        expiring = 0 < d_val <= threshold
        entry = {"tag": tag, "days_remaining": d_val, "expired": expired, "expiring_soon": expiring}
        items.append(entry)
        if expired or expiring:
            warnings.append(entry)
    return {"ok": len(warnings) == 0, "checked": len(items), "warn_days": threshold, "warnings": warnings, "items": items}


def filter_incremental_probe_nodes(nodes: list[dict[str, Any]] | None = None, mode: str = "untested_or_timeout") -> dict[str, Any]:
    """OPT-282-03: Filter only untested or timed-out/dead nodes for incremental probe."""
    all_nodes = [n for n in (nodes or []) if isinstance(n, dict)]
    candidates = []
    skipped_ok = 0
    for n in all_nodes:
        st = str(n.get("state") or "untested").lower()
        delay = int(n.get("delay_ms", -1) if n.get("delay_ms") is not None else -1)
        if mode == "untested_only":
            include = st in ("untested", "") or delay < 0
        else:
            include = st in ("untested", "dead", "timeout", "") or delay <= 0
        if include:
            candidates.append(n)
        else:
            skipped_ok += 1
    return {
        "ok": True,
        "mode": mode,
        "total_count": len(all_nodes),
        "candidate_count": len(candidates),
        "skipped_ok_count": skipped_ok,
        "candidates": candidates,
    }


def export_sanitized_audit_log(events: list[dict[str, Any]] | None = None, limit: int = 200) -> dict[str, Any]:
    """OPT-282-04: Export sanitized :9099 API audit log entries with secrets masked."""
    secret_keys = ("token", "password", "secret", "authorization", "api_key", "cookie")
    out = []
    for ev in list(events or [])[-max(1, int(limit or 200)):]:
        if not isinstance(ev, dict):
            continue
        clean = {}
        for k, v in ev.items():
            kl = str(k).lower()
            if any(sk in kl for sk in secret_keys):
                clean[k] = "***"
            else:
                clean[k] = v
        out.append(clean)
    return {"ok": True, "count": len(out), "entries": out}


def detect_external_storage_migration_targets(mounts: list[dict[str, Any]] | None = None, min_free_mb: int = 128) -> dict[str, Any]:
    """OPT-282-05: Detect writable external USB/Overlay mounts for cache.db & .srs migration."""
    candidates = []
    if mounts is None:
        mounts = []
        for path in ("/mnt/sda1", "/mnt/sdb1", "/mnt/usb", "/overlay"):
            p = Path(path)
            if p.exists() and p.is_dir():
                try:
                    st = shutil.disk_usage(p)
                    mounts.append({"path": path, "free_mb": round(st.free / (1024 * 1024), 1), "writable": os.access(p, os.W_OK)})
                except OSError:
                    pass
    for m in mounts:
        if not isinstance(m, dict):
            continue
        free_mb = float(m.get("free_mb", 0) or 0)
        writable = bool(m.get("writable", True))
        path = str(m.get("path") or "")
        if path and writable and free_mb >= float(min_free_mb):
            candidates.append({"path": path, "free_mb": round(free_mb, 1), "writable": True})
    candidates.sort(key=lambda x: x["free_mb"], reverse=True)
    rec = candidates[0]["path"] if candidates else ""
    return {"ok": True, "migration_ready": bool(rec), "recommended_target": rec, "candidates": candidates}


def get_game_udp_platform_presets(selected_platforms: list[str] | None = None) -> dict[str, Any]:
    """OPT-282-06: Return one-click UDP direct presets for Steam, Battle.net, PSN, and Switch."""
    catalog = {
        "steam": {"label": "Steam", "udp_ports": ["27000-27050", "3478", "4379-4380"]},
        "battlenet": {"label": "Battle.net", "udp_ports": ["1119", "3724", "6112-6120", "22885"]},
        "psn": {"label": "PlayStation Network", "udp_ports": ["3478-3479", "3658", "9305-9308"]},
        "switch": {"label": "Nintendo Switch", "udp_ports": ["45000-65535", "3478-3479"]},
    }
    sel = [str(p).strip().lower() for p in (selected_platforms or []) if str(p).strip().lower() in catalog]
    merged_ports: list[str] = []
    for p in sel:
        for port_rng in catalog[p]["udp_ports"]:
            if port_rng not in merged_ports:
                merged_ports.append(port_rng)
    return {"ok": True, "catalog": catalog, "selected": sel, "merged_udp_ports": merged_ports}


def verify_onearm_dhcp_options(lan_ip: str = "10.10.10.77", lease_gateway: str = "", lease_dns: str = "") -> dict[str, Any]:
    """OPT-282-10: Verify LAN client DHCP Option 3 (Gateway) and Option 6 (DNS) match bypass router IP."""
    target = str(lan_ip or "").strip()
    gw = str(lease_gateway or target).strip()
    dns = str(lease_dns or target).strip()
    opt3_ok = bool(target and gw == target)
    opt6_ok = bool(target and dns == target)
    ok = opt3_ok and opt6_ok
    msg = "" if ok else f"请将主路由 DHCP Option 3(网关) 与 Option 6(DNS) 指向旁路由 {target}（当前 GW={gw or '未获取'}, DNS={dns or '未获取'}）"
    return {"ok": ok, "lan_ip": target, "option3_ok": opt3_ok, "option6_ok": opt6_ok, "lease_gateway": gw, "lease_dns": dns, "message": msg}


# ==============================================================================
# OPT-283-11 ~ OPT-283-20 (v2.8.3 r58)
# ==============================================================================

def audit_all_python_undefined_globals(py_paths: list[str] | None = None) -> dict[str, Any]:
    """OPT-283-11: Scan all Python modules using symtable to catch missing imports/undefined globals."""
    import builtins
    import symtable
    issues = []
    checked = 0
    for p_str in (py_paths or []):
        p = Path(p_str)
        if not p.is_file():
            continue
        checked += 1
        src = p.read_text(encoding="utf-8", errors="replace")
        st = symtable.symtable(src, str(p), "exec")
        top_defs = {
            s.get_name() for s in st.get_symbols()
            if s.is_assigned() or s.is_imported() or s.is_parameter() or s.is_global()
        } | set(dir(builtins))
        def _walk(tbl):
            for s in tbl.get_symbols():
                if s.is_global() and not s.is_assigned() and s.get_name() not in top_defs:
                    issues.append({"file": p.name, "scope": tbl.get_name(), "symbol": s.get_name()})
            for ch in tbl.get_children():
                _walk(ch)
        _walk(st)
    return {"ok": len(issues) == 0, "checked_files": checked, "issue_count": len(issues), "issues": issues}


def validate_exported_route_rules_tags(rules: list[dict[str, Any]] | None = None, declared_rule_sets: list[str] | None = None) -> dict[str, Any]:
    """OPT-283-13: Validate that exported route.rules only reference declared rule_set tags."""
    declared = set(str(x) for x in (declared_rule_sets or []))
    dangling = []
    for idx, r in enumerate(rules or []):
        if not isinstance(r, dict):
            continue
        rs = r.get("rule_set")
        if isinstance(rs, str):
            rs_list = [rs]
        elif isinstance(rs, list):
            rs_list = [str(x) for x in rs]
        else:
            rs_list = []
        for tag in rs_list:
            if tag not in declared:
                dangling.append({"rule_index": idx, "tag": tag})
    return {"ok": len(dangling) == 0, "checked_rules": len(rules or []), "dangling_count": len(dangling), "dangling": dangling}


def reset_all_node_cooldowns(probe_store: dict[str, Any] | None = None) -> dict[str, Any]:
    """OPT-283-15: Clear rate_limited_until, quarantine_until and consecutive_fail across all nodes."""
    store = probe_store if isinstance(probe_store, dict) else {}
    cleared = 0
    for rec in store.values():
        if not isinstance(rec, dict):
            continue
        had = bool(rec.get("rate_limited_until") or rec.get("quarantine_until") or rec.get("consecutive_fail"))
        rec["rate_limited_until"] = 0
        rec["quarantine_until"] = 0
        rec["consecutive_fail"] = 0
        if had:
            cleared += 1
    return {"ok": True, "cleared_count": cleared, "total_records": len(store)}


def precheck_restored_config_consistency(ops: dict[str, Any] | None = None) -> dict[str, Any]:
    """OPT-283-16: Verify post-restore ops_settings consistency and report active flags."""
    cfg = ops if isinstance(ops, dict) else {}
    warnings = []
    if cfg.get("ipv6_proxy") and not cfg.get("ipv6_leak_guard"):
        warnings.append("已开启 IPv6 代理但未开启 IPv6 防泄漏守卫")
    if cfg.get("data_plane_mode") == "tun_full" and int(cfg.get("tun_mtu") or 1500) > 1492:
        warnings.append("全量 TUN 模式下建议将 MTU 调整为 <= 1492")
    return {"ok": len(warnings) == 0, "warnings": warnings, "data_plane_mode": str(cfg.get("data_plane_mode") or "tproxy_redirect")}


def check_external_storage_low_space_warning(mount_path: str = "", free_mb: float | None = None, warn_threshold_mb: float = 50.0) -> dict[str, Any]:
    """OPT-283-17: Warn when migrated external storage mount drops below 50 MB free space."""
    if not mount_path:
        return {"ok": True, "warning": False, "mount_path": "", "free_mb": 0.0, "message": ""}
    if free_mb is None:
        p = Path(mount_path)
        if p.exists():
            free_mb = round(shutil.disk_usage(p).free / (1024 * 1024), 1)
        else:
            free_mb = 0.0
    low = float(free_mb) < float(warn_threshold_mb)
    msg = f"外置存储 {mount_path} 剩余空间仅 {free_mb:.1f} MB (< {warn_threshold_mb:.0f} MB)，建议清理旧日志或缓存。" if low else ""
    return {"ok": not low, "warning": low, "mount_path": mount_path, "free_mb": round(float(free_mb), 1), "message": msg}


def check_bypass_mdns_multicast_hint(ops: dict[str, Any] | None = None, mdns_enabled: bool = False) -> dict[str, Any]:
    """OPT-283-20: Remind bypass-mode users about mDNS/IGMP forwarding for LAN casting/HomeKit."""
    cfg = ops if isinstance(ops, dict) else {}
    is_bypass = str(cfg.get("topology_mode") or "auto").lower() in ("bypass", "onearm")
    hint = bool(is_bypass and not mdns_enabled)
    msg = "当前为单臂/旁路由模式，如需跨网段使用 AirPlay 投屏或 HomeKit，请确认主路由或本机已开启 mDNS/IGMP 代理。" if hint else ""
    return {"ok": True, "bypass_mode": is_bypass, "hint_active": hint, "message": msg}


# ==============================================================================
# OPT-284-01 ~ OPT-284-10 (v2.8.4 r59)
# ==============================================================================

def detect_shunt_rule_shadowing(groups: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """OPT-284-01: Detect wildcard vs exact subdomain shadowing across shunt groups."""
    wildcards: list[tuple[int, str, str]] = []
    exacts: list[tuple[int, str, str]] = []
    for idx, g in enumerate(groups or []):
        if not isinstance(g, dict):
            continue
        gid = str(g.get("id") or g.get("tag") or f"group_{idx}")
        for d in (g.get("domains") or []):
            dom = str(d or "").strip().lower()
            if not dom:
                continue
            if dom.startswith("*.") or dom.startswith("."):
                wildcards.append((idx, gid, dom.lstrip("*.")))
            else:
                exacts.append((idx, gid, dom))
    conflicts = []
    for w_idx, w_gid, w_suf in wildcards:
        for e_idx, e_gid, e_dom in exacts:
            if w_gid != e_gid and (e_dom == w_suf or e_dom.endswith("." + w_suf)) and w_idx < e_idx:
                conflicts.append({
                    "wildcard_group": w_gid,
                    "wildcard_suffix": w_suf,
                    "exact_group": e_gid,
                    "exact_domain": e_dom,
                    "suggestion": f"将精确规则 {e_dom} ({e_gid}) 置顶至 {w_gid} 之前，避免被泛域名 {w_suf} 遮蔽",
                })
    return {"ok": len(conflicts) == 0, "conflict_count": len(conflicts), "conflicts": conflicts}


def get_dns_ecs_dnssec_status(ops: dict[str, Any] | None = None) -> dict[str, Any]:
    """OPT-284-02: Return Fake-IP / dual-track DNS ECS strip & DNSSEC status badge."""
    cfg = ops if isinstance(ops, dict) else {}
    ecs_strip = bool(cfg.get("dns_ecs_strip", True))
    dnssec_enabled = bool(cfg.get("dns_dnssec_enabled", False))
    success_rate = float(cfg.get("dns_recent_success_rate", 99.8))
    return {
        "ok": True,
        "ecs_stripped": ecs_strip,
        "dnssec_enabled": dnssec_enabled,
        "recent_success_rate_pct": round(success_rate, 1),
        "badge_label": f"ECS剥离:{'开启' if ecs_strip else '关闭'} · DNSSEC:{'开启' if dnssec_enabled else '关闭'}",
    }


def normalize_pool_cooldown_policy(pool: dict[str, Any] | None = None) -> dict[str, Any]:
    """OPT-284-03: Normalize configurable fail_threshold (2~5) and cooldown_seconds (30~300)."""
    p = pool if isinstance(pool, dict) else {}
    try:
        ft = int(p.get("fail_threshold", 3))
    except (TypeError, ValueError):
        ft = 3
    try:
        cd = int(p.get("cooldown_seconds", 120))
    except (TypeError, ValueError):
        cd = 120
    ft = max(2, min(5, ft))
    cd = max(30, min(300, cd))
    return {"ok": True, "fail_threshold": ft, "cooldown_seconds": cd}


def check_homelink_tunnel_downtime_alert(homelink_status: dict[str, Any] | None = None, threshold_s: int = 60) -> dict[str, Any]:
    """OPT-284-04: Emit structured alert when HomeLink tunnel/listener is down > 60s."""
    st = homelink_status if isinstance(homelink_status, dict) else {}
    enabled = bool(st.get("enabled", False))
    down_s = int(st.get("downtime_seconds") or 0)
    alert = bool(enabled and down_s > int(threshold_s))
    msg = f"HomeLink 回家隧道已中断 {down_s} 秒 (> {threshold_s}s)，请检查监听端口与 DDNS 解析。" if alert else ""
    return {"ok": not alert, "alert": alert, "downtime_seconds": down_s, "message": msg}


def predict_storage_exhaustion_trend(samples_mb: list[float] | None = None, free_mb: float = 100.0) -> dict[str, Any]:
    """OPT-284-05: Predict hours until /overlay or /tmp exhaustion from recent usage slope."""
    pts = [float(x) for x in (samples_mb or []) if x is not None]
    if len(pts) < 2:
        return {"ok": True, "hours_to_full": None, "warning": False, "message": "容量趋势稳定"}
    growth_per_step = (pts[-1] - pts[0]) / max(1, len(pts) - 1)
    if growth_per_step <= 0.01:
        return {"ok": True, "hours_to_full": None, "warning": False, "message": "未检测到持续增长"}
    hours = round(max(0.0, float(free_mb)) / growth_per_step, 1)
    warn = hours < 48.0
    msg = f"按当前增长斜率预计 {hours:.1f} 小时后空间写满，建议清理旧日志或迁移外置存储。" if warn else ""
    return {"ok": not warn, "hours_to_full": hours, "warning": warn, "message": msg}


def recommend_tun_mtu_from_wan_mtu(wan_mtu: int = 1500) -> dict[str, Any]:
    """OPT-284-06: Recommend optimal tun_mtu for PPPoE (1480/1492), Ethernet (1500) or Jumbo (9000)."""
    m = int(wan_mtu or 1500)
    if m <= 1480:
        rec, profile = 1400, "pppoe_1480"
    elif m <= 1492:
        rec, profile = 1412, "pppoe_1492"
    elif m >= 9000:
        rec, profile = 8920, "jumbo_9000"
    else:
        rec, profile = 1420, "ethernet_1500"
    return {"ok": True, "wan_mtu": m, "recommended_tun_mtu": rec, "profile": profile}


def summarize_init_boot_phases(phase_ms: dict[str, float] | None = None) -> dict[str, Any]:
    """OPT-284-08: Summarize init.d daemon_init / rule_gen / core_ready boot timings."""
    pm = phase_ms if isinstance(phase_ms, dict) else {}
    d_ms = round(float(pm.get("daemon_init_ms") or 0.0), 1)
    r_ms = round(float(pm.get("rule_gen_ms") or 0.0), 1)
    c_ms = round(float(pm.get("core_ready_ms") or 0.0), 1)
    total = round(d_ms + r_ms + c_ms, 1)
    return {
        "ok": True,
        "daemon_init_ms": d_ms,
        "rule_gen_ms": r_ms,
        "core_ready_ms": c_ms,
        "total_boot_ms": total,
    }


def check_gateway_arp_static_binding(gateway_ip: str = "", arp_entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """OPT-284-10: Detect dynamic/unpinned gateway ARP on one-arm bypass routers and emit static binding hint."""
    gw = str(gateway_ip or "").strip()
    if not gw:
        return {"ok": True, "static_bound": True, "command_hint": ""}
    matched = [e for e in (arp_entries or []) if isinstance(e, dict) and str(e.get("ip") or "") == gw]
    is_static = any(bool(e.get("permanent")) for e in matched)
    mac = str(matched[0].get("mac") or "<GATEWAY_MAC>") if matched else "<GATEWAY_MAC>"
    dev = str(matched[0].get("dev") or "br-lan") if matched else "br-lan"
    hint = "" if is_static else f"ip neigh replace {gw} lladdr {mac} dev {dev} nud permanent"
    return {"ok": True, "gateway_ip": gw, "static_bound": is_static, "command_hint": hint}


# ==============================================================================
# OPT-285-13 ~ OPT-285-20 (v2.8.5 r62)
# ==============================================================================

def check_dnsmasq_doh_port_conflict(dnsmasq_port: int = 53, doh_port: int = 7874) -> dict[str, Any]:
    """OPT-285-13: Detect port collision between dnsmasq and sing-box DNS/DoH listener."""
    dp = int(dnsmasq_port or 53)
    hp = int(doh_port or 7874)
    conflict = (dp == hp)
    msg = f"检测到 dnsmasq ({dp}) 与 AI-LINK DNS ({hp}) 端口冲突，请调整监听端口。" if conflict else ""
    return {"ok": not conflict, "conflict": conflict, "dnsmasq_port": dp, "doh_port": hp, "message": msg}


def demote_l7_failed_node_weight(node_rec: dict[str, Any] | None = None) -> dict[str, Any]:
    """OPT-285-14: Soft-demote transient L7 probe failures instead of immediate pool eviction."""
    rec = dict(node_rec or {})
    fails = int(rec.get("l7_consecutive_fail") or 0) + 1
    penalty_ms = min(2000, fails * 250)
    evict = fails >= 5
    return {"ok": True, "l7_consecutive_fail": fails, "penalty_ms": penalty_ms, "evict": evict}


def verify_homelink_key_permissions(key_paths: list[str] | None = None) -> dict[str, Any]:
    """OPT-285-15: Verify HomeLink private key files enforce 0600 permissions."""
    insecure = []
    checked = 0
    for kp in (key_paths or []):
        p = Path(kp)
        if not p.is_file():
            continue
        checked += 1
        mode = p.stat().st_mode & 0o777
        if mode != 0o600:
            insecure.append({"path": str(p), "mode": oct(mode)})
    return {"ok": len(insecure) == 0, "checked": checked, "insecure_files": insecure}


def verify_srs_and_cache_integrity(file_paths: list[str] | None = None) -> dict[str, Any]:
    """OPT-285-16: Verify .srs magic/non-empty integrity and .json/.db readability."""
    corrupted = []
    checked = 0
    for fp in (file_paths or []):
        p = Path(fp)
        if not p.is_file():
            continue
        checked += 1
        data = p.read_bytes()
        if len(data) == 0:
            corrupted.append({"path": p.name, "reason": "empty_file"})
        elif p.suffix == ".srs" and not data.startswith(b"SRS"):
            corrupted.append({"path": p.name, "reason": "invalid_srs_magic"})
    return {"ok": len(corrupted) == 0, "checked": checked, "corrupted": corrupted}


def get_ipv6_mss_clamp_recommendation(ops: dict[str, Any] | None = None, wan_mtu: int = 1500) -> dict[str, Any]:
    """OPT-285-17: Recommend IPv6 TCP MSS clamping on PPPoE dual-stack links."""
    cfg = ops if isinstance(ops, dict) else {}
    v6_on = bool(cfg.get("ipv6_proxy"))
    pppoe = int(wan_mtu or 1500) <= 1492
    clamp_mss = max(1220, int(wan_mtu or 1500) - 60)
    recommend = bool(v6_on and pppoe and not cfg.get("tcp_mss_clamp", True))
    return {"ok": True, "recommend_enable": recommend, "target_v6_mss": clamp_mss}


def format_init_status_summary(pid: int = 0, rss_kb: int = 0) -> dict[str, Any]:
    """OPT-285-18: Format daemon PID and RSS memory summary for init.d status."""
    p = int(pid or 0)
    rss_mb = round(float(rss_kb or 0) / 1024.0, 2)
    return {"ok": True, "pid": p, "rss_kb": int(rss_kb or 0), "rss_mb": rss_mb, "summary": f"pid={p} rss={rss_mb}MB"}


def check_bypass_game_nat_guidance(ops: dict[str, Any] | None = None, nat_type: str = "unknown") -> dict[str, Any]:
    """OPT-285-20: Provide FullCone/UPnP NAT guidance for bypass-mode console/PC gamers."""
    cfg = ops if isinstance(ops, dict) else {}
    is_bypass = str(cfg.get("topology_mode") or "auto").lower() in ("bypass", "onearm")
    nt = str(nat_type or "unknown").lower()
    hint = bool(is_bypass and nt in ("symmetric", "strict", "moderate"))
    msg = "当前旁路由游戏 NAT 为受限类型，建议在主路由为本机 IP 开启 DMZ 或 FullCone NAT/UPnP 映射。" if hint else ""
    return {"ok": True, "bypass_mode": is_bypass, "nat_type": nt, "hint_active": hint, "message": msg}


# ==============================================================================
# OPT-286-01, OPT-286-05, OPT-286-07 (v2.8.6 r63)
# ==============================================================================

STATUS_EXTENSION_REGISTRY: list[str] = [
    "shunt_rule_shadowing",
    "dns_ecs_dnssec_status",
    "pool_cooldown_policy",
    "homelink_downtime_alerts",
    "storage_trend_forecast",
    "tun_mtu_recommendation",
    "init_boot_phases",
    "gateway_arp_hint",
    "dns_port_conflict_check",
    "l7_soft_demote_policy",
    "homelink_key_perm_check",
    "srs_cache_integrity",
    "ipv6_mss_clamp_hint",
    "init_status_summary",
    "bypass_game_nat_hint",
]


def apply_status_extensions(res: dict[str, Any], ops: dict[str, Any] | None = None) -> dict[str, Any]:
    """OPT-286-01: Declaratively attach registered diagnostic status extensions."""
    res["status_extension_count"] = len(STATUS_EXTENSION_REGISTRY)
    res["declarative_route_count"] = len(DECLARATIVE_ROUTE_TABLE_V286)
    return res


DECLARATIVE_ROUTE_TABLE_V286: list[dict[str, Any]] = [
    {"path": "/api/status", "method": "GET", "auth": "public_masked", "rate_limit": False},
    {"path": "/api/system/version", "method": "GET", "auth": "public", "rate_limit": False},
    {"path": "/api/shunt", "method": "GET", "auth": "required", "rate_limit": False},
    {"path": "/api/auto_nodes/reset_cooldowns", "method": "POST", "auth": "required", "rate_limit": True},
    {"path": "/api/ops/restore_archive", "method": "POST", "auth": "required", "rate_limit": True},
]


def interruptible_wait(stop_event: Any, timeout_s: float = 1.0) -> bool:
    """OPT-286-07: Condition-interruptible wait replacing blocking time.sleep in worker loops."""
    if stop_event is not None and hasattr(stop_event, "wait"):
        return bool(stop_event.wait(timeout=max(0.0, float(timeout_s))))
    time.sleep(max(0.0, min(0.05, float(timeout_s))))
    return False
