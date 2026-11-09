# 真机 OTA 验证证据

设备：`10.10.10.77`（ImmortalWrt 25.12.2 / x86_64 / 内核 6.12.103 / Python 3.13.9）
验证时间：2026-10-26 05:49 – 06:12 (GMT+8)
开发机：`10.10.10.62`（本地 HTTP 服务提供测试清单与测试包）

---

## 0. 前置：v1.0.0 → v1.0.1 手动升级（冷启动）

设备原状态：`/etc/ai-link/version` = `1.0.0 (20261025)`，daemon 未运行，`:9099` 未监听，
`ai-link.global.panel_secret='sha256:eb58990a…'`（PWD-1 缺陷现场）。

升级前备份（设备与本机各一份）：
```
/root/ai-link-final-backup/pre-v101-20261026-054917.tgz   2,857,242 B
本地：project/tests/ota_device/device-backup-pre-v101-20261026-054917.tgz
```

安装方式：上传官方 `AI-LINK-v1.0.1.tar.gz`（MD5 `4375ddde…`），执行 `install.sh --upgrade`。

安装后：
```
/etc/ai-link/version  1.0.1 (20261026)
svc_state             daemon=1 core=0 nft=1 enabled=1 boot=1 bypass=0 port=9099
pgrep daemon          1
:9099                 LISTEN
/api/status           200
```

`ai-link probe` 结果（真机首次通过内置自检）：
```
SELF_TEST_PASSED {"ok": true, "app_version": "1.0.1", "ota_version_compare_ok": true,
"ota_script_generation_ok": true, ... "detected_core": "sing-box 1.14.1", ...}
```

> 开发机上同一条自检会因缺少 `127.0.0.1:9090` 的 Clash API 而在性能断言处失败；
> 真机上通过，确认那是环境差异而非产品缺陷。

外网可达性（设备侧 `curl`）：
```
https://ai-link-official.pages.dev/version.json                                     200
https://ghfast.top/https://raw.githubusercontent.com/.../main/version.json          200
https://raw.githubusercontent.com/.../main/version.json                            200
```

## 1. 成功路径：v1.0.1 → v1.0.2（测试包）

测试清单指向 `http://10.10.10.62:8000/version.json`（`uci set ai-link.global.update_manifest_url`）。
测试包：`AI-LINK-v1.0.2.tar.gz`，1,200,634 B，MD5 `3774abe539014321fb5072e0103b9106`，27 个文件。

```
1792965056|prepare|5|开始升级到 v1.0.2（当前 v1.0.1）
1792965056|download|10|尝试第 1 个下载源: http://10.10.10.62:8000/pkg/AI-LINK-v1.0.2.tar.gz
1792965056|download|40|下载完成: http://10.10.10.62:8000/pkg/AI-LINK-v1.0.2.tar.gz
1792965056|verify|50|正在校验升级包完整性
1792965056|verify|58|校验通过 (md5=3774abe539014321fb5072e0103b9106)
1792965056|extract|62|正在解压
1792965056|extract|68|解压完成: /var/run/ai-link/update/extract/ai-link-openwrt
1792965056|backup|72|正在备份用户配置到 /root/ai-link-final-backup/pre-update-v1.0.2-1792965056.tgz
1792965057|backup|76|已备份用户配置与旧版代码（可回滚）
1792965057|install|84|正在写入新版本文件（install.sh --upgrade）
1792965078|restart|92|正在重启服务
1792965105|healthcheck|97|正在检查服务健康状态
1792965105|done|100|升级成功，当前版本 v1.0.2
```

耗时：prepare → done **49 秒**（其中 install 21s、restart→healthcheck 27s）。

升级后：
```
版本文件      : 1.0.2 (20261026)
svc_state     : daemon=1 core=0 nft=1 enabled=1 boot=1 bypass=0 port=9099
进程数        : 1
/api/status   : 200
备份          : /root/ai-link-final-backup/pre-update-v1.0.2-1792965056.tgz
```

CLI 侧同步显示：
```
[ 84%] 正在写入新版本文件 — install.sh --upgrade
[ 92%] 正在重启服务
[100%] 升级完成 — 升级成功，当前版本 v1.0.2
✅ 升级完成，当前版本 v1.0.2
```

## 2. 失败路径：v1.0.2 → v1.0.3（注入故障包，验证自动回滚）

测试包 `AI-LINK-v1.0.3.tar.gz`（1,201,610 B，MD5 `80815d53a0c2b7bc69bd5941a7f1f27a`）：
在 daemon 顶部注入 `raise SystemExit(...)`，让升级后服务必然起不来。

```
1792965858|prepare|5|开始升级到 v1.0.3（当前 v1.0.2）
1792965858|download|10|尝试第 1 个下载源: http://10.10.10.62:8001/pkg/AI-LINK-v1.0.3.tar.gz
1792965858|download|40|下载完成: http://10.10.10.62:8001/pkg/AI-LINK-v1.0.3.tar.gz
1792965858|verify|50|正在校验升级包完整性
1792965858|verify|58|校验通过 (md5=80815d53a0c2b7bc69bd5941a7f1f27a)
1792965858|extract|62|正在解压
1792965858|extract|68|解压完成: /var/run/ai-link/update/extract/ai-link-openwrt
1792965858|backup|72|正在备份用户配置到 /root/ai-link-final-backup/pre-update-v1.0.3-1792965858.tgz
1792965859|backup|76|已备份用户配置与旧版代码（可回滚）
1792965859|install|84|正在写入新版本文件（install.sh --upgrade）
1792965861|install|88|install.sh 返回非零，进入健康检查判定
1792965861|restart|92|正在重启服务
1792965870|healthcheck|97|正在检查服务健康状态
1792965891|failed|0|升级后健康检查失败，正在自动回滚
1792965902|failed|0|升级失败，已回滚到 v1.0.2 并恢复正常
```

关键观察：

1. **包校验没有被跳过** —— md5 比对通过后才进入 install，校验逻辑真实生效。
2. **install.sh 自带的 symtable 门禁在设备上拦住了坏包**（`install.sh 返回非零`），
   比等到健康检查失败更早一步。
3. **回滚后版本与数据都回到升级前**：`/etc/ai-link/version` = `1.0.2 (20261026)`，
   daemon 1 个进程，`/api/status` 200，配置未被污染。
4. **回滚后 nftables 表有约 10 秒空窗**：回滚完成瞬间 `nft list tables` 里没有 `inet ai_link`，
   约 10 秒后被 daemon 的 `auto_heal_interval=10` 自愈循环补回。属可接受但可优化项，见报告第 4 节。

## 3. 收尾：恢复官方版本

验证完成后把设备装回官方 v1.0.1：

```
/etc/ai-link/version  1.0.1 (20261026)
svc_state             daemon=1 core=0 nft=1 enabled=1 boot=1 bypass=0 port=9099
/api/status           200
table inet ai_link    已挂载
sing-box 进程         运行中
```

`uci` 里的测试清单地址已删除，`gh_mirror` 等原配置未改动。

## 4. 复现用脚本

| 脚本 | 作用 |
|---|---|
| `recon.py` | 设备现状侦察（版本 / 服务 / UCI / 磁盘 / 外网） |
| `deploy_v101.py` | 备份 + 上传 + `install.sh --upgrade` + 轮询到 1.0.1 |
| `probe_device.py` | `ai-link probe`、清单候选、外网可达性、`ai-link update` |
| `build_test_pkg.py` | 生成测试包与清单（`--break-daemon` 注入故障） |
| `serve.py` | 本机 HTTP 服务，供设备拉清单与包 |
| `ota_apply_test.py` | 指向测试清单 → 检查 → `--apply` → 轮询八阶段 → 收尾 |
| `check_after.py` | 回滚后状态复查（nft / API / 进程） |

凭据通过环境变量传入（`AI_LINK_DEVICE_HOST/USER/PASS`），脚本里不落盘。
