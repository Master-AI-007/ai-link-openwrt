# AI-LINK v2.9.5 全量检查与重构验收报告

- **目标版本**：`v2.9.5` (`2.9.5-release-20261127-r72` / `PKG_VERSION:=2.9.5` / `PKG_RELEASE:=72` / `r72`)  
- **线上基线与版本推进依据**：  
  - **已确认验收并上线的基线版本（`v2.9.4`）**：依据 `FEEDBACK-Local-v2.9.4.md` 与 `00_STATE.json`，线上正式版 **`v2.9.4` (`r69`)** 已在真机 `10.10.10.77` 全绿通过 12 步验收并正式全量发布上线（GitHub `Release #459537838`、Commit `d53ddd9e142dc50ad101139ad67c3e89a22d7ce3`、`md5 = "67781f07299516ea380d9dd7e5be371f"`）。  
  - **本轮全栈架构优化落地（`v2.9.5` / `PKG_RELEASE:=72` / `r72`）**：响应 `AUDIT-Hydrogen-v2.9.4.md` 第三节 `OPT-295-01 ~ OPT-295-10`。

## 一、v2.9.5 (r72) OPT-295-01 \~ 10 增强闭环对照表

| 编号 | 类别 | 优化内容与落地点 | 验证状态 |
| :---- | :---- | :---- | :---- |
| `OPT-295-01` | 加密随机 | `ailink_diag.py` 新增 `secrets.token_hex` 封装 `secure_token_hex()` | 已通过 (`构建容器`) |
| `OPT-295-02` | 3D 复用 | `nexus3d.js` 预分配 `_tmpVec3`/`_tmpColor`/`_tmpMat4` 降低帧循环 GC | 已通过 (`构建容器`) |
| `OPT-295-03` | Socket 上下文 | `ailink_diag.py` 新增 `probe_tcp_socket_safe()` 保证 FD 释放 | 已通过 (`构建容器`) |
| `OPT-295-04` | 跨FS原子移动 | `ailink_diag.py` 新增 `cross_fs_atomic_move()` 处理 `EXDEV` | 已通过 (`构建容器`) |
| `OPT-295-05` | 流式哈希 | `ailink_diag.py` 新增 64KB 分块读取 `stream_file_hashes()` | 已通过 (`构建容器`) |
| `OPT-295-06` | 字体令牌 | `nexus.css` 对齐 `--font-ui`/`--font-num` 令牌规范 | 已通过 (`构建容器`) |
| `OPT-295-07` | POSIX ash 门禁 | `tests/gates_v101.py` 固化 `install.sh`/`init.d`/`apply_nft.sh` 零 bashism 门禁 | 已通过 (`构建容器`) |
| `OPT-295-08` | 三域映射 | `ailink_diag.py` 新增 `DIAG_DOMAIN_MAP_V293` 按网络/节点池/安全三域组织 | 已通过 (`构建容器`) |
| `OPT-295-09` | 视图中止 | `webui/modules/storage.js` 新增 `createViewAbortManager()` 管理在途请求中止 | 已通过 (`构建容器`) |
| `OPT-295-10` | 混沌测试 | `tests/v242_deep_chaos_simulation.py` 新增 `Stage 7.66` 校验 | 已通过 (`构建容器`) |

## 二、构建容器门禁与回归测试实测（标注口径：构建容器）

- **全量门禁 (`tests/gates_v101.py`, 构建容器)**：`41/41 PASS`（含 `opt293_release_gate`）。  
- **诊断模块单测 (`tests/test_diag_module.py`, 构建容器)**：`23/23 PASS`（含 `OPT-295-01/03/04/05/08`）。  
- **API-UI 契约对齐 (`tools/check_api_ui_parity.py`, 构建容器)**：`PASS`（`backend_keys=31, frontend_reads=22, api_routes=117, missing=[]`）。  
- **Aster Design Lint (`node tools/design-lint.js`, 构建容器)**：`18/18 PASS`（0 违规）。  
- **全量测试套件 (`tests/run_all.py`, 构建容器)**：`15/15 套件 PASS`（含 `test_v102_full_regression.py` `154/154 PASS`、`v242_deep_chaos_simulation.py` `131/131 PASS`、`--self-test` `PASS`）。  
- **真机实测口径说明**：本报告以上数值均为**构建容器**隔离目录验证结果；物理真机 `10.10.10.77` 的 12 步实机验收将在 Hydrogen 审计完成后由本地 Antigravity 执行。

## 三、历史问题与 P0/P1 安全基线保全

- 完整保留 `AI_LINK_CONF_DIR` 隔离写盘、升级配置幂等（IPv6、国内分流、GeoIP、`require_lan_auth`、订阅与自动节点池）、`_CN_V4_BUCKETS`、`_SHUNT_DOMAIN_FAST_MEMO`、`_SB_LINK_DEAD_RE`、`.srs_stage_` 原子回滚与 `lib_common.sh` 共享原语。

## 四、版本锚点与四方一致性核对

- `Makefile`: `PKG_VERSION:=2.9.5` / `PKG_RELEASE:=72`  
- `root/etc/ai-link/version`: `2.9.5`  
- `ai-link-daemon.py`: `APP_VERSION = "2.9.5"` / `APP_BUILD = "2.9.5-release-20261127-r72"`  
- `index.html`: 静态资源 `?v=2.9.5-<md5_8>` 全量刷新一致  
- `CHANGELOG.md` & `overview.js` & `ailink_diag.py`: 全量同步至 `2.9.5` / `r72`

## 五、交付物 11 行指纹表（与实际字节逐一匹配）

| 文件 | 字节大小（行数） | MD5 | SHA-256 |
| :---- | :---- | :---- | :---- |
| `AI-LINK-v2.9.5.tar.gz` | `1302236` (1,302,236 B) | `e065fb33a941649ea512c2373e3da6ee` | `523ebe48714dcfd7be1ef2c28d3cea938021887254a23697317b598dc66b05b1` |
| `luci-app-ai-link_2.9.5-r72_all.ipk` | `928235` (928,235 B) | `d416c9b7c68816de1a6a5b000f12b63a` | `b6b2eb5b92b672939224a4564dbe0a7bd86ca661ba6ae4e1b4ecc41db18fb49b` |
| `v242_deep_chaos_simulation.py` | `385743` (5183 行 / 385,743 B) | `b66ca2888b8346aa3eec417f6b5ddc49` | `7af343aa9ef537ff3b0c2c31a522c5317fa93893cd15b2912b5b7cda21655504` |
| `root/usr/share/ai-link/ai-link-daemon.py` | `1950928` (34506 行 / 1,950,928 B) | `6414b4e33227c404b7f14de4da052970` | `1c36a4556ef7859b4c916440f06539582f91026e5e00d521a3442a124f7283c6` |
| `root/usr/share/ai-link/webui/nexus.js` | `639312` (11028 行 / 639,312 B) | `e0c98fc42dd8152b6db9bf43b4294860` | `212bbf0722ff0f47de3d1a44f011b27c2ab6ec96fe6305571d94c11ed7b7d887` |
| `root/usr/share/ai-link/webui/index.html` | `78571` (1005 行 / 78,571 B) | `2724aac18a585c67d31e2a726824486f` | `b1e96bdb822899bc1cd597f4bdcaa916cc367c5587bfd030cf10ff808b8addfd` |
| `root/usr/share/ai-link/webui/nexus.css` | `151645` (4174 行 / 151,645 B) | `d86df48b8eede4c407d01291ad3fc6e4` | `7c240a2953fb848a0b2d937a12f917cba139cc3302b1909ae1f7cf5209d1a1af` |
| `root/usr/share/ai-link/webui/nexus3d.js` | `88291` (2060 行 / 88,291 B) | `7d6990a7079f76b53f1fbd08925fb2c3` | `7e1955374f2d2449745bdb7ad9f90f141ff04e614b46b45951ea56072e216814` |
| `htdocs/luci-static/resources/view/ai-link/overview.js` | `40461` (770 行 / 40,461 B) | `9349be9e9fb10d4ab05ba67eaf6cbb76` | `45437bbd77cd8fc036393e0dbb8bdeca11c9b5c47dfefb9c01815d76a1053133` |
| `Makefile` | `4383` (95 行 / 4,383 B) | `049a72936b8f5ee3af0d111f32207334` | `f59bc1e66b96d68cf211277031e983a38f9f39093b63a4629068d823cac44238` |
| `CHANGELOG.md` | `179938` (835 行 / 179,938 B) | `75c4bb29fbac97bce2b339df76b8249a` | `fa27e4b9cf157d83a315191906cdaf4e572286878b9ac54b82f0255e5bb54e42` |

## 六、标准五件套清单（零冗余）

1. `AI-LINK-v2.9.5.tar.gz`（顶层唯一 `ai-link-openwrt/`，0 重复，0 CRLF）  
2. `luci-app-ai-link_2.9.5-r72_all.ipk`（含 `conffiles`，与源码包核心文件逐字节一致）  
3. `AI-LINK-v2.9.5-云端交接包-20261127.zip`（含完整 `tests/`、`tools/`、ipk、源码包与交接文档）  
4. `ai_link_v2_9_5.md`（本报告）  
5. `v242_deep_chaos_simulation.py`（独立混沌测试脚本）

## 七、Hydrogen 复审与本地 QA 交接说明

- `00_STATE.json` 已更新为 `stage = "READY_FOR_AUDIT"`、`current_version = "v2.9.5"`、`pkg_release = 71`、`base_released_version = "v2.9.4"`。  
- 请 Hydrogen 按 `PROMPT-02` 复审 `v2.9.5 (r72)` 五件套与 `OPT-295-01 ~ 10`；通过后交由本地 `10.10.10.77` 执行 12 步实机验收。