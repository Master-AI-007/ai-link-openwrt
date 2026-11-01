# AI-LINK OpenWrt 变更日志 (CHANGELOG)

## [v2.3.2] - 2026-11-01 — 紧急修复版：Play 商店 LAN Wi-Fi 下载更新闭环 + 回家节点新建弹窗零卡顿防重复创建

### 🌟 两项紧急问题根因修复 (v2.3.2 Highlights)

1. **[紧急修复 1] 彻底解决「Play 商店在局域网 Wi-Fi 下可以打开但无法更新，而 5G 连回家节点却能更新」的问题**
   - **根因 1（`dnsmasq` `cname=` 导致 `.cn` 谷歌鉴权/下载域名返回空记录 NODATA）**：此前 `apply_dns_rewrite_system` 将 `DEFAULT_DNS_REWRITE_RULES`（`services.googleapis.cn`、`googleapis.cn`、`gstatic.cn`、`developers.google.cn`、`google.cn`）写入 `/tmp/dnsmasq.d/ai-link-rewrite.conf` 为 `cname=services.googleapis.cn,services.googleapis.com`；而 `dnsmasq` 的 `cname=` 指令要求目标域名必须存在于本机 `/etc/hosts` 中，否则 `dnsmasq` 会将源域名标记为本地权威记录并直接返回 **0 条 IP（NODATA）** 且绝不转发给 `:7874` `sing-box`！国行/插国内 SIM 卡的安卓手机在打开 Play 商店浏览时走 `.com`（正常打开），但点击「更新」时系统 `DownloadManager` / `GmsCore` 会请求 `services.googleapis.cn` 与 `gstatic.cn` 校验下载令牌，在局域网 Wi-Fi 下经 `:53` `dnsmasq` 直接收到空记录导致无法更新；而切到 5G 连回家节点时，流量直接进入 `sing-box` 的 `homelink-*-in` 入站绕过了 `dnsmasq`，所以能正常更新。**现已将 `ai-link-rewrite.conf` 中非 IP 重写统一改为 `server=/{src}/127.0.0.1#7874`**，强制交由 `sing-box` 分配 Fake-IP 并走代理分流。
   - **根因 2（`HTTPS` Type 65 / `SVCB` Type 64 记录泄漏国内 GGC 死 IP 与 `h3` ALPN）**：在 `sing-box.json` `dns.rules` 首条新增 `{"query_type": ["HTTPS", "SVCB"], "action": "predefined", "rcode": "NOERROR"}`，并为所有 `dns_fakeip` 规则显式限定 `query_type: ["A"]`（或 `["A", "AAAA"]`），防止安卓 Cronet 下载器收到 `223.5.5.5` 返回的 `HTTPS` 记录（内含 `203.208.x.x` / `180.163.x.x` 国内 GGC 死 IP 的 `ipv4hint` 与 `ipv6hint`）。
   - **根因 3（`route.rules` 顶层 Google Play 保护规则早于 `blocklist_custom` 与 `Domestic_CN`）**：扩展 `ESSENTIAL_APP_WHITELIST` 覆盖 35 个 Google Play 下载与鉴权核心域名（含 `googleapis.com`、`googleapis.cn`、`services.googleapis.cn`、`play-fe.googleapis.cn`、`c.android.clients.google.com`、`dl.google.com`、`dl-ssl.google.com`、`gvt1~3.com`、`xn--ngstr-lra8j.com`、`ota.googlezip.net` 等），并在 `sing-box.json` `route.rules` 置于 `blocklist_custom` 之前直达 `Shunt_Google`。
   - **根因 4（`nftables` `@google_play_v4` 集合前置拦截国内 GGC 网段）**：在 `generate_nft_rules_file` 新增 `@google_play_v4`（含 `203.208.32.0/19`、`180.163.150.0/23`、`114.250.64.0/20`、`220.181.174.0/24`、`120.253.250.0/22`、`142.250.0.0/15`、`172.217.0.0/16`、`74.125.0.0/16`），在 `output_nat` 与 `prerouting_tproxy` 中置于 `@cn_ip4`（国内流量不进内核）之前强制送入 TProxy `:7893`。

2. **[紧急修复 2] 彻底解决「添加回家节点弹窗无法点击、类似卡顿、点几下后无响应并多出一堆回家节点」的重大 BUG**
   - **根因定位**：① 原弹窗内 3 张协议卡片绑定了直接提交创建的 `data-action="create-homelink"`，点击时既不切换 `.active` 高亮也不禁用按钮，而底部「完成」按钮未绑定回调（点击只关闭弹窗）；② 后端 `/api/homelink/quick_create` 在 HTTP 请求线程内同步执行了 `sync_homelink_wan_firewall_rules` + `reload_core_only(force_respawn=True)` + `apply_nft.sh`，单次请求阻塞长达 **6~12 秒**；用户以为点击未生效而连续点击多次，导致后台排队生成一堆带递增端口的回家节点并连续重启内核。
   - **前端交互重构**：将弹窗内 3 张协议卡片改为 **0ms 即时切换选中态 (`data-action="select-homelink-proto"`)**，点击卡片立即高亮 `.active`、显示 `✓` 并自动联动默认端口提示（`18443`/`20443`/`9443`）与底部主按钮文案（`🚀 立即创建 VLESS-Reality / Hysteria2 QUIC / VLESS-TLS 回家节点`）；点击底部主按钮执行创建时立即置 `state.creatingHomelink = true` 防重入锁并禁用按钮显示 `⏳ 正在创建回家节点...`。
   - **后端异步非阻塞化（`<50ms`）+ 3 秒幂等防重 + 一键清理重复节点**：`/api/homelink/quick_create` 与 `/api/homelink/add` 增加 `_HOMELINK_CREATE_LOCK` 与 3 秒幂等去重保护（拦截连点产生的重复请求），并将防火墙同步与内核重载改为后台异步执行（`schedule_async_core_reload`），响应耗时从 `~8000ms` 降至 **`<50ms`**；同时在回家节点页顶部新增 **「🧹 清理重复节点 (`POST /api/homelink/dedup`)」** 按钮，可一键清理此前产生的多余回家节点。


## [v2.3.1] - 2026-11-01 — 远程规则源删除与400严格参数校验 (P2-1) + GET /api/shunt/rule_blocks (P3-2) + 补丁30/30字节一致 (P3-1) 正式版

### 🌟 核心修复与体验打磨 (v2.3.1 Highlights)

1. **[P2-1] 远程规则源完整删除能力 + 创建/更新严格参数校验（拒绝空 URL 垃圾条目）**
   - **多方式删除支持**：`POST /api/shunt/rule_providers` 支持 `{"id": "rp_xxx", "action": "delete"}` / `{"delete": "rp_xxx"}`、`POST /api/shunt/rule_providers/delete` 以及 `DELETE /api/shunt/rule_providers?id=rp_xxx`，删除后从内存与 `/etc/ai-link/rule_providers.json` 同步移除，并自动清理任何无合法 `url` 的历史残留条目。
   - **严格 400 参数校验**：创建或更新规则源时强制校验 `url` 必填且为合法的 `http://` 或 `https://` 地址、`format` 必须为 `domain_list` 或 `srs`；缺失或非法请求立即返回 HTTP `400` 且绝不落盘。
   - **前端交互闭环**：在「🌐 远程分流规则订阅管理」弹窗中为每条规则源提供「🔄 同步」与「🗑️ 删除」按钮，点击删除接入 `confirmModal` 二次确认与 **「↩ 撤销删除」**。

2. **[P3-1] 补丁与安装包 30/30 文件（含二进制图标）100% 字节一致**
   - 修复此前打包脚本对全目录文件执行换行符替换时误触二进制文件 `apple-touch-icon.png` 与 `favicon.ico` 的问题；直接以已发布的 `AI-LINK-v2.3.0.tar.gz` (`sha256 10c0da44…`) 解包目录为只读基线生成 `v2.3.0-to-v2.3.1-code.patch`，实测 `patch -p1` 后 **30/30 文件 100% 字节一致（0 差异）**。

3. **[P3-2 & T6 UI] 补齐 `GET /api/shunt/rule_blocks` + 配置历史回滚双语义按钮**
   - 补齐 `GET /api/shunt/rule_blocks`（支持全局或 `?group_id=...` 按组查询），返回结构化规则块列表；
   - 优化「📜 配置变更历史与回滚」弹窗按钮文案，同时提供 **「⏪ 恢复到此版本（变更后状态）」** 与 **「↩ 撤销此变更（恢复至变更前状态）」**。


## [v2.3.0] - 2026-11-01 — BUG-008 严格锁定持久化闭环 + 方案 A 批次三/四 (T2/T3/T5/T6/T8/T9/T10) 全量正式版

### 🌟 核心修复与架构升级 (v2.3.0 Highlights)

1. **[BUG-008 / P1] 「严格锁定」开关读写对称持久化与死节点防漂移闭环 (`NEXT-SUBMISSION-4.md`)**
   - **根因解决**：修复 `/api/shunt/update` 的 `group_id` 分支与批量 `groups` 分支未接收 `strict_lock: bool` 字段导致前端点击切换无法落盘的问题；同时在 `build_shunt_api_response` 与 `PROBE_ENGINE.apply_shunt_selections` 中前置检查 `strict_lock`，确保当 `strict_lock=true` 且手动指定节点不可达时，`resolved_node` 与内核 selector 均严格保持 `manual_node`（`strict_locked_dead=true`、`manual_drifted=false`），绝不漂移；当 `strict_lock=false` 时允许容灾漂移并返回 `manual_drifted=true` 及 `⚠ 指定节点不可用，当前临时使用 Y` 告警。
   - **前端状态实时同步**：点击分流组卡片的 `🔓 允许漂移` / `🔒 已锁定` 按钮后直接以 `/api/shunt/update` 响应为准刷新按钮文案（死节点锁定时显示 `🔒 已锁定（不可用）`），并在分流组编排弹窗内同步提供严格锁定复选框。

2. **[T2 / P0] 拓扑自动识别 (`main` / `bypass` / `onearm` / `docker`) + 3 步快速接入向导 (`/api/topology/detect` & `/api/topology/apply_wizard`)**
   - 自动根据默认路由出接口、本机 `:67` DHCP 状态、WAN 地址及容器环境特征精准识别 4 类网络拓扑并输出置信度与判据文本；提供顶栏 `🧭 接入向导` 3 步引导（确认拓扑 ➔ 一键复制主路由/本机 DNS 与网关参数 ➔ 联动 T1 第 1/2/3 项实时验证）。

3. **[T3 / P0] 旁路由 IPv6 防漏组合模式两档策略 (`strict` 严格档 / `loose` 宽松档 / `off` 关闭)**
   - 在 `ops_settings` 与 `--generate-nft` 新增 `ipv6_leak_mode` 两档策略：**严格档（默认）**在 `forward_mss` 链阻断全部 LAN→WAN IPv6（仅放行 ND/ICMPv6、DHCPv6、本机 DNS 与保留地址），**宽松档**额外放行 `@cn_ip6` 国内 IPv6 直连网段并阻断海外 IPv6，关闭后无残留移除防漏规则，并与 T1 第 3 项 `ipv6_bypass` 体检闭环联动。

4. **[T5 / P1] 告警通道（Webhook / Telegram Bot / SMTP）+ 30 分钟去重 + 恢复通知 + 事件中心 (`/api/alerts/*`)**
   - 支持 7 类固定事件（节点全挂、订阅同步失败、DDNS 失步、内核异常重启、证书到期、磁盘不足、体检失败），同类告警 30 分钟内智能去重，恢复时自动推送 `recovered` 通知，面板展示最近 200 条事件，且所有密钥/Token 在读取时强制 `***` 脱敏。

5. **[T6 / P1] 配置变更历史 + 结构化字段 Diff + 10 秒内一键回滚 (`/api/ops/config_history` & `/api/ops/config_rollback`)**
   - 写配置前自动生成快照（保留最近 20 份 / 7 天，总体积 `<5 MB`），计算结构化字段级 `added` / `removed` / `modified` Diff，支持在 1 秒内一键回滚至任意历史版本。

6. **[T8 / P1] 规则块增强（`domain_regex` / `src_ip_cidr` / `port` / 两级 `AND-OR` 组合）+ 正则语法位置校验 + 实时试匹配 (`/api/shunt/rule_blocks` & `/api/shunt/test_rule_match`)**
   - 支持表单化编排域名正则（单组上限 20 条，保存前自动编译校验，非法正则精确提示如 `正则不合法：位置 2`）、来源设备 IP/CIDR、端口/端口段及两级 `AND`/`OR` 逻辑组合，内置「🎯 实时试匹配」器。

7. **[T9 / P1] 导入式远程分流规则订阅 (`/api/shunt/rule_providers` & `/api/shunt/rule_providers/sync`)**
   - 支持导入域名列表与 sing-box `.srs` 规则源（默认 24h 周期），展示规则条数、最后更新时间与失败原因；同步失败（如 404 或超时）时 100% 原子保留原有规则不受影响。

8. **[T10 / P1] DNS 按组独立策略 + 1 小时上游缓存命中率/平均延迟/失败率统计 (`/api/dns/upstream_stats`)**
   - 每个分流组支持独立选择「继承全局 / 自定义 DoH / DoT / DoQ / 本地上游」，四阶流量透视第 2 阶段实时反映该组专属 DNS 且不影响其他组；DNS 页展示各上游最近 1 小时的缓存命中率、平均延迟与失败率。

9. **[P3-1 & P3-2] 补丁与安装包 30/30 文件 100% 字节一致（含 `README.md` LF 统一）+ 单一权威发布包**
   - 统一全部 30 个包内文件（含 `README.md`）为 LF 换行符，`v2.2.0-to-v2.3.0-code.patch` 经 `patch -p1` 实测 **30/30 文件 100% 字节一致（0 差异）**。


## [v2.1.1] - 2026-11-01 — 自动节点池 v2 (L1~L4 服务语义与 Google 地区判定 · node_key 无损迁移) + BUG-006/007 全量正式版

### 🌟 核心修复与架构升级 (v2.1.1 Highlights)

1. **[BUG-006 / P1] Google 视角地区判定 (`301 Location TLD`) 与 Gemini 防地域拒服**
   - **根因解决**：针对部分标日/标美节点（如 `VIP1-HY09-日本`）被 Google 自身 GeoIP 判定为香港（访问 `https://www.google.com/?hl=en&gl=us` 被 `301` 重定向至 `google.com.hk`）导致 Gemini 报错「不支持你所在的地区」的问题，新增 `parse_google_redirect_region` 与 `get_node_google_region_info`，并彻底移除旧版 `probe_node_service_l7` 中对 HK 节点盲目放行 `ok=True` 的旁路逻辑。
   - **UI 可视化与自动池联动**：在节点列表、节点详情弹窗及自动池卡片显式展示 **「🚫 Google 地区：HK（不支持 Gemini）」**（红色告警）或 **「Google 地区：JP（支持 Gemini）」**；AI 与 Google 自动节点池在选点时自动排除 Google 判定为 `HK/CN/MO/RU` 等不支持地区的节点；T1 网络健康医生第 8 项同步检测当前 AI 出口的 Google 地区并提供一键切换修复。

2. **[BUG-007 / P2] 允许移除正在使用的池内节点 + 占用确认 + 自动切下一个 + 「↩ 撤销移除」**
   - **后端根因修复**：移除 `evaluate_single_auto_node` 中在特定条件下将外部 `saved_nodes` 静默插回 `groups[0]["node_tags"]` 的自愈代码块，并修正 `_extract_group_resolved_nodes` 中 `cand_tag` 相比旧 `cand_id` 的解析优先级，确保用户在前端移除当前出口节点并保存后，该节点彻底从池中移除并立即切换至下一合格节点。
   - **前端交互闭环**：支持移除任意池内节点（含标注 `⚡ 当前出口` 的节点）；若该节点同时被某分流组手动指定，先弹出影响确认并在确认后自动将该分流组切回自动池；移除后弹出带 **「↩ 撤销移除」** 的 Toast，点击即可将节点还原至原分组与原位置；若池被清空则明确提示「请至少保留 1 个节点」。

3. **[Auto Node Pool v2] 真正可用的四层服务探测与 `node_key` 抗变调度器 (`DESIGN-auto-node-pool-v2.md`)**
   - **四层检测模型 (L1~L4)**：L1 连通性与抖动、L2 服务方视角语义（Google 301 TLD + ChatGPT `/cdn-cgi/trace` `loc=`，按 `(node, service)` 缓存 6 小时、IP 变化即失效）、L3 配额风控识别（HTTP `429` 进入 60 分钟 `cooldown` 冷却而非判死）、L4 被动反馈（从 Clash 活跃连接聚合真实失败率，仅平滑降分不直接触发抖动切换）。
   - **稳定身份 `node_key` 与订阅更新 Diff / 7 天 `missing` 占位 / 影响预览**：定义与 `tag` 无关的 `node_key = sha1(protocol|server|port|cred_fp|sni|pbk)[:16]`；订阅更新改名时池成员 100% 无损保留；节点消失时转入 `missing_members` 保留 7 天占位告警并按 `filters` 自动补位；新增 `/api/subscriptions/preview_sync` 与「🔍 影响预览」弹窗。
   - **防抖稳定性四机制与可解释 UI**：EWMA 延迟与成功率平滑 + 连续 3 败进 10 分钟 `quarantine` 隔离区 / 连续 2 成恢复 + 10 分钟粘性保护（小幅抖动 0 切换，仅硬失败或新节点评分领先 $>30\%$ 才切换）+ 池卡片展示 `💡 选点依据` 与最近切换原因悬浮提示。

4. **[D-1 ~ D-3 & VERIFY-v2.1.0 P3] 交付工程闭环**
   - **D-1**：交接包 `tests/` 完整包含 `diag_e2e.py`、`trace_e2e.py` 与新增 `autopool_v2_e2e.py`（共 11 套测试套件，解压直跑 `python3 tests/run_all.py` 11/11 全绿）。
   - **D-2**：从 `site/ai-link-openwrt/` 移除旧版 `luci-app-ai-link_2.0.0-r8_all.ipk`，并在交接包根目录提供重新构建的 `luci-app-ai-link_2.1.1-r8_all.ipk`（`Version: 2.1.1-r8`）。
   - **D-3 & P3**：修复 `test_v102_full_regression.py` 中 `B2-8` 跨平台路径兼容性；补齐 `/api/diag/run` 顶层 `status` 与 `score` 字段；将 `ipv6_leak_guard` 与 `tcp_mss_clamp` 纳入 `ops_settings` 写盘白名单，确保 `fix_all` 后 `#3 ipv6_bypass` 复检闭环为 `pass`。


## [v2.1.0] - 2026-11-01 — 方案 A (Phase 1 止血与契约清理 + Phase 2 核心诊断能力) 全量正式版

### 🌟 核心修复与新增特性 (v2.1.0 Highlights)

1. **[T1 / P0] 一键网络健康医生 + 一键自动修复 (`/api/diag/run` & `/api/diag/fix` + 顶栏 `🩺 网络医生` & 设置页入口)**
   - **8 项全链路并发诊断 ($\le 10\text{s}$)**：并发执行 `#1 客户端 DNS 归属`、`#2 AAAA 抑制有效性`、`#3 IPv6 绕过路径`、`#4 回家 DDNS 有效性（含权威 NS 与注册商比对）`、`#5 回家端口可达性`、`#6 上游连通性`、`#7 MTU / 分片 PMTU 探测`、`#8 关键应用连通（联动 BUG-004）`。
   - **一键修复与自动复检**：针对可自动修复的异常项提供单项修复与「🛠️ 一键修复异常项 (`fix_all`)」，针对主路由 DHCP / 端口映射 / 域名注册商 NS 提供一键复制排障指引。

2. **[T4 / P0] 1 小时滑动窗口分流规则命中排行榜 (`/api/shunt/hit_stats` + 分流页 `#shunt-hit-leaderboard-card`)**
   - **三维 Top 10 实时聚合**：基于内存级 60 分钟滑动窗口环形缓冲 (`_SHUNT_HIT_STATE`)，支持按「策略组 (`by_group`)」、「具体规则 (`by_rule`)」、「实际出口 (`by_outbound`)」三维切换展示命中次数、占比与累计流量，点击任意排行项可直接跳转并筛选实时活跃连接表。

3. **[T7 / P1] 订阅健康度全量展示 (`parse_subscription_userinfo` + 节点页 `.sub-health-box`)**
   - **流量进度条与到期预警**：解析标准 `Subscription-Userinfo` 响应头，在订阅卡片直观展示已用/总流量进度条、使用百分比、剩余可用流量、剩余天数胶囊（$\le 7$ 天琥珀色预警、$\le 3$ 天红色告警）、每月重置日与最近同步状态；无该响应头的机场订阅优雅降级显示「未提供 (该订阅源未返回 Subscription-Userinfo)」，绝不误显 `0 / 0`。

4. **[BUG-001 ~ BUG-005] Phase 1 五项遗留缺陷彻底根治**
   - **BUG-001 (P1 · 4 阶流量透视契约统一)**：修复后端 `trace_traffic_flow` 与前端 `showTrace` 字段映射错位，测试命中代理组（含自定义组如 `Soul`）时第 3 步准确展示策略组名与匹配原因、第 4 步准确展示真实代理节点（彻底杜绝出现 `"实际出口: DIRECT"`）；测试国内直连（如 `www.baidu.com`）时第 3/4 步一致显示「直连 · 未命中代理组」。
   - **BUG-002 (P3 · 自定义分流组删除按钮)**：在 `/api/shunt` 自动识别非内置自定义分流组并标记 `is_custom: true`，在分流组卡片与编排弹窗内均渲染「🗑️ 删除」按钮并接入 `confirmModal` 二次确认与「↩ 撤销删除」。
   - **BUG-003 (P3 · 自动节点池双入池按钮语义区分)**：将 `#modal-autopool` 中的两个入池按钮明确区分为 **「✅ 仅入池检测达标项」** 与 **「➕ 免测直接加入池」**，并附带清晰悬停说明。
   - **BUG-004 (P1 · Google Play 等核心应用防误杀白名单保护)**：内置 `ESSENTIAL_APP_WHITELIST`（涵盖 `clientservices.googleapis.com`、`clouderrorreporting.googleapis.com`、`play.googleapis.com`、`play-fe.googleapis.com`、`android.clients.google.com`、`gvt1~3.com`、`dl.google.com` 等）并在 `#page-dns` 提供「核心应用防误杀保护 (`#toggle-dns-essential-protect`)」独立开关（默认开启），彻底解决开启 DNS 护盾后 Google Play 无法下载更新的问题，同时保持真实广告域名（如 `google-analytics.com`）100% 阻断。
   - **BUG-005 (P3 · 回家节点改端口自动同步名称后缀)**：在 `/api/homelink/update` 修改 `listen_port` 或 `external_port` 时自动同步更新节点名称括号内的 `(:port)` 后缀。


## [v2.0.2] - 2026-10-31 — 自动节点池「6 步往复筛选检测 ➔ 确认入池 ➔ 直接移除无弹窗」深度打磨 · 危险操作确认弹窗全量接线版

### 🌟 核心修复与交互重构 (v2.0.2 Highlights)

1. **自动节点池「6 步往复筛选、增量检测、确认入池与直接移除」全流程闭环 (`#modal-autopool`)**
   - **Step 1 — 筛选器自由勾选新候选节点（1~10 个）**：通过「订阅源 $\rightarrow$ 国家/地区胶囊 $\rightarrow$ 关键词」找到节点并任意勾选 1~10 个新候选节点；已加入节点池的节点仅显示绿色 **「✓ 已添加」** 标识（复选框禁用且不置 `checked`），与新勾选的待测节点完全区分。
   - **Step 2 — 增量检测（仅对新勾选节点进行检测，已入池节点不重复检测）**：点击 **「⚡ 仅测已勾选 Ping」** 或 **「🧪 检测已勾选 (Ping+服务)」** 时，严格只将当前新勾选的候选节点 (`stagedSet`) 发送至 `/api/auto_nodes/test_candidates` 进行检测，已添加进节点池 (`g1Set` / `g2Set`) 的节点绝不重复检测。
   - **Step 3 — 确认加入节点池（支持「仅加检测通过」或「免测/已勾选直接入池」）**：
     - 点击 **「✅ 将检测通过加入池 (`#btn-an-add-passed`)」**：仅将当前新勾选且检测通过 (`qualified === true`) 的节点加入当前分组节点池，自动丢弃未通过节点的勾选；
     - 点击 **「➕ 将已勾选加入池 (`#btn-an-add-to-pool`)」**：可将不想测试的已勾选节点（或已检测节点）直接确认加入当前分组节点池，加入后自动清空筛选器本轮勾选以便继续下一轮挑选。
   - **Step 4 — 已入池列表单点「🗑️ 移除」直接删除（彻底修复误弹「分流策略组编排 · Copilot 与 Edge 服务」弹窗的 Bug）**：
     - **根因定位**：原先下方列表的「🗑️ 移除」按钮带有 `data-group="1"` 属性，点击事件冒泡至 `document` 后命中了分流页面的 `event.target.closest('[data-group]')` 监听器（`mock.groups[1]` 即为 `Copilot 与 Edge 服务`），导致误弹出分流组编排弹窗覆盖了节点池弹窗；
     - **彻底修复**：将移除按钮属性改为 `data-pool-group`、在 `#an-builder-root` 内调用 `ev.stopPropagation()` 阻断冒泡，并在 `document` 级 `[data-group]` 监听器增加 `!event.target.closest('#modal')` 守卫。现在点击 **「🗑️ 移除」** 直接将该节点从列表移除（同时上方筛选器内该节点立即恢复可勾选状态），**绝不弹出任何弹窗**。
   - **Step 5 & 6 — 多轮往复增删检测直至满意保存**：只要当前分组未满 10 个，可随时继续通过筛选器勾选新节点 $\rightarrow$ 仅对新选中节点检测 $\rightarrow$ 确认加入节点池 $\rightarrow$ 在下方列表直接移除不满意的节点，往复循环直至配置满意后点击底部固定栏的 **「确定保存节点池」**。

2. **`VERIFY-v2.0.1-install.md` 实测反馈 P0/P2/P3 全量闭环**
   - **P0（12 项危险删除与批量覆盖操作接入 `confirmModal` + 状态快照「↩ 撤销」）**：`恢复默认规则库`、`删除自定义分流组`、`全部海外组走智能自动池` 等 12 项高危/批量操作点击必先弹确认窗（点取消 0 API 调用、零副作用），确认执行后支持「↩ 撤销」。
   - **P2（`aria-busy` 完整生命周期保持）**：回家节点路由切换下拉框跨重绘保持 `aria-busy="true"` 直至请求与状态刷新完成，常态为 `"false"` 永不为 `null`。
   - **P3（「☑️ 勾选筛选前10优」严格补足到 10）**：点击后严格按 `10 - targetSet.size` 补足新候选节点，勾选总数恒为 `10`。
