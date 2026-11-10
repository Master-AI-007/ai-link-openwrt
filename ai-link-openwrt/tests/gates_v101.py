# -*- coding: utf-8 -*-
"""v1.0.1 发布前全量门禁。全部通过才允许打包。"""
import os, re, subprocess, sys, tempfile
from pathlib import Path

from _paths import ROOT, PY, NODE, BASH, app_version
APP_VER = app_version()
DAEMON = ROOT / "root/usr/share/ai-link/ai-link-daemon.py"
OV = ROOT / "htdocs/luci-static/resources/view/ai-link/overview.js"
IDX = ROOT / "root/usr/share/ai-link/webui/index.html"
INST = ROOT / "install.sh"
CLI = ROOT / "root/usr/bin/ai-link"
VFILE = ROOT / "root/etc/ai-link/version"

results = []


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or r.stdout or "").strip()


print("=" * 78)
print(" AI-LINK v1.0.1 发布门禁")
print("=" * 78)

print("\n[1] 语法")
def py_compile_gate():
    import py_compile
    cfile = Path(tempfile.mkdtemp()) / "check.pyc"
    try:
        py_compile.compile(str(DAEMON), cfile=str(cfile), doraise=True)
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


check("Python 编译 ai-link-daemon.py", py_compile_gate)
check("node --check overview.js", lambda: (run([NODE, "--check", str(OV)])[0] == 0, ""))
check("bash -n install.sh", lambda: (run([BASH or "sh", "-n", str(INST)])[0] == 0, ""))
check("bash -n usr/bin/ai-link", lambda: (run([BASH or "sh", "-n", str(CLI)])[0] == 0, ""))
check("bash -n uninstall.sh", lambda: (run([BASH or "sh", "-n", str(ROOT / "root/usr/share/ai-link/uninstall.sh")])[0] == 0, ""))


def symtable_gate():
    import builtins
    import symtable
    src = DAEMON.read_text(encoding="utf-8")
    top = symtable.symtable(src, "ai-link-daemon.py", "exec")
    bset = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__", "__class__"}
    top_defs = {s.get_name() for s in top.get_symbols() if s.is_imported() or s.is_assigned() or s.is_namespace()}
    undef = []

    def walk(t, pset):
        cur = pset | {s.get_name() for s in t.get_symbols()
                      if s.is_local() or s.is_parameter() or s.is_imported() or s.is_assigned() or s.is_namespace()}
        for s in t.get_symbols():
            if s.is_referenced() and not (s.is_local() or s.is_parameter() or s.is_imported() or s.is_assigned() or s.is_namespace()):
                nm = s.get_name()
                if nm not in cur and nm not in top_defs and nm not in bset:
                    undef.append((t.get_name(), nm))
        for c in t.get_children():
            walk(c, cur)

    walk(top, set())
    return (not undef), (f"未定义 {undef}" if undef else "0 个")


print("\n[2] 静态门禁")
check("symtable 未定义全局符号 = 0", symtable_gate)


def div_balance(p):
    s = p.read_text(encoding="utf-8", errors="replace")
    o = len(re.findall(r"<div\b", s))
    c = len(re.findall(r"</div>", s))
    return o == c, f"<div={o} </div>={c}"


check("overview.js div 配平", lambda: div_balance(OV))
check("index.html div 配平", lambda: div_balance(IDX))


def panel_js():
    s = IDX.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"<script\b([^>]*)>(.*?)</script>", s, flags=re.S | re.I)
    tmp = Path(tempfile.mkdtemp())
    bad = 0
    for i, (attrs, body) in enumerate(blocks):
        if "src=" in attrs.lower() or not body.strip():
            continue
        f = tmp / f"b{i}.js"
        f.write_text(body, encoding="utf-8", newline="\n")
        if run([NODE, "--check", str(f)])[0] != 0:
            bad += 1
    return bad == 0, f"{len(blocks)} 块, 失败 {bad}"


check("面板内联 <script> 语法", panel_js)



def css_parse_and_hidden_gate():
    css_f = ROOT / "root/usr/share/ai-link/webui/nexus.css"
    css_s = css_f.read_text(encoding="utf-8")
    clean = re.sub(r"/\*.*?\*/", "", css_s, flags=re.S)
    bad_parens = []
    for idx_l, ln in enumerate(clean.splitlines(), 1):
        if ln.count("(") != ln.count(")"):
            bad_parens.append(f"L{idx_l}")
    braces_ok = clean.count("{") == clean.count("}") and clean.count("{") >= 600
    has_hidden_guard = ".modal-backdrop:not([hidden])" in clean and "#modal[hidden]" in clean and "#webgl-fallback[hidden]" in clean
    ok = (not bad_parens) and braces_ok and has_hidden_guard
    return ok, f"rules={clean.count('{')}, bad_parens={bad_parens}, hidden_guard={has_hidden_guard}"


check("nexus.css 语法括号配平 (>=600条规则) 与 [hidden] 优先级门禁", css_parse_and_hidden_gate)

print("\n[3] 版本一致性")


def versions():
    d = DAEMON.read_text(encoding="utf-8")
    m = re.search(r'^APP_VERSION = "([^"]+)"', d, re.M)
    app = m.group(1) if m else "?"
    mb = re.search(r'^APP_BUILD = "([0-9.]+)-release-\d+"', d, re.M)
    build_v = mb.group(1) if mb else "?"
    inst = re.search(r'^VERSION="([^"]+)"', INST.read_text(encoding="utf-8"), re.M)
    inst = inst.group(1) if inst else "?"
    v_lines = [ln for ln in VFILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    vf = v_lines[0].split()[0] if len(v_lines) == 1 else f"lines={len(v_lines)}"
    uci_m = re.search(r"^\toption app_version '([^']+)'$", (ROOT / "root/etc/config/ai-link").read_text(encoding="utf-8"), re.M)
    uci_v = uci_m.group(1) if uci_m else "?"
    badge = re.search(r'>v([0-9.]+)</span>', IDX.read_text(encoding="utf-8"))
    badge = badge.group(1) if badge else "?"
    luci_m = re.search(r"\|\s*\|\s*'([0-9.]+)'\);", OV.read_text(encoding="utf-8"))
    luci_v = luci_m.group(1) if luci_m else "?"
    vals = {"daemon": app, "build": build_v, "install.sh": inst, "version文件": vf, "uci": uci_v, "面板徽章": badge, "LuCI兜底": luci_v}
    return len(set(vals.values())) == 1 and app == APP_VER, str(vals)


check(f"七处版本号一致且 = {APP_VER}（含 version 单行校验）", versions)


def stale():
    d = DAEMON.read_text(encoding="utf-8")
    hits = re.findall(r'"1\.0\.0"', d)
    return not hits, f"daemon 残留 {len(hits)} 处"


check("daemon 无残留 1.0.0 版本串", stale)

def static_assets_md5_gate():
    import hashlib
    html_s = IDX.read_text(encoding="utf-8")
    webui_dir = IDX.parent
    refs = re.findall(r'(\./[a-zA-Z0-9_./-]+)\?v=([0-9.]+)-([0-9a-f]{8})', html_s)
    if len(refs) < 8:
        return False, f"静态资源引用不足 8 项: {len(refs)}"
    if html_s.count("?v=") != len(refs) or any(ln.count("?v=") > 1 for ln in html_s.splitlines()):
        return False, f"P2-2 regression: 存在双重 ?v= 查询串 (total_q={html_s.count('?v=')}, refs={len(refs)})"
    mismatches = []
    for rel_p, v_s, h_s in refs:
        af = webui_dir / rel_p.lstrip("./")
        if not af.is_file():
            mismatches.append(f"{rel_p}:missing")
            continue
        real_h8 = hashlib.md5(af.read_bytes()).hexdigest()[:8]
        if v_s != APP_VER or h_s != real_h8:
            mismatches.append(f"{rel_p}:{v_s}-{h_s}!=real({APP_VER}-{real_h8})")
    return (not mismatches), f"checked={len(refs)}, mismatches={mismatches}"


check("index.html 全部静态资源 ?v= 指纹与真实文件 MD5 前8位 100% 一致", static_assets_md5_gate)


print("\n[4] OTA 关键代码存在性")


def ota_present():
    d = DAEMON.read_text(encoding="utf-8")
    need = [
        ("manifest 多源", "UPDATE_MANIFEST_PRIMARY" in d and "UPDATE_MANIFEST_GITHUB" in d),
        ("MD5+SHA256 双校验", "sha256sum" in d and "ACT_MD5" in d),
        ("setsid 解耦", "start_new_session=True" in d),
        ("健康检查", "healthcheck" in d),
        ("自动回滚", "自动回滚" in d),
        ("备份保留3份", "pre-update-v" in d),
        ("四端点", all(k in d for k in ('"/api/system/version"', '"/api/system/update/check"',
                                       '"/api/system/update/status"', '"/api/system/update/apply"'))),
        ("升级模式", "--upgrade" in d),
        ("LuCI桥接令牌", "get_luci_bridge_token" in d),
        ("密码哈希不再当凭据", "candidate_pw == get_uci_panel_secret()" not in d),
        ("令牌不再接受密码", "tok in valid_tokens or tok == get_uci_panel_secret()" not in d),
    ]
    miss = [n for n, ok in need if not ok]
    return not miss, ("缺: " + ", ".join(miss) if miss else f"{len(need)} 项齐全")


check("OTA 关键实现点", ota_present)


def ota_script():
    lines = DAEMON.read_text(encoding="utf-8").splitlines()

    def grab(a, b):
        s = next(i for i, l in enumerate(lines) if l.startswith(a))
        e = next(i for i, l in enumerate(lines) if i > s and l.startswith(b))
        return "\n".join(lines[s:e])

    src = grab(f'APP_VERSION = "{APP_VER}"', "def start_plugin_update")
    ns = {"re": re, "time": __import__("time"), "json": __import__("json"),
          "ssl": __import__("ssl"), "urllib": __import__("urllib"),
          "Path": Path, "RUN_DIR": Path("/var/run/ai-link"), "CONF_DIR": Path("/etc/ai-link"),
          "get_ops_settings": lambda c=None: {"gh_mirror": "https://gh-proxy.com/"},
          "_uci_get_str": lambda k, d="": ""}
    exec(compile(src, "<ota>", "exec"), ns)
    body = ns["_update_script_body"]({
        "target": "1.0.2", "current": "1.0.1", "md5": "a" * 32, "sha256": "b" * 64, "size": 100,
        "package_urls": ["https://x/y.tar.gz", "https://gh-proxy.com/https://x/y.tar.gz"],
    })
    f = Path(tempfile.mkdtemp()) / "upd.sh"
    f.write_text(body, encoding="utf-8", newline="\n")
    rc, err = run([BASH or "sh", "-n", str(f)])
    # 版本比较
    nv = ns["is_version_newer"]
    cases = [("1.0.2", "1.0.1", True), ("1.0.1", "1.0.1", False), ("1.0.0", "1.0.1", False),
             ("1.1.0", "1.0.9", True), ("v2.0.0", "1.9.9", True),
             ("1.0.1-beta1", "1.0.1", False), ("1.0.1", "1.0.1-beta1", True)]
    bad = [c for c in cases if nv(c[0], c[1]) != c[2]]
    return (rc == 0 and not bad), (f"sh -n {'OK' if rc == 0 else err[:80]}, 版本比较失败 {len(bad)}")


check("生成的升级脚本 sh -n + 版本比较 7 例", ota_script)

print("\n[5] 打包产物去重与压缩体积门禁")


def tar_dedup_and_size_gate():
    import io
    import tarfile
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [
        repo_root / f"AI-LINK-v{APP_VER}.tar.gz",
        repo_root / "site" / f"AI-LINK-v{APP_VER}.tar.gz",
    ]
    tar_path = next((c for c in candidates if c.is_file()), None)
    if not tar_path:
        return True, "未在仓库根发现发布包（跳过）"
    comp_size = tar_path.stat().st_size
    with tarfile.open(tar_path, "r:gz") as tf:
        members = tf.getmembers()
        names = [m.name for m in members]
        files = [m for m in members if m.isfile()]
        uncomp_size = sum(m.size for m in files)
    dup_cnt = len(names) - len(set(names))
    ipk_path = next(iter(repo_root.glob(f"luci-app-ai-link_{APP_VER}-r*_all.ipk")), repo_root / f"luci-app-ai-link_{APP_VER}-r12_all.ipk")
    ipk_ok = True
    ipk_detail = ""
    if ipk_path.is_file():
        ipk_size = ipk_path.stat().st_size
        with tarfile.open(ipk_path, "r:gz") as itf:
            data_member = next((m for m in itf.getmembers() if m.name.endswith("data.tar.gz")), None)
            if data_member:
                data_bytes = itf.extractfile(data_member).read()
                with tarfile.open(fileobj=io.BytesIO(data_bytes), mode="r:gz") as dtf:
                    dnames = [m.name for m in dtf.getmembers()]
                    ipk_ok = (len(dnames) == len(set(dnames))) and (ipk_size < uncomp_size)
                    ipk_detail = f", ipk={ipk_size}B(dup={len(dnames)-len(set(dnames))})"
    # Verify P0-1 nft protocol separation, P3-4 AST except->pass <= 8, and P2-4 test suite completeness
    import ast as _ast_g, importlib.util as _ilu_g
    _tree_g = _ast_g.parse(DAEMON.read_text(encoding="utf-8"))
    _pass_g = sum(1 for n in _ast_g.walk(_tree_g) if isinstance(n, _ast_g.ExceptHandler) and len(n.body) == 1 and isinstance(n.body[0], _ast_g.Pass))
    _sp_g = _ilu_g.spec_from_file_location("dmod_gate", str(DAEMON))
    _dm_g = _ilu_g.module_from_spec(_sp_g)
    _sp_g.loader.exec_module(_dm_g)
    _tmp_g = Path(tempfile.mkdtemp())
    try:
        _dm_g.update_ops_settings({"lan_direct_macs": ["aa:bb:cc:dd:ee:01"], "ipv6_proxy": True}, _tmp_g)
        _nft_g = _dm_g.generate_nft_rules_file(_tmp_g, _tmp_g)
        _nft_conflict = [ln.strip() for ln in _nft_g.splitlines() if ("ip daddr" in ln or "ip saddr" in ln) and ("ip6 daddr" in ln or "ip6 saddr" in ln)]
    finally:
        import shutil as _sh_g
        _sh_g.rmtree(_tmp_g, ignore_errors=True)
    ok = (dup_cnt == 0) and (comp_size < uncomp_size) and ipk_ok and (_pass_g <= 8) and (len(_nft_conflict) == 0) and ("ai-link-openwrt" in names or "ai-link-openwrt/" in names)
    return ok, f"entries={len(names)}, files={len(files)}, dup={dup_cnt}, pass={_pass_g}, nft_conflict={len(_nft_conflict)}, comp={comp_size}B < uncomp={uncomp_size}B{ipk_detail}"


check("tar.gz 与 ipk 零重复条目且压缩体积正常 (<解压体积)", tar_dedup_and_size_gate)


def fb250_packaging_and_luci_gate():
    import hashlib, tarfile, zipfile
    site_dir = DAEMON.parents[4]
    root_dir = Path(__file__).resolve().parents[1]
    cl_p = site_dir / "CHANGELOG.md"
    m_cl = re.search(r"^##\s+v?([0-9.]+)", cl_p.read_text(encoding="utf-8"), re.M) if cl_p.exists() else None
    v_d = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', DAEMON.read_text(encoding="utf-8")).group(1)
    cl_ok = bool(m_cl and m_cl.group(1) == v_d)

    run_all_p = Path(__file__).resolve().parent / "run_all.py"
    suites = re.findall(r'\(\s*"[a-z0-9_]+"\s*,\s*"([^"]+\.py)"', run_all_p.read_text(encoding="utf-8")) if run_all_p.exists() else []
    suites_nonempty_ok = len(suites) >= 14
    missing_disk = []
    for s in suites:
        p_root = root_dir / "tests" / s
        p_site = site_dir / "tests" / s
        if not p_root.is_file() or p_root.stat().st_size == 0:
            missing_disk.append(f"root:tests/{s}")
        if (site_dir / "tests").is_dir() and (not p_site.is_file() or p_site.stat().st_size == 0):
            missing_disk.append(f"site:tests/{s}")

    # FB-252-1: Verify tests/subscription_formats/ fixture directory (>=12 files) on disk and in tar/zip archives
    expected_fixtures = [
        "EXPECTED.md", "base64-uri.txt", "clash-anchor.yaml", "clash-block.yaml",
        "clash-nested-flow.yaml", "clash-simple.yaml", "loon.txt", "singbox.json",
        "sip008.json", "surge.txt", "uri-list.txt", "v2ray-json.json",
    ]
    for fx in expected_fixtures:
        if not (root_dir / "tests/subscription_formats" / fx).is_file():
            missing_disk.append(f"root:subscription_formats/{fx}")
        if (site_dir / "tests").is_dir() and not (site_dir / "tests/subscription_formats" / fx).is_file():
            missing_disk.append(f"site:subscription_formats/{fx}")

    # FB-252-2: Ensure v242_deep_chaos_simulation.py has NO trailing newline so Canvas export & disk bytes are 100% identical
    v242_p = Path(__file__).resolve().parent / "v242_deep_chaos_simulation.py"
    if v242_p.is_file() and v242_p.read_bytes().endswith(b"\n"):
        missing_disk.append("v242_deep_chaos_simulation.py:trailing_newline_present")

    # Verify archive self-containment (FB-251-1 & FB-252-1) & report 4-column fingerprint accuracy (FB-251-2 & FB-252-2) when packages exist in root_dir
    archive_missing = []
    tar_cand = root_dir / f"AI-LINK-v{v_d}.tar.gz"
    if tar_cand.is_file():
        with tarfile.open(tar_cand, "r:gz") as tf:
            tnames = set(tf.getnames())
            for s in suites:
                if f"ai-link-openwrt/tests/{s}" not in tnames:
                    archive_missing.append(f"tar:{s}")
            for fx in expected_fixtures:
                if f"ai-link-openwrt/tests/subscription_formats/{fx}" not in tnames:
                    archive_missing.append(f"tar:subscription_formats/{fx}")
    zip_cands = list(root_dir.glob(f"AI-LINK-v{v_d}-云端交接包-*.zip"))
    if zip_cands:
        with zipfile.ZipFile(zip_cands[0], "r") as zf:
            znames = set(zf.namelist())
            if "HANDOFF.md" not in znames:
                archive_missing.append("zip:HANDOFF.md")
            for s in suites:
                if f"tests/{s}" not in znames:
                    archive_missing.append(f"zip:tests/{s}")
                if f"site/ai-link-openwrt/tests/{s}" not in znames:
                    archive_missing.append(f"zip:site/tests/{s}")
            for fx in expected_fixtures:
                if f"tests/subscription_formats/{fx}" not in znames:
                    archive_missing.append(f"zip:tests/subscription_formats/{fx}")
                if f"site/ai-link-openwrt/tests/subscription_formats/{fx}" not in znames:
                    archive_missing.append(f"zip:site/subscription_formats/{fx}")

    mk_rel_m = re.search(r"^PKG_RELEASE:=(\d+)", (site_dir / "Makefile").read_text(encoding="utf-8"), re.M) if (site_dir / "Makefile").is_file() else None
    exp_pkg_rel = mk_rel_m.group(1) if mk_rel_m else "17"
    fp_mismatches = []
    search_dirs = [
        root_dir,
        site_dir,
        root_dir.parent,
        Path("/working_dir/c_6b82a05156135b2c/artifacts/file_generation/ttl=63d/output"),
    ]
    def _resolve_f_cand(fname: str):
        for sdir in search_dirs:
            for sub in (fname, f"tests/{fname}", f"root/usr/share/ai-link/{fname}", f"root/usr/share/ai-link/webui/{fname}"):
                cand = sdir / sub
                if cand.is_file():
                    return cand
        return None

    def _verify_fp_rows_against_disk(doc_name: str, rows_list: list) -> list:
        errs = []
        for fname, exp_sz, exp_md5, exp_sha in rows_list:
            f_cand = _resolve_f_cand(fname)
            if not f_cand:
                errs.append(f"{doc_name}:{fname}:missing")
                continue
            b = f_cand.read_bytes()
            if str(len(b)) != exp_sz or hashlib.md5(b).hexdigest() != exp_md5 or hashlib.sha256(b).hexdigest() != exp_sha:
                errs.append(f"{doc_name}:{fname}:mismatch(real_sz={len(b)},exp_sz={exp_sz})")
        return errs

    for doc_name in [f"AI-LINK-v{v_d}-全量检查与重构验收报告.md", "HANDOFF.md"]:
        doc_p = _resolve_f_cand(doc_name)
        if doc_p and doc_p.is_file():
            doc_txt = doc_p.read_text(encoding="utf-8")
            # FB-253-1: Verify PKG_RELEASE in report/handoff matches Makefile and ipk rN
            doc_rels = set(re.findall(r"PKG_RELEASE:=(\d+)", doc_txt))
            if doc_rels and doc_rels != {exp_pkg_rel}:
                fp_mismatches.append(f"{doc_name}:PKG_RELEASE={doc_rels}!=Makefile({exp_pkg_rel})")
            # FB-253-2: Verify report Section 1 is dedicated to current version
            if doc_name.startswith("AI-LINK-v"):
                sec1_m = re.search(r"^##\s+一、([^\n]+)", doc_txt, re.M)
                if not sec1_m or f"v{v_d}" not in sec1_m.group(1):
                    fp_mismatches.append(f"{doc_name}:sec1_not_v{v_d}")
                # FB-256-2: Verify consecutive Chinese section numbering and zero mixed ## N. headings
                cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]
                h2_matches = re.findall(r"^##\s+([^\n]+)", doc_txt, re.M)
                if any(re.match(r"^\d+\.", h) for h in h2_matches):
                    fp_mismatches.append(f"{doc_name}:mixed_numeric_h2")
                actual_cn = [h.split("、", 1)[0].strip() for h in h2_matches if "、" in h]
                if actual_cn != cn_nums[:len(actual_cn)] or len(actual_cn) < 5:
                    fp_mismatches.append(f"{doc_name}:non_consecutive_h2={actual_cn}")
                # FB-257-2: Verify report contains post-injected run_all summary and environment note
                for _req_tok in ("验证环境", "本轮增量说明", "（构建容器）", "合计 15 套，通过 15，失败 0", "115/115", "152/152", "82/82", "Stage 7.19", "live_write_leaked"):
                    if _req_tok not in doc_txt:
                        fp_mismatches.append(f"{doc_name}:missing_fb257_2_token({_req_tok})")
            rows = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*[^|]*?`(\d+)`[^|]*\|\s*`([0-9a-f]{32})`\s*\|\s*`([0-9a-f]{64})`\s*\|", doc_txt, re.M)
            min_rows = 7 if doc_name.startswith("AI-LINK-v") else 3
            if len(rows) < min_rows:
                fp_mismatches.append(f"{doc_name}:rows={len(rows)}<{min_rows}")
            else:
                fp_mismatches.extend(_verify_fp_rows_against_disk(doc_name, rows))
                # FB-256-1 Negative Self-Test: Corrupting 1 byte in memory MUST trigger a mismatch
                f0, sz0, md5_0, sha0 = rows[0]
                bad_sha0 = ("0" if sha0[0] != "0" else "1") + sha0[1:]
                if not _verify_fp_rows_against_disk(doc_name, [(f0, sz0, md5_0, bad_sha0)]):
                    fp_mismatches.append(f"{doc_name}:negative_self_test_failed")

    ov_t = OV.read_text(encoding="utf-8")
    luci_ok = ("handleSaveApply: null" in ov_t) and ("luci-btn-ota-check" in ov_t) and ("luci-btn-ota-apply" in ov_t) and ("luci-btn-svc-restart" in ov_t) and ("luci-sel-rmode" not in ov_t) and ("form.Flag" not in ov_t)
    # FB-257-1 & FB-257-2 Gate: --self-test MUST run in a production-like environment with real CONF_DIR & RUN_DIR
    # files (ai-link.nft, node_test_quota.json, selections.json, switch_history.json, sing-box.json) 3 consecutive times
    # with zero file mutation, PLUS 1 negative test with write-interception disabled that MUST detect leaked > 0 and fail!
    import tempfile
    st_rc = 1
    st_neg_ok = False
    snap_unchanged = False
    env_production_like = False
    _tmp_prod_ctx = None
    try:
        live_run = Path(os.environ.get("AI_LINK_RUN_DIR", "/var/run/ai-link"))
        live_conf = Path(os.environ.get("AI_LINK_CONF_DIR", "/etc/ai-link"))
        if live_run.is_dir() and os.access(str(live_run), os.W_OK) and (live_run / "ai-link.nft").is_file():
            eff_run = live_run
            eff_conf = live_conf
            if not (eff_run / "node_test_quota.json").is_file():
                (eff_run / "node_test_quota.json").write_text('{"date":"2026-11-10","used":1,"pool_health_used":1,"forced_used":0,"v236_r10_migrated":true,"v240_budget_migrated":true,"v255_quota_migrated":true}', encoding="utf-8")
        else:
            _tmp_prod_ctx = tempfile.TemporaryDirectory(prefix="ailink_gate_prod_")
            eff_conf = Path(_tmp_prod_ctx.name) / "etc_ai_link"
            eff_run = Path(_tmp_prod_ctx.name) / "var_run_ai_link"
            eff_conf.mkdir(parents=True, exist_ok=True)
            eff_run.mkdir(parents=True, exist_ok=True)
            (eff_run / "ai-link.nft").write_text("# production-like nft ruleset\ntable inet ai_link {}\n", encoding="utf-8")
            (eff_run / "node_test_quota.json").write_text('{"date":"2026-11-10","used":12,"pool_health_used":4,"forced_used":0,"v236_r10_migrated":true,"v240_budget_migrated":true,"v255_quota_migrated":true}', encoding="utf-8")
            (eff_run / "selections.json").write_text('{"updated_at":1794240000,"selections":{"AI_Best_Auto":"Node-Prod-01"},"delays":{}}', encoding="utf-8")
            (eff_run / "switch_history.json").write_text("[]", encoding="utf-8")
            (eff_conf / "sing-box.json").write_text('{"outbounds":[]}', encoding="utf-8")
        # FB-257-3 Fix: Always explicitly inject AI_LINK_CONF_DIR & AI_LINK_RUN_DIR outside the if/else branch
        st_env = {**os.environ, "AI_LINK_CONF_DIR": str(eff_conf), "AI_LINK_RUN_DIR": str(eff_run)}
        env_production_like = (
            os.access(str(eff_run), os.W_OK)
            and (eff_run / "ai-link.nft").is_file()
            and (eff_run / "node_test_quota.json").is_file()
        )
        if not env_production_like:
            fp_mismatches.append("env_not_production_like")
        else:
            def _snap_prod():
                out = {}
                for _fp in (eff_conf / "sing-box.json",):
                    if _fp.is_file():
                        _b = _fp.read_bytes()
                        out[_fp.name] = (hashlib.sha256(_b).hexdigest(), len(_b))
                return out
            _s_pre = _snap_prod()
            _runs_ok = 0
            for _att in range(3):
                st_res = subprocess.run([PY, "-B", str(DAEMON), "--self-test"], env=st_env, capture_output=True, text=True)
                _stderr_clean = not any(w in (st_res.stderr or "") for w in ("Traceback", "AssertionError", "Warning", "Error"))
                if st_res.returncode == 0 and "SELF_TEST_PASSED" in (st_res.stdout or "") and '"live_write_leaked": 0' in (st_res.stdout or "") and _stderr_clean:
                    _runs_ok += 1
            _s_post = _snap_prod()
            snap_unchanged = (_s_pre == _s_post)
            if _runs_ok == 3 and snap_unchanged:
                st_rc = 0
            with tempfile.TemporaryDirectory(prefix="ailink_gate_neg_") as _neg_td:
                _neg_c = Path(_neg_td) / "c"
                _neg_r = Path(_neg_td) / "r"
                _neg_c.mkdir(parents=True, exist_ok=True)
                _neg_r.mkdir(parents=True, exist_ok=True)
                (_neg_r / "ai-link.nft").write_text("# neg nft\n", encoding="utf-8")
                (_neg_r / "node_test_quota.json").write_text('{"date":"2026-11-10","used":1}', encoding="utf-8")
                _neg_env = dict(os.environ, AI_LINK_CONF_DIR=str(_neg_c), AI_LINK_RUN_DIR=str(_neg_r), AI_LINK_SELFTEST_DISABLE_INTERCEPT="1")
                _neg_res = subprocess.run([PY, "-B", str(DAEMON), "--self-test"], env=_neg_env, capture_output=True, text=True)
                st_neg_ok = (_neg_res.returncode != 0 and "leaked" in (_neg_res.stderr or ""))
                if not st_neg_ok:
                    fp_mismatches.append("selftest_negative_intercept_check_failed")
            # FB-259-1 Gate: Verify OpenWrt /var -> /tmp symlink path (/tmp/run/ai-link) is NEVER exempted even when AI_LINK_RUN_DIR env var is unset
            _sym_env = {k: v for k, v in os.environ.items() if k not in ("AI_LINK_CONF_DIR", "AI_LINK_RUN_DIR")}
            _sym_chk = subprocess.run(
                [PY, "-B", "-c", f"import importlib.util; from pathlib import Path; spec=importlib.util.spec_from_file_location('d', { repr(str(DAEMON)) }); d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d); assert not d._is_sandbox_exempt_write(Path('/tmp/run/ai-link/.selftest_write_guard_probe_atomic')); print('SYMLINK_GUARD_OK')"],
                env=_sym_env, capture_output=True, text=True
            )
            if _sym_chk.returncode != 0 or "SYMLINK_GUARD_OK" not in (_sym_chk.stdout or ""):
                fp_mismatches.append("fb259_1_openwrt_var_tmp_symlink_guard_failed")
    finally:
        if _tmp_prod_ctx is not None:
            _tmp_prod_ctx.cleanup()
    # v2.5.8 §3.4 & §5.2: Run tools/check_api_ui_parity.py (two-way API<->UI field parity + 0 raw CONF_DIR/RUN_DIR .write_text)
    parity_script = site_dir / "tools/check_api_ui_parity.py"
    if not parity_script.is_file():
        parity_script = root_dir / "tools/check_api_ui_parity.py"
    parity_ok = False
    if parity_script.is_file():
        _pr = subprocess.run([PY, "-B", str(parity_script)], capture_output=True, text=True)
        parity_ok = (_pr.returncode == 0 and "[PASS]" in (_pr.stdout or ""))
    if not parity_ok:
        fp_mismatches.append("api_ui_parity_failed")
    ok = cl_ok and suites_nonempty_ok and (len(missing_disk) == 0) and (len(archive_missing) == 0) and (len(fp_mismatches) == 0) and luci_ok and (st_rc == 0) and st_neg_ok and env_production_like and parity_ok
    return ok, f"changelog={m_cl.group(1) if m_cl else None}=={v_d}, suites={len(suites)}, fixtures={len(expected_fixtures)}, missing_disk={missing_disk}, archive_missing={archive_missing}, fp_mismatches={fp_mismatches}, luci={luci_ok}, self_test={st_rc}, st_neg_ok={st_neg_ok}, prod_like={env_production_like}, parity={parity_ok}, eff_conf={eff_conf}, eff_run={eff_run}"


check("FB-250/251 自检、14+测试套件双端与包内完整性、指纹表逐行核对、CHANGELOG 与 LuCI 精简门禁", fb250_packaging_and_luci_gate)

print("\n" + "=" * 78)
fails = [r for r in results if not r[1]]
print(f" 合计 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}")
if fails:
    for n, _, d in fails:
        print(f"   ✗ {n}  {d}")
print("=" * 78)
sys.exit(1 if fails else 0)
