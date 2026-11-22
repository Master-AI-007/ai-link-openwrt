# AI-LINK v2.7.6 正式发布说明

`v2.7.6 (r51)` 在 `v2.7.5` 稳定线上基准基础上，闭环修复 2 项用户报障 P0 缺陷并完成 10 项全栈架构增强（P0-1, P0-2, OPT-276-01 ~ OPT-276-10）：

### 核心修复与优化
- **自动节点卡片跨订阅筛选穿透与 CF1 串标根治（P0-1）**：移除 `preview_subscription_update` 硬编码 `scope_source="ALL"` 与 `new_clean` 回退；修复 `nexus.js` 中 `resolveNodeSubDisplayName` 兜底首个订阅名称假象；
- **分流组直连自锁死循环根治（P0-2）**：重构 `_normalize_group_shunt_params()`、`/api/shunt/update` 与前端清洗逻辑，彻底解决 `Games` 等分流组从直连切换至自动/手动模式的参数锁死；
- **诊断子模块实质迁入（OPT-276-01）**：抽离独立纯函数诊断子模块 `ailink_diag.py`，对外导出标准诊断清单函数；
- **前端并发操作锁保护（OPT-276-02）**：LuCI 界面增加 `withLuciActionLock` 守卫，杜绝高频连点竞态；
- **自动节点池区域优选模型升级**：新增 Stage 7.49 混沌覆盖，完善低延迟选路与故障快速自愈。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **112/112 PASS**（含 `Stage 7.49` 新增闭环）、发布门禁双布局 `21/21`、Aster Design `18/18`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务自愈稳定；UI 六页三视口零溢出；设备侧出网 200/200/204/200 全通。

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
AI-LINK-v2.7.6.tar.gz   1,233,898 B
md5     a6947d11e5e0dbcaeb47a5e861e8dc49
sha256  91cd16a8a625d3539fce3a04b091de7a23c7d85ce27dda4c6d51a1b52c8a095f
```
