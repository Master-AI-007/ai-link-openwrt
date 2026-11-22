# AI-LINK v2.7.8 正式发布说明

`v2.7.8 (r53)` 在 `v2.7.7` 稳定线上基准基础上，完成 OPT-278-01 ~ OPT-278-10 10 项全栈架构增强与独立单测闭环：

### 核心特性与架构增强
- **分流规则批量导入/导出与校验（OPT-278-01）**：新增 `parse_and_validate_bulk_shunt_rules()`、`/api/shunt/bulk_rules` 批量规则导入接口与前端 `bulkExportShuntRules()`；
- **autoPagedLargeList 分页边界修复（OPT-278-02）**：对齐 `effTotalPages` 按钮上限并保持搜索重置第 1 页；
- **节点订阅流量与到期时间倒计时（OPT-278-03）**：新增 `compute_subscription_usage_summary()` 计算流量用量与到期时间并接入 `/api/status`；
- **鉴权 429 锁定倒计时回显（OPT-278-04）**：新增 `startAuthLockCountdown()` 动态秒级倒计时组件，优化防爆破锁定提示体验；
- **ailink_diag.py 独立单元测试（OPT-278-05）**：子模块扩容至 696 行，新增独立单测 `tests/test_diag_module.py`（10/10 PASS，<0.1s）并接入 `run_all.py`；
- **架构运维与稳定性增强（OPT-278-06~10）**：TProxy/TUN 数据链路快速自检探测、`init.d` 启动端口冲突告警、WebUI 快捷键支持（`/` 聚焦搜索、`Esc` 关闭抽屉）、定时任务下次执行时间预览以及多网段旁路由冲突检测；
- **混沌工程覆盖升级**：新增 `Stage 7.51` 自动化覆盖，混沌测试集扩展至 114 项全绿通过。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **114/114 PASS**（含 `Stage 7.51` 新增闭环）、发布门禁双布局 `23/23`、Aster Design `18/18`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务自愈稳定；UI 六页三视口零溢出；设备侧出网 200/200/204/200 全通。

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
AI-LINK-v2.7.8.tar.gz   1,248,340 B
md5     971807d490bb14a258434f14c092d899
sha256  b6231102190f279e8f9e67ecd78059aa0e5a4849f07c2f9812e8f59408abe488
```
