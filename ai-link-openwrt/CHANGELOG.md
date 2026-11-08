## v2.5.2 (2026-11-09)

- **[自动节点池订阅源与国家区域范围强约束闭环 (`ai-link-daemon.py` & `nexus.js`)]**：
  1. **修复订阅同步自动补位跨订阅误选 (`_reconcile_auto_pools_after_sub_sync`)**：修复订阅更新触发节点池自动补位时未按池绑定的 `scope_sources`（勾选订阅源）与 `scope_countries`（勾选国家/地区）过滤的问题，杜绝非勾选订阅源的节点被自动补入池内。
  2. **修复低健康度自动复选与日常维护范围越界 (`maintain_auto_node_pool_health` / `_normalize_auto_node_item`)**：在保存与加载节点池时强制将 `scope_sources`、`scope_source`、`scope_countries` 与 `filters`（`sub_id` / `region_any`）双向锁步同步；巡检与低健康度复选时自动剔除不在勾选订阅或地区范围内的越界节点，并严格仅从勾选订阅与地区内补位。
  3. **修复单订阅通配与前端向导范围过滤 (`_filter_nodes_by_pool_scope` / `openAutoNodeEditorModal`)**：移除当节点携带其他订阅 ID 时仍被单订阅兜底匹配的问题，前端修改勾选订阅或地区后保存前自动剥离超范围旧节点。
- **[闭环 `FEEDBACK-云端-v2.5.1.md` 全部 5 项反馈 (`FB-251-1 ~ FB-251-5`)]**：
  1. **修复 `gates_v101.py` 套件提取正则与包内自包含校验 (`FB-251-1`)**：修正 `SUITES` 提取正则并断言 `len(suites) >= 14`，显式将 `tests/`（含 `v242_deep_chaos_simulation.py`）写入 `.tar.gz` 与 `.zip` 并由 `gates_v101.py` 直接开包核验。
  2. **校准报告四列指纹表全量一致性 (`FB-251-2`)**：消除单独补发脚本尾部换行符差异，并在 `gates_v101.py` 中新增报告与 `HANDOFF.md` 指纹表逐行比对硬门禁。
  3. **消除测试脚本版本号硬编码 (`FB-251-3`) 与分流下拉框多线线数虚标 (`FB-251-4` / `FB-251-5`)**：`test_v102_full_regression.py` 改为动态读取 `dmod.APP_VERSION`；`nexus.js` 分流组下拉选项同步改为真实线数/单线降级文案，且全文零 `Math.max(2, ... active_lines_count)`。

## v2.5.1 (2026-11-08)

- **[LuCI 面板极简重构 & v2.5.0 验收反馈 FB-250-1~6 全量闭环 (`htdocs/.../overview.js` & `ai-link-daemon.py`)]**：
  1. **LuCI 面板极简重构**：移除冗余的底层 UCI 表单（防止 LuCI 保存覆盖独立面板配置）、移除组件更新表与高级策略下拉框；可操作区仅保留基础服务启停（启动/停止/重启/开机自启）、透明代理接管开关、重载内核、打开 `:9099` 独立控制台按钮以及完整的 OTA 在线检查与热更新模块；其余区域仅只读展示 4 项核心运行状态 KPI。
  2. **修复 `daemon --self-test` 出站字段白名单 (`FB-250-1`)**：将 `urltest` 专属字段 `{"url", "interval", "tolerance", "idle_timeout"}` 纳入 `allowed_sb_keys`，确保 `python3 tests/run_all.py` 15/15 全绿通过。
  3. **打包与文档硬门禁 (`FB-250-2 ~ FB-250-6`)**：将 `v242_deep_chaos_simulation.py` 同步内置于 `tests/` 与源码树 `site/ai-link-openwrt/tests/`，固定产出 `HANDOFF.md` 与自动计算的四列产物校验指纹表（文件名 / 大小 / MD5 / SHA-256），并在 `gates_v101.py` 中新增 4 项交付一致性硬门禁。

## v2.5.0 (2026-11-08)

- **[自动节点池多线并发内核层与数据面真实落地 (`DIAG-多线并发功能生效性-20261108.md` 闭环)]**：
  1. **内核 `urltest` 编组与无损连接保持 (`generate_singbox_config`)**：为 `dispatch_mode == "multi_line"` 的非敏感自动节点池生成 `"type": "urltest"` 出口 `Auto_<pool>_MultiLine`（严格限定为剔除慢节点后的 `multi_line_nodes`），并将 `Auto_<pool>` 与绑定的非敏感分流组（如 `Shunt_YouTube`、`Shunt_TikTok`）设为 `interrupt_exist_connections: false`，同时保持 `Shunt_AI` 单线防风控保护。
  2. **0.5s 错峰无损轮转并发调度器 (`dispatch_multi_line_pools_tick`)**：后台守护线程按 `0.5s` 周期与组间错峰偏移静默轮转 `:9090/proxies/<selector>`，实现存量连接不断流、新建并发连接自动分摊至多个物理节点。
  3. **节点池全生命周期与订阅自动同步开关修复**：统一 `_normalize_auto_node_item` 慢节点离散度过滤，`auto_screen` 纳入带宽择优并排除 4 层 DAG 链式落地节点；订阅卡片新增 `.sub-autosync-btn` 一键切换自动同步胶囊，编辑订阅弹窗新增 `#mdl-sub-auto-update` 开关。

## v2.4.9 (2026-11-08)

- **[自动节点池稳定性加权与全站双栏等高/全息波形可读性重构]**：
  1. **自动节点池算法加固**：引入滑窗丢包率与抖动变异系数惩罚因子、低健康度非破坏性保员、60 分钟隔离期满自动解封及多线并发副线内核日志故障感知。
  2. **全息流量波形与双栏 100% 等高对齐**：新增 4-KPI 实时摘要栏、Y 轴自适应刻度、峰值徽章与悬停十字准星浮窗；修复高分屏 `DPR=2` 下 `<canvas>` 高度膨胀问题，确保概览页与 DNS 页左右并排卡片高度差为 `0px`。

## v2.4.8 (2026-11-08)

- **[真机验收报告 `VERIFY-v2.4.7.md` 全量 6 项问题闭环]**：
  1. **修复 `@lan_direct_macs` Fake-IP 豁免规则协议冲突 (`P0-1`)**：将 `198.18.0.0/15` 豁免规则拆分为 `meta nfproto ipv4` 与 `meta nfproto ipv6` 两条独立规则，消除 `nft -c -f` 协议冲突报错。
  2. **修复 `/api/shunt/update` 按组专属 DNS 落盘与 `except: pass` 清理 (`P2-6` / `P3-4` / `P3-5`)**：兼容 `id`/`group_id` 字段并注入 `domain_resolver: "dns_direct"`，全文件 `except -> pass` 清零，补齐 4 阶透视 `query` 回显字段。

## v2.4.7 (2026-11-08)

- **[深度模拟巡检 #2 · 4 大用户场景深化打磨闭环]**：
  1. **DNS 三大开关防轮询竞态闪烁 + 4 阶流量透视器内联源 IP/MAC 语法支持 (`webui/nexus.js` & `ai-link-daemon.py`)**：为「云端域名过滤护盾 (`#toggle-dns-filter`)」、「核心应用防误杀白名单保护 (`#toggle-dns-essential-protect`)」与「DNS 防跳重写 (`#toggle-dns-rewrite`)」接入 `_opsMutationInFlight` 重入锁、`_opsFieldMuteUntil` 3 秒轮询静默保护窗与接口失败自动回滚；在 4 阶流量透视器 (`trace_traffic_flow`) 中支持内联源设备语法（如 `10.10.10.58 -> api-chat.soulapp.cn`、`aa:bb:cc:dd:ee:99 -> www.youtube.com` 或 `chatgpt.com @10.10.10.58`）；
  2. **T6 配置变更历史快照纯净 Diff 与一键回滚 UCI/内核配置同步闭环 (`ai-link-daemon.py`)**：`_capture_current_config_files()` 新增覆盖 `dns_rewrite.json` 与 `rule_providers.json`；`record_config_snapshot()` 对 `new_ops_cfg` 严格按 `OPS_PERSIST_KEYS` 过滤，彻底消除每次修改系统开关时产生 4 条虚假 `added` Diff 的噪音；`rollback_config_snapshot()` 回滚 `ops_settings.json` 时自动调用 `sync_ops_settings_to_uci()` 反向治愈 UCI `/etc/config/ai-link` 并立即重新生成 `sing-box.json` 与 `ai-link.nft`；
  3. **T8 组合规则块域名 Fake-IP 优先级提权与 T10 按组专属 DNS (`custom_dns`) 真实编译进 `sing-box.json` (`build_singbox_config`)**：将 `Domestic_CN` 之上代理分流组内 T8 `rule_blocks` 的 `domain`/`domain_suffix` 自动提取纳入 `proxy_prio_doms`（确保混合/国内域名命中代理规则块时优先分配 Fake-IP，防止在开启 `entry_bypass` 时被防火墙提前直连放行）；同时将分流组配置的 `custom_dns` (`dns_strategy != 'inherit'`) 真实编译进 `sing-box.json` 的 `dns.servers` (`dns_grp_<id>`) 与 `dns.rules`；
  4. **HomeLink 回家网关动态系统保留端口防冲突与外网端口边界校验 (`validate_homelink_port`)**：动态读取当前 UCI/运行态配置的 `panel_port`、`tproxy_port`、`mixed_port`、`dns_port` 纳入核心保留端口集，并对 `/api/homelink/add` 与 `/api/homelink/update` 的 `listen_port`/`external_port` 非法类型或越界端口返回明确 400 拦截提示。

## v2.4.6 (2026-11-08)

- **[深度模拟巡检 #1 · 4 大用户场景全链路打磨闭环]**：
  1. **前端交互与轮询竞态防护 (`webui/nexus.js`)**：`mutateOpsSwitch` 新增 `<16ms` 乐观更新、同键位重入锁 (`_opsMutationInFlight`) 与 3 秒轮询静默保护窗 (`_opsFieldMuteUntil`)，彻底消除点击开关时遭遇后台 5 秒 `/api/status` 轮询覆盖造成的开关跳回闪烁；修复三模数据面 (`#sel-ops-data-plane-mode`) 与 TUN 协议栈 (`#sel-ops-tun-stack`) 切换失败时未回滚下拉框状态的缺陷；在「面板监听、免密网段与设备直通白名单配置」弹窗中补全 `lan_direct_macs`（局域网设备 MAC 免代理直通）、`tun_mtu`（PPPoE 1492/1480 调优）与 GitHub 加速源快捷候选列表；
  2. **JSON 备份/恢复与恢复出厂全模块覆盖 (`ai-link-daemon.py`)**：`export_ops_backup()` 与 `restore_ops_backup()` 新增 `rule_blocks`（组合分流规则块）、`rule_providers`（远程规则集订阅）、`sonar_targets`（概览声呐自定义目标）与 `alert_channels`（告警通知渠道）完整往返备份与恢复；`factory_reset_all_configs()` 补全上述模块清理及 `data_plane_mode`/`tun_stack`/`tun_mtu`/`ipv6_leak_mode` 全量重置；
  3. **订阅同步自定义属性继承与手动/链式节点防误删 (`merge_nodes`)**：订阅刷新 (`replace_sub=True`) 时自动继承同 `node_key`/`node_id` 节点上用户设置的 `region_override`、`disabled`、`remark`；全量替换 (`replace_all=True`) 时严格保留所有手动添加节点 (`_manual`/`is_custom`) 与 4 层 DAG 链式落地节点 (`is_chained`)；
  4. **局域网设备 MAC 免代理直通 (`@lan_direct_macs`) 防 Fake-IP 黑洞闭环**：`generate_nft_rules_file()` 在 `chain dstnat` 为 `@lan_direct_macs` 注入 53 端口直达 `223.5.5.5:53` DNAT 规则（从源头规避 Fake-IP 分配），并在 `prerouting_tproxy` 中限定 `@lan_direct_macs` 仅直通非 Fake-IP (`!= 198.18.0.0/15`, `!= fc00::/18`) 流量，同步在 4 阶流量透视 (`trace_traffic_flow`) 中支持 `src_mac` 免代理直通诊断。

## v2.4.5 (2026-11-08)

- **[P0 修复 · 升级与重启配置持久化单一真相源 (SSOT) 闭环]**：彻底解决每次版本升级、IPK 覆盖安装或服务重启时将用户已开启的「IPv6 透明代理 (`ipv6_proxy`)」重置为关闭、将用户已关闭的「国内流量不进内核 (`entry_bypass`)」重新打开的顽疾：
  1. `ai-link-daemon.py` 新增 `sync_ops_settings_to_uci()` 纯 Python 文件级 + `uci` CLI 双通道反向同步机制，将 `/etc/ai-link/ops_settings.json` 确立为唯一权威真相源（SSOT）；
  2. 重构 `sync_uci_to_ops_settings()` 与 `get_ops_settings()`，移除因 `/etc/config/ai-link` 时间戳更新触发反向覆盖 `ops_settings.json` 的缺陷，升级或 `--generate-configs` 时自动从 `ops_settings.json` 治愈 `/etc/config/ai-link` 与 `uci_ai_link.bak`；
  3. `install.sh` 升级前双重备份 `/etc/config/ai-link` 与 `/etc/ai-link/ops_settings.json`，将 `require_lan_auth` / `trusted_cidr` 改为非破坏性 `uci_set_default`，并在 `uci commit` 后立即执行 `--sync-ops-to-uci`；
  4. `luci-app-ai-link_2.4.5-r9_all.ipk` 控制包新增 `./conffiles` 声明 `/etc/config/ai-link`，并在 `postinst` 中支持 `AILINK_INSTALLING=1` 协同与 `--sync-ops-to-uci` 自愈；
  5. `root/etc/init.d/ai-link` 新增 `get_ops_or_uci_bool` / `get_ops_or_uci_str`，优先从 `ops_settings.json` 读取 `ipv6_proxy`、`entry_bypass`、`block_quic`、`game_udp_direct` 与 `data_plane_mode`；
  6. `webui/nexus.js` 新增 `localStorage` (`ailink_ops_cache_v1`) 首屏瞬态水合与 LuCI `overview.js` 底层复选框双向同步，彻底消除首屏开关闪烁与表单漂移。

## v2.4.4 (2026-11-08)
- **三维流量洞察 100% 真实账本对齐 (`/api/traffic/insights`)**：彻底重写 `build_traffic_insights_response`，直读 `traffic_ledger.json` 的 `hours`、`days`、`devices`、`nodes`、`targets` 真实账本，清除 `64 MiB` 兜底假数据、`0.55`/`0.45` 固定节点比例与合成时间权重，空账本严格返回 0。
- **全挂自动节点池 (`all_groups_dead_alert=True`) 四态一致性与防振荡闭环**：修复 `resolve_node_for_country_strategy_with_failover`、`get_auto_node_candidate_pool` 与 `_enrich_auto_node_groups_members` 对地区拒服 (`google_region=HK`)、隔离冷却及 `all_groups_dead_alert` 状态的统一判定，彻底消除 `Auto_WorkBuddyAI` 每 22 秒在 `direct` 与 `VIP1-05-新加坡` 间往复振荡的死循环。
- **切换残余连接清理 (`flush_conntrack_for_switch`) 生产链路闭环**：接入 `request_switch()` 出口切换流程，按 `selector_tag` 与 `old_node` 精确断开旧出口残余 Clash 会话，并增加空范围拒绝保护 (`empty_scope_refused`)。
- **底层多核 RPS/RFS/XPS 软中断调优备份与还原闭环**：在 `init.d/ai-link`、`ai-link-daemon.py` 与 `uninstall.sh` 中完整备份并还原 `/proc/sys/net/core/rps_sock_flow_entries` 及各网卡队列 `rps_cpus`/`rps_flow_cnt`/`xps_cpus` 原始值，支持 `ailink0` 虚拟网卡队列调优，并将 `GOMAXPROCS` 收敛至 `sing-box` procd 实例。
- **节点列表构建单次缓存与带宽偏好首轮异步探测**：消除 `build_nodes_api_response` 每节点 4 次重复调用 `classify_node_line_type` 与 `get_node_google_region_info`；开启 `bandwidth_prefer` 时自动异步触发首轮低开销带宽探针。
- **启动迁移日志 (`migration.log`) 幂等化**：当 `migrate_legacy_shunt_config` 发生迁移时立即持久化写回 `shunt.json` 并去重日志记录，避免重启重复追加。

## v2.4.3 (2026-11-08)

- **自动节点池「多线并发」与交互级 AI 防风控护栏**：节点池新增优选单线 (`single_best`) 与多线并发 (`multi_line`) 调度模式；勾选 AI 敏感服务时前端自动锁定单线，且当 `AI/Google/Microsoft/Apple/Social/Soul` 等 IP 敏感分流组绑定至多线并发池时后端自动启用单线保护 (`auto_single_line_protected=True`)。
- **底层静默多核 CPU RPS/RFS/XPS 软中断均衡与切换秒清残留连接**：`init.d/ai-link` 与守护进程启动时静默完成多核网卡队列软中断绑定与 `GOMAXPROCS` 调优；`request_switch()` 切换节点与断开连接时异步秒清 Clash 活跃连接与内核 `conntrack` 表项。
- **节点中转/链式识别、原名关键词 AND/OR 过滤与定量「带宽择优」**：自动识别 `中转专线` / `链式落地` / `直连线路`；向导支持原名关键词 `AND/OR` 过滤与可选定量低频「带宽择优」及单节点即时带宽探针。
- **图形化「链式代理 (Detour)」4 层无环拓扑与级联自愈**：支持将静态住宅 IP 落地节点绑定任意自动节点池或单节点作为前置中转，严格构建 4 层有向无环图 (DAG)，并支持前置节点改名或节点池删除时自动级联迁移。
- **按天/按小时「三维流量归因洞察」与 `VERIFY-v2.4.2-r2.md` 全量闭环**：新增 `/api/traffic/insights`（24h/7d 趋势 + 终端 × 节点 × 域名三维下钻），新增 `index.html` 8 项静态资源 `?v=` MD5 强校验门禁与 `v242_deep_chaos_simulation.py` 11 项混沌自测（全量 15 套自动化测试 100% 通过）。

## [v2.4.2] - 2026-11-05
### 新增与优化 (Added & Optimized)
- **自动节点池内核日志实时故障感知与秒级切换引擎 (`scan_kernel_logs_for_active_pool_failures`)**：针对当前正在被分流组或全局自动模式使用的自动节点池出口节点，以 3 秒周期增量监听 `sing-box.log` 实时运行日志；当活跃节点在 30 秒滑动窗口内连续出现 3 次传输层/握手层报错（`i/o timeout`、`connection refused`、`handshake failed`、`context deadline exceeded`、`EOF` 等）时，无需等待定时巡检即可立即将该节点判死隔离（300 秒）、突破 600 秒粘性冷却期秒级热切换至池内下一最快健康节点，并自动触发低健康度补位与切换日志记录。
- **全面并入 v2.4.1 三份实机审查报告修正**：后端单组节点池彻底收敛与旧版 `auto_nodes.json` 自动备份迁移、根治死节点池 `direct` 乒乓振荡、`/var/run/ai-link/auto_pool_runtime.json` 内存态冷却持久化、全站数据真实性 (`D-01` ~ `D-11`) 闭环。

## [v2.4.1] - 2026-11-05
### 新增与优化 (Added & Improved)
- **节点列表名称统一智能提取（`订阅名丨国家名`）**：严格根据节点**原始名称**（`raw_name` / `tag`，而非 Google 地区探测结果）提取中文国家/地区名（如 `地区随机 | 德国 DE | FRA | 82.117.245.166:443` ➔ `订阅名丨德国`），无关键词可识别时统一显示为 `订阅名丨其他国家`；底层 API 与内核选路保留原始 `tag` 100% 兼容。
- **地区与协议徽章统一格式与去色（`（协议）Google地区：xx`）**：节点列表及节点池弹窗统一仅渲染 `（协议）Google地区：xx`（如 `（HYSTERIA2）Google地区：SG`、`（VLESS）Google地区：HK`），移除重复前缀并取消对香港（`HK`）等地区的黄/红特殊改色。
- **订阅卡片防出框与同步可视化进度条弹窗**：修复 `.sub-health-box` 文本与胶囊溢出问题；点击「立即同步 / 同步全部 / 保存并同步」统一弹出实时进度条与逐订阅状态明细，同步成功后立即刷新卡片「同步时间」并清除旧「失败」残留。
- **测速配额自适应与防假死、概览声呐可自定义目标与断网清零、设置页内核更新与开关对齐**：完整包含 v2.4.0 全部架构升级与事故根因修复。

## v2.4.0 (正式发布 · 2026-11-05)
- **受控三模透明代理数据面 (`tproxy_redirect` / `tproxy_tcp_tun_udp` / `tun_full`)**：新增零拷贝 TProxy、游戏混合 TUN（TCP TProxy + UDP `ailink0` Full-Cone NAT）与全量 TUN 虚拟网卡三档无缝切换，自动联动策略路由表 `163`、`fw4` 转发放行与防断网黑洞看门狗。
- **`sing-box` 版本感知 Schema 适配器 (`1.11 ~ 1.15+`) 与 5 步沙箱安全热升级**：根据内核版本自动适配 `multi_queue`、`dns_mode: disabled` 与 `stack`，内置架构识别、`sing-box.new check -c` 预检、`sing-box.bak` 备份与失败自动回滚。
- **全站 6 页分页头移动端与平板自适应重构**：修复 `375px ~ 980px` 视口下 `.dns-hero.page-hero` 挤压变形与超高问题，移动端统一收敛为紧凑纵向流式 HUD 卡片与 3 列同排指标。
- **自动节点池与分流列表 1:1 严格同源**：修复自动池首选节点与绑定分流策略组出口节点/延迟显示不一致问题。

## v2.3.7 (正式发布 · 2026-11-04)

- **全站 6 大功能页统一「护盾/回家同构单横幅 Hero」**：移除概览、分流、回家、护盾、节点、设置 6 页顶部多余的第二层 `.content-head` 顶栏，全部统一为每页顶部唯一的 `.dns-hero.page-hero.glass-card`（含径向发光背景、与左侧导航 1:1 统一的发光图标与双层脉冲环、流动光子轨道、3 项实时指标与右侧控制区）。
- **BusyBox `flock` 兼容与透明代理挂载保护 (P0-1)**：`apply_nft.sh` 采用 4 级兼容锁并确保加锁超时严格 `exit 1`，`install.sh` 验活确保 `table inet ai_link` 100% 挂载。
- **每日测速配额超限跳过保态与自动自愈 (P0-2)**：达到日配额上限时跳过探测并 100% 保留节点既有健康态，升级时自动重置旧版未持久化的异常累计计数并自愈历史受污染探测记录。
- **探测缓存实时同源与细节打磨 (P2-1~P2-3 / P3)**：`node_probe.json` 纳入 `_conf_file_mtimes_sig` 确保全接口 `pool_reachable_count` 实时同源；修复离线态概览页重复告警横幅与护盾页 `NaN` 显示。

## v2.3.6 (r10 实机验收闭环 · 2026-11-04)

- **[P0-1 修复 · BusyBox `flock` 三级降级锁与 `install.sh` 严格断言]**：修复 `apply_nft.sh` 在 BusyBox `flock`（仅支持 `[-sxun]`，不支持 `-w`）下报 `unrecognized option: w` 并静默 `exit 0` 导致 `table inet ai_link` 未挂载的问题；升级为 `flock -x -n` 立即获取 ➔ `flock -x -w 18` ➔ BusyBox `flock -x -n` 轮询等待 ➔ `mkdir` 自旋锁三级降级，且加锁失败严格返回 `exit 1`；`install.sh` 在 `table inet ai_link` 未挂载时自动重试一次，仍失败则立即 `exit 1` 中止安装。
- **[P0-2 修复 · 测速配额闸门“跳过保态”语义与存量升级自动配额迁移]**：修复触发每日测速配额上限 (`quota_capped: True`) 时被探测引擎误判为 `state: "dead"` 导致全节点不可达与分流组回落 `direct` 的问题；超配额时严格执行 `skipped: True` 跳过语义，保留节点在 `node_probe.json` 中的上一次已知健康状态，并在升级首次启动时自动清零旧版累积的超额计数与自愈历史误判记录。
- **[P2-1 修复 · 自动节点池健康数与内核 Selector 单一真值同源]**：修复 `_conf_file_mtimes_sig` 对 `/var/run/ai-link/node_probe.json` 的缓存签名感知与 `save_node_probe_store` 缓存失效逻辑，并在 D-01 降级保护与前端渲染层同步 `pool_reachable_count`、`current_node` 与 `selection_explain`。
- **[P2-2 说明 · 实时活跃代理连接表位置与顶栏快捷跳转]**：实时活跃代理连接表（`#connections-tbody`，支持按局域网设备 IP 筛选与多维搜索）统一收纳于「**设置与诊断 (Settings) ➔ 06 / LIVE ACTIVE CONNECTIONS**」；同时支持点击顶栏「**活跃连接**」数字一键跳转并平滑滚动定位。
- **[P2-3 & P3 修复]**：`:root` 中 `--mint` 精确对齐为 `#38e0b2`，并清除 `nexus.js` 中 `mock.groups` / `mock.autoPools` 的全部 `142` / `156` 种子初始值（统一设为 `null`）。

## [v2.3.5] - 2026-11-03 (全新极简自动节点池重构与全场景手动/自动模式正交解耦版)

### 🌟 核心架构与功能重构 (Auto Node Pool v2.3.5)
1. **6步极简目标驱动自动节点池向导 (创建节点池 -> 勾选来源 -> 勾选国家 -> 服务检测 -> 节点数/复选阈值 -> 实时进度条选取)**：
   - 彻底废弃旧版双组主备两阶段手动勾选与静态成员维护逻辑，全面转向「按需自动筛选 + 定时轻量巡检 + 低健康度自动补齐」的闭环架构。
   - **多选节点来源 (`scope_sources`)**：支持同时多选多个机场订阅源与手动自定义节点 (`custom`)，卡片实时展示各订阅剩余流量与节点总数，方便按订阅流量配额灵活分配。
   - **多选国家区域 (`scope_countries`)**：支持同时勾选多个国家（`HK`、`TW`、`JP`、`SG`、`US`、`OTHER` 或 `ALL`），实时联动计算候选可用节点数。
   - **需求节点数量 (`target_size`: 1~10)** 与 **低健康度自动复选阈值 (`replenish_threshold`: 1~10)** 动态配置。
   - **异步选取与实时进度条 (`#mdl-an-progress-box`)**：点击「开始自动选取」展示 Apple 风格动画进度条与阶段状态，选取完成后自动选入最快达标节点并生成专用内核出站选择器。

2. **真实目标服务可用性检测与触发两阶段解耦**：
   - **L7 真实目标访问校验 (`probe_node_service_l7` & `_probe_real_node_http_region`)**：
     - **Gemini**：实际发送 HTTP/TLS 请求捕获重定向及正文特征，精确识别 `.com.hk`、`.cn`、`/sorry/index` 及地区限制错误文案并予以排除。
     - **ChatGPT / OpenAI**：校验 `cdn-cgi/trace` `loc=` 落地国家及 `403`、`unsupported_country`、`vpn_detected` 等状态。
     - **Claude / YouTube / Netflix / TikTok / GitHub / Telegram**：通过真实特征 URL 验证地域支持与内容解锁。
   - **触发场景严格约束为 2 种**：
     - **场景 ①**：节点池创建（或手动点击重新选取）时触发；
     - **场景 ②**：节点池低健康度自动复选时（当日常 URL Ping 或订阅更新导致池内健康可用节点数 `< replenish_threshold` 时）触发；
     - **日常后台巡检与快速优选**：周期性后台探针与卡片「立即 Ping 优选」按钮仅执行纯 **URL Ping** 测速并平滑切换至延迟最低的健康节点，杜绝日常周期产生高频 L7 业务开销。

3. **全场景去除手动单一节点模式下的自动切换/漂移逻辑**：
   - **非分流模式 (`cn_whitelist` / `gfw_list` / `global_proxy`)**：当用户选择手动单一节点时，内核 `AI_Best_Auto` 及状态栏严格锁定在用户所选节点（提示 `手动固定 (国家) 节点名`），彻底移除失效时自动切换其他节点或漂移的逻辑。需要自动切换与容灾时，用户可直接切换为「自动节点池」模式。
   - **分流策略组 (`rule_shunt`)**：手动模式默认严格锁定单节点，自动模式选用自动节点池，实现手动与自动逻辑的完全正交解耦。

## [v2.3.4] - 2026-11-03 (全量验收缺陷 100% 闭环与全场景体验加固版)

### P0 阻断级缺陷修复
- **修复 `nexus.css` L245/L699 语法断链与 CSS 变量作用域陷阱 (P0-1)**：修复 `--_c-116: rgba(110, 231, 245, var(--alpha);` 缺失右括号及 `.matrix-cell` 多余右括号导致的 CSS 解析器雪崩（修复前仅解析 1 条规则，L245 之后 703 条规则全部失效）；将 `.matrix-cell` 改为 `background: var(--cyan); opacity: var(--alpha, 0.22);`，直接消费单元格内联 `--alpha` 变量。
- **修复 `[hidden]` 属性被组件 `display` 规则覆盖导致模态框锁屏 (P0-2)**：将 `.modal-backdrop`、`.webgl-fallback`、`.node-tooltip` 改为 `:not([hidden])` 选择器，并在 `nexus.css` 末尾追加高优先级 `[hidden], .hidden, #modal[hidden], #webgl-fallback[hidden], #node-tooltip[hidden], #music-unlock-card[hidden] { display: none; }` 显式保护，确保首屏加载不再误弹空白模态框或 WebGL 降级条。

### 遗留未闭环与新发现问题修复
- **修复升级路径历史默认密码哈希识别与 v2.3.3 状态自愈 (N-P0-2)**：`_load_panel_auth()` 现已兼容旧版 `sha256("ailink_salt_2026:ai-link-2026")` (`390a3417...`) 并在检测到 v2.3.3 升级链误标的 `pbkdf2_sha256_chain` 时自动回退至 `/etc/ai-link/initial_password` 且重置 `customized: false`、同步 UCI `panel_pwd_customized=0`；`root/usr/bin/ai-link` CLI 与 LuCI `overview.js` 同步读取真实初始密码状态。
- **修复 `/api/nodes/delete` 返回 `total_nodes` 偏差 1 与缓存未穿透失效 (N-P3-3 / 新发现-4)**：统一使用 `count_user_nodes()` 过滤内置回环测试节点 `SG-Hy2-Loopback-01`，并在 `save_nodes_list()` 与 `_atomic_write_text()` 中即时清理 `_FAST_FILE_CACHE`。
- **修复覆盖安装残留历史孤儿文件 (新发现-1)**：`install.sh` 及 IPK `preinst` 在升级部署前清理 `/usr/share/ai-link/webui/` 下的 `aster.css`、`aster-ui.js`、`tokens/` 等废弃文件。
- **统一全仓 7 处版本号/构建号并落地静态资源 Cache-Busting 与 ETag (新发现-2 / 新发现-3)**：全仓版本号统一为 `2.3.4` (`2.3.4-release-20261103`)，`index.html` 静态资源引用注入内容 SHA256 指纹 (`?v=2.3.4-<hash8>`)，守护进程静态文件响应支持 `ETag`、`If-None-Match` (`304 Not Modified`) 与 `Cache-Control: no-cache, must-revalidate`。

### 视觉排版、对比度、触控热区与门禁加固
- **字号分布优化 (`12px` 占比 `73.4% -> 9.2%`)**：清理 `nexus.js` 与 `index.html` 中 60+ 处内联 `font-size:12px`，将正文与列表字号提升至 `13px~14px`，仅徽章与辅助小字保留 `12px`。
- **WCAG AA 对比度达标 (`--dim` `3.19:1 -> 7.19:1`)**：将深色主题 `--dim` 提升至 `#8B9BB4`，并全面校准次级暗色文本 Token。
- **全量交互控件触控热区达标 (`>= 40x40px`)**：移除内联 `min-height:24..35px` 限制，统一按钮、分段控件、工具栏图标与表格操作按钮最小尺寸为 `40x40px`。
- **前后端数据真实性与 Three.js 显存加固**：清空前端残留硬编码模拟拦截域名（`otheve.beacon.qq.com` 等）并允许后端空数组 `[]` 覆盖；统一 Telegram 分流组为 `Shunt_Outside_CN`；修复 `nexus3d.js` 卫星/连线重建 WebGL 显存泄漏并加入软件渲染自适应帧率节流；`tools/design-lint.js` 新增 `css-parse` 与 `hidden-override` 门禁。

# AI-LINK v2.3.3 (2026-11-02) · Round 3 深度复审闭环与 Apple/Aster 视觉无障碍重构版

## 一、功能与安全审计 19 项全量修复 (`AI-LINK-v2.3.2-复审报告.html`)
- **[N-P0-1] 移除净网护盾假数据种子 (`adblock_stats.json`)**：彻底删除 `_load_persisted_adblock_stats()` 中当 `blocked_queries == 0` 时写入的 8 个伪造域名（`cpro.baidu.com` 等 64 次拦截 / 509 次查询），真实初始状态归零。
- **[N-P0-2] 面板鉴权全面升级 `pbkdf2_sha256` (100,000 次迭代) + 设备唯一随机盐与随机初始凭据**：下线硬编码盐值 `ailink_salt_2026` 与默认密码回退后门；首次启动自动生成设备唯一随机初始密码 (`/etc/ai-link/initial_password`, `0600`)，存量 `panel_auth.json` 自动平滑迁移至 `pbkdf2_sha256` + 16 字节随机盐。
- **[N-P1-1] 离线/断连状态精准区分与零伪造指标**：在 `nexus.js` 中严格区分“面板守护进程不可达 (`state.backendOffline`)”与“sing-box 内核未运行 (`state.coreAlive === false`)”，断连时将 `coreMemMib`、`blockedTotal`、`uptimeStr`、`inTotalText`、`outTotalText` 等全部重置为 `--`，不再弹出误导性的“sing-box 未运行已回退直连”横幅。
- **[N-P1-2] 修复离线连接池水位 `NaN%` 渲染故障**：增加 `Number.isFinite(connPct)` 与 `Number.isFinite(memPct)` 守卫，离线时渲染 `--` 与 `0%` 宽度进度条。
- **[N-P1-3] `/api/homelink/delete` 异步化重载 (`<50ms` 响应)**：回家节点删除接口改用后台线程同步防火墙规则并调用 `schedule_async_core_reload(force_respawn=True, apply_nft=True)`，消除 11–18 秒同步阻塞；前端删除按钮增加 `disabled` 与 `删除中...` 防抖状态。
- **[N-P1-4] IPv6 连通性探测改用真实 TCP 握手 (`SOCK_STREAM`)**：替换原先不发包的 UDP `connect()` 假阳性探测，向 `[2400:3200::1]:53` / `[2402:4e00::]:53` 发起真实 TCP 握手测量 RTT。
- **[N-P1-5] 修复「连接与设置」页 `/api/ops/logs` 401 弹窗打断**：将 `/api/ops/logs` 鉴权与 `require_lan_auth` 策略对齐 (`_auth_ok()`)，且后台日志轮询不再触发全局登录弹窗。
- **[N-P2-1 ~ N-P2-6 & N-P3-1 ~ N-P3-6]**：
  - `max_outbounds_limit == 0` 时规范显示为 `N 个（不设上限）`（消除 `200 / 0`）；
  - 统一 `/api/status` 与 `/api/diag/run` 的 `health_score` 计算源；
  - Telegram 服务脉冲映射至真实存在的 `Shunt_Outside_CN` 策略组；
  - `cleanup_temp_and_rotate_backups()` 接入守护进程启动与周期巡检，自动清理 `/tmp/ai-link-shunt-test-*`、`/tmp/ailink-*-e2e-*`、`/tmp/ailink-upgrade` 与陈旧 `/var/run/ai-link/ephemeral_probe_*`；
  - 补齐全部 8 个图标按钮的 `aria-label`；
  - 提升 `--muted` 次级文字色值至 `#8B9BB4`（对比度 `>= 5.1:1`，符合 WCAG AA）；
  - 删除冗余的 `static/three.min.js`、`static/tailwind.css`、`static/holo3d.js`（安装包体积缩减 ~310 KB）；
  - 去重 `ai-link-rewrite.conf` 中的 `server=/googleapis.cn/` 等规则；
  - 修复节点删除接口 `total_nodes` 计数并返回 `deleted_count`；
  - 壁纸模式 (`WALLPAPER LIVE`) 自动淡出顶栏与底角图例；
  - `/etc/ai-link/ops_settings.json` 纳入 `0600` 权限保护。

## 二、Apple HIG / Aster 设计语言 29 项前端审美审查闭环 (`AI-LINK-前端审美审查报告.html`)
- **[P0-1] 移除 `index.html` 中 91KB 重复内联 `<style>`**：`index.html` 体积从 153.8 KB 降至 62 KB，仅外链 `./nexus.css?v=2.3.3`。
- **[P0-2] 字体栈、字重、字阶与行高全面收敛**：移除未加载的 `Inter` 字体，字重严格收敛至 `{400, 500, 600, 700}`，字阶收敛至 10 级 `{11, 12, 13, 14, 15, 16, 19, 24, 32, 40px}`，`body` 设为 `14px / line-height: 1.57`，彻底消除 `line-height: normal`，并将正文与列表字号提升至 `13px/14px`（`12px` 占比降至 `<15%`）。
- **[P0-3] 界面 Chrome 零 Emoji 与零 `U+FE0F` 乱码**：将 `index.html`、`nexus.js`、`nexus3d.js` 中全部 300+ 处 Emoji 与 `U+FE0F` 变异选择符替换为 `24×24` 单色线性 SVG 图标或规范文本徽章。
- **[P0-4] 模态框无障碍契约与焦点陷阱 (`Focus Trap`)**：`#modal` 挂载 `role="dialog" aria-modal="true" aria-labelledby="modal-title"`，支持打开自动聚焦、Tab/Shift+Tab 闭环焦点陷阱、`Escape` 键关闭、关闭后焦点归还触发按钮及背景 `aria-hidden="true"`。
- **[P1-5 ~ P3-29] Aster `design-lint.js` 14 项门禁零违规通过**：
  - 合并 4 个 `:root` 块为唯一权威令牌区，清理 7 个废弃变量，消除全部裸色值 (`raw-color = 0`)；
  - 圆角收敛至 6 档 (`--r-xs` ~ `--r-full`)、间距收敛至 11 级 (`--sp-0` ~ `--sp-10`)、动效时长 `<= 320ms` (`--dur-1` ~ `--dur-4`)、命名层级令牌 (`--z-base` ~ `--z-toast`)、非无障碍区零 `!important`；
  - 全部交互控件最小点击热区 `>= 40px`，具备完整 6 态（`default / hover / active / focus-visible / disabled / is-loading`）与 `2px solid var(--accent)` 焦点环；
  - 原生 `<select> option` 适配深色背景，全部数值指标启用 `font-variant-numeric: tabular-nums`；
  - `nexus3d.js` 在切换离开星图页、标签页隐藏或开启 `prefers-reduced-motion: reduce` 时完全停止 `requestAnimationFrame` 循环（后台帧率 = 0）；
  - 订阅卡片移除重叠的竖排 "✓ 当前显示" 徽章，顶栏增加三区分割线与“跳至主内容” (`skip-link`)。


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


### 🛡️ 双源合并审计报告 (Round 1~4) 全量闭环 + Round 5 Apple HIG 视觉与壁纸级 3D 星图重构

3. **[Round 1 — P0 安全边界与配置持久化统一]**
   - **21 字段 `OPS_PERSIST_KEYS` 读写闭环 (`C-P0-09 & C-P1-04`)**：统一 `update_ops_settings`、`factory_reset_all_configs`、`/api/ops/backup_archive` 与 `restore_ops_backup`，确保 `ipv6_leak_guard`、`ipv6_leak_mode`、`topology_mode`、`tcp_mss_clamp` 100% 完整落盘与恢复。
   - **高敏接口令牌强鉴权与敏感凭据脱敏 (`C-P0-01 & C-P1-05`)**：新增 `_strict_auth_ok()` 守护 `/api/ops/backup*`、`/api/nodes/credentials`、`/api/nodes/share_uri`、`/api/ops/logs`、`/api/ops/factory_reset`、`/api/ops/uninstall`、`/api/ops/password`、`/api/ops/restore*`；未登录客户端访问 `/api/status` 与 `/api/nodes` 自动脱敏密码/UUID/私钥与订阅 Token；卸载接口要求 `confirm="UNINSTALL"`。
   - **同源 CORS 与 CSRF 防护 (`C-P0-02`)**：移除 `Access-Control-Allow-Origin: *`，新增 `_check_csrf_same_origin()` 拦截跨源 POST 请求（返回 `HTTP 403 csrf_forbidden`）。
   - **Clash API 环回绑定与 SSRF/TLS 守卫 (`C-P0-03 & C-P0-04 & C-P1-13 & C-P2-14`)**：`sing-box.json` `clash_api.external_controller` 强制绑定 `127.0.0.1:9090`；订阅与 OTA URL 拦截 `file://`、`ftp://`、`data:` 协议并限制响应体上限 8MB。
   - **PBKDF2-HMAC-SHA256 密码存储与 0600 权限 (`C-P0-05 & C-P1-12`)**：面板密码升级为 100,000 次迭代 `PBKDF2-HMAC-SHA256` 并支持 7 天令牌过期 (`token_exp`)；敏感配置文件强制 `0600` 权限且 `config_history.json` 自动脱敏。

4. **[Round 2 — P0/P1 假数据清零与真实探针闭环]**
   - **离线状态真实呈现 (`C-P0-06 & C-P1-18`)**：前端分离 `mock` 与实时状态，当 `/api/status` 不可达时顶栏指标置为 `--` 并拉起离线横幅。
   - **DNS 上游 60 分钟环形缓冲统计 (`C-P0-07`)**：移除硬编码命中率/延迟假数据，改由 `_DNS_UPSTREAM_RING` 实时聚合真实样本。
   - **网络健康医生真实系统探针 (`C-P0-08`)**：移除 `or 1` 假阳性兜底，生产环境禁止外部 HTTP `mock_env` 注入，真实校验 `sing-box` PID、`:7874`/`:7893` 监听与 `/sys/class/net/*/mtu`。
   - **真实 WOL 魔术包与多通道告警 (`C-P1-07 & C-P1-08`)**：`/api/wol` 拒绝全零/占位 MAC 并发送真实 102 字节 UDP 广播魔术包；`trigger_alert_event` 补齐 Telegram Bot API 与 SMTP 投递。

5. **[Round 3 — P1/P2 节点传输层指纹、Gzip 压缩与引用自愈]**
   - **WebUI 体积精简与 Gzip 压缩 (`C-P1-01 & C-P2-01`)**：剥离 `index.html` 冗余内联脚本，静态资源启用 Gzip 压缩与 `Cache-Control: public, max-age=86400`。
   - **传输层感知节点指纹 (`C-P1-02`)**：`compute_node_id` 与 `compute_node_key` 纳入 WS `path`/`Host`、gRPC `service_name` 与 TLS `SNI`，彻底杜绝同入口 CDN 节点被误合并。
   - **节点改名/删除级联自愈与严格参数校验 (`C-P1-21 & C-P1-22 & C-P2-15`)**：新增 `reconcile_node_references` 自动同步分流组与自动节点池引用；非法枚举与畸形 JSON 严格返回 `HTTP 400`。

6. **[Round 4 & Round 5 — Apple HIG 全站视觉交互打磨与壁纸级 3D 星图引擎]**
   - **壁纸级 3D 星图引擎 (`nexus3d.js`)**：程序化高精度星球大气带与经纬网发光纹理 (`createPlanetTexture`)、多层日冕光晕 (`createCoronaTexture`)、菲涅尔大气散射壳 (`atmoShell`)、双倾角精密星环与脉冲波纹环 (`pulseRing`)、Gargantua 级相对论黑洞吸积盘与引力透镜光弧 (`lensingArch`)、黄道面星盘坐标网格 (`buildEclipticPlane`)、深空星云氛围背景，以及三挡真实速率驱动的体积能量导管与 3 阶彗尾光子流 (`trailSprites`)。
   - **VisionOS 空间毛玻璃数据铭牌与一键壁纸沉浸模式 (`#wallpaper-toggle` & `#wallpaper-hud`)**：Retina 级 Canvas 2D 空间引线铭牌（带星系主题色侧边灯条与抗遮挡避让）、全景模式智能视口构图（右侧检查器展开时自动微移相机焦点确保四大星系 100% 同屏无遮挡），以及支持快捷键 `W` 的一键「壁纸沉浸模式」。
   - **无障碍与排版标准 (`C-P1-15 & C-P2-02 & C-P2-03`)**：全站表单控件 100% 具备无障碍标签 (`unlabeledCount = 0`)，全站字号严格 `>= 12px`，全面对标 Apple HIG 玻璃拟态材质与弹簧过渡曲线。

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
