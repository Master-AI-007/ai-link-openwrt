# AI-LINK v2.4.8

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-08 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：把上一轮的 P0 和 5 项遗留一次性闭环

### 🔥 P0 根治：nftables 协议族拆分

v2.4.7 的 `ai-link.nft` 在单条规则里混用 `ip daddr` 与 `ip6 daddr`，nftables 报
`conflicting network layer protocols specified: ip vs. ip6`，导致整张表挂不上、安装 `exit 1`、透明代理完全失效。

v2.4.8 在 `generate_nft_rules_file()` 中把该规则拆成 **6 条独立规则**，显式用
`meta nfproto ipv4` / `meta nfproto ipv6` 区分协议族（含 `meta mark`、`ct mark`、`accept`）。
真机验证：安装真实退出码 `0`、`svc_state nft=1`、`nft_apply_status ok:true`、
生成的规则中协议混写行清零，**重启服务后仍 `nft=1` 且出网 204**。

同时在 `install.sh` 里加了挂载失败诊断（输出 `nft_apply_status.json` 与 `nft -c -f` 前 10 行），
并在发布门禁新增「nft 协议混写清零」静态检查，防止复发。

### ✅ 其余 5 项闭环

- **P2-6 · T10 按组专属 DNS**：`/api/shunt/update` 兼容 `id` / `group_id`，变更时强制 `write_all_configs`；
  所有非 `inherit` 的 `dns_strategy` 都注册 `dns_grp_<ID>` 到 `dns.servers`，域名型上游自动附加 `domain_resolver: "dns_direct"`。
  真机实测 `doh` 与 `custom` 均生成 `dns_grp_AI`，`sing-box check` 退出码 0；
- **P3-5 · 流量透视器**：三种内联语法（`10.10.10.58 -> chatgpt.com:443`、
  `AA-BB-CC-DD-EE-77 -> www.youtube.com`、`chatgpt.com @10.10.10.58`）均完整回显
  `raw_input / target / src_ip / src_mac`；
- **P2-7 · 测试沙箱隔离**：`is_live` 判定收敛，沙箱测试不再读取真机 `/etc/config/ai-link`；
- **P3-4 · 异常吞没**：AST 扫描 `except->pass` 由 11 降为 **0**，并写入门禁；
- **P2-4 · 测试集**：`v242_deep_chaos_simulation.py` 本轮单独交付，官方回归 **15/15 套全绿**（混沌 29/29、`rule_blocks` 15/15、`test_v102` 149/149）。

### 🧪 功能延续

DNS 三大开关防轮询竞态闪烁、T6 配置变更历史纯净 Diff 与一键回滚 UCI/内核同步、
T8 规则块域名 Fake-IP 提权、HomeLink 端口动态保留与越界校验、多线并发、
链式代理 4 层 DAG、三维流量归因洞察、内核日志秒级故障切换。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x / 2.1.x / 2.2.x / 2.3.x / 2.4.x 直升，配置、节点、订阅、节点池全部保留，失败自动回滚。
**使用 v2.4.3 的设备可直接通过 OTA 升级到 2.4.8**；中间 2.4.4~2.4.7 未对外发布。

---

## 已知限制

- 订阅为网页/HTML 或 Token 失效时无法解析，需要更新链接；
- 500+ 节点规模下 `quick_create` 首次约 1 秒；
- 面板默认仅信任本机回环，需从局域网其他设备访问时请自行配置令牌或可信网段。

---

## 包指纹

```
AI-LINK-v2.4.8.tar.gz   792,585 B
md5     128af9bc4304fd6cc3e46ba684e3a9d8
sha256  e22a062c59fcf28b9f6ff1c8492ece3d1951e44031339cea66b37ce5eded4f1d
```
