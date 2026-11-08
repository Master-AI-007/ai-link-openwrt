# AI-LINK v2.5.3

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-09 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：交付质量收口，测试集真正自包含

### 📦 交接包可以"开箱即测"

此前几轮虽然把测试脚本打进了包，但 `tests/subscription_formats/` 那批订阅格式样本一直没进去，导致解压后直接跑 `run_all` 会缺文件。本版把 **12 个夹具全量随包**（`clash-simple/block/nested-flow/anchor.yaml`、`uri-list.txt`、`base64-uri.txt`、`singbox.json`、`surge.txt`、`loon.txt`、`sip008.json`、`v2ray-json.json`、`EXPECTED.md`），tar 达到 84 条目 / 56 文件。

**验证方式**：出包后解压到全新目录、**零外部补发**直接 `python3 tests/run_all.py` → **15/15 全通过**。门禁也加了 `fixtures=12` 与"原始包零补发解压"两项检查。

### 🔍 指纹与自检机制化

- 产物定稿后统一计算并注入四列指纹（字节数 / MD5 / SHA-256），单文件也不再出现"差 1 字节"；
- `daemon --self-test` 的全部检查改到独立临时沙箱，测试套件之间不再互相污染；
- `run_all.py` 首个套件前先等 `/api/status` 连续两次 200，避免"刚重启就开跑"造成的假失败。

### 🧩 功能延续

节点池严格遵循勾选的订阅源与地区（补位/巡检/保存/前端向导六层）、WAN 闪断防团灭、评估引擎实时范围守卫、多线并发 `urltest` 出口与 0.5 秒错峰轮转、概览双栏等高与波形均值线，全部延续。

### ✅ 稳定性

安装真实退出码 0、`nft=1`、重启后仍稳定；Design Lint 18/18、发布门禁 17/17、官方回归 **15/15 套全绿**。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x ~ 2.5.2 直升，配置、节点、订阅、节点池全部保留，失败自动回滚。

---

## 已知限制

- 订阅为网页/HTML 或 Token 失效时无法解析，需要更新链接；
- 500+ 节点规模下 `quick_create` 首次约 1 秒；
- 面板默认仅信任本机回环，需从局域网其他设备访问时请自行配置令牌或可信网段。

---

## 包指纹

```
AI-LINK-v2.5.3.tar.gz   949,934 B
md5     4864bc1c376ecf82d8ae1b8b359cb233
sha256  8991b2cb1fde59e6f5d159be3281ccd1dca7386cfcae2cf00b968ff575a53057
```
