# AI-LINK v2.4.3

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-08 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：把上一轮的问题全部闭环，再补五个新能力

### 🔄 交付闭环（VERIFY-v2.4.2-r2 逐条修复）

- **升版 2.4.3**，七处版本锚点对齐，解决「同版本号修包 → 现网设备收不到 OTA 提示」的死锁；
- `index.html` 全部 8 项静态资源 `?v=2.4.3-<hash8>` 与文件真实 MD5 前 8 位 100% 一致，`gates_v101.py` 新增第 16 项 `static_assets_md5_gate` 硬门禁；
- 交接包完整收录 `tests/`（15 套套件 + 12 个订阅格式夹具）、`tools/`、`site/ai-link-openwrt/` 源码树与全部文档；
- 接管手册重写至 2.4.3 基线，清除 v2.3.6 残留；`except->pass` 收敛回 8。

### ⚡ 多线并发与 AI 防风控

- 自动节点池新增 `single_best`（优选单线）与 `multi_line`（多线并发）两种调度模式；
- 当 `AI / Google / Microsoft / Apple / Social / Soul / Copilot / WorkBuddy` 等 IP 敏感分流组绑定多线并发池时，后端自动启用 `auto_single_line_protected=True` 锚定单主节点，流媒体组仍保持多线并发；
- 池内健康节点 4→3→1→0→补满全周期零振荡、零死锁，0 健康时稳定回退 direct 不把死节点塞回并发列表。

### 🕸 链式代理 4 层 DAG 与线路识别

- 构建严格 4 层有向无环图（Shunt Selector → Chained Node → Auto-Pool Selector → Physical Transit Node），自动剥离环路；
- 前置节点改名或节点池删除时 `reconcile_node_references` 级联迁移 `detour`，零孤儿引用；
- 自动识别「中转专线 / 链式落地 / 直连线路」，向导支持原名关键词 `AND / OR` 过滤与定量低频「带宽择优」。

### 📊 三维流量归因洞察与底层调优

- 新增 `/api/traffic/insights`：24h / 7d 趋势 + 终端 × 节点 × 目标域名三维下钻；
- 多核 CPU `RPS / RFS / XPS` 软中断静默均衡与 `GOMAXPROCS` 调优；节点切换时异步秒清 Clash 活跃连接与内核 `conntrack` 表项。

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
- 面板默认仅信任本机回环，需从局域网其他设备访问时请自行配置令牌或可信网段；
- 本轮交接包中 `run_all.py` 列出的 `v242_deep_chaos_simulation.py` 未随包交付，该套件无法在验收侧复现（不影响产品功能）。

---

## 包指纹

```
AI-LINK-v2.4.3.tar.gz   776,930 B
md5     dd7baa8299f10dd59eeffd3b1299f2cd
sha256  d26c9db0723e11ee5d824c065d125b767b27d712f23c6c9fc78989f8f038fa7f
```
