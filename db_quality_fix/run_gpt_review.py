# -*- coding: utf-8 -*-
"""
GPT-4o壁打ち専用スクリプト — db_quality_fix 設計レビュー依頼
ジョブズが生成。wall_hitting.py をラップして設計レビューを実施する。
"""

import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # ses_work/
WALL = BASE_DIR / "wall_hitting.py"

PROBLEM = """
SES人材派遣事業のNotionエンジニアDBクレンジングシステムを設計した。
以下の仕様について、漏れ・設計上の問題点・改善提案があれば指摘してほしい。

【目的】
mail_pipeline（Pythonメール自動取込）が生成したNotionエンジニアDBの汚染データを
ルールベースで検出・修正する。

【検出パターン】
P1: 外国籍×提案対象フラグTrue（絶対除外ルール違反）
P2: 国籍=要確認×提案対象フラグTrue
P3: 経験年数>40または<0（パース誤り）
P4: 稼働可能日が180日以上前（過去日付）
P5: 名前がプレースホルダ（"名前"/"開発太郎"等）
P6: 備考に案件メールキーワードが含まれる（案件/人材の誤分類）
P7: 単価null×フラグTrue（警告のみ）

【修正方針】
- 物理削除禁止、提案対象フラグをFalseにするのみ
- dry_runデフォルト、--liveフラグで実際に更新
- CostGuard通過済み（LLM未使用）
- Notion API直接呼び出し（requests）

【懸念点として確認したいこと】
1. P6の案件メール誤分類検出は文字列マッチングで十分か
2. 鮮度判定をlast_edited_timeでなくカスタムフィールド（情報取得日）にする設計は妥当か
3. dry_run後のlive実行フローで見落としがあるか
4. P7を「フラグ変更なし・警告のみ」にした判断は正しいか

300文字以内で日本語で回答してください。
"""


def run_wall(problem: str) -> str:
    result = subprocess.run(
        [sys.executable, str(WALL), "--problem", problem],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(BASE_DIR),
    )
    return result.stdout + result.stderr


if __name__ == "__main__":
    print("[GPT壁打ち] 設計レビュー開始...")
    output = run_wall(PROBLEM[:500])
    print(output)

    # 結果をファイルに保存
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"gpt_review_{int(time.time())}.txt"
    out_file.write_text(PROBLEM + "\n\n=== GPT回答 ===\n" + output, encoding="utf-8")
    print(f"[INFO] レビュー結果保存: {out_file}")
