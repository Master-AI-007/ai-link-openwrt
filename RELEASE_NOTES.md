# AI-LINK v2.9.6 全量检查与重构验收报告

- **目标版本**：`v2.9.6` (`2.9.6-release-20261127-r74` / `PKG_VERSION:=2.9.6` / `PKG_RELEASE:=74` / `r74`)  
- **线上基线与版本推进依据**：  
  - **已确认验收并上线的基线版本（`v2.9.5`）**：依据 `FEEDBACK-Local-v2.9.5.md` 与 `00_STATE.json`，线上正式版 **`v2.9.5` (`r72`)** 已在真机 `10.10.10.77` 全绿通过 12 步验收并正式全量发布上线（GitHub `Release #459760069`、Commit `c2980600e7ccc2d3a1ae1cce6a7599e1198dc524`、`cloudflare_url`: `https://ai-link-official.pages.dev`）。  
  - **本轮缺陷修复闭环（`v2.9.6` / `PKG_RELEASE:=74` / `r74`）**：全量修复 `FEEDBACK-Local-v2.9.6.md`、`FEEDBACK-Local-v2.9.6-r73.md` 与 `AUDIT-Hydrogen-v2.9.6.md` 指出的全部 2 项问题：  
    - `[Blocker] LOCAL_QA-20261127-01`：`tests/gates_v101.py` 将 `fails = [r for r in results if not r[1]]` 移至所有 `check(...)`（含 `OPT-294`/`OPT-295`/`OPT-296`）之后并追加 `assert len(results) >= 42`，消除提前求值导致的假绿 `RC=0` 盲区。  
    - `[Major] LOCAL_QA-20261127-02`：`root/usr/share/ai-link/webui/index.html` 补齐 `<meta name="referrer" content="no-referrer">`，`opt296_release_gate()` 真实检查通过。

## 一、v2.9.6 (r74) OPT-296-01 \~ 10 增强闭环对照表

| 编号 | 类别 | 优化内容与落地点 | 验证状态 |
| :---- | :---- | :---- | :---- |
| `OPT-296-01` | 加密随机 | `ailink_diag.py` 新增 `secrets.token_hex` 封装 `secure_token_hex()` | 已通过 (`构建容器`) |
| `OPT-296-02` | 3D 复用 | `nexus3d.js` 预分配 `_tmpVec3`/`_tmpColor`/`_tmpMat4` 降低帧循环 GC | 已通过 (`构建容器`) |
| `OPT-296-03` | Socket 上下文 | `ailink_diag.py` 新增 `probe_tcp_socket_safe()` 保证 FD 释放 | 已通过 (`构建容器`) |
| `OPT-296-04` | 跨FS原子移动 | `ailink_diag.py` 新增 `cross_fs_atomic_move()` 处理 `EXDEV` | 已通过 (`构建容器`) |
| `OPT-296-05` | 流式哈希 | `ailink_diag.py` 新增 64KB 分块读取 `stream_file_hashes()` | 已通过 (`构建容器`) |
| `OPT-296-06` | 字体令牌 | `nexus.css` 对齐 `--font-ui`/`--font-num` 令牌规范 | 已通过 (`构建容器`) |
| `OPT-296-07` | POSIX ash 门禁 | `tests/gates_v101.py` 固化 `install.sh`/`init.d`/`apply_nft.sh` 零 bashism 门禁 | 已通过 (`构建容器`) |
| `OPT-296-08` | 三域映射 | `ailink_diag.py` 新增 `DIAG_DOMAIN_MAP_V293` 按网络/节点池/安全三域组织 | 已通过 (`构建容器`) |
| `OPT-296-09` | 视图中止 | `webui/modules/storage.js` 新增 `createViewAbortManager()` 管理在途请求中止 | 已通过 (`构建容器`) |
| `OPT-296-10` | 混沌测试 | `tests/v242_deep_chaos_simulation.py` 新增 `Stage 7.66` 校验 | 已通过 (`构建容器`) |

## 二、构建容器门禁与回归测试实测（标注口径：构建容器）

- **全量门禁 (`tests/gates_v101.py`, 构建容器)**：`42/42 PASS`（`fails` 在末尾真实汇总，含 `opt296_release_gate`）。  
- **诊断模块单测 (`tests/test_diag_module.py`, 构建容器)**：`23/23 PASS`（含 `OPT-296-01/03/04/05/08`）。  
- **API-UI 契约对齐 (`tools/check_api_ui_parity.py`, 构建容器)**：`PASS`（`backend_keys=31, frontend_reads=22, api_routes=117, missing=[]`）。  
- **Aster Design Lint (`node tools/design-lint.js`, 构建容器)**：`18/18 PASS`（0 违规）。  
- **全量测试套件 (`tests/run_all.py`, 构建容器)**：`15/15 套件 PASS`（含 `test_v102_full_regression.py` `154/154 PASS`、`v242_deep_chaos_simulation.py` `132/132 PASS`、`check_panel_js.py` `PASS`、`--self-test` `PASS`）。  
- **真机实测口径说明**：本报告以上数值均为**构建容器**隔离目录验证结果；物理真机 `10.10.10.77` 的 12 步实机验收将在 Hydrogen 审计完成后由本地 Antigravity 执行。

## 三、历史问题与 P0/P1 安全基线保全

- 完整保留 `AI_LINK_CONF_DIR` 隔离写盘、升级配置幂等（IPv6、国内分流、GeoIP、`require_lan_auth`、订阅与自动节点池）、`_CN_V4_BUCKETS`、`_SHUNT_DOMAIN_FAST_MEMO`、`_SB_LINK_DEAD_RE`、`.srs_stage_` 原子回滚与 `lib_common.sh` 共享原语。

## 四、版本锚点与四方一致性核对

- `Makefile`: `PKG_VERSION:=2.9.6` / `PKG_RELEASE:=74`  
- `root/etc/ai-link/version`: `2.9.6`  
- `ai-link-daemon.py`: `APP_VERSION = "2.9.6"` / `APP_BUILD = "2.9.6-release-20261127-r74"`  
- `index.html`: 含 `<meta name="referrer" content="no-referrer">` 与静态资源 `?v=2.9.6-<md5_8>` 全量刷新一致  
- `CHANGELOG.md` & `overview.js` & `ailink_diag.py`: 全量同步至 `2.9.6` / `r74`

## 五、交付物 11 行指纹表（与实际字节逐一匹配）

| 文件 | 字节大小（行数） | MD5 | SHA-256 |
| :---- | :---- | :---- | :---- |
| `AI-LINK-v2.9.6.tar.gz` | `1304171` (1,304,171 B) | `16bdd2a6861d49260aec6d83ab2e6ee8` | `ffefe98813051c50393d806720caeeb28d81ad106fc91047fcd0e6bc1e6ae54f` |
| `luci-app-ai-link_2.9.6-r74_all.ipk` | `929341` (929,341 B) | `cf99970d2a4362ce8763332a93c15a15` | `99b057563794b55768e65be9dfa8fd22083567b963760ae986847107ec8db0d1` |
| `v242_deep_chaos_simulation.py` | `388778` (5196 行 / 388,778 B) | `4d0310f97f443cc2be3cfd69c6e44ddc` | `3a15d57a5b1e2f5a1d449edd8d578ecbae336cb661c8d2bd910f0deb609aa9c6` |
| `root/usr/share/ai-link/ai-link-daemon.py` | `1951338` (34512 行 / 1,951,338 B) | `3a4f25f9379bfadc37c992dcf8ec8a4d` | `d5359e7d99e5b6445658a2a655a26409882e2028235d8d07d41c995380d3c14a` |
| `root/usr/share/ai-link/webui/nexus.js` | `639538` (11034 行 / 639,538 B) | `64b59404253475037df545087eb2cff7` | `9acb1aa4f7454d1c0be4f2bee26c2e01bfceadda4d9d2f6dd042e2e93ba2d10a` |
| `root/usr/share/ai-link/webui/index.html` | `78618` (1006 行 / 78,618 B) | `46f5236f48ca37db1a5edbb15ca777fa` | `5d9af6a9a6e31fd9929cfcb93f9cc7c995fa86e101746857c3bb555142395f16` |
| `root/usr/share/ai-link/webui/nexus.css` | `151645` (4174 行 / 151,645 B) | `d86df48b8eede4c407d01291ad3fc6e4` | `7c240a2953fb848a0b2d937a12f917cba139cc3302b1909ae1f7cf5209d1a1af` |
| `root/usr/share/ai-link/webui/nexus3d.js` | `88291` (2060 行 / 88,291 B) | `7d6990a7079f76b53f1fbd08925fb2c3` | `7e1955374f2d2449745bdb7ad9f90f141ff04e614b46b45951ea56072e216814` |
| `htdocs/luci-static/resources/view/ai-link/overview.js` | `40486` (770 行 / 40,486 B) | `41ee98dd7220eb2133e52656f2da4ca7` | `c405ca6fdc1cd788771eb330068aa486e1a956ac13edafbf743a77f17bf42db4` |
| `Makefile` | `4383` (95 行 / 4,383 B) | `750b4619d845d576a9adf8f197fab410` | `8cdad9a796fe863c05f08efa63face79b849f700105941146096c0c87c2c0bda` |
| `CHANGELOG.md` | `180973` (839 行 / 180,973 B) | `3e58340ca9ee23487767e9e358656413` | `04abdceb6d5b94694353907d0e8aa8a111e9dfb7e3a577485cf8302b00d1c7c3` |

## 六、标准五件套清单（零冗余）

1. `AI-LINK-v2.9.6.tar.gz`（顶层唯一 `ai-link-openwrt/`，0 重复，0 CRLF）  
2. `luci-app-ai-link_2.9.6-r74_all.ipk`（含 `conffiles`，与源码包核心文件逐字节一致）  
3. `AI-LINK-v2.9.6-云端交接包-20261127.zip`（含完整 `tests/`、`tools/`、ipk、源码包与交接文档）  
4. `ai_link_v2_9_6.md`（本报告）  
5. `v242_deep_chaos_simulation.py`（独立混沌测试脚本）

## 七、Hydrogen 复审与本地 QA 交接说明

- `00_STATE.json` 已更新为 `stage = "READY_FOR_AUDIT"`、`current_version = "v2.9.6"`、`pkg_release = 74`、`build_revision = "r74"`、`base_released_version = "v2.9.5"`。  
- 请 Hydrogen 按 `PROMPT-02` 复审 `v2.9.6 (r74)` 五件套与 `LOCAL_QA-20261127-01/02` 修复；通过后交由本地 `10.10.10.77` 执行 12 步实机验收。