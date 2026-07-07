"""统一测试运行器：跑所有测试并汇总结果。"""
import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).parent
TESTS = [
    ("test_draft.py", "Draft 解析与基本操作"),
    ("test_e2e.py", "端到端工作流"),
    ("test_mcp.py", "MCP dispatch_tool"),
    ("test_cli.py", "CLI 命令行"),
    ("test_http.py", "HTTP API"),
    ("test_regression.py", "Bug 修复回归测试"),
]


def run_one(test_file: str, desc: str):
    print(f"\n{'='*60}")
    print(f"运行: {test_file} — {desc}")
    print(f"{'='*60}")
    start = time.time()
    r = subprocess.run(
        [sys.executable, str(TESTS_DIR / test_file)],
        capture_output=True, text=True, cwd=str(TESTS_DIR),
    )
    elapsed = time.time() - start
    # 打印最后 15 行输出
    out_lines = r.stdout.strip().split("\n")
    err_lines = r.stderr.strip().split("\n")
    if r.stdout:
        print("\n".join(out_lines[-15:]))
    if r.returncode != 0 and r.stderr:
        print("\n--- stderr ---")
        print("\n".join(err_lines[-20:]))
    status = "✓ PASS" if r.returncode == 0 else "✗ FAIL"
    print(f"\n[{status}] {test_file} ({elapsed:.1f}s)")
    return r.returncode == 0


def main():
    print("cut.skill 测试套件")
    print(f"Python: {sys.version.split()[0]}")
    print(f"测试目录: {TESTS_DIR}")

    results = []
    for tf, desc in TESTS:
        ok = run_one(tf, desc)
        results.append((tf, desc, ok))

    print(f"\n{'='*60}")
    print("汇总")
    print(f"{'='*60}")
    passed = sum(1 for _, _, ok in results if ok)
    total = len(results)
    for tf, desc, ok in results:
        mark = "✓" if ok else "✗"
        print(f"  {mark} {tf:20s} {desc}")
    print(f"\n  {passed}/{total} 通过")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
