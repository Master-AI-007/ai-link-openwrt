# AI-LINK v1.0.2

> OpenWrt 下一代「永不断连」智能透明代理 · 异地组网回家 · DNS 净网护盾
> 发布日期：2026-10-26 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）
> 安装包：`AI-LINK-v1.0.2.tar.gz`（`1,242,745 B` · MD5 `d64f77afa6547f69c9d97ee02942a3e3` · SHA256 `a8a796355b82f29436ede2fc4ce706cec4fcca7844207753bb05849225231230`）

---

## 本版主题

**全量安全加固 + 启动与看门狗防黑洞 + `.tgz` 归档上传恢复 + 跨架构兼容。**
本版本完整合并了 v1.0.2 RC 的安全/启动/回滚修复（A 节）与 `KNOWN-ISSUES.md` B 节全部 20 项改进，并将包内 7 处版本标识统一对齐为 `1.0.2`。

---

## 🔐 安全加固（SEC-1~SEC-5 & B1-1~B1-4）

1. **面板令牌不再随首页下发（SEC-1）**：仅在 `POST /api/login` 校验密码通过后签发令牌，杜绝未登录客户端访问首页即获取有效令牌。
2. **接口鉴权与敏感数据脱敏闭环（SEC-2~SEC-5）**：`/api/status` 对未授权客户端脱敏回家节点 `password`/`uuid`/`private_key`/`uri` 及订阅 `token=`，并将鉴权状态与 `panel_auth.json` 纳入缓存键；`GET /api/nodes/share_uri` 与 `GET /api/ops/logs` 强制校验 `_auth_ok()`（未授权返回 401）。
3. **UCI 凭据零留存（B1-2）**：`/etc/config/ai-link` 移除 `panel_secret`，改用布尔 `option panel_pwd_customized '0/1'`，升级时自动迁移并清除历史 `panel_secret`，CLI `ai-link password` 不再向 UCI 写明文或哈希。
4. **永久下线弱默认密码 `admin`（B1-3）**：出厂状态仅接受 `ai-link-2026`，登录框移除预填明文 value。
5. **内网免密风险提示与自动登录引导（B1-1）**：未鉴权打开面板自动弹出登录窗；WebUI 设置页新增 `#lan-auth-security-notice` 风险提示；LuCI 新增 `require_lan_auth` 开关并与 `ops_settings.json` 双向同步。

---

## 🚀 启动可靠性与看门狗防黑洞（BOOT-1 / CORE-1 / RB-1 / B1-4 / B3-12）

1. **多栈端口就绪探针（BOOT-1 & B3-12）**：`init.d/ai-link` 采用 `netstat` → `ss` → `/proc/net/tcp{,6}` 探针，同时兼容无 `toupper()` 的精简版 BusyBox `awk`，等待预算放宽至 60 秒。
2. **BusyBox `pgrep` 兼容（CORE-1 & B3-12）**：统一使用 `singbox_alive()`（`pidof sing-box` 探针）与 `pgrep -f "ai-link-dae[m]on.py"`。
3. **看门狗与 `restore_proxy` 端口前置校验（B1-4）**：挂载 `table inet ai_link` 前强制验证 `:7893` 端口监听，防止核心未就绪时造成局域网黑洞。
4. **回滚收尾立即恢复代理（RB-1）**：OTA 回滚段重启后立即执行 `/etc/init.d/ai-link restore_proxy`，消除 10 秒空窗。

---

## 📦 备份恢复与在线更新增强（B2-6 ~ B2-11）

1. **浏览器直接上传 `.tgz` / `.json` 恢复与 `.tgz` 导出（B2-6）**：面板与 LuCI 均支持上传 `.tgz`/`.tar.gz` 归档或 `.json` 备份直接恢复，并支持一键导出 `.tgz` 归档（内置路径穿越、非普通文件与 100MB 体积安全校验，且不覆盖当前版本标识）。
2. **新增 `ai-link restore <file|--latest>` CLI 命令（B2-7）**：支持命令行直接恢复 `.tgz` 或 `.json` 备份并自动重载服务。
3. **OTA 升级进度闪存持久化（B2-8）**：升级日志双写至 `/root/ai-link-final-backup/last_update_progress.log`，断电重启后自动恢复中断状态。
4. **`auto_nodes.json` 静态哈希恒定（B2-9）**：落盘剥离实时探测噪声，跨探测周期 MD5 100% 稳定。
5. **自定义更新源域名与冷启动说明（B2-10 & B2-11）**：支持 `update_manifest_url` 自定义域名清单源，并与 UCI 删除/修改双向同步。

---

## ⬆️ 升级与重编号刷回说明

```sh
# 1. 已安装 v1.0.1 的设备直接在线升级
ai-link update --apply
# 或一键升级脚本
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh

# 2. 若测试机此前安装过构建代号为 1.0.3 的测试包，请解压本包执行一次 --upgrade 刷回正式 1.0.2：
tar -xzf AI-LINK-v1.0.2.tar.gz && sh ai-link-openwrt/install.sh --upgrade
```
