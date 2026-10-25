#!/bin/sh
# ==============================================================================
# AI-LINK v1.0.1 (luci-app-ai-link v2.0.0-r8) Universal Cross-Platform Installer
# Supports:
#   - Architectures : x86_64 (amd64), aarch64 (arm64), armv7l (armhf), mipsel, riscv64
#   - Package Mgrs  : OPKG (OpenWrt <=23.05) & APK (OpenWrt 24.10+ / ImmortalWrt 25.x+)
#   - Libc Runtime  : musl (OpenWrt default) & glibc auto-detection
#   - Smart DualStack: DNS :7874 Upstream + Overseas AAAA Suppression + Domestic Native IPv6
#   - Auto Checks   : Dependency verification, conflict plugin auto-muting & self-test
#   - Upgrade Mode  : `install.sh --upgrade` 保留用户已装的附加组件（如音乐解锁）
# ==============================================================================
set -e
export PYTHONDONTWRITEBYTECODE="1"

VERSION="1.0.1"
UPGRADE_MODE=0
for arg in "$@"; do
	case "$arg" in
		--upgrade|-u) UPGRADE_MODE=1 ;;
	esac
done
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

echo "=================================================================="
if [ "$UPGRADE_MODE" = "1" ]; then
	echo "  ⬆️  AI-LINK (v${VERSION}) 在线升级程序（保留用户配置与附加组件）"
else
	echo "  🚀 AI-LINK (v${VERSION}) 全平台一键安装与环境检测程序"
fi
echo "=================================================================="

# ------------------------------------------------------------------------------
# [1/6] 硬件架构、系统版本与 C 运行库 (musl / glibc) 自动识别
# ------------------------------------------------------------------------------
RAW_ARCH=$(uname -m 2>/dev/null || echo "unknown")
case "$RAW_ARCH" in
	x86_64|amd64)
		NORM_ARCH="amd64 (x86_64)"
		SB_ARCH="amd64"
		;;
	aarch64|arm64|armv8*)
		NORM_ARCH="arm64 (aarch64)"
		SB_ARCH="arm64"
		;;
	armv7*|armhf|arm)
		NORM_ARCH="armv7 (armhf)"
		SB_ARCH="armv7"
		;;
	mipsel|mipsle)
		NORM_ARCH="mipsel"
		SB_ARCH="mipsle"
		;;
	mips*)
		NORM_ARCH="mips"
		SB_ARCH="mips"
		;;
	riscv64)
		NORM_ARCH="riscv64"
		SB_ARCH="riscv64"
		;;
	*)
		NORM_ARCH="$RAW_ARCH"
		SB_ARCH="$RAW_ARCH"
		;;
esac

if ls /lib/ld-musl-*.so* >/dev/null 2>&1 || ldd --version 2>&1 | grep -qi "musl"; then
	LIBC_TYPE="musl"
else
	LIBC_TYPE="glibc"
fi

DISTRO_NAME="OpenWrt/Linux"
if [ -f /etc/openwrt_release ]; then
	. /etc/openwrt_release
	DISTRO_NAME="${DISTRIB_ID:-OpenWrt} ${DISTRIB_RELEASE:-} (${DISTRIB_TARGET:-$RAW_ARCH})"
fi

if command -v apk >/dev/null 2>&1 && [ -f /etc/apk/repositories -o -d /lib/apk ]; then
	PKG_MGR="apk"
elif command -v opkg >/dev/null 2>&1; then
	PKG_MGR="opkg"
elif command -v apk >/dev/null 2>&1; then
	PKG_MGR="apk"
else
	PKG_MGR="manual"
fi

echo "[1/6] 平台环境识别结果:"
echo "  · 系统发行版 : ${DISTRO_NAME}"
echo "  · 处理器架构 : ${NORM_ARCH}"
echo "  · C 运行时库 : ${LIBC_TYPE} (优选 sing-box-*-linux-${SB_ARCH}-${LIBC_TYPE})"
echo "  · 包管理器   : ${PKG_MGR}"

# ------------------------------------------------------------------------------
# [2/6] 核心依赖项检测与按需自动安装 (OPKG & APK 双栈兼容)
# ------------------------------------------------------------------------------
echo "[2/6] 正在检测系统内核模块与运行依赖..."

check_and_install_deps() {
	[ "${AILINK_SKIP_DEPS:-0}" = "1" ] && {
		echo "  -> 已跳过在线依赖安装 (AILINK_SKIP_DEPS=1)"
		return 0
	}

	MISSING_PKGS=""
	command -v python3 >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS python3"
	command -v nft >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS nftables"
	command -v ip >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS ip-full"
	command -v openssl >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS openssl-util"

	if [ ! -d /sys/module/nft_tproxy ] && ! grep -q "nft_tproxy" /proc/modules 2>/dev/null; then
		MISSING_PKGS="$MISSING_PKGS kmod-nft-tproxy kmod-nft-socket"
	fi
	if [ ! -c /dev/net/tun ] && [ ! -d /sys/module/tun ]; then
		MISSING_PKGS="$MISSING_PKGS kmod-tun"
	fi
	if ! python3 -c "import cryptography" >/dev/null 2>&1; then
		MISSING_PKGS="$MISSING_PKGS python3-cryptography"
	fi

	if [ -z "$MISSING_PKGS" ]; then
		echo "  -> ✓ 所有核心依赖 (python3 / nftables / tproxy / tun / cryptography) 均已就绪！"
		return 0
	fi

	echo "  -> 发现待补齐组件:${MISSING_PKGS}，正在通过 ${PKG_MGR} 自动安装..."
	if [ "$PKG_MGR" = "opkg" ]; then
		opkg update >/dev/null 2>&1 || true
		for pkg in kmod-nft-tproxy kmod-nft-socket kmod-tun nftables ip-full ca-bundle python3-light python3-urllib python3-openssl python3-cryptography openssl-util curl; do
			opkg install "$pkg" >/dev/null 2>&1 || true
		done
	elif [ "$PKG_MGR" = "apk" ]; then
		apk update >/dev/null 2>&1 || true
		apk add --allow-untrusted kmod-nft-tproxy kmod-nft-socket kmod-tun nftables ip-full ca-bundle python3 python3-cryptography openssl-util curl >/dev/null 2>&1 || true
	fi
	echo "  -> ✓ 依赖项检查与补齐流程已完成"
}

check_and_install_deps

# ------------------------------------------------------------------------------
# [3/6] 冲突代理插件扫描与安全互斥处理
# ------------------------------------------------------------------------------
echo "[3/6] 正在扫描并处理冲突透明代理插件 (防止 fwmark / DNS 53 / TProxy 冲突)..."
CONFLICT_SERVICES="passwall passwall2 openclash shadowsocksr homeproxy nikki momo neko nekobox shellcrash nolo nolo-core open-box v2ray xray clash"
FOUND_CONFLICTS=0

if [ "$UPGRADE_MODE" = "1" ]; then
	# 升级模式不再 stop/disable 其他服务：首次安装时已处理过，
	# 再次扫描容易误伤用户后续自行安装的附加组件（如音乐解锁后端）。
	echo "  -> ⏭️ 升级模式：跳过冲突服务停止/禁用（仅清理残留 nft 表）"
else
for svc in $CONFLICT_SERVICES; do
	if [ -x "/etc/init.d/$svc" ]; then
		if /etc/init.d/$svc running >/dev/null 2>&1 || pgrep -f "/etc/init.d/$svc" >/dev/null 2>&1 || pgrep -x "$svc" >/dev/null 2>&1; then
			echo "  -> ⚠️ 检测到运行中的冲突插件 [$svc]，正在安全停止并禁用自启..."
			/etc/init.d/$svc stop >/dev/null 2>&1 || true
			/etc/init.d/$svc disable >/dev/null 2>&1 || true
			FOUND_CONFLICTS=$((FOUND_CONFLICTS + 1))
		fi
	fi
done
fi

for tbl in passwall passwall2 openclash homeproxy nikki momo nolo open_box; do
	nft delete table inet "$tbl" 2>/dev/null || true
	nft delete table ip "$tbl" 2>/dev/null || true
done

if [ "$UPGRADE_MODE" = "1" ]; then
	echo "  -> ✓ 已清理冲突插件残留的 nftables 表"
elif [ "$FOUND_CONFLICTS" -eq 0 ]; then
	echo "  -> ✓ 未检测到运行中的冲突代理服务"
else
	echo "  -> ✓ 已安全隔离 ${FOUND_CONFLICTS} 个冲突代理服务"
fi

# ------------------------------------------------------------------------------
# [4/6] 部署 AI-LINK 系统文件与软件包
# ------------------------------------------------------------------------------
echo "[4/6] 正在部署 AI-LINK (v${VERSION}) 系统文件..."
IPK_FILE=$(ls "$SCRIPT_DIR"/luci-app-ai-link_*.ipk 2>/dev/null | head -n 1 || true)

# Preserve existing /etc/config/ai-link before copying package files so user settings (gh_mirror, ipv6_proxy, entry_bypass, panel_port) are never overwritten
HAD_UCI_CFG=0
if [ -f /etc/config/ai-link ]; then
	cp -f /etc/config/ai-link /tmp/.ai-link-uci.preserve 2>/dev/null && HAD_UCI_CFG=1 || true
fi

if [ "$PKG_MGR" = "opkg" ] && [ -n "$IPK_FILE" ] && [ -f "$IPK_FILE" ]; then
	AILINK_INSTALLING=1 opkg install --force-reinstall "$IPK_FILE" >/dev/null 2>&1 || true
fi

cp -rf "$SCRIPT_DIR/root/"* /
if [ "$HAD_UCI_CFG" -eq 1 ] && [ -f /tmp/.ai-link-uci.preserve ]; then
	cp -f /tmp/.ai-link-uci.preserve /etc/config/ai-link 2>/dev/null || true
	rm -f /tmp/.ai-link-uci.preserve 2>/dev/null || true
fi
if [ -f "$SCRIPT_DIR/uninstall.sh" ]; then
	cp -f "$SCRIPT_DIR/uninstall.sh" /usr/share/ai-link/uninstall.sh 2>/dev/null || true
	chmod +x /usr/share/ai-link/uninstall.sh 2>/dev/null || true
fi
rm -rf /usr/share/ai-link/__pycache__ /usr/share/ai-link/webui/assets /usr/share/ai-link/webui/vendor 2>/dev/null || true
ln -snf /usr/share/ai-link/webui/static/tailwind.css /usr/share/ai-link/webui/static/tailwind.offline.css 2>/dev/null || true
ln -snf /usr/share/ai-link/webui/static /usr/share/ai-link/webui/assets 2>/dev/null || true
ln -snf /usr/share/ai-link/webui/static /usr/share/ai-link/webui/vendor 2>/dev/null || true
mkdir -p /www/luci-static/resources/view/ai-link
cp -rf "$SCRIPT_DIR/htdocs/luci-static/resources/view/ai-link/"* /www/luci-static/resources/view/ai-link/ 2>/dev/null || true

chmod +x /etc/init.d/ai-link /usr/bin/ai-link /usr/share/ai-link/ai-link-daemon.py /usr/share/ai-link/nftables/apply_nft.sh /usr/share/ai-link/nftables/normalize_nft_sets.py 2>/dev/null || true
mkdir -p /etc/ai-link
cp -f "$SCRIPT_DIR/root/etc/ai-link/version" /etc/ai-link/version 2>/dev/null || echo "${VERSION}" > /etc/ai-link/version

MEM_KB=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 4194304)
MEM_MIB=$(( ${MEM_KB:-4194304} / 1024 ))
if [ "$MEM_MIB" -le 2200 ]; then
	REC_MAX_OB="120"
else
	REC_MAX_OB="200"
fi

# Non-destructive UCI item-by-item merge: only set defaults if the option does not already exist
uci_set_default() {
	local k="$1"
	local v="$2"
	local cur
	cur=$(uci -q get "ai-link.global.${k}" 2>/dev/null || true)
	if [ -z "$cur" ]; then
		uci -q set "ai-link.global.${k}=${v}" 2>/dev/null || true
	fi
}
# Migrate any legacy webui_port to panel_port before deleting webui_port
LEGACY_WPORT=$(uci -q get ai-link.global.webui_port 2>/dev/null || true)
if [ -n "$LEGACY_WPORT" ] && [ "$LEGACY_WPORT" != "9099" ]; then
	uci -q set "ai-link.global.panel_port=${LEGACY_WPORT}" 2>/dev/null || true
fi
uci_set_default "enabled" "1"
uci_set_default "panel_port" "9099"
uci_set_default "panel_secret" "ai-link-2026"
uci_set_default "tproxy_port" "7893"
uci_set_default "mixed_port" "7890"
uci_set_default "dns_port" "7874"
uci_set_default "ipv6_proxy" "0"
uci_set_default "entry_bypass" "1"
uci_set_default "block_quic" "1"
uci_set_default "game_udp_direct" "1"
uci_set_default "auto_mute_conflicts" "1"
uci_set_default "gh_mirror" "https://gh-proxy.com/"
uci_set_default "dns_rewrite_enabled" "1"
uci_set_default "dns_filter_enabled" "1"
uci_set_default "max_outbounds" "$REC_MAX_OB"
# OTA 在线更新：版本号 + LuCI 桥接令牌（与面板密码解耦，供 LuCI 页面调用面板 API）
uci_set_default "app_version" "${VERSION}"
if [ -z "$(uci -q get ai-link.global.luci_bridge_token 2>/dev/null)" ]; then
	uci -q set "ai-link.global.luci_bridge_token=$(head -c 16 /dev/urandom 2>/dev/null | md5sum 2>/dev/null | cut -d' ' -f1)" 2>/dev/null || true
fi

if [ ! -f /etc/ai-link/max_outbounds.txt ] || [ "$(cat /etc/ai-link/max_outbounds.txt 2>/dev/null)" = "60" ] || [ "$(cat /etc/ai-link/max_outbounds.txt 2>/dev/null)" = "0" ]; then
	echo "$REC_MAX_OB" > /etc/ai-link/max_outbounds.txt
fi
# Auto-sync r8_myfix.py state enum whitelist on test device if present (adds proxy_degraded / proxy_checking)
for mf in /root/r8_myfix.py /tmp/r8_myfix.py; do
	if [ -f "$mf" ] && ! grep -q "proxy_degraded" "$mf" 2>/dev/null; then
		sed -i 's/"emergency_direct")/"emergency_direct", "proxy_degraded", "proxy_checking")/g' "$mf" 2>/dev/null || true
	fi
done
# Clean up any legacy AI-LINK internal music unlock files/UCI & dead UCI keys
uci -q delete ai-link.unblockmusic 2>/dev/null || true
uci -q delete ai-link.global.core_type 2>/dev/null || true
uci -q delete ai-link.global.dns_mode 2>/dev/null || true
uci -q delete ai-link.global.webui_port 2>/dev/null || true
if [ "$UPGRADE_MODE" = "1" ]; then
	# 升级模式绝不删除用户已装的音乐解锁组件（否则升级会静默"卸载"功能）
	echo "  -> ⏭️ 升级模式：保留用户已安装的附加组件（音乐解锁等）"
else
	rm -rf /usr/bin/UnblockNeteaseMusic /etc/ai-link/music /etc/ai-link/music_settings.json /opt/nolo-music /etc/init.d/nolo-music /etc/ai-link/mihomo.yaml 2>/dev/null || true
fi
uci commit ai-link 2>/dev/null || true
# If ops_settings.json already exists on router, keep its mtime newer than /etc/config/ai-link so user's ops_settings are preserved
if [ -f /etc/ai-link/ops_settings.json ]; then
	touch /etc/ai-link/ops_settings.json 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# [5/6] 导入缓存、生成安全证书、DNS 重写规则与全栈代理配置
# ------------------------------------------------------------------------------
mkdir -p /tmp/ai-link-cache /etc/ai-link/rules /etc/ai-link/certs /var/run/ai-link
if [ -d "$SCRIPT_DIR/cache" ]; then
	cp -rf "$SCRIPT_DIR/cache/"* /tmp/ai-link-cache/ 2>/dev/null || true
fi

echo "[5/6] 正在初始化安全证书、智能双栈 DNS 分流规则与内核配置..."
/usr/bin/env python3 -B /usr/share/ai-link/ai-link-daemon.py --import-cache /tmp/ai-link-cache >/dev/null 2>&1 || true
/usr/bin/env python3 -B /usr/share/ai-link/ai-link-daemon.py --generate-configs

# ------------------------------------------------------------------------------
# [6/6] 启动服务并执行安装后全链路自检
# ------------------------------------------------------------------------------
echo "[6/6] 正在清理旧版进程缓存、刷新 LuCI 视图并启动服务..."
rm -rf /tmp/luci-indexcache* /tmp/luci-modulecache/* /var/run/ai-link/probe.lock /usr/share/ai-link/__pycache__ 2>/dev/null || true
for old_pid in $(pgrep -f "ai-link-daemon.py" 2>/dev/null); do
	kill -TERM "$old_pid" 2>/dev/null || true
done
sleep 1
/etc/init.d/ai-link enable 2>/dev/null || true
/etc/init.d/ai-link restart 2>/dev/null || true
/usr/share/ai-link/nftables/apply_nft.sh || true
if command -v nft >/dev/null 2>&1; then
	if nft list table inet ai_link >/dev/null 2>&1; then
		echo "  -> ✓ nftables 透明代理表 (table inet ai_link) 已成功挂载并校验通过！"
	else
		echo "  -> ❌ 告警: table inet ai_link 未挂载，请检查 nftables 模块！" >&2
		exit 1
	fi
fi
/etc/init.d/rpcd reload 2>/dev/null || true
/etc/init.d/uhttpd reload 2>/dev/null || true

if /usr/bin/env python3 -B -c "
import symtable, builtins
src = open('/usr/share/ai-link/ai-link-daemon.py', encoding='utf-8').read()
top = symtable.symtable(src, 'ai-link-daemon.py', 'exec')
bset = set(dir(builtins)) | {'__file__', '__name__', '__doc__', '__package__', '__class__'}
top_defs = {s.get_name() for s in top.get_symbols() if s.is_imported() or s.is_assigned() or s.is_namespace()}
undef = []
def walk(t, pset):
    cur = pset | {s.get_name() for s in t.get_symbols() if s.is_local() or s.is_parameter() or s.is_imported() or s.is_assigned() or s.is_namespace()}
    for s in t.get_symbols():
        if s.is_referenced() and not (s.is_local() or s.is_parameter() or s.is_imported() or s.is_assigned() or s.is_namespace()):
            nm = s.get_name()
            if nm not in cur and nm not in top_defs and nm not in bset:
                undef.append((t.get_name(), nm))
    for c in t.get_children():
        walk(c, cur)
walk(top, set())
assert not undef, f'Undefined symbols: {undef}'
" 2>/dev/null; then
	echo "  -> ✓ Python 静态符号门禁 (symtable 零未定义全局符号) 校验通过！"
fi

if /usr/bin/env python3 -B /usr/share/ai-link/ai-link-daemon.py --self-test >/dev/null 2>&1; then
	echo "  -> ✓ 安装后功能自检 (分流 / 回家节点 / 智能双栈DNS / 净网黑洞拦截) 100% 通过！"
fi

LAN_IP=$(uci -q get network.lan.ipaddr 2>/dev/null || ip -4 addr show br-lan 2>/dev/null | awk '/inet / {split($2,a,"/"); print a[1]; exit}' || echo "10.10.10.77")
PORT=$(uci -q get ai-link.global.panel_port 2>/dev/null || echo "9099")
SECRET=$(uci -q get ai-link.global.panel_secret 2>/dev/null || echo "ai-link-2026")

echo "=================================================================="
echo "  🎉 AI-LINK (v${VERSION}) 安装完成！"
echo "  👉 控制面板地址 : http://${LAN_IP}:${PORT}"
echo "  🔑 面板访问密码 : (已隐藏 · 可执行 ai-link password 查看或修改)"
echo "  🧹 彻底卸载命令 : ai-link uninstall -y (或 opkg remove luci-app-ai-link)"
if [ -f /root/ai-link-final-backup/etc-ai-link.tgz ]; then
	echo "  📦 历史备份提示 : 检测到 /root/ai-link-final-backup/etc-ai-link.tgz，可在面板「设置」页一键恢复"
fi
echo "  🖥️ 硬件平台环境 : ${NORM_ARCH} · ${LIBC_TYPE} · ${PKG_MGR}"
echo "=================================================================="
