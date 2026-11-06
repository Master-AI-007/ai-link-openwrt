# AI-LINK v2.4.2

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-07 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：把门关严，把切换做快

### 🔒 面板鉴权与桥接令牌加固

- 升级后强制 `require_lan_auth=1`，`trusted_cidr` 收紧为 `127.0.0.1/32, ::1/128`，UCI 配置文件权限 600；
- 非本机未鉴权访问 `/api/*`（含 `/api/status`）统一返回 `HTTP 401`，不再有局域网免密可调全量 API 的窗口；
- `luci_bridge_token` 从 `/etc/config/ai-link` 明文彻底移除，改为仅驻留 `/var/run/ai-link/luci_bridge_token.json`（`0600`），`3600s` 自动过期轮换；
- 桥接令牌被显式拒绝访问 `/api/ops/logs`、`/api/ops/backup` 等高敏接口。

### ⚡ 内核日志实时故障感知与秒级切换

- 对当前正在使用的自动节点池出口节点，以 3 秒周期增量监听 `sing-box.log`；
- 30 秒滑动窗口内连续 3 次传输层/握手层报错即判死隔离 300 秒，突破 600 秒粘性冷却期**秒级热切换**至池内下一最快健康节点；
- 目标多样性守卫（`min_distinct_targets=2`）：日志全部指向同一死站时抑制切换，避免单站宕机误判；
- 切前 1.5 秒轻量复核确认节点失活，切换后与 Clash `:9090` 实态回读闭环；
- `/api/status` 与 `/api/auto_nodes` 同步暴露 `kernel_log_failover` / `log_failover_guard` 可观测字段。

### 🧩 单组节点池收敛与数据真实性

- 后端单组节点池彻底收敛，存量 `G1 + G2` 自动迁移（`single_group_migrated=true`）；
- 根治死节点池 `direct` 乒乓振荡，`/var/run/ai-link/auto_pool_runtime.json` 内存态冷却持久化；
- 全站数据真实性 D-01 ~ D-11 闭环，字节单位统一为 `KiB / MiB / GiB / TiB`；
- 仅完成 TCP 降级探测的节点显式渲染黄色「L7 降级」徽章。

### 📱 移动端与工程细节

- `<=720px` 顶部操作按钮收敛为紧凑胶囊，底部导航保持横向单排滚动；
- 裸 `except Exception` 收敛为具体异常元组并计入内部诊断（`except Exception` 141 处 / `except->pass` 8 处）；
- `index.html` 中 `nexus.css` / `nexus.js` / `nexus3d.js` 的 `?v=2.4.2-<hash8>` 与文件真实 MD5 前 8 位严格一致。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x / 2.1.x / 2.2.x / 2.3.x / 2.4.x 直升，配置、节点、订阅、节点池全部保留，失败自动回滚。

---

## 已知限制

- 订阅为网页/HTML 或 Token 失效时无法解析，需要更新链接；
- 500+ 节点规模下 `quick_create` 首次约 1 秒；
- 面板默认仅信任本机回环，需从局域网其他设备访问时请自行配置令牌或可信网段。

---

## 包指纹

```
AI-LINK-v2.4.2.tar.gz   763,083 B
md5     21e1f1f7f0b1dd5070c599f3037171bd
sha256  7c855ed9cb2226ce35f2d5c2378a6e22b05f4e61aa2ee6cd7123f0e06140f3ad
```
