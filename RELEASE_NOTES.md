# AI-LINK v2.7.5 正式发布说明

`v2.7.5 (r50)` 在 `v2.7.4` 稳定线上基准基础上，完成 10 项全栈诊断拆包、并发安全与多订阅权重增强（OPT-275-01 ~ OPT-275-10）：

### 核心优化
- **单文件拆包里程碑化**（OPT-275-01）：抽离独立纯函数诊断子模块 `ailink_diag.py` 与 `get_diag_submodule_manifest()`；
- **分流缓存并发锁保护**（OPT-275-02）：`discover_live_unmatched_traffic()` 的 `mtime` 缓存增加 `_DISCOVER_SHUNT_CACHE_LOCK` 线程锁与命中计数；
- **出站标签安全截断**（OPT-275-03）：新增 `sanitize_singbox_outbound_tag()` 出站标签 UTF-8 字节上限截断守卫；
- **Fake-IP 缓存一键清理**（OPT-275-04）：新增 `clear_fakeip_cache_entries()` 清理持久化映射残留；
- **多订阅加权测速评分**（OPT-275-05）：新增 `score_node_with_sub_priority()` 按订阅优先级加权延迟评分模型；
- **脱敏字段二次预览摘要**（OPT-275-06）：新增 `summarize_backup_redacted_fields()` 标注已脱敏密码/Token 字段；
- **归档配额低内存保护**（OPT-275-07）：`rotate_and_compress_logs_if_needed()` 增加低内存 `.gz` 归档总字节配额限制（`<=2MB`）；
- **多 WAN 出站路由提示**（OPT-275-08）：新增 `detect_multi_wan_egress_hint()` 检测多 WAN 口并提示路由核对；
- **2D 拓扑偏好持久化**（OPT-275-09）：`nexus3d.js` 切换轻量 2D 拓扑增加 `localStorage` 持久化记录；
- **旁路由网关指向指引**（OPT-275-10）：新增 `get_bypass_client_gateway_hint()` 提供详细客户端网关与 DNS 指向指引。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **111/111 PASS**（含 `Stage 7.48` 新增闭环）、发布门禁双布局 `20/20`、Aster Design `18/18`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务自愈稳定；UI 六页三视口零溢出；设备侧出网 200/200/204/200 全通。

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
AI-LINK-v2.7.5.tar.gz   1,230,969 B
md5     24c1ad91c3b670fa6b179e8d42b36379
sha256  c6ac645796614ed1ccd12bd795221939b2a52e66b86358f719ccc7208d1c0fc0
```
