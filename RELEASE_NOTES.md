# AI-LINK v2.3.7

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-04 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：六个页面，一条横幅；两个 P0，一并收掉

### 🖼 全站统一单横幅 Hero

概览、分流、回家、护盾、节点、设置六页全部改成同构单横幅：

- 左侧光子轨道 + 中心发光主核（与导航图标 1:1）；
- 中间主标题 + `?` 战术指南 + 3 项实时 KPI；
- 右侧控制区（各页操作按钮）；
- 旧的独立 `.content-head` 全部移除，**零双顶栏叠加**。

### 🛡 P0 修复

- **P0-1**：`apply_nft.sh` 改为三级加锁（`flock -x -n` → util-linux `-w` → BusyBox 轮询 → mkdir 自旋），BusyBox 不再因 `-w` 不支持而静默跳过 `table inet ai_link` 挂载；
- **P0-2**：每日测速配额达到上限时改为「跳过并保留原健康状态」（`QUOTA_SKIPPED_PRESERVE`），不再把全部节点写成 `dead`、不再清空节点池把分流降级直连。

### 🧩 细节

- 探测缓存纳入 `node_probe.json` 签名，`/api/status` 与 `/api/auto_nodes` 的可用计数同源；
- 顶栏连接数可点击跳到实时连接表；
- `--mint` 对齐 `#38e0b2`；修复离线概览重复告警条与护盾页 `NaN`；
- 订阅自适应（11 格式）与「手动即固定」延续 v2.3.6。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x / 2.1.x / 2.2.x / 2.3.x 直升，配置、节点、订阅、节点池全部保留，失败自动回滚。

---

## 已知限制

- 订阅为网页/HTML 或 Token 失效时无法解析，需要更新链接；
- 594 节点规模下 `quick_create` 首次约 1 秒；
- 面板默认信任局域网，公网暴露请开启强制登录。

---

## 包指纹

```
AI-LINK-v2.3.7.tar.gz   724,101 B
md5     8b1e6187e0c800ac53f0da522de34e3f
sha256  87fbef7b5568dcb72dec8ce19f655b6a53a688dfef7ac87a3e88fa2dc4622bfc
```
