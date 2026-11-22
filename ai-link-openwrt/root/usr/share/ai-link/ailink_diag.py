# -*- coding: utf-8 -*-
"""AI-LINK Diagnostic & Audit Pure-Function Submodule (OPT-275-01 / OPT-276-01)."""


def sanitize_singbox_outbound_tag(tag: str, max_bytes: int = 64) -> str:
    """OPT-275-03: UTF-8 safe byte-length truncation guard for sing-box outbound tags."""
    raw = str(tag or "").strip()
    enc = raw.encode("utf-8")
    if len(enc) <= max_bytes:
        return raw
    return enc[:max_bytes].decode("utf-8", errors="ignore").rstrip()


def score_node_with_sub_priority(delay_ms: float, sub_priority: int = 1) -> float:
    """OPT-275-05: Weight node latency score by subscription priority (lower is better)."""
    base = max(1.0, float(delay_ms or 9999.0))
    prio_bonus = max(0, min(5, int(sub_priority or 1) - 1)) * 15.0
    return round(base + prio_bonus, 2)


def summarize_backup_redacted_fields(backup_obj: dict | None = None) -> dict:
    """OPT-275-06: List redacted credential fields before backup export/import."""
    obj = backup_obj if isinstance(backup_obj, dict) else {}
    redacted = []
    for k in ("panel_secret", "token", "password", "uuid", "private_key"):
        if k in obj or (isinstance(obj.get("ops_settings"), dict) and k in obj["ops_settings"]):
            redacted.append(k)
    return {"ok": True, "redacted_fields": redacted, "has_redacted": len(redacted) > 0}


def build_diag_module_manifest() -> dict:
    return {
        "module": "ailink_diag",
        "version": "2.7.6",
        "functions": [
            "sanitize_singbox_outbound_tag",
            "score_node_with_sub_priority",
            "summarize_backup_redacted_fields",
        ],
    }
