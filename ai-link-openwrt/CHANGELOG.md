# AI-LINK 更新日志

本文件记录 AI-LINK 智能分流网关的全部版本变更。
在线更新客户端读取的机器可读清单是 `version.json`，本文件是面向人的详细说明。

版本号规则：`主版本.次版本.修订号`
- 主版本：架构级变更（如内核切换、配置模型重构）
- 次版本：新增功能，向后兼容
- 修订号：缺陷修复与安全补丁，向后兼容

---

## v1.0.1 · 2026-10-26

> 主题：**在线更新体系 + 面板密码安全修复**

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
