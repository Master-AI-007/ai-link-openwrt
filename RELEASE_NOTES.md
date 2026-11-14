# AI-LINK v2.6.1

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-15 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：全面闭环 FB-2600 反馈与深度审查 27 项遗留缺陷

`v2.6.1 (r29)` 是在 `v2.6.0` 基础上的**质量与安全性稳健提升版本**，全面闭环了交付反馈与 27 项遗留缺陷：

### 🔐 门禁隔离与安全加固
- `gates_v101.py` 强制使用隔离的临时目录进行快照比对，彻底根治真机并发写盘导致的偶发 16/17 假阳性误报；
- 配置备份 `/api/ops/backup` 默认脱敏导出（遮罩 Telegram 与 SMTP 凭据）；
- 登录限流增加线程锁与 LRU 淘汰；拦截非法负数 `Content-Length` (400)；

### 🌐 分流精度与网络稳定性
- T10 自定义海外 DNS 自动绑定 `detour` 并在关闭 IPv6 时前置插入 `AAAA` 抑制防污染；
- `direct_all` 将 `198.18.0.0/15` 改为 `outbound: "block"` 毫秒级重查真实 DNS，彻底杜绝 30s SYN 挂起；
- `forward_mss` 严格受控于 `tcp_mss_clamp` 开关，并将 IPv6 防漏解耦独立为 `chain forward_v6_guard`；
- 新增备用国内 DNS `119.29.29.29`，单组远程规则容量提升至 20,000 条；

### ⚙️ 系统保护与前端交互
- `sing-box` 的 `cache.db` 迁入内存盘 `/var/run/ai-link/cache.db`，不再磨损闪存；
- 动态识别 LAN 网卡设备名，`init.d` 优先调用 `jsonfilter` 并保留 `mwan3` 100/101 路由表；
- 剔除 OpenAI / Claude / TikTok 探测假阳性；
- 修复 3D 星图 galaxy 页面渲染，切换分流模式自动联动解除 `bypassActive`；

### ✅ 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **93/93 PASS**（含新增 `Stage 7.30`）、发布门禁双布局 `17/17`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务稳定；UI 六页三视口零溢出；出网 200/200/204。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从现网直升，配置、节点、订阅、节点池全部保留，失败自动回滚。本次为正常升版，现网设备会收到 OTA 提示。

---

## 包指纹

```
AI-LINK-v2.6.1.tar.gz   1,136,031 B
md5     a48d1a8dded6f47c039a4e4bc7d3611b
sha256  573350cbdcd7c2bfb6510068638830a712635b2bfada1d3b7754e74c9875e161
```
