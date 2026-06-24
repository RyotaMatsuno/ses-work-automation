"""
案件登録単体テスト - register_project が修正後に通るか確認
"""

import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline")

import mail_pipeline as mp

# ダミー案件データ
test_info = {
    "type": "project",
    "name": "【テスト】Java案件_自動登録確認_削除してください",
    "required_skills": ["Java"],
    "optional_skills": ["AWS"],
    "price": 70,
    "start_date": "2026-06-01",
    "location": "東京都",
    "note": "ジョブズ自動テスト用。確認後削除してください。",
}

ok = mp.register_project(test_info, "テスト件名", "test@example.com")
print(f"案件登録: {'OK' if ok else 'NG'}")
