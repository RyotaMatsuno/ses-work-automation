import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ガードロジックの問題を整理
# 現状: len > 100 → None
# 問題: 「おつかれさまです！\n【名 前】H.S\n...」= 38文字 → ガード通過 → project_query
#       しかし classify_query が "おつかれさまです！" をproject名として処理 → 「一致する案件が見つかりません」
#
# これはproject_queryが「一致する案件が見つかりません」を返すだけなので
# 機能上は問題ない（誤動作ではなく正常な「案件なし」メッセージ）
#
# ただし webhook_server.py が「一致する案件が見つかりませんでした」を受け取って
# Lineに返信してしまうのが問題（前回のバグと同じ症状）
#
# 本当の問題: process_message内のフロー
# 1. handle_line_query(long_text) → None (100文字超) or "一致なし"(100文字以下)
# 2. result が None → classify_message に渡る（正常フロー）
# 3. result が "一致する案件が見つかりません" → これをLINEに返信してしまう！

# webhook_server.pyの該当箇所を確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    ws = f.read()

idx = ws.find("import sys; sys.path")
print("process_message内のline_query呼び出し部分:")
print(ws[idx : idx + 300])
print()
print("=== 問題の分析 ===")
print("handle_line_query が 'None以外の文字列' を返すと")
print("process_messageはそれをLINEに返信してしまう")
print()
print("=== 修正すべき点 ===")
print("handle_line_query は:")
print("  - 照会クエリ(HS 北小金等) → マッチ結果文字列")
print("  - スキルシート本文等 → None（スルー）")
print("  - 短いランダムテキスト → project_query呼んで「一致なし」")
print("  最後のケースでも None を返してほしい")
print()
print("対策オプション:")
print("A) project_queryが「一致なし」の場合もNoneを返す")
print("   → classify_messageに処理を渡せる")
print("B) process_messageで 'result != None and not result.startswith(\"一致\")' チェック")
print("   → 実装が汚い")
print()
print("→ Aを採用: handle_line_query は 'マッチした結果' のみ返す")
print("  一致なし→None を返すことでprocess_messageがclassify_messageに回す")
