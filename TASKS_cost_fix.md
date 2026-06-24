# TASKS_cost_fix.md — 実装チェックリスト

## Fix1: mail_pipeline スキルシート判定修正

- [ ] **F1-1.** `mail_pipeline/mail_pipeline.py` に `SKIP_ATTACHMENT_KEYWORDS` タプルを定数として追加
  - 場所: 既存の `SKILL_SHEET_MIME_TYPES` / `SKILL_SHEET_EXTENSIONS` 定数の直下
- [ ] **F1-2.** `_is_skill_sheet_by_filename(filename: str) -> bool` 関数を追加
  - ファイル名 None/空は True（保守的）
  - SKIP_ATTACHMENT_KEYWORDS のいずれかが含まれれば False
  - それ以外は True
- [ ] **F1-3.** `is_skill_sheet` 判定に `and _is_skill_sheet_by_filename(filename)` を追加
- [ ] **F1-4.** 動作確認: `python -c "from mail_pipeline.mail_pipeline import _is_skill_sheet_by_filename; assert not _is_skill_sheet_by_filename('発注書_PO-001.pdf'); assert _is_skill_sheet_by_filename('田中太郎_スキルシート.pdf'); print('OK')"`

## Fix2: matching_v3 model名フォールバック修正

- [ ] **F2-1.** `matching_v3/config.py` の `DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL` を `DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL or "gpt-4.1-nano"` に変更
- [ ] **F2-2.** `Config.__init__` の `structurer_model` セットを4段フォールバックに変更
- [ ] **F2-3.** 動作確認: `cd matching_v3 && python -c "from config import DEFAULT_STRUCTURER_MODEL; assert DEFAULT_STRUCTURER_MODEL == 'gpt-4.1-nano', f'got {DEFAULT_STRUCTURER_MODEL}'; print('OK')"`

## 最終確認

- [ ] **F3.** `pytest matching_v3/tests/ -v` 全パス
- [ ] **F4.** `py_compile mail_pipeline/mail_pipeline.py` エラーなし
- [ ] **F1-5.** 英語キーワード（"contract", "statement", "receipt", "quotation", "delivery"）も SKIP_ATTACHMENT_KEYWORDS に追加されていること
- [ ] **F1-6.** 追加テスト: `_is_skill_sheet_by_filename('resume_suzuki.docx')` が True を返すこと
- [ ] **F1-7.** 追加テスト: `_is_skill_sheet_by_filename('invoice_2026.pdf')` が False を返すこと
