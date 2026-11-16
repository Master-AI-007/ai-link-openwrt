# AI-LINK v2.6.3

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-16 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：全栈深度优化 + 3D 切换闭环 + 国服游戏直连

`v2.6.3 (r34)` 在 `v2.6.2` 基础上完成 11 项全栈深度优化、闭环用户本人提出的 3D 终端列表切换诉求，并落地 5 项国服游戏直连专项：

### 3D 终端列表切换闭环（用户诉求）
- 3D 拓扑页「KERNEL HUB / 局域网终端列表」新增显式「TOP3 / 所有设备」切换控件，不再随数据轮询在两态间跳动；
- `NexusStorage` / `localStorage`（`ailink_galaxy_device_view`）持久化用户选择，刷新保持；
- 多设备条件 24 次采样相邻翻转 **0 次**。

### 国服游戏直连 5 项
- 魔兽/战网/LoL TCP + UDP 双协议端口内核直通；`@direct_bypass` 脱钩 `entry_bypass`；
- `block_quic` 不误杀国内 App / 战网 HTTP-3；`Domestic_CN` 优先于 `Outside_CN`；战网/网易风控白名单。

### 全栈 10 项深度优化
- 3D 显存/监听零泄漏、首屏 HUD ≤8 按钮、分流页 ≤12 按钮、CSS Elevation 三级令牌、6 独立 JS 模块、47 处原子写、HTTP 安全响应头、探测脚本加固。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **98/98 PASS**（含新增 `Stage 7.33/7.34/7.35`）、发布门禁双布局 `17/17`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务稳定；UI 六页三视口零溢出；设备侧出网 200/200/204。

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
AI-LINK-v2.6.3.tar.gz   1,156,709 B
md5     2edb06e886cec1750343a85f1d7c1264
sha256  b27a38b0956bfb01734e17187e5b660f6851d79c9b19be79cae93d01789bf2c4
```
