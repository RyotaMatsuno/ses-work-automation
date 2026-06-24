# -*- coding: utf-8 -*-
"""Cursor指示書 修正: 配信の人員はskip"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks\20260618_180907_pipeline_full_intake.md"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 修正1: 改修方針の人員部分
content = content.replace(
    "4. 人員メールも今まで通りNotion登録\n5. メルマガ・広告・自動返信等のみskip",
    "4. 配信メールの人員紹介は取り込まない（skip）※人員は松野/岡本がLINE経由で手動登録\n5. メルマガ・広告・自動返信・人員紹介のみskip",
)

# 修正2: classify_systemプロンプト
old_prompt = """- engineer: エンジニア・技術者・人材の紹介メール
- skip: セミナー案内、メルマガ、配信停止通知、自動返信、
  営業挨拶（案件情報なし）、求人広告、ニュースレター"""

new_prompt = """- skip: 以下は全てskip
  ・エンジニア/技術者/人材の紹介メール（「弊社エンジニア」「要員ご紹介」等）
  ・セミナー案内、メルマガ、配信停止通知、自動返信
  ・営業挨拶（案件情報なし）、求人広告、ニュースレター
  ※人員は松野/岡本がLINE経由で手動登録するため、配信の人員紹介は不要"""

content = content.replace(old_prompt, new_prompt)

# 修正3: 分類を2値化（project / skip）
content = content.replace(
    '形式: {"type": "project"|"engineer"|"skip"}',
    '形式: {"type": "project"|"skip"}\n※engineerは廃止。人員紹介メールはskipに統合',
)

# 修正4: engineer_systemプロンプト関連の注記追加
content = content.replace(
    "## 注意事項",
    """## 重要ルール（CEO確定済み）
- 配信メールの人員紹介（engineer）は取り込まない
- 人員は松野/岡本がLINE→松野公式LINEに送って手動登録する運用
- mail_pipelineで取り込むのは「案件（project）」のみ
- classify_systemの分類は project / skip の2値
- engineer_system プロンプトは残すが、配信メールからのengineer登録は行わない
  （LINE経由のauto-registerは別フロー）

## 注意事項""",
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("修正完了")
print(f"ファイル: {path}")

# 差分確認
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if any(kw in line for kw in ["人員", "engineer", "skip", "LINE", "松野", "CEO"]):
            print(f"  {line.rstrip()[:100]}")
