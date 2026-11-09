# -*- coding: utf-8 -*-
"""在 self-test 失败时也能打印 profile 的包装器（诊断用，不修改 daemon）。"""
import cProfile
import io
import pstats
import runpy
import sys
import traceback

target = r"F:\deepailink\project\site\ai-link-openwrt\root\usr\share\ai-link\ai-link-daemon.py"
sys.argv = [target, "--self-test"]

prof = cProfile.Profile()
buf = io.StringIO()
try:
    prof.enable()
    runpy.run_path(target, run_name="__main__")
except SystemExit:
    pass
except Exception:
    traceback.print_exc()
finally:
    prof.disable()
    st = pstats.Stats(prof, stream=buf)
    st.sort_stats("cumulative").print_stats(35)
    print(buf.getvalue())
