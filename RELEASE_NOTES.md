# AI-LINK v2.6.4

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-16 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：3D 与稳定性深度优化、审计问题全量闭环

`v2.6.4 (r36)` 在 `v2.6.3` 基础上，闭环 Hydrogen v2.6.4 审计的 2 项 Blocker、4 项 Major 与 10 项穿透优化：

### Blocker 修复
- **下拉菜单裁剪**：解除 `.glass-card`/`.metric-card` 的 `overflow:hidden`，`#shunt-more-menu` z-index 提升至 300，新增 `closeShuntMoreMenu()` 支持外部点击、菜单项与 `Escape` 关闭；
- **弹窗语义二分**：27 处交互式向导/编辑表单恢复水平垂直居中的 `openModal()`（复杂表单自动挂载 `.modal-panel.wide min(880px,100%)`，实测居中偏差 0px），仅 13 处只读明细/诊断报告使用 `openDrawer()` 并实现零内边距右贴边。

### Major 修复
- 移动端弹窗/下拉响应式规则补齐（768px 满宽底部抽屉、375/430px 零横向溢出），1280px 顶栏优雅折行；
- 清理未定义的 `--z-dropdown`/`--z-popover` 令牌（0 残留）；消除 `index.html` 6 处双重 Tooltip 重叠。

### 体验加固
- 设置页低频排障入口折入折叠面板（静态按钮压降至 22 个，完整保留内核升级与 OTA 入口）；
- Modal 栈保存并恢复 `scrollTop`；3D 多指触控防抖 + `touch-action:none`。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **100/100 PASS**（含新增 `Stage 7.36`/`7.37`）、发布门禁双布局 `17/17`、Aster Design `18/18`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务稳定；UI 六页三视口零溢出；设备侧出网 200/200/204。

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
AI-LINK-v2.6.4.tar.gz   1,166,184 B
md5     978986b91fa755c774137e3b8b3b834e
sha256  52cc132c357695542516f9260e5f0849bb0587e2a08c908f0df684a544cc157a
```
