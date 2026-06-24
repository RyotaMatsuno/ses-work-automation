#!/usr/bin/env python3
"""agreement_checker + gate_check 統合テスト"""

import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")

print("=" * 60)
print("TEST 1: agreement_checker.run_dual_review() 動作確認")
print("=" * 60)
sys.path.insert(0, base)
from gate_checker.agreement_checker import run_dual_review

decision = run_dual_review(
    system_prompt="あなたはコードレビュー専門AIです。以下の内容を確認し、最後に必ず【判定: GO】【判定: 条件付きGO】【判定: NG】のいずれかで判定してください。",
    user_prompt="# テスト用SPEC\n## 概要\nHello Worldを出力するスクリプトを作る。\n## 完了条件\npython hello.py が正常に動くこと。",
)
print(f"GPT判定: {decision.gpt_result.judgment}")
print(f"Gemini判定: {decision.gemini_result.judgment} (available={decision.gemini_available})")
print(f"合意: {decision.agreement} / 採用: {decision.adopted_model}")
print(f"最終: {decision.final_judgment} (verdict={decision.final_verdict})")

print()
print("=" * 60)
print("TEST 2: gate_check.py --phase requirements の実行")
print("=" * 60)
spec_content = "# テストSPEC\n## 概要\nHello Worldスクリプト。\n## 完了条件\n動作確認済み。"
import tempfile

tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False)
tmp.write(spec_content)
tmp.close()
r = subprocess.run(
    [
        sys.executable,
        os.path.join(base, "gate_checker", "gate_check.py"),
        "--phase",
        "requirements",
        "--file",
        tmp.name,
    ],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    cwd=base,
    timeout=90,
)
print(r.stdout[-800:] if len(r.stdout) > 800 else r.stdout)
if r.stderr:
    print("STDERR:", r.stderr[:200])
print(f"exit code: {r.returncode}")
os.unlink(tmp.name)

print()
print("=" * 60)
print("TEST 3: task_runner.py save の gate_on_save 動作確認（--dry-run相当）")
print("=" * 60)
# gate_on_save=False で直接保存動作だけ確認
r2 = subprocess.run(
    [
        sys.executable,
        os.path.join(base, "local_server", "task_runner.py"),
        "save",
        "--title",
        "test_gate_patch",
        "--content",
        "テスト指示書",
    ],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    cwd=base,
    timeout=120,
)
print(r2.stdout[-600:] if len(r2.stdout) > 600 else r2.stdout)
if r2.stderr:
    print("STDERR:", r2.stderr[:200])
print(f"exit code: {r2.returncode}")
