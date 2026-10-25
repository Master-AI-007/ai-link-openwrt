# AI-LINK v1.0.1

> OpenWrt 下一代「永不断连」智能透明代理 · 异地组网回家 · DNS 净网护盾
> 发布日期：2026-10-26 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 本版主题

**服务总开关 + 在线更新体系 + 面板密码安全修复。**

v1.0.1 是**第一个支持在线一键升级的版本**。从这一版起，插件可以自己检查新版本、自己下载、自己校验、自己升级、失败自动回滚。

---

## ⚙️ 服务总开关（新功能）

### 解决了什么问题

v1.0.0 有一个隐藏死锁：一旦服务被停掉（`/etc/init.d/ai-link stop`），
LuCI 概览页上**所有按钮全部失效**——因为它们都去调 `:9099` 的 API，而面板已经没了。
而「启用 AI-LINK 透明代理服务」那个勾选框只管**流量接管**、不管**进程启停**，
用户勾了也没用，只能 SSH 进去手动 `start`。

### 现在怎么做

LuCI 概览页顶部新增独立的「⚙️ 服务总开关」卡片：

| 能力 | 说明 |
|---|---|
| 状态徽章 | `● 运行中` / `◐ 部分运行（内核未起）` / `⏹ 已停止` |
| 元信息 | 开机自启 · 透明代理接管 · nftables 挂载 · 面板端口 |
| 四个按钮 | **▶ 启动服务** / **⏹ 停止服务** / **🔄 重启服务** / **🔁 开机自启开关** |
| 自动刷新 | 每 5 秒同步一次真实状态 |

**关键设计：这条通路不依赖 `:9099`。**
它走 LuCI 自己的 `fs.exec` → `/etc/init.d/ai-link svc_state|start|stop|restart`，
所以**即使守护进程已经停了，也能在网页上一键把它拉起来**，完全不需要 SSH。

### 语义澄清

| 开关 | 管什么 |
|---|---|
| ⚙️ **服务总开关**（新增） | 进程生命周期：启动 / 停止 / 重启 / 开机自启 |
| ☑️ 启用 AI-LINK 透明代理服务（原有） | 是否接管流量（nftables / dnsmasq / sing-box） |

两者独立：`enabled=0` 时设计上面板仍在线，只是不接管流量。

### 其他改动

- **`reload_service()` 兜底**：`enabled=1` 时若 daemon 或 sing-box 任一未运行，直接整体 `start`
- **新增 init 动作 `svc_state`**：输出单行 `daemon= core= nft= enabled= boot= bypass= port=`，供前端统一解析
- **独立面板同步**：设置页新增服务状态卡片 + 「🔄 重启服务」按钮，5 秒自动刷新

---

## 🔐 安全修复（建议所有 v1.0.0 用户升级）

| 编号 | 问题 | 说明 |
|---|---|---|
| PWD-1 | LuCI「面板密码」显示为 `sha256:xxxx` 哈希 | 改密后 UCI 字段被写入哈希，LuCI 直接把它当密码显示 |
| PWD-2 | **安装自检会污染生产环境密码字段** | `--self-test` 用临时目录跑改密回归，但函数体无条件 `uci set`，导致每次安装自检 / `ai-link probe` 都把真实 `panel_secret` 覆盖成测试串的哈希 |
| PWD-3 | 哈希串可直接当密码登录 | `candidate_pw == get_uci_panel_secret()` 旁路已移除 |
| PWD-4 | **哈希串可直接当 Bearer 令牌绕过登录** | `tok == get_uci_panel_secret()` 旁路已移除，令牌只认签发过的值 |
| PWD-5 | 认证文件丢失后用户被锁死 | 旧逻辑用哈希当初始密码重建，真密码失效；现回退默认密码供救急 |

**新增 LuCI 专用桥接令牌** `luci_bridge_token`：与面板密码完全解耦的 32 位随机串，仅用于 LuCI 页面调用面板 API。改面板密码不影响它，它也不能用来登录面板。

---

## ⬆️ 在线更新体系（新功能）

### 使用方式

| 入口 | 操作 |
|---|---|
| **LuCI** 服务 → AI-LINK → 概览页 | 「插件版本与在线更新」卡片 → 检查更新 → 立即更新 |
| **独立面板** :9099 → 设置 | 同款卡片，位于「核心库与订阅更新」上方 |
| **SSH 命令行** | `ai-link update`（只检查）／`ai-link update --apply`（检查并升级） |

### 升级流程（八步）

1. 拉取 `version.json` —— Cloudflare Pages 主源 → `gh_mirror` 加速镜像 → GitHub raw 直连，自动重试
2. 下载升级包 —— 清单内多源依次重试
3. **校验大小 + MD5 + SHA256** —— 任一不符立即中止，绝不执行未校验的包
4. 解压并校验包结构
5. 备份用户配置到 `/root/ai-link-final-backup/pre-update-v{版本}-{时间戳}.tgz`（自动保留最近 3 份）；空间充足时额外备份旧代码
6. 执行 `install.sh --upgrade`
7. 重启服务并做健康检查
8. 健康检查失败 → **自动回滚**并再次验证

### 工程要点

- **升级进程与主服务解耦**：升级脚本用 `setsid` 脱离 daemon 会话，安装脚本重启服务不会把它杀掉；进度实时落盘，重启后新进程接着读，因此用户能看到完整结果，而不是"页面转圈然后失联"。
- **安全护栏**：清单缺 MD5 直接拒绝升级；同一时间只允许一个升级任务；升级中重复点击被拒绝。
- **代理环境变量免疫**：清单与升级包请求显式绕过 `http_proxy`/`https_proxy`，避免路由器上残留的代理变量把 OTA 误判成"清单不可达"。

### 新增 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/system/version` | 当前版本、构建号、清单源列表 |
| GET | `/api/system/update/check` | 拉取清单并比较版本（`?force=1` 跳过 5 分钟缓存） |
| GET | `/api/system/update/status` | 升级进度与最近日志 |
| POST | `/api/system/update/apply` | 启动升级 |
| POST | `/api/system/update/ack` | 清除已完成的升级结果 |

---

## 🛠 安装脚本

- 新增 `install.sh --upgrade` 升级模式：
  - 不再停止/禁用其他代理服务（避免误伤用户后装的组件）
  - **不再删除音乐解锁组件**（原安装流程会 `rm -rf` 掉，在线升级时会造成"静默卸载"）
  - 其余流程保持幂等，用户配置与 UCI 设置全部保留

---

## 📦 下载

| 文件 | 大小 | MD5 |
|---|---:|---|
| `AI-LINK-v1.0.1.tar.gz` | 1,196,610 B | `5582bd0f9eb49105d38813036cb6ca66` |
| `version.json` | 2,083 B | 见文件内 `sha256` 字段 |
| `CHANGELOG.md` | 7,459 B | — |

SHA256：`49eb2322b5328cbd4b784253de2130123070493c4f44f1058331984a03ee54e8`

> 校验：`md5sum AI-LINK-v1.0.1.tar.gz` 应等于上表值。

---

## 安装 / 升级

### v1.0.0 用户（需手动升级一次）

v1.0.0 尚未内置在线更新模块，请手动执行一次：

```sh
curl -fsSL https://ai-link-official.pages.dev/install.sh | sh
```

### v1.0.1 及以后（在线一键）

```sh
ai-link update --apply
```

或在面板 / LuCI 点「立即更新」。

### 全新安装

```sh
curl -fsSL https://ai-link-official.pages.dev/install.sh | sh
```

国内网络强制走加速镜像：

```sh
curl -fsSL https://ai-link-official.pages.dev/install.sh | AI_LINK_MIRROR=https://ghfast.top/https://github.com/Master-AI-007/ai-link-openwrt/releases/download/v1.0.1 sh
```

### 手动安装

```sh
tar -xzf AI-LINK-v1.0.1.tar.gz
cd ai-link-openwrt
sh install.sh
```

安装完成后访问 `http://<路由器IP>:9099`（独立面板）或 LuCI → 服务 → AI-LINK 智能代理。

**卸载**：

```sh
ai-link uninstall -y             # 彻底卸载（自动归档 /etc/ai-link）
ai-link uninstall --keep-config  # 保留配置卸载
```

---

## 验收状态

| 项 | 结果 |
|---|---|
| 发布门禁（13 项） | **13 / 13 PASS** |
| OTA 端到端测试（19 项） | **19 / 19 PASS** |
| 面板密码缺陷 A/B 对照 | 3 条漏洞全部堵死，真密码/真令牌/默认密码救急未回归 |
| 静态门禁 | `py_compile` ✓ · `node --check` ✓ · `bash -n` ✓ · symtable 未定义 0 ✓ |
| HTML 标签配平 | overview.js `34/34` · index.html `842/842` |
| 面板内联脚本语法 | 4 块全部通过 |
| 版本一致性 | daemon / install.sh / version 文件 / 面板徽章 四处一致 |

---

## 已知问题

1. **v1.0.0 → v1.0.1 必须手动升级一次**（v1.0.0 没有 OTA 模块）。
2. 面板与 LuCI 的升级进度在服务重启瞬间会短暂断连，属正常现象，2 秒轮询会自动恢复。
3. `auto_nodes.json` 含实时探测数据，daemon 运行时会持续重写，**不适合作为备份一致性比对项**。

---

## 反馈

- 问题与建议：本仓库 Issues
- 更新日志：<https://ai-link-official.pages.dev/changelog.html>
- 版本清单：<https://ai-link-official.pages.dev/version.json>
