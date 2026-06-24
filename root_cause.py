import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("=" * 70)
print("根本原因 完全分析レポート")
print("=" * 70)

# ── BUG-A: remote空欄 "()" 表示 ─────────────────────────────────────
print()
print("[BUG-A] 池袋() / 不明() / 品川（常駐）※週2程度はリモート可() 表示")
print("  根本原因:")
print("    format_project_result の表示行:")
print('    f"  {loc}({remote})"')
print('    → remote = "" (全5案件でリモートフィールドが空)')
print('    → "池袋()" / "不明()" / "品川（常駐）※週2程度はリモート可()" と表示される')
print("  修正: remote が空のとき括弧を表示しない")
print()

# ── BUG-B: assignee表示（既修正確認） ──────────────────────────────────
print("[BUG-B] 担当者空欄 (確認)")
print('  全5案件で PROP_ASSIGNEE = "" (case DB の担当者フィールドが未設定)')
print('  → 修正コード: f" / {assignee}担当" if assignee else "" は既に実装済み')
print('  → 現出力では "/ 担当" が出ていないので ✅ OK')
print()

# ── BUG-C: _clean_detail が挨拶文で始まる ──────────────────────────────
print("[BUG-C] 概要が挨拶文で始まる (2ケース)")
print()

print('  ① 音声認識: "よろしくお願いいたします。※ご返信の際は..." から始まる')
print("  根本原因 C-1:")
print('    greet_patterns に "よろしくお願いいたします" がない')

# 実際に確認
patterns_check = [
    r"\u304a\u9858\u3044\u3044\u305f\u3057\u307e\u3059$",  # お願いいたします$ (現在のパターン)
]
test = "よろしくお願いいたします。"
for p in patterns_check:
    match = bool(re.search(p, test))
    print(f'    re.search(r"{p[:30]}...", "{test}") → {"マッチ" if match else "マッチしない！← BUG"}')

print()
print("  根本原因 C-2:")
print('    "$" アンカーが "。" (句点) の前にあるため行末マッチしない')
print('    "よろしくお願いいたします。" の末尾は "います" ではなく "。"')
print('    → re.search(お願いいたします$, "よろしくお願いいたします。") = None')

print()
print("  根本原因 C-3 (③生命保険):")
print('    "BTM DX推進事業本部でございます。" が greet_patterns にヒットしない')
print('    → "BTM" で始まるため "^株式会社" パターンにマッチしない')
print('    → "でございます" が終了部分にあるが skipping=True 中は検査対象')
print()
print("  根本原因 C-4 (構造的問題):")
print("    skipping=True → greet行をスキップ → 非greet行で skipping=False")
print("    → skipping=False になったら以降は全行を無条件で追加")
print('    → "よろしくお願いいたします。" が初めて非greet行と判定される')
print("    → その後の ※ご返信の際は... --------... ※必須スキルには... も全部追加される")
print()

# 現在のgreet_patternsを検証
greet_patterns = [
    r"^\u682a\u5f0f\u4f1a\u793e",
    r"^\u5408\u540c\u4f1a\u793e",
    r"\u3054\u62c5\u5f53\u8005",
    r"\u304a\u4e16\u8a71\u306b\u306a\u3063\u3066",
    r"\u3044\u3064\u3082.*\u304a\u4e16\u8a71",
    r"\u5927\u5909.*\u304a\u4e16\u8a71",
    r"\u898b\u5408\u3046\u65b9\u304c\u3044\u3089\u3063\u3057\u3083",
    r"\u4e0b\u8a18\u6848\u4ef6",
    r"\u304a\u9858\u3044\u3044\u305f\u3057\u307e\u3059$",  # ← BUG: $アンカー
]
test_lines = [
    "よろしくお願いいたします。",  # ① の問題行
    "BTM DX推進事業本部でございます。",  # ③ の問題行
    "当社案件のご紹介となります。",
    "見合う要員がいらっしゃいましたら",
]
print("  各問題行のgreet_patterns判定:")
for line in test_lines:
    matched = any(re.search(p, line) for p in greet_patterns)
    print(f"    [{line}] → {'スキップ ✅' if matched else '通過 ❌ ← BUG'}")

print()

# ── BUG-D: 単価140万/130万の案件 ──────────────────────────────────────
print("[BUG-D] 単価140万(粗利70万) / 130万(粗利60万) の案件が上位に表示")
print("  根本原因:")
print("    SES月次レートとして 100-150万 は実在する（コンサル/AI/ブロックチェーン）")
print("    ただし ② Java×AI の年齢条件「~45歳」にH.S(55歳)は非適合")
print("    → 年齢フィルタが未実装")
print("    → 案件DBに「年齢上限」フィールドがないためコード側での対応不可")
print("    → 概要に年齢条件が表示されるので目視確認で判断（現状維持）")
print()

print("=" * 70)
print("修正すべきバグ（優先順）")
print("=" * 70)
print()
print("【必須修正】")
print('  1. BUG-A: format_project_result の remote空欄 "()" 表示')
print('     → f"{loc}({remote})" → remote空なら括弧なし')
print()
print("  2. BUG-C: _clean_detail の根本リライト")
print("     現状: 挨拶スキップロジックが不完全（false-negative多数）")
print("     解決策: 挨拶スキップではなく「連絡先抽出 + 業務内容抽出」のデュアル方式")
print("       - 連絡先: メールアドレス/電話番号/担当者名を全文から直接抽出")
print("         （送信者:行は除外）")
print("       - 業務内容: 業務内容マーカー(◆業務内容,■業務内容,【概要】等)以降")
print("       - 表示: [連絡先] | [業務内容]")
print()
print("【対応不要（仕様/データ問題）】")
print("  3. 所属: Staffing company employee")
print("     → H.SのNotionレコードのデータ品質問題。コードバグではない")
print("        手動でNotionの所属会社/担当者名/メールを更新すれば解決")
print()
print("  4. BUG-D: 単価140万/130万案件")
print("     → 実在する高単価案件。概要を見て判断可能。現状維持")
