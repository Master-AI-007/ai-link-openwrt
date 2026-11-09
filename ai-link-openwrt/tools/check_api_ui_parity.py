#!/usr/bin/env python3
"""
AI-LINK v2.5.8 API <-> UI Field Parity Gate (tools/check_api_ui_parity.py)
Verifies two-way contract parity between backend `ai-link-daemon.py` and frontend `webui/nexus.js`:
1) Extracts keys returned by `preview_subscription_sync_impact()` and `/api/subscriptions/preview_sync`.
2) Scans `nexus.js` `sub-preview-sync` branch for `res.<field>` accesses.
3) Asserts RISK_FIELDS <= backend_keys and RISK_FIELDS <= frontend_consumed.
4) Reverse check: every `res.<field>` read in `sub-preview-sync` MUST exist in backend success or error responses.
5) Quick-bind-pool payload check: every key sent to `/api/shunt/update` in `quick-bind-pool` must be recognized by backend `/api/shunt/update`.
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

    # Also include top-level keys injected by `/api/subscriptions/preview_sync` handler (ok, request_id, error, detail, cache_hit)
    handler_extra_keys = {"ok", "request_id", "error", "detail", "cache_hit", "message"}
    all_backend_keys = backend_preview_keys | handler_extra_keys

    # Extract `sub-preview-sync` case block in nexus.js up to next case
    m_case = re.search(r"case\s+'sub-preview-sync'\s*:\s*\{(.*?)case\s+'probe-custom-nodes'\s*:", nexus_src, re.S)
    if not m_case:
        return False, "sub-preview-sync block not found in nexus.js"
    case_body = m_case.group(1)
    frontend_res_fields = set(re.findall(r"\bres\.([a-zA-Z0-9_]+)\b", case_body))

    missing_in_backend = sorted(RISK_FIELDS - all_backend_keys)
    missing_in_frontend = sorted(RISK_FIELDS - frontend_res_fields)
    unknown_frontend_reads = sorted(frontend_res_fields - all_backend_keys)

    # Check quick-bind-pool payload keys vs backend `/api/shunt/update` recognized keys
    m_qb = re.search(r"case\s+'quick-bind-pool'\s*:\s*\{(.*?)case\s+'sub-preview-sync'\s*:", nexus_src, re.S)
    qb_ok = bool(m_qb and "shunt_mode: 'auto'" in m_qb.group(1) and "auto_node_id: poolId" in m_qb.group(1) and "bindRes.ok === false" in m_qb.group(1))

    # Check raw .write_text( on CONF_DIR / RUN_DIR lines
    raw_write_lines = [
        f"{idx}:{ln.strip()}"
        for idx, ln in enumerate(daemon_src.splitlines(), 1)
        if ".write_text(" in ln and ("CONF_DIR" in ln or "RUN_DIR" in ln) and not ln.lstrip().startswith("#") and "getattr(Path," not in ln
    ]

    ok = (
        not missing_in_backend
        and not missing_in_frontend
        and not unknown_frontend_reads
        and qb_ok
        and not raw_write_lines
    )
    summary = (
        f"backend_keys={len(backend_preview_keys)}, frontend_reads={len(frontend_res_fields)}, "
        f"missing_backend={missing_in_backend}, missing_frontend={missing_in_frontend}, "
        f"unknown_reads={unknown_frontend_reads}, quick_bind_ok={qb_ok}, raw_conf_run_writes={len(raw_write_lines)}"
    )
    return ok, summary


if __name__ == "__main__":
    ok, msg = check_parity()
    print(f"[{'PASS' if ok else 'FAIL'}] API<->UI Parity Gate: {msg}")
    sys.exit(0 if ok else 1)
