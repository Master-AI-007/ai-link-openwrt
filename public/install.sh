#!/bin/sh
# ==============================================================================
#  AI-LINK v1.0.0 在线一键安装脚本
#  用法： curl -fsSL https://ai-link-official.pages.dev/install.sh | sh
#  参数： --dry-run   只检测环境并下载校验，不执行安装
#         --keep      安装后保留 /tmp 下的解包目录
#  环境： AI_LINK_MIRROR=https://your.mirror   指定下载镜像前缀
# ==============================================================================
set -e

VER="v2.0.2"
PKG="AI-LINK-v2.0.2.tar.gz"
PKG_MD5="d0b5f23e05e4712a54f16722039e0ec9"
SITE="https://ai-link-official.pages.dev"
GH="https://github.com/Master-AI-007/ai-link-openwrt/releases/download/${VER}/${PKG}"

DRY_RUN=0
KEEP=0
for a in "$@"; do
    case "$a" in
        --dry-run) DRY_RUN=1 ;;
        --keep)    KEEP=1 ;;
        -h|--help)
            echo "AI-LINK 在线一键安装"
            echo "  用法: curl -fsSL ${SITE:-https://ai-link-official.pages.dev}/install.sh | sh"
            echo "  参数: --dry-run 仅检测与下载校验; --keep 保留解包目录"
            echo "  环境: AI_LINK_MIRROR=https://your.mirror  指定镜像前缀"
            exit 0 ;;
        *) echo "未知参数: $a"; exit 2 ;;
    esac
done

c_g() { printf '\033[32m%s\033[0m\n' "$*"; }
c_y() { printf '\033[33m%s\033[0m\n' "$*"; }
c_r() { printf '\033[31m%s\033[0m\n' "$*"; }
step() { printf '\n\033[36m[%s]\033[0m %s\n' "$1" "$2"; }

# ------------------------------------------------------------------ 1. 环境检测
step "1/5" "检测系统环境"
OS_NAME=""
if [ -f /etc/openwrt_release ]; then
    OS_NAME=$(sed -n "s/^DISTRIB_DESCRIPTION='\(.*\)'/\1/p" /etc/openwrt_release 2>/dev/null | head -1)
fi
if [ -z "$OS_NAME" ] && [ -f /etc/os-release ]; then
    OS_NAME=$(. /etc/os-release 2>/dev/null; echo "$PRETTY_NAME")
fi
[ -n "$OS_NAME" ] || OS_NAME="unknown"
ARCH=$(uname -m 2>/dev/null || echo unknown)

if [ ! -f /etc/openwrt_release ] && [ ! -d /etc/config ]; then
    c_y "⚠️  未检测到 OpenWrt 环境（当前：${OS_NAME:-unknown} / ${ARCH}）"
    c_y "    本脚本面向 OpenWrt / ImmortalWrt / LEDE，继续执行可能失败。"
    printf "    仍要继续？[y/N] "
    read -r ans < /dev/tty 2>/dev/null || ans=n
    case "$ans" in y|Y) ;; *) echo "已取消"; exit 1 ;; esac
fi

echo "  · 系统   : ${OS_NAME:-unknown}"
echo "  · 架构   : ${ARCH}"
echo "  · 内核   : $(uname -r 2>/dev/null || echo unknown)"

DL=""
for t in curl wget; do
    if command -v "$t" >/dev/null 2>&1; then DL=$t; break; fi
done
if [ -z "$DL" ]; then
    c_r "✗ 缺少 curl 或 wget，无法下载。请先执行：opkg update && opkg install curl"
    exit 1
fi
if ! command -v tar >/dev/null 2>&1; then
    c_r "✗ 缺少 tar"; exit 1
fi
MD5BIN=""
for m in md5sum busybox; do
    if command -v "$m" >/dev/null 2>&1; then MD5BIN=$m; break; fi
done
[ -n "$MD5BIN" ] || MD5BIN="md5sum"
echo "  · 下载器 : $DL"
c_g "✓ 环境检测通过"

# ------------------------------------------------------------------ 2. 选择镜像
step "2/5" "选择下载源（按顺序自动尝试）"
if [ -n "$AI_LINK_MIRROR" ]; then
    MIRROR_BASE=${AI_LINK_MIRROR%/}
    SOURCES="${MIRROR_BASE}/${PKG}"
    echo "  · 使用自定义镜像: $MIRROR_BASE"
else
    SOURCES="${SITE}/pkg/${PKG}
https://ghfast.top/${GH}
https://gh-proxy.com/${GH}
${GH}"
fi

WORK="/tmp/ai-link-install-$$"
mkdir -p "$WORK"
TARBALL="$WORK/$PKG"
OK=0
for url in $SOURCES; do
    echo "  → 尝试: $url"
    if [ "$DL" = "curl" ]; then
        curl -fL --connect-timeout 10 --max-time 300 -o "$TARBALL" "$url" 2>/dev/null && OK=1
    else
        wget -q -T 30 -O "$TARBALL" "$url" 2>/dev/null && OK=1
    fi
    if [ "$OK" = "1" ] && [ -s "$TARBALL" ]; then
        SZ=$(wc -c < "$TARBALL" | tr -d ' ')
        echo "    ✓ 下载成功 (${SZ} B)"
        break
    fi
    OK=0
    rm -f "$TARBALL"
done
[ "$OK" = "1" ] || { c_r "✗ 所有下载源均失败。可手动下载后上传到 /tmp 安装。"; rm -rf "$WORK"; exit 1; }

# ------------------------------------------------------------------ 3. 校验
step "3/5" "校验安装包完整性"
if [ "$MD5BIN" = "md5sum" ]; then
    GOT=$(md5sum "$TARBALL" | cut -d' ' -f1)
else
    GOT=$(busybox md5sum "$TARBALL" | cut -d' ' -f1)
fi
echo "  · 期望 MD5: $PKG_MD5"
echo "  · 实际 MD5: $GOT"
if [ "$GOT" != "$PKG_MD5" ]; then
    c_r "✗ 校验失败，安装包可能被篡改或下载不完整，已中止。"
    rm -rf "$WORK"; exit 1
fi
c_g "✓ 校验通过"

if [ "$DRY_RUN" = "1" ]; then
    step "4/5" "dry-run 模式，跳过安装"
    echo "  · 解包目录: $WORK"
    if [ "$KEEP" != "1" ]; then rm -rf "$WORK"; fi
    c_g "✓ 环境检测、下载、校验全部通过"
    exit 0
fi

# ------------------------------------------------------------------ 4. 解包
step "4/5" "解包"
tar -xzf "$TARBALL" -C "$WORK"
[ -d "$WORK/ai-link-openwrt" ] || { c_r "✗ 解包结构异常"; rm -rf "$WORK"; exit 1; }
echo "  · 目录: $WORK/ai-link-openwrt"
c_g "✓ 解包完成"

# ------------------------------------------------------------------ 5. 安装
step "5/5" "执行安装"
cd "$WORK/ai-link-openwrt"
chmod +x install.sh uninstall.sh 2>/dev/null || true
# 已装过则自动使用 --upgrade 模式：不停止其他代理服务、不删除音乐解锁等附加组件
INSTALL_ARGS=""
if [ -f /etc/config/ai-link ] || [ -d /etc/ai-link ]; then
    INSTALL_ARGS="--upgrade"
    echo "  · 检测到已安装 AI-LINK，自动使用 --upgrade 模式（保留配置与附加组件）"
fi
sh ./install.sh $INSTALL_ARGS
RC=$?

cd /
if [ "$KEEP" = "1" ]; then
    echo ""
    echo "  · 已保留解包目录: $WORK/ai-link-openwrt"
else
    rm -rf "$WORK"
fi

if [ "$RC" = "0" ]; then
    echo ""
    c_g "============================================================"
    c_g "  AI-LINK ${VER} 安装完成"
    c_g "============================================================"
    echo "  · 独立面板 : http://<路由器IP>:9099"
    echo "  · LuCI 后台: http://<路由器IP>/cgi-bin/luci/admin/services/ai-link"
    echo "  · 查看状态 : ai-link status"
    echo "  · 卸载     : ai-link uninstall -y"
else
    c_r "✗ 安装脚本返回错误码 $RC，请查看上方输出。"
    exit "$RC"
fi
