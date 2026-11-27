# AI-LINK v2.9.7 全量检查与重构验收报告

- **目标版本**：`v2.9.7` (`2.9.7-release-20261127-r75` / `PKG_VERSION:=2.9.7` / `PKG_RELEASE:=75` / `r75`)  
- **线上基线与版本推进依据**：  
  - **已确认验收并上线的基线版本（`v2.9.6`）**：依据 `FEEDBACK-Local-v2.9.6.md` 与 `00_STATE.json`，线上正式版 **`v2.9.6` (`r74`)** 已在真机 `10.10.10.77` 全绿通过 12 步验收并正式全量发布上线（GitHub `Release #460058055`、Commit `949345486c31b29593d72b22888c8db6fd035ca6`、`cloudflare_url`: `https://ai-link-official.pages.dev`）。  
  - **本轮全栈架构优化落地（`v2.9.7` / `PKG_RELEASE:=75` / `r75`）**：响应 `AUDIT-Hydrogen-v2.9.6.md` 第三节 `OPT-297-01 ~ OPT-297-10`。

## 一、v2.9.7 (r75) OPT-297-01 \~ 10 增强闭环对照表

| 编号 | 类别 | 优化内容与落地点 | 验证状态 |
| :---- | :---- | :---- | :---- |
| `OPT-297-01` | 门禁强断言 | `tests/gates_v101.py` 校验 `fails=` 位于最后 `check()` 之后并强化 `assert len(results) >= 43` | 已通过 (`构建容器`) |
| `OPT-297-02` | 状态收敛 | `ai-link-daemon.py` 将 32 个模块级可变全局字典收敛注册至 `DAEMON_STATE.ensure_dict()` | 已通过 (`构建容器`) |
| `OPT-297-03` | 溢出审计 | `nexus.css` 完成 39 处 `overflow: hidden` 裁切风险复查与安全边界固化 | 已通过 (`构建容器`) |
| `OPT-297-04` | 脚本延迟 | `index.html` 非首屏外联 `<script>` 引入 `defer` 属性并保持文档序执行 | 已通过 (`构建容器`) |
| `OPT-297-05` | 端口回退提示 | `overview.js` 增强 UCI `panel_port` 回退 `9099` 默认端口标识 (`isDefaultPortFallback`) | 已通过 (`构建容器`) |
| `OPT-297-06` | 零循环依赖 | `tests/test_diag_module.py` 与 `gates_v101.py` 固化 `ailink_diag.py` 零反向导入 AST 门禁 | 已通过 (`构建容器`) |
| `OPT-297-07` | 门禁防跳过 | `tests/gates_v101.py` 校验全部 `opt*_release_gate()` 显式接入 `check()` | 已通过 (`构建容器`) |
| `OPT-297-08` | SRS 退避校验 | `ensure_srs_rulesets()` 新增 `.srs` 下载失败指数退避与 `.srs_checksums.json` SHA-256 保留 | 已通过 (`构建容器`) |
| `OPT-297-09` | 防连点冷却 | `nexus.js` `confirmModal()` 新增 500ms 防连点冷却保护 | 已通过 (`构建容器`) |
| `OPT-297-10` | RA/网关漂移 | `ailink_diag.py` 新增 `record_bypass_ra_and_gateway_drift()` 持久化旁路由 RA 冲突与网关漂移告警 | 已通过 (`构建容器`) |

## 二、构建容器门禁与回归测试实测（标注口径：构建容器）

- **全量门禁 (`tests/gates_v101.py`, 构建容器)**：`43/43 PASS`（含 `opt297_release_gate`）。  
- **诊断模块单测 (`tests/test_diag_module.py`, 构建容器)**：`24/24 PASS`（含 `OPT-297-06` 与 `OPT-297-10`）。  
- **API-UI 契约对齐 (`tools/check_api_ui_parity.py`, 构建容器)**：`PASS`（`backend_keys=31, frontend_reads=22, api_routes=117, missing=[]`）。  
- **Aster Design Lint (`node tools/design-lint.js`, 构建容器)**：`18/18 PASS`（0 违规）。  
- **全量测试套件 (`tests/run_all.py`, 构建容器)**：`15/15 套件 PASS`（含 `test_v102_full_regression.py` `154/154 PASS`、`v242_deep_chaos_simulation.py` `133/133 PASS`、`--self-test` `PASS`）。  
- **真机实测口径说明**：本报告以上数值均为**构建容器**隔离目录验证结果；物理真机 `10.10.10.77` 的 12 步实机验收将在 Hydrogen 审计完成后由本地 Antigravity 执行。

## 三、历史问题与 P0/P1 安全基线保全

- 完整保留 `AI_LINK_CONF_DIR` 隔离写盘、升级配置幂等（IPv6、国内分流、GeoIP、`require_lan_auth`、订阅与自动节点池）、`_CN_V4_BUCKETS`、`_SHUNT_DOMAIN_FAST_MEMO`、`_SB_LINK_DEAD_RE`、`.srs_stage_` 原子回滚与 `lib_common.sh` 共享原语。

## 四、版本锚点与四方一致性核对

- `Makefile`: `PKG_VERSION:=2.9.7` / `PKG_RELEASE:=75`  
- `root/etc/ai-link/version`: `2.9.7`  
- `ai-link-daemon.py`: `APP_VERSION = "2.9.7"` / `APP_BUILD = "2.9.7-release-20261127-r75"`  
- `index.html`: 含 `<meta name="referrer" content="no-referrer">`、`<script defer>` 与静态资源 `?v=2.9.7-<md5_8>` 全量刷新一致  
- `CHANGELOG.md` & `overview.js` & `ailink_diag.py`: 全量同步至 `2.9.7` / `r75`

## 五、交付物 11 行指纹表（与实际字节逐一匹配）

| 文件 | 字节大小（行数） | MD5 | SHA-256 |
| :---- | :---- | :---- | :---- |
| `AI-LINK-v2.9.7.tar.gz` | `1308577` (1,308,577 B) | `62b4a1a3218da104b52ba35280c8e2f8` | `041c2e5d3211e22c2133cbc24ec83a54c36784d1defb62d46331b60301a7d98c` |
| `luci-app-ai-link_2.9.7-r75_all.ipk` | `931373` (931,373 B) | `53638e8c81746a5fd45ca4a91e7103ff` | `3b62aee25bfd955847dc9ba9891047a18739973ee70af6a50664ac1fd5c8111b` |
| `v242_deep_chaos_simulation.py` | `391555` (5217 行 / 391,555 B) | `79db95f661e7411e366bfec39de76969` | `ad45dca1a958e5c1e08cae2e93175bfdf5ef32c919ed4585fea092e9a29f297e` |
| `root/usr/share/ai-link/ai-link-daemon.py` | `1954941` (34540 行 / 1,954,941 B) | `6feec2a6d0c5d8085803d62bbbc0d91d` | `dbc28fa2e82dc95a84c397b337aa348e0771ac6d25264eaa129132823d6d67bd` |
| `root/usr/share/ai-link/webui/nexus.js` | `639698` (11038 行 / 639,698 B) | `a3fdeda96e67d5cc095551e31cf1b1f8` | `954a521dc270f7ef7d96bc6839de0411b5da5284bc257376553e0f01588c9559` |
| `root/usr/share/ai-link/webui/index.html` | `78666` (1006 行 / 78,666 B) | `d71cfad8b26946117433addfe842406d` | `a4be149818f0ca2e38d76dd559380eb72fabc9bde7a5d7921180e45fd3ae036f` |
| `root/usr/share/ai-link/webui/nexus.css` | `151804` (4174 行 / 151,804 B) | `8420c07529ddfc9a02441ac7d3e8c440` | `fa31a78a5478b8b9873bfeea1c5c935280d553ea49c6c58e5f9a99d2e93f9b6b` |
| `root/usr/share/ai-link/webui/nexus3d.js` | `88291` (2060 行 / 88,291 B) | `7d6990a7079f76b53f1fbd08925fb2c3` | `7e1955374f2d2449745bdb7ad9f90f141ff04e614b46b45951ea56072e216814` |
| `htdocs/luci-static/resources/view/ai-link/overview.js` | `40725` (774 行 / 40,725 B) | `1578670bcce338b341905c4f743ffb49` | `cd591e8b2280a26a285c94ae2deb262b42ad2723a45343686e68fd2634c56b78` |
| `Makefile` | `4383` (95 行 / 4,383 B) | `4d2401795e25748039679645e3d26015` | `c4c8f532a31a132592ecbd2ea9c7f64b337a6c37b4f14c689c5e96518cc8e7c9` |
| `CHANGELOG.md` | `182171` (852 行 / 182,171 B) | `c51317f7b84230314f06ef2ed80bac33` | `0ccc64a55082ee85b4a7d70bf3a2fb8386a6159750ed03faaf7d252fb2caf080` |

## 六、标准五件套清单（零冗余）

1. `AI-LINK-v2.9.7.tar.gz`（顶层唯一 `ai-link-openwrt/`，0 重复，0 CRLF）  
2. `luci-app-ai-link_2.9.7-r75_all.ipk`（含 `conffiles`，与源码包核心文件逐字节一致）  
3. `AI-LINK-v2.9.7-云端交接包-20261127.zip`（含完整 `tests/`、`tools/`、ipk、源码包与交接文档）  
4. `ai_link_v2_9_7.md`（本报告）  
5. `v242_deep_chaos_simulation.py`（独立混沌测试脚本）

## 七、Hydrogen 复审与本地 QA 交接说明

- `00_STATE.json` 已更新为 `stage = "READY_FOR_AUDIT"`、`current_version = "v2.9.7"`、`pkg_release = 75`、`build_revision = "r75"`、`base_released_version = "v2.9.6"`。  
- 请 Hydrogen 按 `PROMPT-02` 复审 `v2.9.7 (r75)` 五件套与 `OPT-297-01 ~ 10`；通过后交由本地 `10.10.10.77` 执行 12 步实机验收。