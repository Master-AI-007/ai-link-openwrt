# AI-LINK v2.8.7 正式发布说明

`v2.8.7 (r64)` 在 `v2.8.6` 稳定线上基准（Release #456819548 / `201662c`）基础上，完成 OPT-287-01 ~ OPT-287-10 10 项全栈架构解耦、配置管线分层与前端能效优化闭环：

### 核心特性与架构增强
- **POST 业务域分发架构解耦（OPT-287-01）**：`ailink_diag.py` 引入 `POST_DISPATCH_DOMAINS_V287` 与 `resolve_post_domain()`，守护进程 API 分发逻辑实现清晰解耦；
- **配置管线分层与状态汇总（OPT-287-02）**：`ailink_diag.py` 新增 `SINGBOX_CONFIG_SECTIONS_V287` 与 `NFT_RULE_STAGES_V287` 分层架构，提供端到端管线可视化摘要；
- **线程安全工厂（OPT-287-03）**：新增 `create_daemon_thread()` 强制构造 `daemon=True` 守护线程，彻底避免进程退出时挂起；
- **CLI 脚本统一收敛（OPT-287-04）**：`usr/bin/ai-link` 深度整合 `lib_common.sh`，统一版本号与系统命令调用；
- **3D 视图节能智能停帧（OPT-287-05）**：`nexus3d.js` 统一由 `_scheduleNextFrame()` 纳管，标签页不可见时自动暂停渲染，降低能耗；
- **CSS 规范深度治理（OPT-287-06）**：严格清理 `!important` 依赖，符合 Aster Design Token 规范；
- **前端模块化持续下沉（OPT-287-07）**：扩充 `modules/api.js` 与 `settings-panel.js`，降低主文件复杂度；
- **防火墙链一致性静态门禁（OPT-287-08）**：门禁强校验 `apply_nft.sh` 与守护进程生成的 nftables 规则链 100% 同源；
- **节点评估微缓存（OPT-287-09）**：`MicroEvalCache` 缓存周期内节点健康评分，大幅减少频繁探测时的计算开销；
- **LuCI RPC 错误处理闭环（OPT-287-10）**：统一 LuCI 远程接口异常返回格式与用户提示；
- **深度混沌仿真套件全面扩充**：新增 Stage 7.60 场景，混沌工程用例增至 **123/123** 项全绿通过。

### 全量验证数据
- **真机安装与自检**：`sh install.sh --upgrade` RC=0；连续 10 轮生产态内置自检 10/10 PASS；负向防泄露自检（`AI_LINK_SELFTEST_DISABLE_INTERCEPT=1`）精准检出 `leaked`，`NEGATIVE_RC=1` 预期成立；
- **回归与混沌测试**：物理机 15 套回归套件 15/15 PASS；深度混沌测试 123/123 PASS；
- **视觉与契约门禁**：Aster Design Lint v2.0 14/14 PASS；API/UI 对齐 PASS；
- **双布局质量门禁与防篡改**：纯解压布局 32/32 PASS；标准出包布局 32/32 PASS；单字节篡改精准转红 RC!=0，恢复原状后立即恢复 32/32 PASS；
- **UI 无头 CDP 验收**：3D Canvas 正常渲染；6 大主页面切换正常；移动端 3 档视口（430/375/768）零横向滚动溢出；控制台 0 异常；
- **设备出网核验**：Cloudflare (200)、Baidu (200)、Google204 (204)、Panel (200) 全通；LAN 鉴权持久化 `require_lan_auth=1`。
