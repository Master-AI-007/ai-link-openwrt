# AI-LINK v2.5.13

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-11 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：把云端规则集真正用起来

之前的在线 GeoIP / Geosite 列表只是被动下载，分流组无法显式绑定，纯 IP 流量（Telegram MTProto 直连 IP、Netflix OCA、Discord 语音 UDP、Steam CDN）容易漏进兜底组。这版做了一次分流能力重构。

### 🌐 云端 GeoIP / Geosite 双轨引擎

内置 **26 个云端规则集**（8 个 GeoIP ASN/国家库 + 18 个高频 Geosite 应用库），覆盖 Telegram `AS62041`、Netflix `AS2906`、Google `AS15169`、Cloudflare `AS13335`、Fastly `AS54113`、OpenAI 与 CN 等核心网段。每个分流组可原生挂载 `geosite_sets`、`geoip_sets` 与 `rule_providers`，自动编译进内核 `route.rules` / `route.rule_set`；4 阶流量透视器现在能识别纯 IP 所属的 ASN/GeoIP 规则集。

真机抽验：内核 `route.rule_set` 11 个（10 个 geoip/geosite 集合）、`route.rules` 52 条，AI 分流组已挂载 5 个 Geosite + 1 个 GeoIP 集合。

### 📦 一键场景分流包

面向真实使用场景内置 6 个组合包，逐个查 URL、手填标签的时代结束了：

| 场景 | 内容 |
| :--- | :--- |
| AI 全家桶防封锁 | OpenAI / Claude / Cursor / Perplexity 域名 + `geoip-openai` 锁定 AI 组 |
| Telegram 极速防失联 | `geosite-telegram` + `geoip-telegram` AS62041 双轨接管 |
| 4K 流媒体全解锁 | Netflix / Disney+ / Spotify + `geoip-netflix` |
| 开发者与云原生 | GitHub / Docker / NPM / PyPI / HuggingFace |
| 主机与 Steam 联机 | 下载 CDN 直连、社区商店走代理 |
| Google 全家桶与 FCM 保活 | 含 5228–5230 端口与 `geoip-google` |

一键下发后支持 **8 秒撤销**，误操作可立即回退。

### 📡 实时流量归组雷达

新增「实时流量归组」标签页：扫描当前连接与最近访问流，按 eTLD+1 域名或 `/24` IP 聚合未细分流量，智能推荐归属组与云端 `.srs` 集合，支持单行「一键归入推荐组」（自动写入后缀/精确域名/IP 段或绑定云端集合），同样带 8 秒撤销。真机抽验接口返回 12 条实时未归类流量。

### 🛠 配置体验与状态契约

- 组合规则弹窗升级为**多块编辑**（`#1..#N` 增删），「立即试匹配」可读未保存草稿并给出三态反馈（草稿命中 / 现有命中 / 兜底未命中），空输入与兜底不再误判命中；
- 分流卡片完整编辑并保留 `exact_domains`、`ports`、`source_ip_cidrs` 与云端规则集芯片，保存不再丢高阶字段；
- 新增 `/api/status/schema` 与 `lite_fields` 显式契约、`state_seq` / `config_seq` 序列号，lite 心跳改为深度合并、配置或状态变化时自动拉全量；
- 候选节点 `node_tags` 10/10 零截断，卡片动态显示真实驻留周期（不再硬编码「每 30 秒轮换」）；同区亲和只剩 1 个成员时提供一键「关闭同区锁定」恢复多线轮换。

### ✅ 验证

真机原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 `87/87`、发布门禁双布局 `17/17`、Design Lint `18/18`、静态资源 `8/8`、11 行指纹逐行校验（改 1 字节即转红）；自检生产态 10 连跑通过且负向泄露检出有效；安装退出码 0、`nft=1`、重启后稳定；UI 零异常、三视口零溢出。

真机三口径实测：默认状态 **64,231 B**（含完整域名与云端规则集）、`?lite=1` **8,444 B**、`?include=full` 171,094 B、gzip 传输 17,619 B；ETag / `If-None-Match` 正常 304。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x ~ 2.5.12 直升，配置、节点、订阅、节点池全部保留，失败自动回滚。本次为正常升版，现网设备会收到 OTA 提示。

---

## 已知限制

- 订阅为网页/HTML 或 Token 失效时无法解析，需要更新链接；
- 500+ 节点规模下 `quick_create` 首次约 1 秒；
- 面板默认仅信任本机回环，需从局域网其他设备访问时请自行配置令牌或可信网段；
- 多出口轮询为实验特性，不叠加单流带宽；开启同区亲和且某池只有 1 个同地区节点时表现为单出口，可在池菜单一键关闭同区锁定；
- 云端规则集随分流组挂载增多，状态载荷会相应增大（真机默认约 64 KB、gzip 约 17 KB），大规模环境建议启用 gzip 与 ETag 缓存；
- 安装完成后的 1~2 分钟内出网探测可能短暂失败，服务收敛后自动恢复。

---

## 包指纹

```
AI-LINK-v2.5.13.tar.gz   1,084,841 B
md5     203426316856269f0412053010415db2
sha256  e28a7164994112ff71904c483b3ad5d87f86c8f26d730a39ac9984859e3f54de
```
