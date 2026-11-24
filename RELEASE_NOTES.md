# AI-LINK v2.8.5 正式发布说明

`v2.8.5 (r62)` 在 `v2.8.4` 稳定线上基准（Release #456402031 / `2300461`）基础上，完成 OPT-285-11 ~ OPT-285-20 10 项全栈增强、深度网络冲突排查与防回归质量门禁闭环：

### 核心特性与架构增强
- **ai_link_v2_8_5.md 同步对齐单份 tests/ 与 13 夹具交接包规范布局（OPT-285-11）**：规范交接包测试夹具布局，消除冗余测试目录；
- **nexus.js autoFixShuntShadowingOrder() 分流遮蔽一键重排生效（OPT-285-12）**：前端控制台支持一键自动修复分流规则拓扑遮蔽顺序；
- **ailink_diag.py check_dnsmasq_doh_port_conflict() DNS/DoH 端口冲突自检（OPT-285-13）**：网络医生深度探测本地 dnsmasq 与 DoH 监听端口占用冲突；
- **ailink_diag.py demote_l7_failed_node_weight() L7 瞬时失败降权防误剔除（OPT-285-14）**：L7 握手瞬态失败采取优雅降权而非立即剔除，避免节点震荡；
- **ailink_diag.py verify_homelink_key_permissions() 密钥 0600 权限校验（OPT-285-15）**：强化 HomeLink 密钥安全性，校验文件权限为严格 0600；
- **ailink_diag.py verify_srs_and_cache_integrity() .srs/缓存完整性头校验（OPT-285-16）**：验证预编译规则集与本地缓存头部完整性；
- **ailink_diag.py get_ipv6_mss_clamp_recommendation() PPPoE 双栈 IPv6 MSS 联动（OPT-285-17）**：智能推导双栈环境下的最优 IPv6 MSS 钳制值；
- **ailink_diag.py format_init_status_summary() init.d status PID/RSS 摘要（OPT-285-18）**：系统状态命令输出核心进程 PID、物理内存 RSS 与运行摘要；
- **overview.js formatLuciHealthBadge() LuCI 首页健康状态徽标（OPT-285-19）**：在 LuCI 系统首页直接呈现 AI-LINK 核心健康状态徽标；
- **ailink_diag.py check_bypass_game_nat_guidance() 旁路由游戏 NAT/UPnP 排查指引（OPT-285-20）**：针对旁路由游戏主机 NAT 类型与 UPnP 穿透提供全自动诊断排查指南；
- **混沌仿真套件全面扩充**：新增 Stage 7.58，混沌工程用例增至 **121/121** 项全绿通过。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **121/121 PASS**、发布门禁双布局 `30/30`、Aster Design `18/18`、指纹表 11 项全量匹配（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务自愈稳定；UI 六页三视口零溢出；设备侧出网 200/200/204/200 全通。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/install.sh | sh
```

支持从现网直升，配置、节点、订阅、节点池全部保留，失败自动回滚。本次为正常升版，现网设备会收到 OTA 提示。

---

## 包指纹

```
AI-LINK-v2.8.5.tar.gz   1,276,350 B
md5     cb1ab167c288bd8bfbcd38fa45be52e6
sha256  8da07d7e98fe841d2b097d33cf6f8a96f489af6942fd55fb827e1515bd504a56
```
