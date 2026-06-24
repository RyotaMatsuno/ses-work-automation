import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 問題を精密に整理

# ─── A) PROP_OPTSK のhexを正確に計算 ───
target = "尚可スキル"
hex_correct = target.encode("utf-8").hex()
hex_in_code = "e5b09ae58fabe382b9e382ade383ab"
decoded_in_code = bytes.fromhex(hex_in_code).decode("utf-8")

print("=== PROP_OPTSK バグ詳細 ===")
print(f'  目標文字列: "{target}"')
print(f"  正しいhex : {hex_correct}")
print(f"  コード内hex: {hex_in_code}")
print(f'  コードのdecode結果: "{decoded_in_code}"')
print(f"  差分: {'faf' if 'e58faf' in hex_correct else '?'} vs {'fab' if 'e58fab' in hex_in_code else '?'}")
print("  → U+53EF(可)=e58faf、U+53EB(叫)=e58fab  ← 1バイト違い")
print()

# ─── B) コメント行は実害なし ───
print("=== B) JP-LITERAL誤検知の整理 ===")
jp_false_positives = [
    'L187: コメント行 "# 案件フィルタ: ステータス=募集中..."',
    'L188: コメント行 "# スキル空案件は後段で..."',
    'L218: コメント行 "# スキル未設定案件はマッチング対象外"',
    'L238: コメント行 "# FIX-BUG11: ステータス=募集中..."',
    'L269: コメント行 "# FIX-BUG1/2: 定数でイニシャル・最寄り駅取得"',
    'L324: docstring内 "- 「HS 北小金」「TK 渋谷」「案件名」..."',
    'L325: docstring内 "- マッチなし / スキルシート本文..."',
    'L329: コメント行 "# 100文字超はスキルシート本文..."',
]
for fp in jp_false_positives:
    print(f"  無視OK: {fp}")

print()

# ─── C) ガード68文字テストの整理 ───
print("=== C) 68文字テスト: 実際のフロー確認 ===")
skillsheet_68 = "おつかれさまです！\n【名 前】H.S(55歳/男性)※業界経験26年\n【最寄駅】北小金駅(千代田線)\n【稼 働】7月~\n【単 金】70万"
print(f"  文字数: {len(skillsheet_68.strip())}文字")
print(f"  100文字ガード: {'通過(APIへ)' if len(skillsheet_68.strip()) <= 100 else 'スルー(None)'}")
print("  ↓ classify_query → type=project（エンジニアパターン不一致）")
print('  ↓ project_query("おつかれさまです！...") → 一致なし文字列')
print("  ↓ handle_line_query: 一致なし検出 → None を返す ← 正しい")
print("  → 実際の挙動は正常。モックが浅かった（False Positive）")

print()
print("=== 修正が必要な本物のバグ ===")
print("  [1件] PROP_OPTSK: e58fab (叫) → e58faf (可) に修正が必要")
