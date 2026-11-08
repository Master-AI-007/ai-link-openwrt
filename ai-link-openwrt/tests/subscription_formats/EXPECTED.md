# 订阅格式期望矩阵

| 用例文件 | 格式 | 当前期望 | 修复后期望 |
|---|---|---|---|
| clash-simple.yaml | Clash YAML 单层 flow | ✅ 通过 | ✅ |
| clash-block.yaml | Clash YAML 块式（`-` 单独一行）| ✅ 通过（需补丁）| ✅ |
| clash-nested-flow.yaml | Clash YAML 嵌套 flow | ✅ 通过（需补丁）| ✅ |
| clash-anchor.yaml | Clash YAML 锚点 + merge | ✅ 通过（需补丁 + PyYAML）| ✅ |
| uri-list.txt | 明文 URI 列表 | ✅ 通过 | ✅ |
| base64-uri.txt | Base64 URI 列表 | ✅ 通过 | ✅ |
| singbox.json | sing-box JSON | ✅ 通过 | ✅ |
| surge.txt | Surge INI 段 | ❌ 待适配器 | ✅ |
| loon.txt | Loon INI 段 | ❌ 待适配器 | ✅ |
| sip008.json | SIP008 JSON | ❌ 待适配器 | ✅ |
| v2ray-json.json | V2Ray JSON 配置 | ❌ 待适配器 | ✅ |

> 说明：本包附带 `acceptance-fixes.diff` 只解决 YAML 与拉取重试；Surge/Loon/SIP008/V2Ray JSON 需要下一轮适配器实现。
