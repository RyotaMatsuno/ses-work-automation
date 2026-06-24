#!/usr/bin/env python3
"""gate_check.py パッチスクリプト: GPT単独 → GPT+Gemini並列（agreement_checker統合）"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
gc_path = os.path.join(base, "gate_checker", "gate_check.py")

src = open(gc_path, encoding="utf-8").read()

# ① importに agreement_checker を追加
old_imports = "from typing import Any"
new_imports = """from typing import Any
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from agreement_checker import run_dual_review, AgreementDecision"""

# すでにパッチ済みなら中断
if "run_dual_review" in src:
    print("既にパッチ済みです。スキップ。")
    sys.exit(0)

src = src.replace(
    old_imports,
    old_imports
    + "\n\n# agreement_checker (GPT+Gemini並列)\ntry:\n    from gate_checker.agreement_checker import run_dual_review, AgreementDecision\nexcept ImportError:\n    from agreement_checker import run_dual_review, AgreementDecision",
)

# ② api_key取得部分の直後に gemini_key 取得を追加
old_apikey = '    api_key = env.get("OPENAI_API_KEY", "")\n    if not api_key:\n        logger.error("OPENAI_API_KEYが設定されていません（config/.env）")\n        return 1'
new_apikey = '    api_key = env.get("OPENAI_API_KEY", "")\n    if not api_key:\n        logger.error("OPENAI_API_KEYが設定されていません（config/.env）")\n        return 1\n    # Geminiキーはフォールバック可なので必須チェックしない\n    # gemini_keyはagreement_checker内部で_load_env()して使用'
src = src.replace(old_apikey, new_apikey)

# ③ call_gpt4o呼び出しブロック全体をrun_dual_reviewに差し替え
old_block = """    try:
        review_text, in_tokens, out_tokens = call_gpt4o(system_prompt, user_prompt, api_key)
    except Exception as exc:
        logger.error("API呼び出しエラー: %s", exc)
        payload = {
            "timestamp": datetime.now(JST).isoformat(),
            "phase": phase,
            "target_file": str(target_file) if target_file else None,
            "target_dir": str(target_dir) if target_dir else None,
            "tasks_file": str(tasks_path) if tasks_path else None,
            "verdict": "ERROR",
            "judgment": "ERROR",
            "review_text": str(exc),
            "model": REVIEW_MODEL,
            "input_tokens": 0,
            "output_tokens": 0,
            "daily_count": current_count,
            "needs_human_review": False,
        }
        save_result(payload)
        return 1

    daily_count = increment_daily_counter()
    judgment, verdict = parse_judgment(review_text)
    human_review = resolve_human_review(verdict, phase, review_text)"""

new_block = """    # ── GPT-4o + Gemini 並列レビュー ──────────────────────────
    try:
        decision = run_dual_review(system_prompt, user_prompt, env)
        review_text = decision.adopted_result.text
        judgment = decision.final_judgment
        verdict = decision.final_verdict
        gpt_text = decision.gpt_result.text
        gemini_text = decision.gemini_result.text if decision.gemini_available else "(Geminiフォールバック)"
        in_tokens = 0   # agreement_checker内で計上
        out_tokens = 0
        logger.info(
            "2AI合意判定: GPT=%s / Gemini=%s → %s (%s)",
            decision.gpt_result.judgment,
            decision.gemini_result.judgment,
            decision.final_judgment,
            "一致" if decision.agreement else "不一致→保守的",
        )
    except Exception as exc:
        logger.error("API呼び出しエラー: %s", exc)
        payload = {
            "timestamp": datetime.now(JST).isoformat(),
            "phase": phase,
            "target_file": str(target_file) if target_file else None,
            "target_dir": str(target_dir) if target_dir else None,
            "tasks_file": str(tasks_path) if tasks_path else None,
            "verdict": "ERROR",
            "judgment": "ERROR",
            "review_text": str(exc),
            "model": "gpt-4o+gemini",
            "input_tokens": 0,
            "output_tokens": 0,
            "daily_count": current_count,
            "needs_human_review": False,
        }
        save_result(payload)
        return 1

    daily_count = increment_daily_counter()
    human_review = resolve_human_review(verdict, phase, review_text)"""

src = src.replace(old_block, new_block)

# ④ payloadのmodel欄を更新
src = src.replace(
    '"model": REVIEW_MODEL,',
    '"model": "gpt-4o+gemini",\n        "gpt_review": gpt_text if "gpt_text" in dir() else "",\n        "gemini_review": gemini_text if "gemini_text" in dir() else "",',
)

# ⑤ コンソール出力に両AI結果を追加
old_print = '    print(f"\\n{\'=\'*60}")\n    print(review_text)\n    print(f"{\'=\'*60}")\n    print(f"判定: {judgment} → verdict={verdict}")\n    print(f"松野確認: {\'要\' if human_review else \'不要\'}")\n    print(f"本日の使用回数: {daily_count}/{DAILY_CALL_LIMIT}")'
new_print = "    print(f\"\\n{'='*60}\")\n    print(f\"[GPT-4o]\\n{gpt_text if 'gpt_text' in dir() else review_text}\")\n    print(f\"\\n{'─'*40}\")\n    print(f\"[Gemini]\\n{gemini_text if 'gemini_text' in dir() else '(フォールバック)'}\")\n    print(f\"{'='*60}\")\n    print(f\"合意判定: {judgment} → verdict={verdict}\")\n    print(f\"松野確認: {'要' if human_review else '不要'}\")\n    print(f\"本日の使用回数: {daily_count}/{DAILY_CALL_LIMIT}\")"
src = src.replace(old_print, new_print)

open(gc_path, "w", encoding="utf-8").write(src)
print("gate_check.py パッチ完了")

# 構文チェック
import subprocess
import sys as _sys

r = subprocess.run([_sys.executable, "-m", "py_compile", gc_path], capture_output=True, encoding="utf-8")
if r.returncode == 0:
    print("構文チェック OK")
else:
    print("構文エラー:", r.stderr)
    # バックアップ復元
    import shutil

    shutil.copy(gc_path + ".bak", gc_path)
    print("バックアップから復元しました")
