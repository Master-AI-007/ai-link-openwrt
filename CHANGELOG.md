# AI-LINK OpenWrt 变更日志 (CHANGELOG)

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

---

## \[v2.0.0\] - 2026-10-27（NEXUS 全域 3D 正式版 · 全量检查更新包）

### 🎨 四项实机定制化视觉与交互升级

1. **国内直连母星 (`cn`) 切换为淡粉色 (`#f9a8d4` / `0xf9a8d4`)，与内核中枢青色鲜明区分**

   * 解决实测反馈中「内核中枢母星 (`core`, `#28b8d4` / `#6ee7f5`) 与国内直连母星 (`cn`, 旧色 `#1fc699`) 在 WebGL 光晕与色调映射下颜色过于接近」的问题。

   * 将 `国内直连` 母星球体材质、自发光 (`0xf472b6`)、环绕轨道环 (`0xfbcfe8`)、下属国内目标卫星、主干连线 (`core_cn`)、2D 投影标签与右侧检查器指标全面升级为**淡粉色 (`#f9a8d4`)**，在深空背景下与青色内核、紫色海外代理、琥珀黑洞形成四色高对比度视觉体系。

2. **「⚡ 流量激增」按钮 (`#surge-toggle`) 升级为真实连接的 3D 表达**

   * 打开「⚡ 流量激增」按钮不再是简单的动画倍速，而是实时拉取 `/api/clash/connections` 与 `/api/overview/galaxy` 的真实并发连接数据，在 3D 星图中构建**跨星系端到端真实连接 3D 轨迹弧 (`CatmullRomCurve3`)**：从 `内核中枢 (core)` 周围的具体局域网/回家终端卫星出发 \$
     ightarrow\$ 经由 `内核中枢` 母星分流 \$
     ightarrow\$ 飞向 `国内直连 (淡粉)`、`海外代理 (紫/青)` 或 `黑洞拦截 (琥珀)` 母星 \$
     ightarrow\$ 精准落入对应的真实访问目标卫星（如 `WeChat`、`Bilibili`、`ChatGPT`、`YouTube` 等）。

   * 3D 视口顶部同步呈现全息 HUD 实时横幅：`⚡ 真实连接 3D 表达已激活 · 实时映射 N 条跨星系轨迹 (M 并发连接) · 挡位: 高[X] / 中[Y] / 低[Z]`。

3. **连线上的流动光球支持「高 / 中 / 低」三个速度挡位，按真实连接数与吞吐速率动态驱动**

   * 新增三挡流速引擎 `NexusScene.computeSpeedGear(rateBps, conns)`：

     * **高挡 (`high` · 高速)**：当链路真实速率 `>= 200 KB/s` 或并发连接 `>= 12` 时触发，光球流速 `0.56`、体积缩放 `1.36x`、全密度脉冲；

     * **中挡 (`med` · 中速)**：当链路真实速率在 `15 KB/s ~ 200 KB/s` 或并发连接 `3 ~ 11` 时触发，光球流速 `0.26`、体积缩放 `1.04x`；

     * **低挡 (`low` · 低速)**：当链路真实速率 `< 15 KB/s` 且并发连接 `< 3` 时触发，光球流速 `0.095`、体积缩放 `0.78x`。

   * 同时作用于四大星系主干连线 (`core_global`、`core_cn`、`core_blackhole`、`cn_global`)、各星系卫星径向连线 (`tetherPackets`) 以及流量激增模式下的 3D 真实连接轨迹弧，并在 3D 连线中段实时渲染 `流速:高/中/低 · N连` 胶囊标签。

4. **概览页 (`#page-overview`) 底部三个标签卡片可点击查看具体信息 + 修复终端头像重复显示 `10` 问题**

   * 将概览页底部三张核心洞察卡片（`01 / DEVICES · 局域网终端设备`、`02 / OUTBOUNDS · 入核出站节点`、`03 / DESTINATIONS · 热门访问目标`）及卡片内的终端头像圆圈、目标域名芯片全部升级为可点击交互组件（带 `查看明细 ↗` 徽章与悬浮高亮）。

   * 修复 `01 / DEVICES` 卡片终端头像在 `10.10.10.x` 网段下截取前两位导致全部显示 `10` 的问题，改为智能提取 IPv4 末段（如 `.224`、`.77`、`.10`）或主机名缩写。

   * 点击任意一张卡片即弹出 NEXUS 宽幅详情模态框，内置 4 宫格汇总指标、分类筛选芯片、实时搜索框、高中低流速挡位徽章以及一键操作（`🔍 查看连接`、`⚡ 真测速`、`🚀 设为出口`、`🔍 4阶透视`）。

# AI-LINK 更新日志

本文件记录 AI-LINK 智能分流网关的全部版本变更。
在线更新客户端读取的机器可读清单是 `version.json`，本文件是面向人的详细说明。

版本号规则：`主版本.次版本.修订号`

* 主版本：架构级变更（如内核切换、配置模型重构）

* 次版本：新增功能，向后兼容

* 修订号：缺陷修复与安全补丁，向后兼容

## v1.0.3 · 2026-10-26

> 主题：**双机实测根因深度修复（10.10.10.7 & 192.168.100.37）· 彻底终结 Sing-box 内核掉线与全网黑洞**

### 🌌 NEXUS v3 全域深空视觉深度重构与四项定制改造 + `VERIFY-frontend-deep.md` 100% 清零

* **四项核心 UI/UX 深度重构（100% 还原实机交互诉求）**

  1. **概览页「全球核心应用延迟声呐」面板纯雷达放大化**：移除旧版底部冗余芯片列表 (`#service-list`)，将圆形声呐雷达盘放大至 `288px × 288px` 居中展示；盘内全部 8 个核心业务信标（`ChatGPT`、`Gemini`、`YouTube`、`GitHub`、`Netflix`、`TikTok`、`Telegram`、`Bilibili`）均升级为可点击探测按钮 (`<button class="sonar-blip">`)，点击直接调用 `/api/clash/delay` 与 `/api/probe/service_l7` 实测对应策略组真实延迟，并采用 8 轨纵向交错坐标与右半球 `.blip-left` 向内锚定，实现零裁切、零重叠。

  2. **订阅与节点页新增「📦 全部订阅源汇总」卡片与点击过滤联动**：在 `#subscription-list` 最左侧固定渲染「📦 全部订阅源汇总」卡片 (`data-sub-select="ALL"`)，支持点击任意订阅卡片高亮选中并联动过滤下方节点测速列表 (`#probe-nodes-tbody`)、状态统计芯片與 7 大地区筛选芯片计数。

  3. **顶部状态栏 (`.topbar .global-route`) 模式感知与防误导展示**：顶栏清晰展示五大运行模式徽章（`精细规则分流` / `GFW 模式` / `非国内模式` / `全局模式` / `直连模式`）；在「精细规则分流 (`rule_shunt`)」与「全局直连 (`direct_all`)」模式下**不再显示具有误导性的单一出口节点名**（改为展示策略组智能矩阵或全直连描述），仅在单一出口模式（`gfw_list` / `cn_whitelist` / `global_proxy`）下展示当前统一出口节点或自动节点池及实时延迟。

  4. **3D 全域星图 (`#page-galaxy` & `nexus3d.js`) 四星系动态卫星与深空详情面板重构**：恢复并升级四大星系围绕运转的动态卫星实体（带脉冲连接线、悬浮速率标签与严格数量上限控制：`MAX_GALAXY_SATELLITES = 8`、`MAX_BLACKHOLE_SATELLITES = 6`，彻底告别密集杂乱）：

     * `🧠 内核中枢 (core)`：实时展示局域网与回家通道活跃终端设备（整合 `host_map` 在线设备与活跃连接，硬件旁路下亦不漏显）；

     * `🇨🇳 国内直连 (cn)`：实时展示大陆直连访问目标站点与速率；

     * `🌍 海外代理 (global)`：实时展示海外代理访问目标服务、所属策略组与实时速率；

     * `🕳️ 黑洞拦截 (blackhole)`：实时展示 Top 拦截广告/追踪域名卫星，并内置吸积盘粒子向事件视界中心螺旋坍缩吞噬动效；

     * 右侧检查器 (`#inspector-galaxy-detail`) 按 NEXUS 视觉体系重构四星系专属面板（4 宫格 KPI 卡片 + 内核连接池/内存水位条或威胁分类占比条 + 实时速率排行列表）。

* **`VERIFY-frontend-deep.md` 深度审计报告全量缺陷 100% 清零**

  * **遥测真值字段 100% 对齐**：全面修正 `overview_telemetry.active_connections`、`in_rate_bps`/`in_rate_str`、`out_rate_bps`/`out_rate_str`、`core_mem_mib`、`month_total_str`、`insight_data.devices`/`targets`、`dns_telemetry.stats_24h.blocked_queries`、`total_loaded_rules`、`dns_layer_blocks`、`route_reject_blocks`、动态健康度 `healthScore` 与 8 项 `pulse_services`，彻底清除 `rx_rate_bps`、`core_rss_mib`、`month_rx_bytes`、`blocked_queries_24h` 等死字段引用。

  * **13+ 项后端核心能力 100% 接入新 UI**：完整接入手动新增单节点与批量导入预览 (`/api/nodes/add` & `/api/nodes/parse_preview`)、节点明文凭据查看弹窗 (`/api/nodes/credentials`)、单节点真实测速 (`/api/nodes/test_real_delay`)、服务 L7 真连接探测 (`/api/probe/service_l7`)、系统诊断报告弹窗 (`/api/ops/diag`)、全量健康自检 (`/api/ops/health_check`)、断网逃生自测 (`/api/ops/fail_open_test`)、规则集立即同步 (`/api/rules/sync`)、IPv6 双栈模式切换 (`/api/ipv6/status` & `/api/ops/ipv6`)、DNS 7 项高级设置保存 (`/api/dns/settings`)、OTA 升级实时进度轮询与中断恢复 (`/api/system/update/status` & `/api/system/update/ack`) 以及安全卸载向导 (`/api/ops/uninstall`)。

  * **统一 API 错误提示与失败回滚**：`callRouterApi` 对 `ok === false` 或网络异常统一弹出错误 Toast 并返回标准化失败对象；路由模式切换与开关切换在后端返回失败时自动回滚 UI 状态；移除假成功兜底 `default: toast('操作指令已执行')`，改为显式未知指令告警。

  * **移动端自适应与可访问性收口**：`<980px` 下自动隐藏顶栏冗余搜索框并支持点击背景遮罩关闭抽屉；补齐全部表单控件 `aria-label` 与模态框 `ESC` 关闭支持。

### 🛡️ 核心引擎防掉线与自愈闭环（P0-1 \~ P0-3）

* **解除 procd 1 小时 6 次重启放弃配额（P0-1）**
  `/etc/init.d/ai-link` 中 `ai-link-daemon` 与 `ai-link-core` 的重启策略由 `respawn 3600 5 5` 调整为 `respawn 0 5 0`（无限重试、5 秒退避），彻底根除因日常分流调整触发主动重启与异常退出共用配额导致的 `Instance ai-link::ai-link-core s in a crash loop 6 crashes` 永久放弃拉起问题；同时新增 `/etc/init.d/ai-link restart_core` 独立恢复命令，在不中断 9099 面板守护进程的前提下重置并拉起内核。

* **看门狗新增 Sing-box 进程存活守护（P0-2）**
  `_telemetry_and_watchdog_loop` 新增 `ensure_core_alive_and_recover()`（每 15 秒巡检 `_get_live_singbox_pids()`，自动过滤僵尸进程 `State: Z` 与 `version`/`check`/`rule-set` 短期辅助进程）。检测到内核进程意外缺失且未处于重构重载窗口时，立即记录日志 `Watchdog: core process missing; restarting service.` 并自动调用 `_respawn_core_only()` / `restart_core` 恢复内核。

* **内核离线立即撤除 nftables 与策略路由防黑洞（P0-3）**
  `ensure_nft_and_routing_intact()` 新增 `_teardown_blackhole_nft_and_routing()`：一旦检测到 `sing-box` 进程不在或 `:7893` 端口未监听，立即主动删除 `table inet ai_link`、清理 `ip rule fwmark 0x162 table 162` 并回退 `dnsmasq` 上游，使局域网与旁路由自身平滑退回直连上网（彻底消除 `curl 000` 全网黑洞）；待内核恢复监听后自动重挂透明代理。同时 `_sync_ipv6_policy_routing()` 增加前置内核与端口存活断言。

### ⚡ 幂等配置重载、指纹非易失持久化与启动防抢杀（P1-1 \~ P1-3）

* **全端点规则指纹比对，幂等操作零重启（P1-1）**
  增强 `_compute_core_rules_fingerprint()`（覆盖 `route`、`dns`、`inbounds`、选择器成员拓扑与代理出站定义，排除可通过 Clash API 热切换的 `default` 字段）。在 `schedule_async_core_reload()`、`reload_core_only()` 以及 `/api/shunt/reorder`、`/api/shunt/custom_rule`、`/api/dns/rewrite`、`/api/dns/filter/toggle` 等端点前置比较操作前后指纹：若拓扑规则未变化（如原样提交分流顺序），自动降级为 `hot_selector` 热更新，绝不杀内核进程（`requires_core_respawn=False`）。

* **规则指纹持久化至非 tmpfs `/etc/ai-link/.applied_core_rule_hash`（P1-2）**
  `_record_applied_core_rule_hash()` 与 `_get_applied_core_rule_hash()` 双写 `/etc/ai-link/.applied_core_rule_hash` 与 `/var/run/ai-link/applied_core_rule_hash.txt`；设备重启或 tmpfs 清空后自动从持久化文件恢复指纹，避免开机首次巡检误判「规则脏」而多杀一次内核。

* **消除启动期 `context canceled` 抢杀与 `.srs` 原子编译（Path ④）**
  `reload_core_only()` 新增 `_get_min_singbox_proc_age()` 启动保护窗口（进程刚拉起 `<6.5s` 时先等待 Clash API 就绪而不发送 `SIGTERM`）；`blocklist_custom.srs` 改为编译至临时文件后 `os.replace()` 原子替换；`--daemon` 启动时若 `sing-box.json` 已在 25 秒内由 `init.d` 生成则跳过重复写盘。

* **`install.sh` 与 OTA 升级脚本增加真实健康断言（P1-3）**
  安装与升级收尾阶段强制校验 `pidof sing-box` 及 `:7890` / `:7893` 端口监听状态（未就绪时自动触发一次 `restart_core` 自愈），输出 `UPGRADE OK: core=... ports ok` 或 `UPGRADE FAIL: ...`。

### 🌐 10.10.10.7 实测问题专项修复与面板可见性（DIAG-1 \~ DIAG-3 / P2 / P3）

* **静默捕获客户端提前断开 `BrokenPipeError`（DIAG-1）**
  `AILinkRequestHandler` 的 `handle_one_request`、`finish`、`_send_json`、`_try_send_wire_memo`、`do_OPTIONS` 统一捕获 `(BrokenPipeError, ConnectionResetError, socket.timeout)`，消除浏览器刷新或中断请求时的堆栈刷屏。

* **停机/重启/内核离线期间保留旁路由自身 DNS 解析（DIAG-2）**
  `init.d/ai-link` 与 `ai-link-daemon.py` 新增 `fallback_resolv_conf_direct()` / `restore_resolv_conf_local()`：在服务停止、重启等待或内核离线窗口自动将 `/etc/resolv.conf` 与 `/tmp/resolv.conf.d/resolv.conf.auto` 回退至主路由网关 + 公共 DNS（`223.5.5.5` / `119.29.29.29`），彻底解决停机期间旁路由自身 `ttyd CPD No internet` 无法解析域名的问题；待 `:7893` / `:7874` 就绪后再切回 `127.0.0.1`。

* **修复新装设备 `wait_for_ports_And_apply_nft` 挂载延迟（DIAG-3）**
  `init.d/ai-link` 后台端口等待子进程增加 `trap '' HUP` 与 `</dev/null >/dev/null 2>&1 &` 标准流解耦（防止 SSH 会话退出时 `SIGHUP` 中断后台挂载），并在等待第 8s / 20s 检测到内核未起时自动触发重拉；`install.sh` 依赖检查补齐 `sing-box` 软件包检测。

* **面板与 LuCI 暴露真实内核离线红色告警横幅（P2）**
  修复 `build_routing_health()` 在内核离线时仍因历史测速缓存返回 `✅ 代理中` 的盲区；WebUI 新增顶部悬浮 `#core-offline-alert-banner` 与概览页 `#ov-core-offline-card` 醒目红色告警条及「🔄 一键重启内核」按钮，并将 `tuple(_get_live_singbox_pids())` 纳入 `/api/status` 缓存键实现毫秒级状态感知。

* **统一版本字段 `status.build_ver` 为 `1.0.3`（P3）**
  `/api/status` 的 `build_ver` 由历史残留值 `2.0.0-r8-v24-nolo` 统一为 `APP_VERSION` (`"1.0.3"`)，全仓 7 处版本标识 100% 对齐为 `1.0.3`。

## v1.0.2 · 2026-10-26

> 主题：**全量安全加固 + 启动与看门狗可靠性 + `.tgz` 归档上传恢复 + 跨架构兼容与自动化回归**

### 🔐 安全加固（SEC-1\~SEC-5 & B1-1\~B1-4）

* **面板令牌不再随首页下发（SEC-1）**
  移除 `end_headers` 中对 `/` 请求下发 `Set-Cookie: ailink_token=<有效令牌>` 的缺陷；令牌仅在 `POST /api/login` 校验密码通过后签发，由前端保存在 `localStorage` 与 `Cookie`。

* **`/api/status`、`/api/nodes/share_uri`、`/api/ops/logs` 鉴权与凭据脱敏闭环（SEC-2\~SEC-5）**

  * `/api/status` 按访问控制同一口径判定：未鉴权客户端脱敏回家节点的 `password` / `uuid` / `private_key` / `uri`（含 `uri` 内嵌明文凭据）及订阅 `?token=` 参数，并将鉴权状态与 `panel_auth.json` 纳入 wire-memo 缓存键；

  * `GET /api/nodes/share_uri` 与 `GET /api/ops/logs` 强制校验 `_auth_ok()`，未授权请求一律返回 HTTP 401。

* **UCI 凭据零留存，彻底改为布尔 `panel_pwd_customized=0/1`（B1-2）**
  `/etc/config/ai-link` 移除 `panel_secret` 字段，改用布尔 `option panel_pwd_customized '0'`；`install.sh` 升级时自动迁移并清除历史 `panel_secret`；CLI `ai-link password` 不再向 UCI 写入任何明文或哈希串。

* **永久下线弱默认密码 `admin`（B1-3）**
  出厂状态仅接受 `ai-link-2026` 作为初始密码，彻底禁用弱口令 `admin`；面板登录弹窗移除预填明文 value。

* **内网免密风险提示与自动登录引导（B1-1）**
  `/api/status` 新增 `auth_required` 与 `pwd_customized` 状态位，未鉴权打开面板自动弹出登录窗；WebUI 设置页新增 `#lan-auth-security-notice` 动态安全风险警示条；LuCI 新增 `require_lan_auth` 开关并与 `ops_settings.json` 双向同步。

### 🚀 启动可靠性与防黑洞看门狗（BOOT-1 / CORE-1 / RB-1 / B1-4 / B3-12）

* **多栈端口就绪探针（BOOT-1 & B3-12）**
  `init.d/ai-link` 的 `port_is_listening()` 采用 `netstat` → `ss` → `/proc/net/tcp{,6}` 三级探针，同时比对大小写十六进制端口（消除精简版 BusyBox `awk toupper()` 依赖），等待预算放宽至 60 秒（`AI_LINK_PORT_WAIT` 可覆盖）。

* **修复 BusyBox `pgrep` 探针与全仓进程匹配（CORE-1 & B3-12）**
  `init.d/ai-link` 统一使用 `singbox_alive()`（`pidof sing-box` + `pgrep -f` 兜底）并动态解析 `command -v sing-box`；全仓 `install.sh` / `uninstall.sh` / `usr/bin/ai-link` 统一使用 `pgrep -f "ai-link-dae[m]on.py"` 防止 shell 自匹配误杀。

* **看门狗与 `restore_proxy` 挂载 nftables 前强制校验端口（B1-4）**
  `ensure_nft_and_routing_intact()`、`restore_proxy()` 及 `update_ops_settings()` 在挂载 `table inet ai_link` 前强制校验 TProxy `:7893` 端口监听状态，核心未就绪时跳过挂载以杜绝局域网断网黑洞。

* **在线升级回滚立即恢复透明代理（RB-1）**
  OTA 回滚段在重启服务后主动调用 `/etc/init.d/ai-link restore_proxy`，消除约 10 秒的透明代理空窗。

### 📦 备份恢复与在线更新增强（B2-6 \~ B2-11）

* **面板与 LuCI 支持 `.tgz` / `.json` 浏览器直接上传恢复与 `.tgz` 归档下载（B2-6）**
  新增 `GET /api/ops/backup_archive`（一键导出 `.tgz` 全量归档）并升级 `POST /api/ops/restore_archive` 支持浏览器直接上传 `.tgz` / `.tar.gz` 或 `.json` 备份恢复，内置 `tarfile` 路径穿越（`..`）、非普通文件与 100MB 解压上限安全校验，且仅在校验与恢复成功后更新持久化备份。

* **新增 `ai-link restore <file|--latest>` CLI 命令行恢复入口（B2-7）**
  支持通过命令行直接传入 `.tgz` 归档或 `.json` 备份文件完成全量恢复与服务重载（`ai-link-daemon.py --restore <file>`）。

* **OTA 升级进度闪存持久化（B2-8）**
  升级脚本将实时进度双写至 `/root/ai-link-final-backup/last_update_progress.log`，设备断电重启导致 `/var/run` tmpfs 丢失后仍可自动还原升级中断状态。

* **`auto_nodes.json` 剥离实时探测噪声（B2-9）**
  落盘时通过 `_strip_auto_node_runtime_fields()` 剔除 `quality_ranking`、`last_check_ts`、`members` 等高频探测字段（读取时动态注入内存），跨探测周期文件 MD5 保持 100% 恒定。

* **自定义更新源域名与冷启动提示（B2-10 & B2-11）**
  `ops_settings` 白名单新增 `update_manifest_url` 支持绑定自有域名作为第一优先级 OTA 清单源，并与 UCI 删除/修改双向同步；界面与文档保留 v1.0.0 首次手动升级说明。

### 🛠 工程与验证工具链（TOOL-1\~3 / HYG-1 / TEST-1 / B3-13\~14 / B4-16\~20）

* **Clash API 负缓存断路器（B4-20）**：`clash_api_request()` 新增 `_CLASH_API_DOWN_UNTIL` 断路器与 Linux `/proc/net/tcp` 零套接字权威判定，无 Clash API 环境下 `--self-test --strict` 耗时 < 1.5s。

* **发布与核对工具链增强（TOOL-1\~3 & B4-16\~17）**：修复 `release.py` 7 处版本同步正则与门禁校验，支持自动检测工作区仓库与同版本预置发布；`verify_online.py` 支持进程环境变量覆盖。

* **全链路 E2E 与无头浏览器 UI 自动化回归（B3-13 & B3-14）**：新增 `test_v102_full_regression.py`（42 项断言），覆盖真实 HTTP 服务端密码登录/改密/鉴权、`.tgz` 上传恢复及 Headless Chromium 浏览器 UI 渲染与交互验证。

## v1.0.1 · 2026-10-26

> 主题：**服务总开关 + 在线更新体系 + 面板密码安全修复**

### ⚙️ 服务总开关（新功能）

* **LuCI 概览页顶部新增「服务总开关」卡片**，实时显示并控制服务生命周期：

  * 状态徽章：`● 运行中` / `◐ 部分运行（内核未起）` / `⏹ 已停止`

  * 元信息：开机自启、透明代理接管、nftables 挂载、面板端口

  * 四个动作按钮：**启动服务 / 停止服务 / 重启服务 / 开机自启开关**

* **关键设计：这条通路不依赖 `:9099` 面板。**
  它走 LuCI 自己的 `fs.exec` → `/etc/init.d/ai-link svc_state|start|stop|restart`，
  所以**即使守护进程已经停了，也能在 LuCI 里一键把它拉起来**，不需要 SSH。

* **修复死锁**：此前若服务被 `stop` 掉，LuCI 概览页所有按钮全部失效（它们都调 `:9099` 的 API），
  而「启用 AI-LINK 透明代理服务」这个勾选框只管流量接管、不管进程启停，导致用户无处可恢复。

* **`enabled` 语义澄清**：该开关只控制「是否接管流量」；进程启停由新的总开关负责。
  卡片下方有明确文案区分两者，避免再混淆。

* **`reload_service()` 兜底**：`enabled=1` 时若 daemon 或 sing-box 任一未运行，直接整体 `start`，
  不再依赖「reload 只重载运行中实例」的旧行为。

* **独立面板同步**：设置页新增服务状态卡片（运行中 / 开机自启 / nftables / 端口）+「🔄 重启服务」按钮，
  5 秒自动刷新。

* **新增 init 动作 `svc_state`**：输出单行 `daemon= core= nft= enabled= boot= bypass= port=`，
  供 LuCI 与面板统一解析。

### 🔐 安全修复

* **修复：LuCI 概览页「面板密码」显示为一串 `sha256:xxxx` 哈希**

  * 根因一：改密后 `ai-link.global.panel_secret` 被写入 `sha256:<hash前24位>`，而 LuCI 直接把它当密码显示。

  * 根因二（更严重）：`--self-test` 用临时目录调用改密函数，但函数体无条件 `uci set`，导致**每次安装自检 / `ai-link probe` 都会把生产环境的 `panel_secret` 覆盖成测试串 `custom-secret-2026` 的哈希**。

* **修复：哈希串可直接当密码登录**
  `_verify_panel_password` 中的 `candidate_pw == get_uci_panel_secret()` 已移除；UCI 里只有「明文初始密码」才允许直通比对。

* **修复：哈希串可直接当 Bearer 令牌绕过登录**
  `_is_request_authenticated` 中的 `tok == get_uci_panel_secret()` 已移除，令牌只认 `panel_auth.json` / `panel_token` 里签发过的值。

* **修复：`panel_auth.json` 丢失后用户被锁死**
  旧逻辑会用 UCI 里的哈希当初始密码重建，导致真实密码彻底失效。现在回退到默认密码 `ai-link-2026`，用户可进面板重设。

* **新增：LuCI 专用桥接令牌 `luci_bridge_token`**
  与面板密码完全解耦的 32 位随机串，仅用于 LuCI 页面调用面板 API；改面板密码不会影响它，它也不能用来登录面板。

* **加固：`ai-link password` 成功后不再回显明文密码**，只提示字符数。

### ⬆️ 在线更新体系（新功能）

* **LuCI 概览页新增「插件版本与在线更新」卡片**：显示当前版本、检查更新、立即更新、进度条与实时日志、更新说明入口。

* **独立控制面板新增同款卡片**，位于「核心规则库与订阅更新」上方。

* **新增 CLI 命令**：

  * `ai-link update` —— 只检查是否有新版本

  * `ai-link update --apply` —— 检查并直接在线升级（带实时进度输出）

* **新增 API 端点**：

  | 方法 | 路径 | 说明 | 
  | ----- | ----- | ----- | 
  | GET | `/api/system/version` | 当前版本、构建号、清单源列表 | 
  | GET | `/api/system/update/check` | 拉取版本清单并比较（`?force=1` 跳过 5 分钟缓存） | 
  | GET | `/api/system/update/status` | 升级进度与最近日志 | 
  | POST | `/api/system/update/apply` | 启动升级 | 
  | POST | `/api/system/update/ack` | 清除已完成的升级结果 | 

* **升级流程（八步，全程可观测）**：

  1. 拉取 `version.json`（Cloudflare Pages 主源 → gh_mirror 镜像 → GitHub raw 直连，自动重试）

  2. 下载升级包（清单内多个下载源依次重试）

  3. **校验包大小 + MD5 + SHA256**，任一不符立即中止，绝不执行未校验的包

  4. 解压并校验包结构（必须含 `install.sh` 与 `root/`）

  5. 备份用户配置到 `/root/ai-link-final-backup/pre-update-v{版本}-{时间戳}.tgz`（自动保留最近 3 份）；空间充足时额外备份旧代码用于回滚

  6. 执行 `install.sh --upgrade`（保留用户配置与已装附加组件）

  7. 重启服务并做健康检查（最多 10 次轮询 `/api/status`）

  8. 健康检查失败 → **自动回滚**用户配置与旧代码，并再次验证

* **升级进程与 daemon 解耦**：升级脚本用 `setsid` 脱离 daemon 会话，`install.sh` 重启服务不会把它杀掉；进度落盘到 `/var/run/ai-link/update/progress.log`，重启后新 daemon 接着读，用户能看到完整结果。

* **安全护栏**：清单缺少 MD5 时直接拒绝升级；同一时间只允许一个升级任务；升级中重复点击会被拒绝。

### 🛠 安装脚本

* 新增 `install.sh --upgrade` 升级模式：

  * 不再停止/禁用其他代理服务（避免误伤用户后装的组件）

  * **不再删除音乐解锁组件**（原安装流程会 `rm -rf` 掉，升级时会造成"静默卸载"）

  * 其余流程保持幂等，用户配置与 UCI 设置全部保留

### 📦 版本号统一

* 全量版本号由 `1.0.0` 升至 `1.0.1`，统一来源为 daemon 内的 `APP_VERSION` 常量；启动时同步写入 `ai-link.global.app_version` 供 LuCI / CLI / 面板读取。

* `/etc/ai-link/version` 更新为 `1.0.1 (20261026)`。

### ✅ 验证

* 面板密码缺陷 A/B 对照：补丁前「哈希当密码 ✓ / 哈希当令牌 ✓ / auth 丢失后哈希可登 ✓」→ 补丁后三项全部拒绝，真实密码与真实令牌未回归。

* 静态门禁：`py_compile` ✓、`node --check` ✓、`bash -n`（install.sh / usr/bin/ai-link / 生成的升级脚本）✓、symtable 未定义符号 0 ✓、HTML div 配平 0 ✓。

* OTA 版本比较 7 条用例全通过（含 `v` 前缀、预发布版语义）。

## v1.0.0 · 2026-10-25

> 首个正式版

* 纯血 Sing-box 单内核架构（移除 mihomo 遗留路径）

* 五种分流模式：`shunt` / `gfw_list` / `global` / `direct` / `homelink`

* 智能双栈 DNS（:7874 上游 + 海外 AAAA 剥离 + 国内原生 IPv6）

* 国内 IP 硬件级入口直连（Entry Bypass）+ 旁路由对称 NAT 断流保护

* 回家节点（VLESS-Reality / Hysteria2）

* 净网黑洞拦截、DNS 重写与过滤库

* 独立全功能控制面板（:9099）+ LuCI 概览页

* 一键恢复出厂、备份归档与恢复、彻底卸载

* 跨平台安装：x86_64 / aarch64 / armv7 / mipsel / riscv64，opkg + apk 双栈
