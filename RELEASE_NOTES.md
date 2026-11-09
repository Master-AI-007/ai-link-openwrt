# AI-LINK v2.5.6

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-09 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：加强复审计

这一轮把上一版复审计里暴露的问题逐条收口，共 6 项 P1、6 项 P2，并追加一轮深度打磨增量。

### 🔒 自检不再与后台服务抢写状态

`--self-test` 末尾的「全文件逐字节相等」断言升级为**进程级零生产写入守卫 + 语义脏标签断言**：只判断本进程有没有写过生产状态文件、`selections.json` / `switch_history.json` 里有没有假节点残留，不再受后台常驻 daemon 正常选点写入的时序影响。真机在生产流量下连跑两次，均为 `RC=0 / SELF_TEST_PASSED / stderr 零告警`。

`tarfile.extractall` 也补了 `filter="data"` 兼容参数，消除 Python 3.14 的弃用告警。

### 🧵 多线写入只有一个出口

新增唯一 `SelectorWriteCoordinator` 收口全部 Clash Selector 写入路径：

- 目标未变化时直接跳过 `PUT`（`skipped_noop`），不再 2~4 秒一次无意义回跳；
- `dispatch_multi_line_pools_tick` 与 dispatch 接口默认启用 30 秒驻留；
- `evaluate_all_auto_nodes` / `apply_shunt_selections` 对已处于合法 `multi_line_nodes` 内的选择器保持原状，正常轮换只更新遥测、不污染切换历史；
- 外部热切（内核日志被动秒切、手动切换、退化收敛）实时同步轮询器状态，消除后续冗余写入。

### 🛡️ 故障判定与订阅更保守

- 内核日志故障转移把「无明确目标」的超时日志纳入抑制守卫，杜绝单条/空目标误触发直连降级；
- 订阅同步预览完整区分同名但换端点/换凭据的节点，连续拉取重合度过低时给出动态随机订阅预警；替换候选严格按池地区、关键词、AI 锁区与健康度排序；
- **TLS 默认严格**：移除 curl 35/51/60 自动 `-k` 重试与 localhost 默认 `-k`，`urllib` 改用 `create_default_context()`，仅在订阅显式配置 `allow_insecure_tls` 时放宽。

### 📦 卸载与闪存更干净

IPK 补齐 `prerm` / `postrm`：自动停服务、删除 `table inet ai_link`、清理 dnsmasq 转发并重启恢复 DNS；`control` 的 `Description` 与 `Version` 对齐 2.5.6-r16。`node_probe.json` 实时写入改到 tmpfs，闪存副本按 180 秒节流同步，消除每次探测双份落盘。Watchdog 恢复现在会记录前后 PID、退出原因与恢复耗时。

### ✅ 交付与验证

四项出包标准保持：**夹具整棵随包、零补发 15 套全量回归、自检沙箱隔离、报告数据实测注入**。真机用原始包不补任何文件跑出 `run_all 15/15 PASS / RC=0`、混沌门禁 `78/78`、Design Lint `18/18`、发布门禁 `17/17`；安装退出码 0、`nft=1`、重启后稳定；4 个多线出口在线、AI 敏感组保持单线保护；UI 零异常、三视口零溢出。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x ~ 2.5.5 直升，配置、节点、订阅、节点池全部保留，失败自动回滚。

---

## 已知限制

- 订阅为网页/HTML 或 Token 失效时无法解析，需要更新链接；
- 500+ 节点规模下 `quick_create` 首次约 1 秒；
- 面板默认仅信任本机回环，需从局域网其他设备访问时请自行配置令牌或可信网段；
- 多出口轮询为实验特性，不叠加单流带宽。

---

## 包指纹

```
AI-LINK-v2.5.6.tar.gz   1,008,250 B
md5     45a80b918adbbef159dded8910f16a72
sha256  5a4eb5aa97a189528bfc135ed7966606bd1343f5bf5c4f866c63800df87e3aa9
```
