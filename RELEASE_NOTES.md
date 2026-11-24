# AI-LINK v2.8.6 正式发布说明

`v2.8.6 (r63)` 在 `v2.8.5` 稳定线上基准（Release #456591832 / `aff4c76f`）基础上，完成 OPT-286-01 ~ OPT-286-10 10 项全栈架构解耦、前端资源生命周期管控与高鲁棒性门禁闭环：

### 核心特性与架构增强
- **状态扩展注册表解耦（OPT-286-01）**：`ailink_diag.py` 引入 `STATUS_EXTENSION_REGISTRY` 与 `apply_status_extensions()`，彻底取代多层散落的猴补丁链，提升模块独立性与可维护性；
- **诊断公共原语规范接入（OPT-286-02）**：`ai-link-daemon.py` 统一复用诊断模块纯函数，标准化集成至 `/api/status` 遥测接口；
- **前端事件监听统一回收机制（OPT-286-03）**：`nexus.js` 新增 `createManagedAbortController()` 与 `cleanupManagedAbortControllers()`，视图切换时自动释放所有事件监听，根除长连接内存泄漏；
- **LuCI 后台标签页智能节流（OPT-286-04）**：`overview.js` 新增 `isLuciPageVisible()` 探测，当页面不可见或处于后台标签页时大幅降低轮询频次，节省路由 CPU 开销；
- **声明式路由元数据表（OPT-286-05）**：重构守护进程 API 路由为 `DECLARATIVE_ROUTE_TABLE_V286` 声明式表，统一管理鉴权级别、限流阈值与处理函数；
- **前端定时器生命周期池（OPT-286-06）**：`nexus.js` 引入 `NexusIntervalPool` 统一注册与销毁定时器，页面销毁时百分之百清空后台计时循环；
- **非阻塞可中断等待机制（OPT-286-07）**：核心守护进程全面引入 `interruptible_wait(stop_event, timeout_s)`，服务重启与退出响应提速至毫秒级；
- **CSS 移动端断点彻底收敛（OPT-286-08）**：`nexus.css` 与 `design-lint.js` 统一校验 3 档响应式断点（430/375/768），杜绝任何样式断点漂移；
- **自研脚本零 console.log 严格门禁（OPT-286-09）**：`gates_v101.py` 严格校验自研核心脚本零 `console.log`，白名单过滤第三方压缩库；
- **公共 Shell 工具函数抽离（OPT-286-10）**：抽离 `root/usr/share/ai-link/lib_common.sh`，统一端口检查、UCI 读写等脚本复用；
- **深度混沌仿真套件全面扩充**：新增 Stage 7.59，覆盖 OPT-286 专属场景，全量混沌用例增至 **122/122** 项全绿通过。

### 全量验证数据
- **真机安装与自检**：`sh install.sh --upgrade` RC=0；连续 10 轮生产态内置自检 10/10 PASS；负向防泄露自检（`AI_LINK_SELFTEST_DISABLE_INTERCEPT=1`）精准检出 `leaked`，`NEGATIVE_RC=1` 预期成立；
- **回归与混沌测试**：物理机 15 套回归套件 15/15 PASS；深度混沌测试 122/122 PASS；
- **视觉与契约门禁**：Aster Design Lint v2.0 (18 Gates) 18/18 PASS；API/UI 对齐 PASS；
- **双布局质量门禁与防篡改**：纯解压布局 31/31 PASS；标准出包布局 31/31 PASS；单字节篡改（`3f94bcb1` -> `0094bcb1`）精准转红 RC!=0，恢复原状后立即恢复 31/31 PASS；
- **UI 无头 CDP 验收**：3D Canvas 正常渲染；6 大主页面切换正常；移动端 3 档视口（430/375/768）零横向滚动溢出；控制台 0 异常；
- **设备出网核验**：Cloudflare (200)、Baidu (200)、Google204 (204)、Panel (200) 全通；LAN 鉴权持久化 `require_lan_auth=1`。
