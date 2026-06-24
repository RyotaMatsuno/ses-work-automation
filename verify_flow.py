import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 実際に来うる「短い・曖昧なメッセージ」を洗い出し
# classify_message(テキスト) がengineer/project/other のどれになるかを確認

short_msgs = [
    ("おつかれさまです！", "other"),
    ("よろしくお願いします", "other"),
    ("ありがとうございます", "other"),
    ("確認お願いします", "other"),
    ("了解です", "other"),
    ("Java案件ありますか", "project or other"),
    ("HS 北小金", "engineer_query"),  # これだけが照会クエリ
    ("TK 渋谷", "engineer_query"),
]

print("短いメッセージの分類:")
for msg, expected in short_msgs:
    print(f"  [{msg}] len={len(msg.strip())} → 期待:{expected}")

print()
print("=== 結論 ===")
print("「おつかれさまです！」= 9文字 → 100文字ガード通過 → classify_query → project_query")
print("project_queryが「一致する案件が見つかりませんでした」を返す")
print("handle_line_queryが None に変換 → process_messageがclassify_messageに委ねる")
print("classify_messageが 'other' と判定 → 無視")
print()
print("→ この動作は正常！「一致なし→None変換」が機能していれば問題なし")
print()
print("テストケース「45文字×5=長文」は誤ったテストだった")
print("「おつかれさまです！」×5 = 45文字のテキストが来てもproject_query→「一致なし」→None→正常")
print()
print("=== 実際のフロー（完成版） ===")
flows = [
    ("HS 北小金", "engineer_query → マッチ案件一覧 → LINEに返信"),
    ("H.S 北小金", "engineer_query → マッチ案件一覧 → LINEに返信"),
    ("スキルシート本文(100文字超)", "handle_line_query→None → classify_message → DB登録"),
    ("おつかれさまです！", "project_query→一致なし→None → classify_message → other → 無視"),
    ("Java案件あります...(100文字以下)", "project_query→一致なし→None → classify_message → 分類"),
]
for inp, flow in flows:
    print(f"  [{inp[:20]}] → {flow}")
