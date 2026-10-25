#!/bin/sh
# AI-LINK v24 Unified Single-Source fw4/nftables Loader
# Note: Ruleset generation is unified in /usr/share/ai-link/ai-link-daemon.py (--generate-nft)
# so runtime state and CLI flags always produce a single canonical /var/run/ai-link/ai-link.nft.

if command -v modprobe >/dev/null 2>&1; then
	for _m in nft_queue nft_nat nft_redir nft_tproxy nft_socket nft_fib_inet nft_ct; do
		modprobe "$_m" >/dev/null 2>&1 || true
	done
fi

LOG_FILE="${AI_LINK_LOG_FILE:-/var/log/ai-link.log}"
RUN_DIR="${AI_LINK_RUN_DIR:-/var/run/ai-link}"
mkdir -p "$RUN_DIR" 2>/dev/null || { RUN_DIR="/tmp/ai-link"; mkdir -p "$RUN_DIR"; }
NFT_FILE="$RUN_DIR/ai-link.nft"
DAEMON_PY="/usr/share/ai-link/ai-link-daemon.py"

if command -v python3 >/dev/null 2>&1 && [ -f "$DAEMON_PY" ]; then
	python3 -B "$DAEMON_PY" --generate-nft "$@" >/dev/null 2>&1 || true
fi

if [ ! -f "$NFT_FILE" ]; then
	logger -t "ai-link" "ERROR: $NFT_FILE not found and daemon generator unavailable"
	exit 1
fi

if command -v python3 >/dev/null 2>&1 && [ -f /usr/share/ai-link/nftables/normalize_nft_sets.py ]; then
	python3 /usr/share/ai-link/nftables/normalize_nft_sets.py "$NFT_FILE" >/dev/null 2>&1 || true
fi

if command -v nft >/dev/null 2>&1; then
	NFT_ERR=$(nft -f "$NFT_FILE" 2>&1)
	NFT_RC=$?
	if [ $NFT_RC -ne 0 ]; then
		logger -t "ai-link" "ERROR: apply_nft.sh failed (rc=$NFT_RC): $NFT_ERR"
		echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] nftables load failed (rc=$NFT_RC): $NFT_ERR" >> "$LOG_FILE" 2>/dev/null || true
		exit $NFT_RC
	else
		logger -t "ai-link" "nftables table inet ai_link mounted from single-source $NFT_FILE."
	fi
fi
exit 0
