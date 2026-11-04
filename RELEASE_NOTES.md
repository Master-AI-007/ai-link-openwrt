# AI-LINK v2.4.0

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-05 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：三模数据面，自己选

### 🧭 受控三模

| 模式 | 适用 | 行为 |
|---|---|---|
| `tproxy_redirect`（默认）| 绝大多数旁路由 / 主路由 | LAN 海外 TCP/UDP 走 TProxy :7893，本机 TCP 走 Redirect :7891 |
| `tproxy_tcp_tun_udp` | 游戏 / 需要完整 UDP 与 ICMP | TCP 仍走 TProxy，海外 UDP 与 Fake-IP ICMP 打标注入 `ailink0` |
| `tun_full` | 全量接管 | 海外 TCP/UDP/ICMP 全走 TUN；大陆 IP 与国服游戏端口顶层直通 |

切换即时生效，可在「设置与诊断 → 数据面」里选；切回默认不需要重装。

### 📱 移动端与平板 Hero

- 430px / 375px：文案区满宽、3 项指标单排、操作按钮两列铺满、零横向溢出；
- 768px：顶栏 `.global-route` 单行不折行，横幅高度收敛；
- 桌面端仍是六页统一单横幅。

### ⚙️ 内核安全热升级

升级 sing-box 内核时不再中断现有分流与回家隧道。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从 2.0.x / 2.1.x / 2.2.x / 2.3.x / 2.4.x 直升，配置、节点、订阅、节点池全部保留，失败自动回滚。

---

## 已知限制

- 订阅为网页/HTML 或 Token 失效时无法解析，需要更新链接；
- 594 节点规模下 `quick_create` 首次约 1 秒；
- 面板默认信任局域网，公网暴露请开启强制登录。

---

## 包指纹

```
AI-LINK-v2.4.0.tar.gz   736,184 B
md5     15928d926ac2202bc42a3bbabd654d13
sha256  87dabb0e2a38cdcdcbef3059f90d15f85579ee59186b2fc3b64ea36bdcf9b3a9
```
