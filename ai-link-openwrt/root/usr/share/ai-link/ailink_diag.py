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
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

DIAG_MODULE_VERSION = "2.7.8"

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
