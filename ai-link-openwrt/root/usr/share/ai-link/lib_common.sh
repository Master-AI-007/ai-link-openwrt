#!/bin/sh
# OPT-286-10: Shared OpenWrt port & UCI helper functions (SSOT)
ailink_uci_get() {
  uci -q get "ai-link.global.$1" 2>/dev/null || echo "${2:-}"
}
ailink_port_listening() {
  local port="$1"
  ss -lnt 2>/dev/null | grep -q ":${port}[[:space:]]" || netstat -lnt 2>/dev/null | grep -q ":${port}[[:space:]]"
}

# OPT-288-07: Fine-grained 0.2s polling wait with bounded timeout (in 0.2s ticks)
ailink_poll_wait() {
  local check_fn="$1"
  local max_ticks="${2:-15}"
  local _i=0
  while [ "$_i" -lt "$max_ticks" ]; do
    if eval "$check_fn" >/dev/null 2>&1; then
      return 0
    fi
    usleep 200000 2>/dev/null || sleep 1
    _i=$((_i + 1))
  done
  return 1
}

# OPT-292-06: Shared boolean UCI reader
uci_get_bool() {
  local val
  val="$(ailink_uci_get "$1" "${2:-0}")"
  case "$val" in
    1|true|yes|on|enabled) echo "1" ;;
    *) echo "0" ;;
  esac
}
