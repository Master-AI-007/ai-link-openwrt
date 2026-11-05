## [v2.4.1] - 2026-11-05
### 新增与优化 (Added & Improved)
- **节点列表名称统一智能提取（`订阅名丨国家名`）**：严格根据节点**原始名称**（`raw_name` / `tag`，而非 Google 地区探测结果）提取中文国家/地区名（如 `地区随机 | 德国 DE | FRA | 82.117.245.166:443` ➔ `订阅名丨德国`），无关键词可识别时统一显示为 `订阅名丨其他国家`；底层 API 与内核选路保留原始 `tag` 100% 兼容。
- **地区与协议徽章统一格式与去色（`（协议）Google地区：xx`）**：节点列表及节点池弹窗统一仅渲染 `（协议）Google地区：xx`（如 `（HYSTERIA2）Google地区：SG`、`（VLESS）Google地区：HK`），移除重复前缀并取消对香港（`HK`）等地区的黄/红特殊改色。
- **订阅卡片防出框与同步可视化进度条弹窗**：修复 `.sub-health-box` 文本与胶囊溢出问题；点击「立即同步 / 同步全部 / 保存并同步」统一弹出实时进度条与逐订阅状态明细，同步成功后立即刷新卡片「同步时间」并清除旧「失败」残留。
- **测速配额自适应与防假死、概览声呐可自定义目标与断网清零、设置页内核更新与开关对齐**：完整包含 v2.4.0 全部架构升级与事故根因修复。

## [v2.4.0] (正式发布 · 2026-11-05)
- **受控三模透明代理数据面 (`tproxy_redirect` / `tproxy_tcp_tun_udp` / `tun_full`)**：新增零拷贝 TProxy、游戏混合 TUN（TCP TProxy + UDP `ailink0` Full-Cone NAT）与全量 TUN 虚拟网卡三档无缝切换，自动联动策略路由表 `163`、`fw4` 转发放行与防断网黑洞看门狗。
- **`sing-box` 版本感知 Schema 适配器 (`1.11 ~ 1.15+`) 与 5 步沙箱安全热升级**：根据内核版本自动适配 `multi_queue`、`dns_mode: disabled` 与 `stack`，内置架构识别、`sing-box.new check -c` 预检、`sing-box.bak` 备份与失败自动回滚。
- **全站 6 页分页头移动端与平板自适应重构**：修复 `375px ~ 980px` 视口下 `.dns-hero.page-hero` 挤压变形与超高问题，移动端统一收敛为紧凑纵向流式 HUD 卡片与 3 列同排指标。
- **自动节点池与分流列表 1:1 严格同源**：修复自动池首选节点与绑定分流策略组出口节点/延迟显示不一致问题。

## [v2.3.7] (正式发布 · 2026-11-04)

- **全站 6 大功能页统一「护盾/回家同构单横幅 Hero」**：移除概览、分流、回家、护盾、节点、设置 6 页顶部多余的第二层 `.content-head` 顶栏，全部统一为每页顶部唯一的 `.dns-hero.page-hero.glass-card`（含径向发光背景、与左侧导航 1:1 统一的发光图标与双层脉冲环、流动光子轨道、3 项实时指标与右侧控制区）。
- **BusyBox `flock` 兼容与透明代理挂载保护 (P0-1)**：`apply_nft.sh` 采用 4 级兼容锁并确保加锁超时严格 `exit 1`，`install.sh` 验活确保 `table inet ai_link` 100% 挂载。
- **每日测速配额超限跳过保态与自动自愈 (P0-2)**：达到日配额上限时跳过探测并 100% 保留节点既有健康态，升级时自动重置旧版未持久化的异常累计计数并自愈历史受污染探测记录。
- **探测缓存实时同源与细节打磨 (P2-1~P2-3 / P3)**：`node_probe.json` 纳入 `_conf_file_mtimes_sig` 确保全接口 `pool_reachable_count` 实时同源；修复离线态概览页重复告警横幅与护盾页 `NaN` 显示。

## [v2.3.6] (r10 实机验收闭环 · 2026-11-04)

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

### 一、功能与安全审计 19 项全量修复 (`AI-LINK-v2.3.2-复审报告.html`)
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

### 二、Apple HIG / Aster 设计语言 29 项前端审美审查闭环 (`AI-LINK-前端审美审查报告.html`)
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

## [v2.2.0] - 2026-11-01 — 目标驱动自动节点池 + 取消入核上限 + URL Ping 全链路修复

### 亮点

1. **目标驱动自动节点池**：节点范围（订阅/手动/全部）、两种模式（仅连通性 / 连通性+服务）、一键按延迟选最快 10 个；
2. **URL Ping 全链路修复**：移除 `/delay` 超时对全局熔断器的误伤、默认超时 5s + 双目标见证、全量节点直接入核；
3. **取消入核数量上限**：649 个节点 100% 写入 `sing-box` outbounds；
4. **节点两态简化**：可用 / 不可达（后续在 2.3.1 补为三态）；
5. **订阅卡片**：同步时间精确到分钟，失败追加红色「失败」后缀。

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

## [v2.0.0] - 2026-10-27（NEXUS 全域 3D 正式版 · 全量检查更新包）

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

## [v1.0.3] · 2026-10-26

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

## [v1.0.2] · 2026-10-26

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

## [v1.0.1] · 2026-10-26

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

## [v1.0.0] · 2026-10-25

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
