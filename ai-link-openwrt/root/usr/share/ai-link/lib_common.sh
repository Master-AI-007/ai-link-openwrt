#!/bin/sh
# OPT-286-10: Shared OpenWrt port & UCI helper functions (SSOT)
ailink_uci_get() {
  uci -q get "ai-link.global.$1" 2>/dev/null || echo "${2:-}"
}
ailink_port_listening() {
  local port="$1"
  ss -lnt 2>/dev/null | grep -q ":${port}[[:space:]]" || netstat -lnt 2>/dev/null | grep -q ":${port}[[:space:]]"
}
