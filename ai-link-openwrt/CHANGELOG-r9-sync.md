# AI-LINK v2.0.0-r8 (build_ver: `2.0.0-r8-v22-nolo`) Release Notes

## 1. Dual-Machine v21 -> v22 Full Closure Summary

### Machine A (`ImmortalWrt 25.12.2 / x86_64 / apk`) Closure
- **V21-01 [P0] & V21-03 [P3] (`uninstall.sh` packaged & `apk` platform uninstall support)**:
  - `ai-link-openwrt/uninstall.sh` and `ai-link-openwrt/root/usr/share/ai-link/uninstall.sh` are both packaged (`chmod 0755`) inside `ai-link-openwrt-v2.0.0-r8-full.tar.gz` and `luci-app-ai-link_2.0.0-r8_all.ipk`.
  - `/usr/bin/ai-link uninstall` supports both `apk` and `opkg` plus an embedded full teardown fallback and post-uninstall verification gate (never returns `0` if processes or `table inet ai_link` remain).
- **V21-02 [P2] (Automatic `/root/ai-link-final-backup/etc-ai-link.tgz` archive on `apk` & orphan watchdog)**:
  - Both `uninstall.sh`, `/usr/bin/ai-link uninstall`, and the daemon orphan watchdog archive `/etc/ai-link` to `/root/ai-link-final-backup/etc-ai-link.tgz` (`chmod 600`) before cleanup.

### Machine B (`iStoreOS 24.10.8 / x86_64 / opkg + Chromium CDP`) Closure
- **P0-1 & P2-6 (LAN Authentication & Private Key Protection)**:
  - `/api/homelink` and `/api/status` never expose `private_key` over non-loopback HTTP (`*** (仅本机 127.0.0.1 可读)`), and mask subscription URL tokens (`token=***`) for unauthenticated non-loopback requests.
  - Added `require_lan_auth`, `trusted_cidr`, and `panel_bind` to `ops_settings` and WebUI Settings, plus automatic `Set-Cookie: ailink_token` browser session binding.
- **P0-2 (`ai-link uninstall --help` & interactive confirmation)**:
  - `-h`, `--help`, `help`, `--dry-run`, and any unknown `-*` flag safely print usage help and exit `0` without uninstalling.
- **P0-3 (4-Layer Elimination of `127.0.0.1:7893` TProxy Self-Loop)**:
  - Layer 1 (`sing-box.json` `route.rules`): Blocks any inbound connection targeting `127.0.0.0/8` or `::1/128` on local proxy ports (`7893, 7890, 7874, 9090`) before `ip_is_private -> direct`.
  - Layer 2 (`_is_local_port_listening`): Reads `/proc/net/tcp` & `/proc/net/tcp6` in-memory (0 sockets opened) and never opens a raw TCP connection to TProxy port `7893`.
  - Layer 3 (`apply_nft.sh`): `output_tproxy` early-accepts `meta mark 0x162` and `ip daddr 127.0.0.0/8`; `prerouting_tproxy` accepts `iifname "lo" ip daddr 127.0.0.0/8` and drops non-TProxy packets to `127.0.0.1:7893`.
  - Layer 4 (Watchdog self-healing): Automatically flushes `/connections` if `sing-box` open fd > 1,200 or conntrack > 60%.
- **P0-4 (Unified Connection Count & `DELETE /api/clash/connections`)**:
  - Implemented `do_DELETE` on `:9099` (`DELETE /api/clash/connections` returns `200 OK` and flushes `:9090/connections`), added「🧹 清空连接表」button in UI, and filtered loopback self-checks from `clash_get_connections_fast()`.
- **P1-1 ~ P1-10 & P2-1 ~ P3-2**:
  - Slimmed `/api/status` (~11 KB gzipped even with 244 nodes) and made selector sync non-blocking.
  - Multi-stage progress bar for subscription import, mobile bottom nav text labels (`390×844`) + 3D small-screen declutter, `116px` bottom padding clearance, instant Pause/Resume proxy button refresh, accurate UNM Node runtime & GeoIP/GeoSite status in LuCI, visual kernel mount progress bar + Top 120 selector sync, single-node URL ping toast with latency, WebGL-off 2D topology fallback, and 1-click backup archive restore.
