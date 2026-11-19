# AI-LINK v2.7.4 正式发布说明

`v2.7.4 (r49)` 在 `v2.7.3` 稳定线上基准基础上，完成 10 项全栈性能、稳定性与路由热重载增强（OPT-274-11 ~ OPT-274-20）：

### 核心优化
- **边缘低功耗 CPU 冷启动基准校准**（OPT-274-11）：`v242_deep_chaos_simulation.py` 新增 `benchmark_edge_cold_and_warm()`；
- **分流缓存加速**（OPT-274-12）：`discover_live_unmatched_traffic()` 增加 `shunt.json` `mtime` 轻量内存缓存，二次调用降至 `<5ms`；
- **分流规则冲突检测**（OPT-274-13）：新增 `detect_shunt_rule_conflicts()` 识别 5×3 分流矩阵重叠与冲突；
- **双栈 DNS 泄露自检**（OPT-274-14）：新增 `probe_dns_leak_v4_v6()` 支持 IPv6 `AAAA` 并发验证；
- **测速失败原因细分**（OPT-274-15）：新增 `classify_l7_probe_failure_reason()` 区分 TLS 握手超时、HTTP 403/502 与 TCP 不可达；
- **HomeLink 密钥轮换提醒**（OPT-274-16）：新增 `check_homelink_key_rotation_notice()` 90 天温和提示且不阻断现有连接；
- **日志轮转压缩降载**（OPT-274-17）：新增 `rotate_and_compress_logs_if_needed()` 在低内存（<128MB）环境下自动压缩归档；
- **WAN 子接口热插拔绑定**（OPT-274-18）：新增 `check_wan_interface_rebind_needed()` 动态追踪 PPPoE/VLAN 变化并重绑 nftables；
- **卸载彻底性核验**（OPT-274-19）：`uninstall.sh` 增加 `nft list tables` 强校验，确保无残留表；
- **3D 视图低帧率降级**（OPT-274-20）：`nexus3d.js` 连续 FPS < 15 时自动提供轻量 2D 拓扑切换。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **110/110 PASS**（含 `Stage 7.47` 新增闭环）、发布门禁双布局 `19/19`、Aster Design `18/18`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务自愈稳定；UI 六页三视口零溢出；设备侧出网 200/200/204/200 全通。

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
AI-LINK-v2.7.4.tar.gz   1,228,713 B
md5     51082f03a7fd1cffa37837d8b6a4128b
sha256  9afeabcf8f56755ee67a3756d4a84c82376f52640a7fc0665ecee0da2b1ef239
```
