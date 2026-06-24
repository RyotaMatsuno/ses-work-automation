import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("=" * 70)
print("問題の完全分類（3層）")
print("=" * 70)
print("""
【Layer 1: 表示バグ（コードで今すぐ直せる）】
  - 所属が常に英語/空欄で表示される
    根本原因: format_project_result が PROP_AFFIL フィールドだけ参照している
    実態:     備考（LINEメモ）に "送信元: 名前<email>" が全員入っている
    修正:     _affil_contact() ヘルパーを追加して備考から抽出して表示

    例）
    UT    → 備考: 送信元: r.takahashi@gatlab.co.jp
    F.J   → 備考: 送信元: 藤巻 盛<mori.fujimaki@roots-tec.co.jp>
    OA    → 備考: 【手動登録】弊社社員 → "自社社員"
    H.S   → 備考: [LINE auto-register] メールなし → "要確認"

【Layer 2: データ品質（mail_pipelineの設計不備）】
  - 所属会社/所属担当者名/所属メールが全員空
    根本原因: mail_pipeline.py が送信元情報を 備考 にテキストで入れるだけで
              所属会社/所属メール/所属担当者名フィールドには書き込まない
    修正:     mail_pipeline の register_engineer 呼び出し時に
              送信者情報をパースして対応フィールドに設定する
    ※ これをやると既存19件も差分なし（フィールドが空のまま）なので
       別途 backfill スクリプトが必要

  - イニシャルが全員未設定（18件が "?"）
    根本原因: mail_pipeline が classify → register_engineer するが
              イニシャルを抽出して設定していない
    修正:     mail_pipeline で氏名からイニシャルを自動生成して設定

  - 名前が "開発 太郎" "174BZ06" "名前" など不正値
    根本原因: Claude の classify_message が名前を正しく抽出できない場合
              プレースホルダーが入っている
    修正:     classify_message のプロンプト改善 or 手動確認

【Layer 3: 個別データ（H.S固有）】
  - H.S: 所属会社=英語、メール=空、担当者名=空
    根本原因: LINE登録時に所属会社情報がメッセージに含まれていなかった
              LINEの送信者情報はAPIで取れない
    修正:     松野が手動でNotionを更新（送ってきた人のメール等を入力）
""")

print("=" * 70)
print("今すぐ実施する修正（Layer 1のみ、テスト済みのものを確実に）")
print("=" * 70)
print("""
1. _affil_contact() ヘルパー追加
   - PROP_AFFIL が有効日本語 → そのまま
   - 備考に [自動取込] + 送信元: → 送信元のメールを抽出
   - 備考に [手動登録] 弊社社員 → "自社社員"
   - それ以外（H.S等） → 表示しない（空行削除）

2. format_project_result の 所属行を _affil_contact() に差し替え

3. mail_pipeline の backfill は別セッションで対応
   （19件を一括で所属メール/担当者名を設定するスクリプト）

4. H.S の手動更新は松野にお願い
""")
