# AI-LINK v2.6.7

> OpenWrt 智能分流网关 · sing-box 单内核 · 15 组分流 · 自动节点池 · 订阅自适应
> 发布日期：2026-11-18 ｜ 适用：OpenWrt 23.05 / 24.10 / ImmortalWrt / LEDE（`fw4` + `nftables`）

---

## 这一版：10 项全栈打磨优化、异步退避与架构解耦加固

`v2.6.7 (r39)` 在 `v2.6.6` 稳定线上基线基础上，完成 10 项全栈打磨优化与安全韧性加固：

### 核心优化
- **Toast 容器显式无障碍契约**：补齐 `aria-live="polite"` 与 `aria-atomic="false"`；
- **LuCI 轮询指数退避**：连续失败自动按 `3s → 6s → 15s` 退避，恢复后秒级复位；
- **全局变量收拢清零**：22 处 `global` 声明收拢至 `DaemonState` 单例容器（降为 0 处）；
- **JSON 解析安全统一**：82 处直接调用 `json.loads` 收拢至 `_safe_json_loads`（降为 0 处）；
- **持锁安全审计清零**：持锁区间内 `time.sleep` 降为 0 处，杜绝并发请求阻塞；
- **四域子模块架构映射**：建立四大子系统映射，保持结构高内聚低耦合；
- **前端视图下沉**：节点表与分流矩阵片段下沉至 `webui/modules/shunt-nodes.js`；
- **样式精简与设计规范**：`nexus.css` 精简至 4,174 行，design-lint 18/18 零违规；
- **订阅解析前置过滤**：前置拦截空 host 与越界端口，结构化统计跳过原因；
- **模块双向指纹校验**：双向核验 `webui/modules/*.js` 与 `?v=` 哈希，防漏防缓存污染。

### 全量验证数据
真机 `10.10.10.77` 原始包零补发 `run_all 15/15 PASS / RC=0`、混沌 **103/103 PASS**（含新增 `Stage 7.40`）、发布门禁双布局 `17/17`、Aster Design `18/18`、11 行指纹逐行校验（改 1 字节即转红）；生产态自检 10 连跑通过且负向泄露检出有效；`INSTALL_RC=0`、重启后服务自愈稳定；UI 六页三视口零溢出；设备侧出网 200/200/204。

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
AI-LINK-v2.6.7.tar.gz   1,187,794 B
md5     6326cc114792c5fb7f1fe5a8d38e2961
sha256  ac4bdfa5d749a68e370afa5c7d99a6a227060ca021b437f7e79bda85739ffb58
```
