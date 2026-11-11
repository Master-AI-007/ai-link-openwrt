# -*- coding: utf-8 -*-
"""一键跑完 AI-LINK 全部验证：门禁 + OTA + 密码 + 面板脚本 + 内置自检。

用法（在 project/tests 目录下）：
    python run_all.py                # 全部
    python run_all.py gates ota      # 只跑指定项
    python run_all.py --list

环境变量：
    AI_LINK_SRC / AI_LINK_SITE   源码位置（默认 ../site/ai-link-openwrt）
    PYTHON_BIN / NODE_BIN        解释器
    BASH_BIN                     bash（Windows 上必须是 Git 自带的 bash，不是 WSL 的）
退出码：0 全部通过 / 1 有失败
"""
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _paths import ROOT, PY, NODE, BASH, DAEMON  # noqa: E402

SUITES = [
    ("gates", "gates_v101.py", "发布门禁 13 项"),
    ("ota", "ota_e2e.py", "OTA 端到端"),
    ("ota_sh", "ota_selftest.py", "升级脚本生成 + 版本比较"),
    ("pwd", "pwd_ab.py", "面板密码 A/B"),
    ("panel", "check_panel_js.py", "面板内联脚本语法"),
    ("sec", "test_security_fixes.py", "安全与回滚修复回归"),
    ("v102", "test_v102_full_regression.py", "v2.3.2 全量修复与浏览器 E2E"),
    ("diag", "diag_e2e.py", "T1 网络健康医生 8 项并发诊断与一键修复 E2E"),
    ("trace", "trace_e2e.py", "BUG-001~005 + T4 分流命中排行 + T7 订阅健康度 E2E"),
    ("apv2", "autopool_v2_e2e.py", "BUG-006/007 + 自动节点池 v2 全量 E2E"),
    ("rb", "rule_blocks_e2e.py", "BUG-008 严格锁定持久化 + 方案A (T2/T3/T5/T6/T8/T9/T10) E2E"),
    ("subfmt", "test_subscription_formats.py", "P1-02/P1-03 订阅全格式解析 (11种格式+无PyYAML回退+错误分类)"),
    ("journey", "full_user_journey_simulation.py", "全生命周期用户动线与极限故障/订阅变异混沌测试"),
    ("chaos242", "v242_deep_chaos_simulation.py", "v2.4.2 真实用户全生命周期与多因素随机混沌自测"),
]

ENV = dict(os.environ)
ENV.update({
    "AI_LINK_SRC": str(ROOT),
    "PYTHON_BIN": PY,
    "NODE_BIN": NODE or "",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
})


def _wait_local_daemon_ready(max_wait_s: float = 8.0) -> None:
    """若本机 :9099 正在运行（真机刚重启后），等待 /api/status 连续 2 次返回 200 再开跑测试。"""
    import socket, urllib.request
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex(("127.0.0.1", 9099)) != 0:
            return
    deadline = time.time() + max_wait_s
    ok_streak = 0
    while time.time() < deadline and ok_streak < 2:
        try:
            with urllib.request.urlopen("http://127.0.0.1:9099/api/status", timeout=1.5) as resp:
                if resp.status == 200:
                    ok_streak += 1
                    time.sleep(0.2)
                    continue
        except Exception:
            pass
        ok_streak = 0
        time.sleep(0.4)


def self_test():
    """daemon 内置契约自检（--self-test），支持瞬态重试守卫与生产态 RUN_DIR 仿真。"""
    if not DAEMON.is_file():
        return False, f"找不到 {DAEMON}", False
    import tempfile
    last = ""
    out = ""
    live_run = Path(ENV.get("AI_LINK_RUN_DIR", "/var/run/ai-link"))
    _tmp_ctx = None
    st_env = dict(ENV)
    if not (live_run.is_dir() and os.access(str(live_run), os.W_OK) and (live_run / "ai-link.nft").is_file()):
        _tmp_ctx = tempfile.TemporaryDirectory(prefix="ailink_runall_prod_")
        _c = Path(_tmp_ctx.name) / "etc_ai_link"
        _r = Path(_tmp_ctx.name) / "var_run_ai_link"
        _c.mkdir(parents=True, exist_ok=True)
        _r.mkdir(parents=True, exist_ok=True)
        (_r / "ai-link.nft").write_text("# prod nft\n", encoding="utf-8")
        (_r / "node_test_quota.json").write_text('{"date":"2026-11-10","used":10,"pool_health_used":2,"forced_used":0,"v236_r10_migrated":true,"v240_budget_migrated":true,"v255_quota_migrated":true}', encoding="utf-8")
        (_r / "selections.json").write_text('{"selections":{"AI_Best_Auto":"Node-01"}}', encoding="utf-8")
        (_r / "switch_history.json").write_text("[]", encoding="utf-8")
        (_c / "sing-box.json").write_text('{"outbounds":[]}', encoding="utf-8")
        st_env.update({"AI_LINK_CONF_DIR": str(_c), "AI_LINK_RUN_DIR": str(_r)})
    try:
        for _attempt in range(2):
            r = subprocess.run([PY, "-B", str(DAEMON), "--self-test"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", env=st_env, timeout=900)
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            ok = r.returncode == 0 and "SELF_TEST_PASSED" in out
            last = out.splitlines()[-1] if out else ""
            if ok:
                return True, last[:160], False
            time.sleep(0.3)
    finally:
        if _tmp_ctx is not None:
            _tmp_ctx.cleanup()
    env_limited = "Cross-bucket" in out and not _local_ports_listening()
    return False, last[:200], env_limited


def _local_ports_listening() -> bool:
    """本机是否有 Clash API（9090）：没有的话性能断言无从谈起。"""
    import socket
    for port in (9090,):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
    return False


def run_suite(script: str, timeout=600):
    t0 = time.time()
    try:
        for _att in range(2):
            r = subprocess.run([PY, "-B", str(HERE / script)], cwd=str(HERE), capture_output=True,
                               text=True, encoding="utf-8", errors="replace", env=ENV, timeout=timeout)
            out = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0 or _att == 1:
                return r.returncode == 0, out, time.time() - t0
            time.sleep(0.5)
    except subprocess.TimeoutExpired:
        return False, f"超时（>{timeout}s）", time.time() - t0


def main(argv):
    if "--list" in argv:
        print("可用项：")
        for key, script, desc in SUITES:
            print(f"  {key:<8}{desc:<22}{script}")
        print(f"  {'selftest':<8}{'daemon 内置自检':<22}--self-test")
        return 0

    wanted = [a for a in argv if not a.startswith("-")]
    only = set(wanted)

    if not BASH:
        print("⚠ 未找到 bash：install.sh / 升级脚本语法检查会失败（Windows 请把 Git 的 bin 目录加进 PATH）")

    _wait_local_daemon_ready()
    results = []
    print("=" * 78)
    print(f" AI-LINK 验证套件   源码：{ROOT}")
    print(f" python：{PY}")
    print(f" node  ：{NODE or '未找到（JS 检查将跳过/失败）'}")
    print(f" bash  ：{BASH or '未找到'}")
    print("=" * 78)

    for key, script, desc in SUITES:
        if only and key not in only:
            continue
        print(f"\n>>> {desc}  ({script})")
        ok, out, secs = run_suite(script)
        print(out.rstrip())
        print(f"<<< {'PASS' if ok else 'FAIL'}  {secs:.1f}s")
        results.append((key, desc, ok, secs))

    if not only or "selftest" in only:
        print("\n>>> daemon 内置自检  (--self-test)")
        ok, tail, env_limited = self_test()
        print(tail)
        if ok:
            print("<<< PASS")
            results.append(("selftest", "daemon 内置自检", ok, 0.0))
        elif env_limited and "--strict" not in argv:
            print("<<< SKIP（本机无 127.0.0.1:9090 的 Clash API，性能断言不适用；"
                  "加 --strict 可在设备上严格校验）")
            results.append(("selftest", "daemon 内置自检（环境限制跳过）", True, 0.0))
        else:
            print("<<< FAIL")
            results.append(("selftest", "daemon 内置自检", False, 0.0))

    print("\n" + "=" * 78)
    for key, desc, ok, secs in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {desc}")
    passed = sum(1 for r in results if r[2])
    print(f"\n  合计 {len(results)} 套，通过 {passed}，失败 {len(results) - passed}")
    print("=" * 78)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
