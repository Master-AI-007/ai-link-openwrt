# -*- coding: utf-8 -*-
"""AI-LINK Diagnostic & Audit Pure-Function Submodule (OPT-275-01)."""


def build_diag_module_manifest() -> dict:
    return {
        "module": "ailink_diag",
        "version": "2.7.5",
        "functions": [
            "sanitize_singbox_outbound_tag",
            "score_node_with_sub_priority",
            "summarize_backup_redacted_fields",
        ],
    }
