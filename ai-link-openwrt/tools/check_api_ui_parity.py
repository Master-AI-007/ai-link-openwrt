#!/usr/bin/env python3
"""
AI-LINK v2.5.9 API <-> UI Field, Type & Location Parity Gate (tools/check_api_ui_parity.py)
Verifies two-way contract parity between backend `ai-link-daemon.py` and frontend `webui/nexus.js`:
1) Extracts keys returned by `preview_subscription_sync_impact()` and `/api/subscriptions/preview_sync`.
2) Scans `nexus.js` `sub-preview-sync` branch for `res.<field>` accesses (forward & reverse checks).
3) Verifies type & nesting location parity for `bound_group_targets` (Array of {group_name, current_node, delay_ms, shared_exit}),
   `multi_line_rotation_log` (top-level & per-pool list), and `dwell_bypass_calls` (top-level int consumed in UI).
4) Verifies `quick-bind-pool` payload keys and 0 raw `.write_text(` on `CONF_DIR`/`RUN_DIR`.
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAEMON_PATH = ROOT / "root/usr/share/ai-link/ai-link-daemon.py"
NEXUS_JS_PATH = ROOT / "root/usr/share/ai-link/webui/nexus.js"

RISK_FIELDS = {
    "ok",
    "request_id",
    "stability_warning",
    "dynamic_random_sub",
    "jaccard_stability",
    "impact_ratio",
    "impact_pct",
    "nodes_fingerprint",
    "preserved_count",
    "added_count",
    "removed_count",
    "renamed_count",
    "endpoint_changed_count",
    "credential_changed_count",
    "same_tag_replaced_count",
    "endpoint_changed_tags",
    "credential_changed_tags",
    "same_tag_replaced_tags",
    "affected_pools",
}


def check_parity(daemon_path: Path = DAEMON_PATH, nexus_js_path: Path = NEXUS_JS_PATH) -> tuple[bool, str]:
    daemon_src = daemon_path.read_text(encoding="utf-8")
    nexus_src = nexus_js_path.read_text(encoding="utf-8")

    tree = ast.parse(daemon_src)
    backend_preview_keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "preview_subscription_sync_impact":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Dict):
                    for k in sub.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            backend_preview_keys.add(k.value)

    handler_extra_keys = {"ok", "request_id", "error", "detail", "cache_hit", "message"}
    all_backend_keys = backend_preview_keys | handler_extra_keys

    m_case = re.search(r"case\s+'sub-preview-sync'\s*:\s*\{(.*?)case\s+'probe-custom-nodes'\s*:", nexus_src, re.S)
    if not m_case:
        return False, "sub-preview-sync block not found in nexus.js"
    case_body = m_case.group(1)
    frontend_res_fields = set(re.findall(r"\bres\.([a-zA-Z0-9_]+)\b", case_body))

    missing_in_backend = sorted(RISK_FIELDS - all_backend_keys)
    missing_in_frontend = sorted(RISK_FIELDS - frontend_res_fields)
    unknown_frontend_reads = sorted(frontend_res_fields - all_backend_keys)

    # P2-1b: Verify type & nesting location parity for bound_group_targets, multi_line_rotation_log, and dwell_bypass_calls
    bgt_type_ok = (
        "Array.isArray(p.bound_group_targets)" in nexus_src
        and "Array.isArray(a.bound_group_targets)" in nexus_src
        and "Object.entries(bgtObj)" not in nexus_src
        and all(f"x.{k}" in nexus_src for k in ("group_name", "current_node", "delay_ms", "shared_exit"))
    )
    rot_loc_ok = (
        "sh.multi_line_rotation_log" in nexus_src
        and "stRes.multi_line_rotation_log" in nexus_src
        and "state.multiLineRotationLog" in nexus_src
        and "[多出口轮询]" in nexus_src
    )
    dwell_loc_ok = (
        "sh.dwell_bypass_calls" in nexus_src
        and "stRes.dwell_bypass_calls" in nexus_src
        and "state.dwellBypassCalls" in nexus_src
    )
    obs_type_loc_ok = bool(bgt_type_ok and rot_loc_ok and dwell_loc_ok)

    # Check quick-bind-pool payload keys vs backend `/api/shunt/update` recognized keys
    m_qb = re.search(r"case\s+'quick-bind-pool'\s*:\s*\{(.*?)case\s+'sub-preview-sync'\s*:", nexus_src, re.S)
    qb_ok = bool(m_qb and "shunt_mode: 'auto'" in m_qb.group(1) and "auto_node_id: poolId" in m_qb.group(1) and "bindRes.ok === false" in m_qb.group(1))

    # Check raw .write_text( on CONF_DIR / RUN_DIR lines
    raw_write_lines = [
        f"{idx}:{ln.strip()}"
        for idx, ln in enumerate(daemon_src.splitlines(), 1)
        if ".write_text(" in ln and ("CONF_DIR" in ln or "RUN_DIR" in ln) and not ln.lstrip().startswith("#") and "getattr(Path," not in ln
    ]

    # v2.5.11 P0-1 & P2-1 Gate: Verify 100% of frontend literal /api/* paths exist in backend, all onUndo check res.ok, and drill verification fields are consumed in UI
    js_api_paths = set(re.findall(r"['\"](/api/[a-zA-Z0-9_/\-]+)", nexus_src))
    py_api_paths = set(re.findall(r"['\"](/api/[a-zA-Z0-9_/\-]+)", daemon_src))
    missing_api_routes = sorted(
        p_api for p_api in js_api_paths
        if p_api not in py_api_paths and not p_api.endswith("/")
    )
    drill_ui_refs = sum(nexus_src.count(k) for k in ("plane_verified", "plane_untouched", "in_pool_scope", "selector_plane"))
    drill_ui_ok = (
        "plane_verified" in nexus_src
        and "plane_untouched" in nexus_src
        and "in_pool_scope" in nexus_src
        and "selector_plane" in nexus_src
        and drill_ui_refs >= 6
    )
    undo_blocks = [nexus_src[m.start():m.start()+1300] for m in re.finditer(r"onUndo\s*:\s*async\s*\(\)\s*=>\s*\{", nexus_src)]
    unprotected_undos = [b[:60].strip() for b in undo_blocks if "callRouterApi(" in b and "uRes.ok === false" not in b]

    ok = (
        not missing_in_backend
        and not missing_in_frontend
        and not unknown_frontend_reads
        and obs_type_loc_ok
        and qb_ok
        and not raw_write_lines
        and not missing_api_routes
        and drill_ui_ok
        and not unprotected_undos
    )
    summary = (
        f"backend_keys={len(backend_preview_keys)}, frontend_reads={len(frontend_res_fields)}, "
        f"missing_backend={missing_in_backend}, missing_frontend={missing_in_frontend}, "
        f"unknown_reads={unknown_frontend_reads}, obs_type_loc_ok={obs_type_loc_ok} "
        f"(bgt_arr={bgt_type_ok}, rot_top={rot_loc_ok}, dwell={dwell_loc_ok}), "
        f"quick_bind_ok={qb_ok}, api_routes={len(js_api_paths)}(missing={missing_api_routes}), "
        f"drill_ui_refs={drill_ui_refs}, unprotected_undos={len(unprotected_undos)}, raw_conf_run_writes={len(raw_write_lines)}"
    )
    return ok, summary


if __name__ == "__main__":
    ok, msg = check_parity()
    print(f"[{'PASS' if ok else 'FAIL'}] API<->UI Parity Gate: {msg}")
    sys.exit(0 if ok else 1)
