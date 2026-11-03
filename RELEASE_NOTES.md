# AI-LINK v2.3.6

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-03 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版的重点：订阅不再挑格式，手动不再偷偷换节点

### 📥 订阅自适应（11 种格式）

| 格式 | 支持 |
|---|---|
| Clash / Mihomo YAML | 单行 flow、多行块式、嵌套 flow、锚点与 merge |
| 明文 URI 列表 | vless / vmess / ss / trojan / hysteria2 / tuic / anytls |
| Base64 订阅 | 标准 / URL-safe / 无填充 |
| sing-box JSON | `outbounds[]` |
| Surge / Loon / Quantumult X | `[Proxy]` INI 段 |
| SIP008 | Shadowsocks JSON |
| V2Ray / v2rayN JSON | `outbounds[].settings.vnext` |

配套修复：

- **拉取**：`curl -4` 优先；`--resolve` 绑定的 IP 不通时自动去掉 pin 重试；
- **诊断**：HTTP 200 但没解析出节点时，会区分「Token 失效」「返回网页」「格式不支持」，并把原文写入 `/tmp/ai-link-sub-*.raw`。

### 🖐️ 手动即固定

- 分流组、非分流模式（白名单 / GFW / 全局）中手动选定的节点**不可用也保持固定**并给出提示；
- 需要自动容灾的场景，请改用自动节点池；
- 节点池新建默认「仅 URL Ping」，服务检测按需开启；「任一通过」不再被 AI 地区封锁一票否决。

### 🧩 极简节点池（延续 2.3.5）

创建 → 勾订阅来源（含自定义）→ 勾地区 → 是否服务检测 → 勾服务 → 数量 1-10 → 低健康复选阈值 → 开始自动选取（进度条）。
日常只做 URL Ping 切换；建池与低水位复选才做真实服务访问验证。

### 🖥 窄屏与设计

- 1188px 下节点表格零横向滚动，操作列完整可见；
- 960px 以下自动切换卡片式列表；
- 移动端顶栏不再把「精细规则分流」截断。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x / 2.1.x / 2.2.x / 2.3.x 直升，配置、节点、订阅与节点池全部保留，失败自动回滚。

---

## 已知限制

- 订阅是网页/HTML 或 Token 失效时无法解析，请更新链接；
- 594 节点规模下 `quick_create` 首次约 1 秒（亚秒~一秒级）；
- 面板默认信任局域网，公网暴露请开启强制登录并修改密码。

---

## 包指纹

```
AI-LINK-v2.3.6.tar.gz   707,839 B
md5     a90b9f50aab299ba5aa12874f0ea6689
sha256  e62a4a90b443c7d6478a2fac8fa5043c524a0400afad9f4221690ba4368909da
```
