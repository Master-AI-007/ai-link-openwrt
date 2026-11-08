# AI-LINK v2.5.2

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-09 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：节点池严格守住你勾选的范围

### 🎯 自动节点池「只从你勾选的订阅源和地区里选」

此前存在一个体验问题：建池时勾选了指定订阅源与地区，但订阅更新后的自动补位、健康巡检复选、甚至保存归一化，都可能把范围外的节点带进池子。本版做了 6 层闭环：

1. **订阅同步补位**：`_reconcile_auto_pools_after_sub_sync` 在低水位补位前，先用 `_filter_nodes_by_pool_scope` 按池的 `scope_sources` / `scope_countries` 过滤；不仅补位只从范围内选，**存量里越界的节点也会被自动剔除**；
2. **保存归一化**：每次保存/归一化都把 `scope_sources`、`scope_source`、`scope_countries` 与 `filters`（`sub_id` / `region_any` / `require_services` / `replenish_threshold`）双向锁步，改过范围后旧 `filters` 不再残留；
3. **健康巡检复选**：`maintain_auto_node_pool_health` 入口预计算范围内集合，越界成员立即剔除，只从范围内择优补齐；
4. **范围过滤守卫**：收紧单订阅通配分支的放行漏洞，完善 `id` / `url` / `name` 交叉匹配，并在分组归一化、替换候选、分流解析三处统一接入；
5. **前端向导**：在配置弹窗里改了订阅或地区并保存时，自动剥离已选集合中越界的旧节点，提交的列表 100% 符合新范围；
6. 配套 Stage 6.22 门禁覆盖上述路径。

### 📦 测试集首次真正随包内置

上一轮反馈指出「混沌脚本连续多轮未随包交付」，本版把 `tests/` 真实写入安装包与交接包的三处位置（`tar: ai-link-openwrt/tests/`、`zip: tests/`、`zip: site/ai-link-openwrt/tests/`），并把发布门禁改为：修正套件提取正则、强制 `len(suites) >= 14`、用 `tarfile`/`zipfile` **直接开包**核对每个脚本存在、逐行核对报告指纹表。

> 验收侧补充说明：脚本本体已进包，但 `tests/subscription_formats/` 夹具目录仍未打入，导致「原始包零补发」跑 `run_all` 时订阅格式那套会因缺夹具失败；该项不影响产品运行，已列入反馈单。

### ✅ 稳定性

P0 与多线并发均未退化：安装真实退出码 0、`nft=1`、重启后仍稳定挂载；两个 `urltest` 多线出口在线，AI 敏感组保持单线保护。Design Lint 18/18、发布门禁 17/17、混沌 45/45。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x ~ 2.5.1 直升，配置、节点、订阅、节点池全部保留，失败自动回滚。

---

## 已知限制

- 订阅为网页/HTML 或 Token 失效时无法解析，需要更新链接；
- 500+ 节点规模下 `quick_create` 首次约 1 秒；
- 面板默认仅信任本机回环，需从局域网其他设备访问时请自行配置令牌或可信网段。

---

## 包指纹

```
AI-LINK-v2.5.2.tar.gz   940,660 B
md5     662b647a380b90d00c40c10c0e5f35d6
sha256  f9922563137cef494e61b62bc87fdea32f38c85cc4c4cf3f02086a7dad8430d3
```
