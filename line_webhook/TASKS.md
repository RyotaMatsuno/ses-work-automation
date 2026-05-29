# TASKS.md - スキル年数抽出・古スキル除外改修

## チェックリスト（Codexが順番に実装・完了時に[x]に更新）

- [x] Task 1: skill_extractor.py 新規作成
  - extract_skills_from_bytes(file_bytes, mime_type) -> str
    - PDF: pdfplumberでテキスト抽出
    - xlsx: openpyxlで全シートのセル値を結合
    - docx: python-docxで段落テキストを結合
    - image/*: base64エンコードして返す（Claude Visionは呼び出し元で処理）
    - その他: UTF-8デコード試行
  - analyze_skill_sheet_v2(file_bytes, mime_type, summary_text="") -> dict
    - テキスト化 → summary_textと結合 → Claude haiku APIに投げる
    - プロンプトにactive判定ロジックを含める（10年以上未使用はfalse）
    - JSONパース・エラー時は{}を返す
  - filter_and_sort_skills(skills_list) -> list[str]
    - active: trueのみ抽出
    - VALID_SKILLSと照合（webhook_server.pyからimport）
    - years降順でソート
    - str リストを返す

- [x] Task 2: webhook_server.py にUSER_BUFFERを追加
  - グローバル変数 USER_BUFFER = {} を追加（PENDING_PROPOSALSの直下）
  - BUFFER_TTL = 1800 定数を追加

- [x] Task 3: process_message にバッファ保存ロジックを追加
  - classify_message の結果が "engineer" の場合のみ USER_BUFFER[user_id] に保存
  - {"summary": text, "timestamp": time.time()} の形式
  - TTL超過のバッファを定期クリーンアップ（新規メッセージ受信時に古いものを削除）

- [x] Task 4: handle_file_message を改修
  - skill_extractor.analyze_skill_sheet_v2 をimport
  - res.content（バイト列）をそのまま渡す（b64変換不要）
  - USER_BUFFERから summary を取得して渡す
  - 使用後 USER_BUFFER[user_id] を削除
  - 既存のPDF/画像フロー（analyze_skill_sheet）はanalyze_skill_sheet_v2に統合
  - xlsx/docxの場合も同じフローで処理

- [x] Task 5: register_engineer を改修
  - skills がdict形式の場合 filter_and_sort_skills を呼ぶ
  - skills がstr形式の場合は既存ロジック継続

- [x] Task 6: requirements.txt に追記
  - openpyxl>=3.1.0
  - python-docx>=1.1.0
  が含まれていなければ追記

- [x] Task 7: 動作確認
  - python -c "from skill_extractor import filter_and_sort_skills; print(filter_and_sort_skills([{'name':'Java','years':20,'last_used_year':2025,'active':True},{'name':'C#','years':3,'last_used_year':2013,'active':False}]))"
  - 出力が ['Java'] であることを確認
