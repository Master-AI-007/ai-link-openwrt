#!/bin/sh
# AI-LINK Complete Uninstaller (v1.0.1)
# Supports both apk (OpenWrt 24.10+ / ImmortalWrt 25.x) and opkg (iStoreOS / OpenWrt 23.05)

KEEP_CONFIG=0
ASSUME_YES=0

print_usage() {
	cat <<'EOF'
用法: ai-link uninstall [选项]  或  /usr/share/ai-link/uninstall.sh [选项]

选项:
  -y, --yes, --force   免交互确认直接执行彻底卸载（自动归档备份 /etc/ai-link）
  --keep-config        卸载程序与服务，但保留 /etc/ai-link 原目录不删除
  -h, --help, --dry-run 显示本帮助说明并安全退出（不执行任何卸载操作）

说明:
  卸载前会自动将 /etc/ai-link 完整配置与证书打包备份至:
  /root/ai-link-final-backup/etc-ai-link.tgz (权限 600)
EOF
}

for arg in "$@"; do
	case "$arg" in
		-h|--help|help|--dry-run|--version)
			print_usage
			exit 0
			;;
		-y|--yes|--force)
			ASSUME_YES=1
			;;
		--keep-config)
			KEEP_CONFIG=1
			;;
		-*)
			echo "[AI-LINK] 未知选项: $arg" >&2
			print_usage
			exit 2
			;;
	esac
done

if [ "$ASSUME_YES" != "1" ] && [ -t 0 ] && [ "${AILINK_UNINSTALL_INTERNAL:-0}" != "1" ]; then
	printf "⚠️ 确认彻底卸载 AI-LINK 吗？配置将自动备份至 /root/ai-link-final-backup/etc-ai-link.tgz [Y/n] (3秒无输入默认继续，输入 n 取消): "
	if read -t 3 -r ans; then
		case "$ans" in
			n|N|no|NO)
				echo "已取消卸载。"
				exit 0
				;;
		esac
	else
		echo ""
	fi
fi

echo "[AI-LINK] 正在执行彻底卸载与清理..."

# 1. Archive /etc/ai-link to /root/ai-link-final-backup/etc-ai-link.tgz (chmod 600)
if [ -d /etc/ai-link ]; then
	mkdir -p /root/ai-link-final-backup 2>/dev/null || true
	chmod 700 /root/ai-link-final-backup 2>/dev/null || true
	tar -czf /root/ai-link-final-backup/etc-ai-link.tgz -C / etc/ai-link 2>/dev/null || true
	chmod 600 /root/ai-link-final-backup/etc-ai-link.tgz 2>/dev/null || true
	echo "  -> 📦 已将 /etc/ai-link 配置与密钥安全归档至: /root/ai-link-final-backup/etc-ai-link.tgz (权限 600)"
fi

# 2. Stop & disable init service + remove from procd ubus
if [ -x /etc/init.d/ai-link ]; then
	/etc/init.d/ai-link stop >/dev/null 2>&1 || true
	/etc/init.d/ai-link disable >/dev/null 2>&1 || true
fi
ubus call service delete '{"name":"ai-link"}' >/dev/null 2>&1 || true

# 3. Terminate all processes
for sig in TERM KILL; do
	for pid in $(pgrep -f "ai-link-daemon.py" 2>/dev/null) $(pgrep -f "/etc/ai-link/sing-box.json" 2>/dev/null) $(pidof sing-box 2>/dev/null); do
		kill -"$sig" "$pid" 2>/dev/null || true
	done
	sleep 1
done

# 4. Clean nftables & policy routing rules & dnsmasq snippets
nft delete table inet ai_link 2>/dev/null || true
nft delete table ip ai_link 2>/dev/null || true
while ip rule del fwmark 0x162 lookup 162 2>/dev/null; do :; done
while ip -6 rule del fwmark 0x162 lookup 162 2>/dev/null; do :; done
while ip rule del pref 8999 2>/dev/null; do :; done
while ip -6 rule del pref 8999 2>/dev/null; do :; done
ip route flush table 162 2>/dev/null || true
ip -6 route flush table 162 2>/dev/null || true
ip -6 route del fc00::/18 dev br-lan 2>/dev/null || ip -6 route del fc00::/18 2>/dev/null || true
if [ -f /var/run/ai-link/sysctl_orig/be_liberal ]; then
	sysctl -w net.netfilter.nf_conntrack_tcp_be_liberal="$(cat /var/run/ai-link/sysctl_orig/be_liberal)" >/dev/null 2>&1 || sysctl -w net.netfilter.nf_conntrack_tcp_be_liberal=0 >/dev/null 2>&1 || true
else
	sysctl -w net.netfilter.nf_conntrack_tcp_be_liberal=0 >/dev/null 2>&1 || true
fi
rm -f /tmp/dnsmasq.d/ai-link-*.conf /tmp/dnsmasq.cfg*/ai-link-*.conf 2>/dev/null || true
killall -HUP dnsmasq 2>/dev/null || true

# 5. Remove package record from opkg or apk if present
if [ "${AILINK_UNINSTALL_INTERNAL:-0}" != "1" ]; then
	if command -v opkg >/dev/null 2>&1 && opkg status luci-app-ai-link 2>/dev/null | grep -q "Status:.*installed"; then
		AILINK_UNINSTALL_INTERNAL=1 opkg remove luci-app-ai-link >/dev/null 2>&1 || true
	elif command -v apk >/dev/null 2>&1; then
		AILINK_UNINSTALL_INTERNAL=1 apk del luci-app-ai-link >/dev/null 2>&1 || true
	fi
fi

# 6. Remove all files & directories
rm -f /etc/init.d/ai-link /etc/rc.d/*ai-link* /usr/bin/ai-link 2>/dev/null || true
rm -f /etc/config/ai-link /lib/upgrade/keep.d/ai-link 2>/dev/null || true
rm -f /usr/share/luci/menu.d/luci-app-ai-link.json /usr/share/rpcd/acl.d/luci-app-ai-link.json 2>/dev/null || true
rm -rf /www/luci-static/resources/view/ai-link /usr/share/ai-link /var/run/ai-link /tmp/ai-link /tmp/ai-link-run /tmp/ai-link-cache /tmp/ai-link.log /tmp/ai-link-music.log /tmp/.ai-link* /var/log/ai-link.log /var/log/ai-link-music.log /tmp/luci-indexcache* /tmp/luci-modulecache/* 2>/dev/null || true

if [ "$KEEP_CONFIG" != "1" ]; then
	rm -rf /etc/ai-link 2>/dev/null || true
fi

ubus call service delete '{"name":"ai-link"}' >/dev/null 2>&1 || true
/etc/init.d/rpcd reload >/dev/null 2>&1 || true
/etc/init.d/uhttpd reload >/dev/null 2>&1 || true

# 7. Final verification gate (never return 0 if daemon or nft table still exists)
if pgrep -f "ai-link-daemon.py" >/dev/null 2>&1 || nft list table inet ai_link >/dev/null 2>&1; then
	for pid in $(pgrep -f "ai-link-daemon.py" 2>/dev/null) $(pidof sing-box 2>/dev/null); do
		kill -9 "$pid" 2>/dev/null || true
	done
	nft delete table inet ai_link 2>/dev/null || true
fi

if pgrep -f "ai-link-daemon.py" >/dev/null 2>&1 || nft list table inet ai_link >/dev/null 2>&1; then
	echo "[AI-LINK] ❌ 卸载后校验未通过：仍有残留进程或 nft 表" >&2
	exit 1
fi

echo "[AI-LINK] ✅ 卸载完成（进程=0, nft=0, 备份=/root/ai-link-final-backup/etc-ai-link.tgz）。"
exit 0
