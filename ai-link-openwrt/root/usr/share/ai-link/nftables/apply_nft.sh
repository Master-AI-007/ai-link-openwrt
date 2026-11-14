#!/bin/sh
# AI-LINK v24 Unified Single-Source fw4/nftables Loader (P0-1 BusyBox flock 3-Tier Lock Hardened)
# Note: Ruleset generation is unified in /usr/share/ai-link/ai-link-daemon.py (--generate-nft)
# with 3-tier lock serialization (util-linux flock -w -> BusyBox flock -n loop -> mkdir spinlock),
# atomic temp-file replacement, and non-silent error reporting.

if command -v modprobe >/dev/null 2>&1; then
	for _m in nft_queue nft_nat nft_redir nft_tproxy nft_socket nft_fib_inet nft_ct; do
		modprobe "$_m" >/dev/null 2>&1 || true
	done
fi

LOG_FILE="${AI_LINK_LOG_FILE:-/var/log/ai-link.log}"
RUN_DIR="${AI_LINK_RUN_DIR:-/var/run/ai-link}"
mkdir -p "$RUN_DIR" 2>/dev/null || { RUN_DIR="/tmp/ai-link"; mkdir -p "$RUN_DIR"; }
NFT_FILE="$RUN_DIR/ai-link.nft"
STATUS_FILE="$RUN_DIR/nft_apply_status.json"
LOCK_FILE="$RUN_DIR/apply_nft.lock"
LOCK_DIR="$RUN_DIR/apply_nft.lockdir"
DAEMON_PY="${AI_LINK_DAEMON_PY:-/usr/share/ai-link/ai-link-daemon.py}"
NORM_PY="${AI_LINK_NORM_PY:-/usr/share/ai-link/nftables/normalize_nft_sets.py}"

acquire_nft_lock() {
	if command -v flock >/dev/null 2>&1; then
		exec 9>"$LOCK_FILE"
		# Tier 1: Immediate non-blocking flock -x -n (supported by both BusyBox flock [-sxun] and util-linux flock)
		if flock -x -n 9 2>/dev/null; then
			return 0
		fi
		# Tier 2a: Try util-linux flock -x -w 18 if supported
		if flock -x -w 18 9 2>/dev/null; then
			return 0
		fi
		# Tier 2b: BusyBox flock polling loop (up to 90 * 0.2s = 18s) when -w is unsupported
		_fl_w=0
		while [ "$_fl_w" -lt 90 ]; do
			if flock -x -n 9 2>/dev/null; then
				return 0
			fi
			_fl_w=$((_fl_w + 1))
			sleep 0.2 2>/dev/null || sleep 1
		done
	fi
	# Tier 3: Portable mkdir spinlock fallback (with stale lock recovery)
	_wait=0
	while ! mkdir "$LOCK_DIR" 2>/dev/null; do
		_wait=$((_wait + 1))
		if [ "$_wait" -ge 90 ]; then
			rm -rf "$LOCK_DIR" 2>/dev/null || true
			mkdir "$LOCK_DIR" 2>/dev/null || return 1
			break
		fi
		sleep 0.2 2>/dev/null || sleep 1
	done
	trap 'rm -rf "$LOCK_DIR" 2>/dev/null || true' EXIT INT TERM
	return 0
}

write_nft_status() {
	_ok="$1"
	_rc="$2"
	_msg="$3"
	_ts=$(date +%s 2>/dev/null || echo 0)
	_clean_msg=$(printf "%s" "$_msg" | tr '\r\n\t"' '    ' | cut -c1-360)
	printf '{"ok": %s, "ts": %s, "rc": %s, "error": "%s"}\n' "$_ok" "$_ts" "$_rc" "$_clean_msg" > "$STATUS_FILE.tmp.$$" 2>/dev/null \
		&& mv -f "$STATUS_FILE.tmp.$$" "$STATUS_FILE" 2>/dev/null || true
}

acquire_nft_lock || {
	logger -t "ai-link" "ERROR: apply_nft.sh lock timeout after 18s"
	write_nft_status "false" "1" "apply_nft.sh 互斥锁等待超时 (lock_timeout)"
	exit 1
}

# §2.1 Anti-OOM Single-Process Optimization:
# When invoked by the resident daemon (`AI_LINK_NFT_PREGENERATED=1`) and `$NFT_FILE` is already freshly written
# and normalized in-memory, skip spawning a second Python process to re-parse the 1.7MB daemon script.
if [ "${AI_LINK_NFT_PREGENERATED:-0}" = "1" ] && [ -s "$NFT_FILE" ] && [ $# -eq 0 ]; then
	: # Pre-generated and normalized in-memory by resident ai-link-daemon
else
	if command -v python3 >/dev/null 2>&1 && [ -f "$DAEMON_PY" ]; then
		python3 -B "$DAEMON_PY" --generate-nft "$@" >/dev/null 2>&1 || true
	fi
	if [ ! -s "$NFT_FILE" ]; then
		logger -t "ai-link" "ERROR: $NFT_FILE not found or empty and daemon generator unavailable"
		write_nft_status "false" "1" "防火墙规则文件未生成或为空 ($NFT_FILE)"
		exit 1
	fi
	if command -v python3 >/dev/null 2>&1 && [ -f "$NORM_PY" ]; then
		python3 -B "$NORM_PY" "$NFT_FILE" >/dev/null 2>&1 || true
	fi
fi

if [ ! -s "$NFT_FILE" ]; then
	logger -t "ai-link" "ERROR: $NFT_FILE not found or empty and daemon generator unavailable"
	write_nft_status "false" "1" "防火墙规则文件未生成或为空 ($NFT_FILE)"
	exit 1
fi

if command -v nft >/dev/null 2>&1; then
	NFT_ERR=$(nft -f "$NFT_FILE" 2>&1)
	NFT_RC=$?
	if [ $NFT_RC -ne 0 ]; then
		# P1-06 Self-Heal Retry: If kernel table/set interval conflict occurred ("File exists"), flush/delete table and retry once
		nft delete table inet ai_link >/dev/null 2>&1 || true
		NFT_ERR=$(nft -f "$NFT_FILE" 2>&1)
		NFT_RC=$?
	fi
	if [ $NFT_RC -ne 0 ]; then
		logger -t "ai-link" "ERROR: apply_nft.sh failed (rc=$NFT_RC): $NFT_ERR"
		echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] 防火墙规则挂载失败 (rc=$NFT_RC): $NFT_ERR" >> "$LOG_FILE" 2>/dev/null || true
		write_nft_status "false" "$NFT_RC" "防火墙规则应用失败 (rc=$NFT_RC): $NFT_ERR"
		exit $NFT_RC
	else
		if nft list chain inet fw4 forward >/dev/null 2>&1; then
			if ! nft list chain inet fw4 forward 2>/dev/null | grep -q "ailink0"; then
				nft insert rule inet fw4 forward iifname "ailink0" accept >/dev/null 2>&1 || true
				nft insert rule inet fw4 forward oifname "ailink0" accept >/dev/null 2>&1 || true
				nft insert rule inet fw4 input iifname "ailink0" accept >/dev/null 2>&1 || true
			fi
		fi
		logger -t "ai-link" "nftables table inet ai_link mounted from single-source $NFT_FILE."
		write_nft_status "true" "0" ""
	fi
fi
exit 0
