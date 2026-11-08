# AI-LINK v2.5.0

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-08 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：让「多线并发」从配置真正走到数据面

上一轮功能级诊断（《DIAG-多线并发功能生效性-20261108.md》）指出：`dispatch_mode = multi_line` 只实现到应用层候选池，`sing-box.json` 里没有任何 `urltest`/`loadbalance` 出口，实际仍是单节点承载。本版做三位一体闭环：

1. **内核出口生成层**：对每个非敏感的 `multi_line` 池生成专属 `urltest` 出口 `Auto_<pool>_MultiLine`，成员严格限定为剔除慢节点后的 `multi_line_nodes`，并设 `interrupt_exist_connections: false`；
2. **绑定组无损切换**：`Shunt_YouTube` / `Shunt_TikTok` 等绑定组的 `outbounds` 置顶收敛为多线成员 + urltest，`interrupt_exist_connections: false` 保证存量连接不断流；`Shunt_AI` 等 IP 敏感组维持 `true` 与单线锁定保护；
3. **实时调度层**：新增 `dispatch_multi_line_pools_tick()` 与 0.5 秒守护线程，按组间错峰偏移静默轮转 selector 的 `now`。配合无损连接开关，存量视频流不中断、新建连接均匀分摊到各物理节点；切回 `single_best` 立即停止轮转。

**真机实测**：并发 10 条持续连接，9 条 YouTube 连接**同时由 2 个不同物理节点承载**（6 + 3），各自下载字节持续增长；5 次采样中 `Shunt_YouTube` 的 `now` 依次轮转到 HY42 / 03 / HY41 / HY47 / HY48，`Shunt_TikTok` 错峰指向不同节点。

### 🧩 自动节点池全生命周期严查

- 慢节点离散度过滤在 `_normalize_auto_node_item` / `evaluate_single_auto_node` / `resolve_node_for_country_strategy_with_failover` 三处同源；
- 建池自动选取引入带宽择优与滑窗稳定性加权，严格排除 4 层 DAG 中的链式落地节点；
- 6 步向导引入 `scopeDirty` 脏标记：改了来源/国家/关键词/容量后直接保存，会先自动重筛；
- 低健康补位、手动移除、替换成员后强制 `write_all_configs()`，`sing-box.json` 的 urltest 与 selector 成员实时同步。

### 📥 订阅自动同步可控

- 每张订阅卡片新增「自动同步: 每Xh / 自动同步: 已关闭」胶囊开关，一键切换并持久化；
- 编辑弹窗内新增独立「定时自动同步」开关，关闭时禁用间隔输入框，`auto_update=false` 不再被 `Number(val || 360)` 改回 360；
- 手动点「立即同步」在未显式传参时严格保留原订阅的 `auto_update` 与 `update_interval_min`。

### ✅ 稳定性

延续 v2.4.8 的 P0 修复（nft 协议族分离），安装真实退出码 0、`nft=1`、重启后仍稳定挂载。Design Lint 18/18、发布门禁 16/16、深度混沌 39/39、`test_v102` 152/152。

> 说明：官方 15 套回归中 `daemon --self-test` 一项因内置自测的 outbound 键白名单未同步 `urltest` 的 `url`/`interval`/`tolerance` 三个字段而误报；`sing-box check -c /etc/ai-link/sing-box.json` 实际返回 0，内核配置合法。详见发布记录。

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
AI-LINK-v2.5.0.tar.gz   804,971 B
md5     2ce231ef53c3a5fc31b3cbb38dc5a333
sha256  6261d2e55fa102e8241324bea1953cd5501e772eb1c1b70e36c7d3c327cde6f3
```
