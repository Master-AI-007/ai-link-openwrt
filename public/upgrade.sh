#!/bin/sh
# ==============================================================================
#  AI-LINK 一键在线升级脚本
#
#  用法：
#    curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
#
#  参数：
#    --check      只检查是否有新版本，不升级
#    --force      即使已是最新版本也强制重装一遍（修复用）
#    --keep       升级后保留 /tmp 下的解包目录
#
#  环境：
#    AI_LINK_MIRROR=https://your.mirror   指定下载镜像前缀
# ==============================================================================
set -e

SITE="https://ai-link-official.pages.dev"
GH_REPO="Master-AI-007/ai-link-openwrt"
CONF_DIR="/etc/ai-link"
BACKUP_DIR="/root/ai-link-final-backup"

CHECK_ONLY=0
FORCE=0
KEEP=0
for a in "$@"; do
    case "$a" in
        --check)   CHECK_ONLY=1 ;;
        --force)   FORCE=1 ;;
        --keep)    KEEP=1 ;;
        -h|--help)
            echo "AI-LINK 一键在线升级"
            echo "  用法: curl -fsSL ${SITE}/upgrade.sh | sh"
            echo "  参数: --check 只检查不升级 | --force 强制重装 | --keep 保留解包目录"
            echo "  环境: AI_LINK_MIRROR=https://your.mirror"
            exit 0 ;;
        *) echo "未知参数: $a"; exit 2 ;;
    esac
done

c_g() { printf '\033[32m%s\033[0m\n' "$*"; }
c_y() { printf '\033[33m%s\033[0m\n' "$*"; }
c_r() { printf '\033[31m%s\033[0m\n' "$*"; }
step() { printf '\n\033[36m[%s]\033[0m %s\n' "$1" "$2"; }

# ------------------------------------------------------------------ 0. 前置检查
step "0/6" "检查运行环境"

if [ ! -f /etc/openwrt_release ] && [ ! -d /etc/config ]; then
    c_r "✗ 未检测到 OpenWrt 环境，本脚本仅用于 OpenWrt / ImmortalWrt / LEDE"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    c_r "✗ 缺少 python3，无法解析版本清单。请先执行：opkg update && opkg install python3-light"
    exit 1
fi

if [ ! -d "$CONF_DIR" ] && [ ! -f /etc/config/ai-link ]; then
    c_r "✗ 未检测到已安装的 AI-LINK。"
    c_y "  全新安装请使用：curl -fsSL ${SITE}/install.sh | sh"
    exit 1
fi

CUR_VER="未知"
if [ -f "$CONF_DIR/version" ]; then
    CUR_VER=$(awk '{print $1}' "$CONF_DIR/version" 2>/dev/null || echo "未知")
fi
if [ "$CUR_VER" = "未知" ]; then
    CUR_VER=$(uci -q get ai-link.global.app_version 2>/dev/null || echo "未知")
fi
echo "  · 当前版本 : v${CUR_VER}"

DL=""
for t in curl wget; do
    if command -v "$t" >/dev/null 2>&1; then DL=$t; break; fi
done
if [ -z "$DL" ]; then
    c_r "✗ 缺少 curl 或 wget"; exit 1
fi
echo "  · 下载器   : $DL"
c_g "✓ 环境检查通过"

# ------------------------------------------------------------------ 1. 拉取版本清单
step "1/6" "获取最新版本信息"

WORK="/tmp/ai-link-upgrade-$$"
mkdir -p "$WORK"
MANIFEST="$WORK/version.json"

GH_RAW="https://raw.githubusercontent.com/${GH_REPO}/main/version.json"
MIRROR_PREFIX=""
if [ -n "$AI_LINK_MIRROR" ]; then
    MIRROR_PREFIX="${AI_LINK_MIRROR%/}/"
fi

MANIFEST_SOURCES="${SITE}/version.json
${MIRROR_PREFIX}${GH_RAW}
${GH_RAW}"

GOT_MANIFEST=0
for url in $MANIFEST_SOURCES; do
    if [ -z "$url" ]; then continue; fi
    echo "  → 尝试: $url"
    if [ "$DL" = "curl" ]; then
        curl -fsL --connect-timeout 10 --max-time 30 -o "$MANIFEST" "$url" 2>/dev/null || true
    else
        wget -q -T 20 -O "$MANIFEST" "$url" 2>/dev/null || true
    fi
    if [ -s "$MANIFEST" ] && python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$MANIFEST" >/dev/null 2>&1; then
        GOT_MANIFEST=1
        echo "    ✓ 清单获取成功"
        break
    fi
    rm -f "$MANIFEST"
done

if [ "$GOT_MANIFEST" != "1" ]; then
    c_r "✗ 所有清单源均失败。请检查网络，或稍后重试。"
    rm -rf "$WORK"; exit 1
fi

jget() {
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2], {'d': d}))" "$MANIFEST" "$1"
}

LATEST=$(jget "d['latest']")
PKG_URL=$(jget "d['packages']['full']['url']")
PKG_MD5=$(jget "d['packages']['full'].get('md5','')")
PKG_SHA=$(jget "d['packages']['full'].get('sha256','')")
PKG_SIZE=$(jget "d['packages']['full'].get('size',0)")
NOTES_URL=$(jget "d.get('notes_url','')")
PKG_MIRRORS=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1]))['packages']['full']; [print(m) for m in (d.get('mirrors') or [])]" "$MANIFEST")
PKG_NAME="AI-LINK-v${LATEST}.tar.gz"

echo "  · 最新版本 : v${LATEST}"
if [ -n "$NOTES_URL" ]; then
    echo "  · 更新说明 : $NOTES_URL"
fi

NEED_UPDATE=$(python3 -c "
import re, sys
def p(s):
    m = re.match(r'^v?([0-9]+)\.([0-9]+)\.([0-9]+)', str(s).strip())
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
print('1' if p(sys.argv[2]) > p(sys.argv[1]) else '0')
" "$CUR_VER" "$LATEST")

if [ "$NEED_UPDATE" = "0" ] && [ "$FORCE" = "0" ]; then
    c_g "✓ 当前 v${CUR_VER} 已是最新版本，无需升级。"
    c_y "  如需强制重装，请加 --force"
    rm -rf "$WORK"; exit 0
fi

if [ "$NEED_UPDATE" = "1" ]; then
    c_y "  ⬆ 可升级：v${CUR_VER} → v${LATEST}"
else
    c_y "  ↻ 强制重装：v${CUR_VER}（--force）"
fi

if [ "$CHECK_ONLY" = "1" ]; then
    c_g "✓ --check 模式，仅检查不升级。"
    rm -rf "$WORK"; exit 0
fi

if [ -z "$PKG_MD5" ]; then
    c_r "✗ 版本清单缺少 MD5 校验值，为安全起见拒绝升级。"
    rm -rf "$WORK"; exit 1
fi

# ------------------------------------------------------------------ 2. 下载升级包
step "2/6" "下载升级包 v${LATEST}"

TARBALL="$WORK/$PKG_NAME"
GH_URL="https://github.com/${GH_REPO}/releases/download/v${LATEST}/${PKG_NAME}"

SOURCES="${SITE}/pkg/${PKG_NAME}"
if [ -n "$PKG_MIRRORS" ]; then
    SOURCES="${SOURCES}
${PKG_MIRRORS}"
fi
SOURCES="${SOURCES}
https://ghfast.top/${GH_URL}
https://gh-proxy.com/${GH_URL}
${GH_URL}"

OK=0
for url in $SOURCES; do
    if [ -z "$url" ]; then continue; fi
    echo "  → 尝试: $url"
    if [ "$DL" = "curl" ]; then
        curl -fL --connect-timeout 12 --max-time 300 -o "$TARBALL" "$url" 2>/dev/null || true
    else
        wget -q -T 60 -O "$TARBALL" "$url" 2>/dev/null || true
    fi
    if [ -s "$TARBALL" ]; then
        OK=1
        echo "    ✓ 下载成功 ($(wc -c < "$TARBALL" | tr -d ' ') B)"
        break
    fi
    rm -f "$TARBALL"
done

if [ "$OK" != "1" ]; then
    c_r "✗ 所有下载源均失败。可手动下载后放到 /root 再解包执行 install.sh --upgrade。"
    rm -rf "$WORK"; exit 1
fi

# ------------------------------------------------------------------ 3. 校验
step "3/6" "校验升级包完整性"

ACT_SIZE=$(wc -c < "$TARBALL" | tr -d ' ')
if [ "$PKG_SIZE" != "0" ] && [ "$ACT_SIZE" != "$PKG_SIZE" ]; then
    c_r "✗ 包大小不符（期望 $PKG_SIZE，实际 $ACT_SIZE），已中止。"
    rm -rf "$WORK"; exit 1
fi

if command -v md5sum >/dev/null 2>&1; then
    ACT_MD5=$(md5sum "$TARBALL" | cut -d' ' -f1)
else
    ACT_MD5=$(busybox md5sum "$TARBALL" | cut -d' ' -f1)
fi
if [ "$ACT_MD5" != "$PKG_MD5" ]; then
    c_r "✗ MD5 校验失败（期望 $PKG_MD5，实际 $ACT_MD5），已中止。"
    rm -rf "$WORK"; exit 1
fi
echo "  · MD5    : $ACT_MD5 ✓"

if [ -n "$PKG_SHA" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
        ACT_SHA=$(sha256sum "$TARBALL" | cut -d' ' -f1)
        if [ "$ACT_SHA" != "$PKG_SHA" ]; then
            c_r "✗ SHA256 校验失败，已中止。"
            rm -rf "$WORK"; exit 1
        fi
        echo "  · SHA256 : ✓"
    fi
fi
c_g "✓ 校验通过"

# ------------------------------------------------------------------ 4. 备份当前配置
step "4/6" "备份当前配置"

mkdir -p "$BACKUP_DIR"
PRE_BAK="$BACKUP_DIR/pre-upgrade-v${LATEST}-$(date +%s).tgz"
if tar -czf "$PRE_BAK" -C / etc/ai-link etc/config/ai-link 2>/dev/null; then
    echo "  · 已备份至: $PRE_BAK"
    echo "  · 大小    : $(wc -c < "$PRE_BAK" | tr -d ' ') B"
    ls -1t "$BACKUP_DIR"/pre-upgrade-v*.tgz 2>/dev/null | tail -n +4 | while read -r OLD; do rm -f "$OLD"; done
else
    c_y "  ⚠ 备份失败，继续升级（配置一般不受影响，但建议手动备份）"
fi

# ------------------------------------------------------------------ 5. 解包并升级
step "5/6" "解包并执行升级（--upgrade 模式，保留配置与附加组件）"

tar -xzf "$TARBALL" -C "$WORK" || { c_r "✗ 解包失败"; rm -rf "$WORK"; exit 1; }
SRC="$WORK/ai-link-openwrt"
if [ ! -f "$SRC/install.sh" ]; then
    c_r "✗ 升级包结构异常（找不到 install.sh）"
    rm -rf "$WORK"; exit 1
fi

cd "$SRC"
set +e
sh ./install.sh --upgrade
RC=$?
set -e
cd /

if [ "$KEEP" != "1" ]; then
    rm -rf "$WORK"
else
    echo "  · 已保留解包目录: $SRC"
fi

if [ "$RC" != "0" ]; then
    c_r "✗ install.sh 返回错误码 $RC"
    c_y "  升级前的配置备份在: $PRE_BAK"
    c_y "  如需回滚: tar -xzf $PRE_BAK -C / && /etc/init.d/ai-link restart"
    exit "$RC"
fi

# ------------------------------------------------------------------ 6. 验证
step "6/6" "验证升级结果"

sleep 2
NEW_VER="未知"
if [ -f "$CONF_DIR/version" ]; then
    NEW_VER=$(awk '{print $1}' "$CONF_DIR/version" 2>/dev/null || echo "未知")
fi
PORT=$(uci -q get ai-link.global.panel_port 2>/dev/null || echo "9099")

echo "  · 版本文件 : v${NEW_VER}"
echo "  · 面板端口 : ${PORT}"

HC=1
for i in 1 2 3 4 5 6 7 8; do
    if python3 -c "
import sys, json, urllib.request
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:%s/api/status' % sys.argv[1], timeout=3) as r:
    d = json.loads(r.read().decode('utf-8', 'replace'))
assert d.get('ok') is True
" "$PORT" >/dev/null 2>&1; then
        HC=0
        break
    fi
    sleep 2
done

if [ "$HC" = "0" ]; then
    c_g "  ✓ 面板服务健康检查通过"
else
    c_y "  ⚠ 面板健康检查未通过，请稍后手动访问 http://<路由器IP>:${PORT}"
fi

echo ""
c_g "============================================================"
c_g "  AI-LINK 升级完成：v${CUR_VER} → v${NEW_VER}"
c_g "============================================================"
echo "  · 独立面板  : http://<路由器IP>:${PORT}"
echo "  · 升级前备份: ${PRE_BAK}"
if [ -n "$NOTES_URL" ]; then
    echo "  · 更新说明  : ${NOTES_URL}"
fi
echo "============================================================"
