# AI-LINK v2.8.1 正式发布说明

`v2.8.1 (r56)` 在 `v2.8.0` 稳定线上基准（Release #454694131 / `33f3293`）基础上，完成 OPT-281-01 ~ OPT-281-10 10 项全栈架构增强与稳定性闭环：

### 核心特性与架构增强
- **分流规则批量导入/导出（OPT-281-01）**：新增 `parse_and_validate_bulk_shunt_rules()`、`/api/shunt/bulk_rules` 批量规则校验与导出；
- **大列表分页边界对齐（OPT-281-02）**：修复 `autoPagedLargeList` 翻页控件上限对齐 `effTotalPages`，搜索自动重置首屏；
- **订阅流量与到期倒计时（OPT-281-03）**：新增 `compute_subscription_usage_summary()` 汇总订阅用量并在 `/api/status` 中呈现；
- **鉴权锁定动态秒级倒计时（OPT-281-04）**：429 爆破防护锁定新增 `startAuthLockCountdown()` 动态剩余秒数提醒；
- **诊断模块解耦轻量化单测（OPT-281-05）**：`tests/test_diag_module.py` 10/10 PASS，秒级回归并接入 `run_all.py`；
- **数据面切换双链路快速自检（OPT-281-06）**：TProxy / TUN 切换后 `run_data_plane_quick_probe()` 即刻探测链路连通；
- **端口冲突提前检测与告警（OPT-281-07）**：`init.d` 启动前预检面板端口占用并输出告警，避免静默失败；
- **WebUI 全局键盘快捷键（OPT-281-08）**：按 `/` 键即刻聚焦节点搜索输入框，按 `Esc` 快速关闭所有打开的浮层抽屉；
- **定时调度下次执行时间预览（OPT-281-09）**：`compute_next_schedule_preview()` 预测定时任务触发时间戳并展示于系统状态；
- **旁路由多网段转发冲突预警（OPT-281-10）**：检测旁路由多 VLAN / 访客隔离接口与主路由转发规则潜在冲突；
- **混沌仿真套件全面覆盖**：深度混沌工程 117/117 项全绿通过（覆盖 `Stage 7.54` 闭环测试）。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **117/117 PASS**（覆盖 `Stage 7.54` 新增闭环）、发布门禁双布局 `25/25`、Aster Design `18/18`、指纹表 11 项全量匹配（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务自愈稳定；UI 六页三视口零溢出；设备侧出网 200/200/204/200 全通。

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
AI-LINK-v2.8.1.tar.gz   1,261,619 B
md5     5c8015f28646e58209ff41e7a9b6a2ba
sha256  e33bd63cb3a2bea36fc1bc52a746b44c3293fd15d6b2119555b0cb3daaebbf39
```
