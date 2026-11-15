# AI-LINK v2.6.2

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-15 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：用户前端 UX 审计全量整改

`v2.6.2 (r31)` 在 `v2.6.1` 基础上，按用户本人提出的前端视觉/交互/架构深度审查报告，完成 P0 / P1 / P2 全量整改：

### 架构止血（P0）
- Modal Stack 模态栈防覆写 + 右侧 Drawer 分离，`openModal(` 调用点 48 → 8 处，二次确认弹窗不再吞掉表单草稿；
- 应急直连旁路显式提示、HomeLink 公网 DDNS 告警保留、订阅失败原地粘贴 / 切镜像；
- LuCI HTTPS 场景的 CLI RPC 桥接，消除 Mixed-Content 阻断；清除废弃的音乐解锁僵尸 UI。

### 3D 与视觉（P1 / P2）
- 自定义 GLSL Fresnel 边缘光 Shader + PBR 材质，完整保留遥测 HUD 与检视面板 5 个子视图数据；
- 设置页拆 4 分组导航 + Danger Zone 危险操作隔离；`backdrop-filter` 22 → 3 处，`@media` 收敛为 768/1280 两档；
- 工程术语产品化、`window.NexusModules` 模块化。

### 功能性升级入口恢复
- 恢复设置页「sing-box 内核智能检测升级」（`#btn-check-core-update`）与「检测插件升级 / 立即升级插件」（`#btn-ota-check` / `#btn-ota-apply`）；按钮瘦身不误删这两个入口。

### 系统加固
- 保留 r30 的 NET-262-01~03 网络平面修复；新增动态 LAN 网桥探测与 `init.d` `flock` 并发互斥锁。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **95/95 PASS**（含新增 `Stage 7.32`）、发布门禁双布局 `17/17`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务稳定；UI 六页三视口零溢出；设备侧出网 200/200/204。

---

## 升级方式

```sh
ai-link update --apply
# 或
curl -fsSL https://ai-link-official.pages.dev/upgrade.sh | sh
```

支持从现网直升，配置、节点、订阅、节点池全部保留，失败自动回滚。本次为正常升版，现网设备会收到 OTA 提示。

---

## 包指纹

```
AI-LINK-v2.6.2.tar.gz   1,143,675 B
md5     ba5192e0513f2fe3384e23cea6048189
sha256  0a01384ea45bd011ea2965176cfde66b034292dc3bc3491778a05a9efe46c8e1
```
