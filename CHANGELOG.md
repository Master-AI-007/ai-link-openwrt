# AI-LINK 更新日志

本文件记录 AI-LINK 智能分流网关的全部版本变更。
在线更新客户端读取的机器可读清单是 `version.json`，本文件是面向人的详细说明。

版本号规则：`主版本.次版本.修订号`
- 主版本：架构级变更（如内核切换、配置模型重构）
- 次版本：新增功能，向后兼容
- 修订号：缺陷修复与安全补丁，向后兼容

---

## v1.0.2 · 2026-10-26

> 主题：**全量安全加固 + 启动与看门狗可靠性 + `.tgz` 归档上传恢复 + 跨架构兼容与自动化回归**

### 🔐 安全加固（SEC-1~SEC-5 & B1-1~B1-4）

- **面板令牌不再随首页下发（SEC-1）**
  移除 `end_headers` 中对 `/` 请求下发 `Set-Cookie: ailink_token=<有效令牌>` 的缺陷；令牌仅在 `POST /api/login` 校验密码通过后签发，由前端保存在 `localStorage` 与 `Cookie`。
- **`/api/status`、`/api/nodes/share_uri`、`/api/ops/logs` 鉴权与凭据脱敏闭环（SEC-2~SEC-5）**
  - `/api/status` 按访问控制同一口径判定：未鉴权客户端脱敏回家节点的 `password` / `uuid` / `private_key` / `uri`（含 `uri` 内嵌明文凭据）及订阅 `?token=` 参数，并将鉴权状态与 `panel_auth.json` 纳入 wire-memo 缓存键；
  - `GET /api/nodes/share_uri` 与 `GET /api/ops/logs` 强制校验 `_auth_ok()`，未授权请求一律返回 HTTP 401。
- **UCI 凭据零留存，彻底改为布尔 `panel_pwd_customized=0/1`（B1-2）**
  `/etc/config/ai-link` 移除 `panel_secret` 字段，改用布尔 `option panel_pwd_customized '0'`；`install.sh` 升级时自动迁移并清除历史 `panel_secret`；CLI `ai-link password` 不再向 UCI 写入任何明文或哈希串。
- **永久下线弱默认密码 `admin`（B1-3）**
  出厂状态仅接受 `ai-link-2026` 作为初始密码，彻底禁用弱口令 `admin`；面板登录弹窗移除预填明文 value。
- **内网免密风险提示与自动登录引导（B1-1）**
  `/api/status` 新增 `auth_required` 与 `pwd_customized` 状态位，未鉴权打开面板自动弹出登录窗；WebUI 设置页新增 `#lan-auth-security-notice` 动态安全风险警示条；LuCI 新增 `require_lan_auth` 开关并与 `ops_settings.json` 双向同步。

### 🚀 启动可靠性与防黑洞看门狗（BOOT-1 / CORE-1 / RB-1 / B1-4 / B3-12）

- **多栈端口就绪探针（BOOT-1 & B3-12）**
  `init.d/ai-link` 的 `port_is_listening()` 采用 `netstat` → `ss` → `/proc/net/tcp{,6}` 三级探针，同时比对大小写十六进制端口（消除精简版 BusyBox `awk toupper()` 依赖），等待预算放宽至 60 秒（`AI_LINK_PORT_WAIT` 可覆盖）。
- **修复 BusyBox `pgrep` 探针与全仓进程匹配（CORE-1 & B3-12）**
  `init.d/ai-link` 统一使用 `singbox_alive()`（`pidof sing-box` + `pgrep -f` 兜底）并动态解析 `command -v sing-box`；全仓 `install.sh` / `uninstall.sh` / `usr/bin/ai-link` 统一使用 `pgrep -f "ai-link-dae[m]on.py"` 防止 shell 自匹配误杀。
- **看门狗与 `restore_proxy` 挂载 nftables 前强制校验端口（B1-4）**
  `ensure_nft_and_routing_intact()`、`restore_proxy()` 及 `update_ops_settings()` 在挂载 `table inet ai_link` 前强制校验 TProxy `:7893` 端口监听状态，核心未就绪时跳过挂载以杜绝局域网断网黑洞。
- **在线升级回滚立即恢复透明代理（RB-1）**
  OTA 回滚段在重启服务后主动调用 `/etc/init.d/ai-link restore_proxy`，消除约 10 秒的透明代理空窗。

### 📦 备份恢复与在线更新增强（B2-6 ~ B2-11）

- **面板与 LuCI 支持 `.tgz` / `.json` 浏览器直接上传恢复与 `.tgz` 归档下载（B2-6）**
  新增 `GET /api/ops/backup_archive`（一键导出 `.tgz` 全量归档）并升级 `POST /api/ops/restore_archive` 支持浏览器直接上传 `.tgz` / `.tar.gz` 或 `.json` 备份恢复，内置 `tarfile` 路径穿越（`..`）、非普通文件与 100MB 解压上限安全校验，且仅在校验与恢复成功后更新持久化备份。
- **新增 `ai-link restore <file|--latest>` CLI 命令行恢复入口（B2-7）**
  支持通过命令行直接传入 `.tgz` 归档或 `.json` 备份文件完成全量恢复与服务重载（`ai-link-daemon.py --restore <file>`）。
- **OTA 升级进度闪存持久化（B2-8）**
  升级脚本将实时进度双写至 `/root/ai-link-final-backup/last_update_progress.log`，设备断电重启导致 `/var/run` tmpfs 丢失后仍可自动还原升级中断状态。
- **`auto_nodes.json` 剥离实时探测噪声（B2-9）**
  落盘时通过 `_strip_auto_node_runtime_fields()` 剔除 `quality_ranking`、`last_check_ts`、`members` 等高频探测字段（读取时动态注入内存），跨探测周期文件 MD5 保持 100% 恒定。
- **自定义更新源域名与冷启动提示（B2-10 & B2-11）**
  `ops_settings` 白名单新增 `update_manifest_url` 支持绑定自有域名作为第一优先级 OTA 清单源，并与 UCI 删除/修改双向同步；界面与文档保留 v1.0.0 首次手动升级说明。

### 🛠 工程与验证工具链（TOOL-1~3 / HYG-1 / TEST-1 / B3-13~14 / B4-16~20）

- **Clash API 负缓存断路器（B4-20）**：`clash_api_request()` 新增 `_CLASH_API_DOWN_UNTIL` 断路器与 Linux `/proc/net/tcp` 零套接字权威判定，无 Clash API 环境下 `--self-test --strict` 耗时 < 1.5s。
- **发布与核对工具链增强（TOOL-1~3 & B4-16~17）**：修复 `release.py` 7 处版本同步正则与门禁校验，支持自动检测工作区仓库与同版本预置发布；`verify_online.py` 支持进程环境变量覆盖。
- **全链路 E2E 与无头浏览器 UI 自动化回归（B3-13 & B3-14）**：新增 `test_v102_full_regression.py`（42 项断言），覆盖真实 HTTP 服务端密码登录/改密/鉴权、`.tgz` 上传恢复及 Headless Chromium 浏览器 UI 渲染与交互验证。

## v1.0.1 · 2026-10-26

> 主题：**服务总开关 + 在线更新体系 + 面板密码安全修复**

### ⚙️ 服务总开关（新功能）

- **LuCI 概览页顶部新增「服务总开关」卡片**，实时显示并控制服务生命周期：
  - 状态徽章：`● 运行中` / `◐ 部分运行（内核未起）` / `⏹ 已停止`
  - 元信息：开机自启、透明代理接管、nftables 挂载、面板端口
  - 四个动作按钮：**启动服务 / 停止服务 / 重启服务 / 开机自启开关**
- **关键设计：这条通路不依赖 `:9099` 面板。**
  它走 LuCI 自己的 `fs.exec` → `/etc/init.d/ai-link svc_state|start|stop|restart`，
  所以**即使守护进程已经停了，也能在 LuCI 里一键把它拉起来**，不需要 SSH。
- **修复死锁**：此前若服务被 `stop` 掉，LuCI 概览页所有按钮全部失效（它们都调 `:9099` 的 API），
  而「启用 AI-LINK 透明代理服务」这个勾选框只管流量接管、不管进程启停，导致用户无处可恢复。
- **`enabled` 语义澄清**：该开关只控制「是否接管流量」；进程启停由新的总开关负责。
  卡片下方有明确文案区分两者，避免再混淆。
- **`reload_service()` 兜底**：`enabled=1` 时若 daemon 或 sing-box 任一未运行，直接整体 `start`，
  不再依赖「reload 只重载运行中实例」的旧行为。
- **独立面板同步**：设置页新增服务状态卡片（运行中 / 开机自启 / nftables / 端口）+「🔄 重启服务」按钮，
  5 秒自动刷新。
- **新增 init 动作 `svc_state`**：输出单行 `daemon= core= nft= enabled= boot= bypass= port=`，
  供 LuCI 与面板统一解析。

### 🔐 安全修复

- **修复：LuCI 概览页「面板密码」显示为一串 `sha256:xxxx` 哈希**
  - 根因一：改密后 `ai-link.global.panel_secret` 被写入 `sha256:<hash前24位>`，而 LuCI 直接把它当密码显示。
  - 根因二（更严重）：`--self-test` 用临时目录调用改密函数，但函数体无条件 `uci set`，导致**每次安装自检 / `ai-link probe` 都会把生产环境的 `panel_secret` 覆盖成测试串 `custom-secret-2026` 的哈希**。
- **修复：哈希串可直接当密码登录**
  `_verify_panel_password` 中的 `candidate_pw == get_uci_panel_secret()` 已移除；UCI 里只有「明文初始密码」才允许直通比对。
- **修复：哈希串可直接当 Bearer 令牌绕过登录**
  `_is_request_authenticated` 中的 `tok == get_uci_panel_secret()` 已移除，令牌只认 `panel_auth.json` / `panel_token` 里签发过的值。
- **修复：`panel_auth.json` 丢失后用户被锁死**
  旧逻辑会用 UCI 里的哈希当初始密码重建，导致真实密码彻底失效。现在回退到默认密码 `ai-link-2026`，用户可进面板重设。
- **新增：LuCI 专用桥接令牌 `luci_bridge_token`**
  与面板密码完全解耦的 32 位随机串，仅用于 LuCI 页面调用面板 API；改面板密码不会影响它，它也不能用来登录面板。
- **加固：`ai-link password` 成功后不再回显明文密码**，只提示字符数。

### ⬆️ 在线更新体系（新功能）

- **LuCI 概览页新增「插件版本与在线更新」卡片**：显示当前版本、检查更新、立即更新、进度条与实时日志、更新说明入口。
- **独立控制面板新增同款卡片**，位于「核心规则库与订阅更新」上方。
- **新增 CLI 命令**：
  - `ai-link update` —— 只检查是否有新版本
  - `ai-link update --apply` —— 检查并直接在线升级（带实时进度输出）
- **新增 API 端点**：
  | 方法 | 路径 | 说明 |
  |---|---|---|
  | GET | `/api/system/version` | 当前版本、构建号、清单源列表 |
  | GET | `/api/system/update/check` | 拉取版本清单并比较（`?force=1` 跳过 5 分钟缓存） |
  | GET | `/api/system/update/status` | 升级进度与最近日志 |
  | POST | `/api/system/update/apply` | 启动升级 |
  | POST | `/api/system/update/ack` | 清除已完成的升级结果 |
- **升级流程（八步，全程可观测）**：
  1. 拉取 `version.json`（Cloudflare Pages 主源 → gh_mirror 镜像 → GitHub raw 直连，自动重试）
  2. 下载升级包（清单内多个下载源依次重试）
  3. **校验包大小 + MD5 + SHA256**，任一不符立即中止，绝不执行未校验的包
  4. 解压并校验包结构（必须含 `install.sh` 与 `root/`）
  5. 备份用户配置到 `/root/ai-link-final-backup/pre-update-v{版本}-{时间戳}.tgz`（自动保留最近 3 份）；空间充足时额外备份旧代码用于回滚
  6. 执行 `install.sh --upgrade`（保留用户配置与已装附加组件）
  7. 重启服务并做健康检查（最多 10 次轮询 `/api/status`）
  8. 健康检查失败 → **自动回滚**用户配置与旧代码，并再次验证
- **升级进程与 daemon 解耦**：升级脚本用 `setsid` 脱离 daemon 会话，`install.sh` 重启服务不会把它杀掉；进度落盘到 `/var/run/ai-link/update/progress.log`，重启后新 daemon 接着读，用户能看到完整结果。
- **安全护栏**：清单缺少 MD5 时直接拒绝升级；同一时间只允许一个升级任务；升级中重复点击会被拒绝。

### 🛠 安装脚本

- 新增 `install.sh --upgrade` 升级模式：
  - 不再停止/禁用其他代理服务（避免误伤用户后装的组件）
  - **不再删除音乐解锁组件**（原安装流程会 `rm -rf` 掉，升级时会造成"静默卸载"）
  - 其余流程保持幂等，用户配置与 UCI 设置全部保留

### 📦 版本号统一

- 全量版本号由 `1.0.0` 升至 `1.0.1`，统一来源为 daemon 内的 `APP_VERSION` 常量；启动时同步写入 `ai-link.global.app_version` 供 LuCI / CLI / 面板读取。
- `/etc/ai-link/version` 更新为 `1.0.1 (20261026)`。

### ✅ 验证

- 面板密码缺陷 A/B 对照：补丁前「哈希当密码 ✓ / 哈希当令牌 ✓ / auth 丢失后哈希可登 ✓」→ 补丁后三项全部拒绝，真实密码与真实令牌未回归。
- 静态门禁：`py_compile` ✓、`node --check` ✓、`bash -n`（install.sh / usr/bin/ai-link / 生成的升级脚本）✓、symtable 未定义符号 0 ✓、HTML div 配平 0 ✓。
- OTA 版本比较 7 条用例全通过（含 `v` 前缀、预发布版语义）。

---

## v1.0.0 · 2026-10-25

> 首个正式版

- 纯血 Sing-box 单内核架构（移除 mihomo 遗留路径）
- 五种分流模式：`shunt` / `gfw_list` / `global` / `direct` / `homelink`
- 智能双栈 DNS（:7874 上游 + 海外 AAAA 剥离 + 国内原生 IPv6）
- 国内 IP 硬件级入口直连（Entry Bypass）+ 旁路由对称 NAT 断流保护
- 回家节点（VLESS-Reality / Hysteria2）
- 净网黑洞拦截、DNS 重写与过滤库
- 独立全功能控制面板（:9099）+ LuCI 概览页
- 一键恢复出厂、备份归档与恢复、彻底卸载
- 跨平台安装：x86_64 / aarch64 / armv7 / mipsel / riscv64，opkg + apk 双栈
