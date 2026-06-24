import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(
    0, os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
)

from gate_checker.agreement_checker import run_dual_review

print("=== フォールバック動作テスト ===")
decision = run_dual_review(
    system_prompt=(
        "あなたはコードレビュー専門AIです。"
        "最後に必ず【判定: GO】【判定: 条件付きGO】【判定: NG】のいずれかで判定してください。"
    ),
    user_prompt="# SPEC\nHello Worldを出力するスクリプト。\n## 完了条件\n動作確認済み。\n\nHUMAN_REVIEW: NO",
)
print(f"GPT判定       : {decision.gpt_result.judgment}")
print(
    f"Gemini状態    : {'available' if decision.gemini_available else 'ERROR(フォールバック)'} / {decision.gemini_result.error}"
)
print(f"合意          : {decision.agreement}")
print(f"採用モデル    : {decision.adopted_model}")
print(f"最終判定      : {decision.final_judgment} (verdict={decision.final_verdict})")
print(
    f"フォールバック: {'正常動作' if not decision.gemini_available and decision.final_verdict in ('OK', 'NG') else '確認要'}"
)
