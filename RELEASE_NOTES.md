# AI-LINK v1.0.0 正式版

> OpenWrt 下一代「永不断连」智能透明代理 · 异地组网回家 · DNS 净网护盾
> 发布日期：2026-10-26 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 本版要点

**v1.0.0 是封版（Production Release）**，核心引擎 `sing-box 1.12+/1.14+` + `nftables TProxy/Redirect`。

### 主要能力

- **自动节点池（1~5 组优先级）**：粘性锁定 + 双组探测 + 20 秒死节点自动逃生，节点切换不掉线
- **单臂旁路由对称 NAT**：`@cn_ip4/@cn_ip6` 硬件级国内旁路，配合 `srcnat masquerade` 解决回程非对称
- **免证书 HomeLink**：VLESS-Reality 与 Hysteria2，动态 `pinSHA256`，手机流量直连回家
- **五种全局路由模式**：分流 / 全局代理 / 全直连 / 国内白名单 / 仅被墙网站
- **DNS 净网护盾**：50,074 条拦截规则，DNS 层 REFUSED + 路由层 REJECT 双层记账
- **备份 / 恢复出厂**：归档备份字节级还原（含面板密码与 UCI），一键恢复出厂自动归档

### 本版修复（相对上一轮验收）

| 编号 | 修复 |
|---|---|
| FR-1 | 停止/卸载时清理 `fc00::/18` FakeIP 路由 |
| FR-2 | `nf_conntrack_tcp_be_liberal` 记录原值并在卸载时还原（不再给系统留全局副作用） |
| FR-3 | JSON 备份完整覆盖 `panel_auth` 与 UCI `panel_secret`，恢复后面板密码不再回默认弱口令 |
| FR-4 | `仅被墙网站走代理` 模式修正：bing / apple / microsoft / cloudflare 等未墙站点恢复直连 |
| FR-5 | 卸载不再用 `/tmp/ai-link*` 通配删除，避免误删用户解包的源码目录 |
| FR-6 | `sleep 0.3` → `sleep 1`，兼容精简版 BusyBox |

---

## 下载

| 文件 | 大小 | MD5 |
|---|---:|---|
| `AI-LINK-v1.0.0.tar.gz` | 1,176,852 B | `3d2710605ce844b0702bb60926fa5e2c` |
| `luci-app-ai-link_2.0.0-r8_all.ipk` | 567,995 B | `875ff6cf138252359bb8102a2667289b` |
| `AI-LINK-v1.0.0-manual.pdf` | 4,064,322 B | `aaa100db4c90960b08d50b411312973d` |

> 校验：`md5sum AI-LINK-v1.0.0.tar.gz` 应等于上表值。
> 注：压缩包与内部构建产物（`6b8f53b6…`）仅差一个 `README.md`（本手册更新版），其余 25 个文件字节一致。

---

## 安装

```sh
tar -xzf AI-LINK-v1.0.0.tar.gz
cd ai-link-openwrt
sh install.sh
```

安装完成后访问 `http://<路由器IP>:9099`（独立面板）或 LuCI → 服务 → AI-LINK 智能代理。

**升级**：直接执行 `install.sh` 即可，脚本会备份现有 `/etc/config/ai-link` 并逐项合并，保留节点、订阅与系统开关。

**卸载**：

```sh
ai-link uninstall -y            # 彻底卸载（自动归档 /etc/ai-link 到 /root/ai-link-final-backup/）
ai-link uninstall --keep-config # 保留配置卸载
```

---

## 验收状态

| 项 | 结果 |
|---|---|
| 交付门禁（23 项） | **23 / 23 PASS** |
| 内置契约自检 `--self-test` | **SELF_TEST_PASSED** |
| 静态门禁 | `div 834/834` · CRLF 0 · symtable 未定义 0 |
| 全新安装（零残留状态） | **22/22 组件完整** |
| 卸载残留 | **0**（源码目录保留） |
| 备份 → 恢复出厂 → 恢复 | 数据与设置 16/17 一致（`auto_nodes.json` 为运行时探测数据） |
| 五种路由模式 | 逐模式实测通过 |
| IPv6 双模式 | 防火墙层差异验证通过 |

---

## 已知问题

1. **手册提到的 `scripts/state_hash.py` / `scripts/residue_scan.py` 未随压缩包分发**（手册第 7 章）。这两个是验收工具，可在本仓库 `scripts/` 目录获取。
2. `auto_nodes.json` 含实时探测数据（`current_delay_ms`、`quality_ranking` 等），daemon 运行时会持续重写，**不适合作为备份一致性比对项**。

---

## 反馈

- 问题与建议：本仓库 Issues
- 使用手册：`AI-LINK-v1.0.0-manual.pdf`
