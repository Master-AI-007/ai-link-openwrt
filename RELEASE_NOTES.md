# AI-LINK v1.0.2

> OpenWrt 下一代「永不断连」智能透明代理 · 异地组网回家 · DNS 净网护盾
> 发布日期：2026-10-26 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 本版主题

**安全加固 + 启动可靠性修复。** 这一版不加新功能，只把 v1.0.1 暴露出来的三处硬伤修掉：
面板令牌可以被未登录拿到、状态接口把节点凭据一并吐出来、以及每次启动都要等 25 秒才挂 nftables。

---

## 🔐 安全修复

### 1. 面板令牌不再随首页下发（严重）

旧实现会给任何请求 `/` 的客户端塞一个 `Set-Cookie: ailink_token=<有效令牌>`。
**未登录、零凭据，打开一次面板地址就有令牌**，之后可以调用全部 API；
即使打开「强制内网登录」也绕得过去，面板一旦被端口转发到公网就等同远程接管。

现在：令牌只由 `POST /api/login` 校验密码后签发，客户端自己保存。

### 2. `/api/status` 对未授权客户端脱敏

以前该接口会把回家节点的 `password` / `uuid` / `private_key` / `uri`
和订阅地址（含 `?token=`）一并返回。现在按访问控制同一口径判断，
未放行即脱敏；鉴权状态也纳入缓存键，避免已鉴权客户端的完整应答被后续请求复用。

### 3. 回家节点脱敏覆盖 `uri`

`mask_all_secrets` 以前只遮字段，`uri` 里内嵌的明文密码/UUID 仍然裸露，现在一并处理。

---

## 🚀 启动可靠性

### 4. 修复 `ss` 探针不存在

`init.d` 的端口就绪探针只用 `ss`，而 ImmortalWrt 25.x 默认不带 `ss`（`ash: ss: not found`）。
结果每次启动都等满 25 秒、打印「TProxy port not listening」并跳过 nftables 挂载，
只靠看门狗事后补挂。现在改用 `netstat` 为主、`ss` 与 `/proc/net/tcp` 兜底，预算放宽到 60 秒。

### 5. 修复 BusyBox `pgrep -x` 失效

BusyBox 1.37 的 `pgrep -x sing-box` 匹配不到 `/usr/bin/sing-box`，导致
`svc_state` 恒报 `core=0`、每次 reload 退化成整机重启、`restore_proxy` 误判核心没起来。
统一换成 `pidof` 探针。

---

## ♻️ 升级回滚

### 6. 回滚收尾立即重挂透明代理

回滚后不再等 10 秒自愈，立即 `restore_proxy`，避免「面板正常但流量不走代理」的空窗。

---

## ⬆️ 升级方式

```sh
# 设备上直接升级
ai-link update --apply

# 或者一键脚本（会自动识别已安装并升级）
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

升级失败会自动回滚到升级前版本，配置与节点数据不受影响。

---

## 📌 已知限制

- 面板默认信任局域网（`require_lan_auth=false`）。若面板端口可能暴露到公网，
  请开启「强制内网登录」，或把 `trusted_cidr` 收窄到管理网段。
- v1.0.0 用户仍需手动升级一次（v1.0.0 没有 OTA 模块）。

---

## 包指纹

见 `version.json`（`packages.full.md5` / `sha256` / `size`）。
