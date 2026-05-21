# CLAUDE.md - skill_reader

## 目的
スキルシート（PDF/Word/画像）を読み取り、案件の必須・尚可スキルと照合して○×を自動生成するシステム。

## 技術スタック
- Python 3.12
- anthropic SDK（Claude API）: スキルシート読み取り・スキル抽出
- pdfplumber: PDF テキスト抽出
- python-docx: Word ファイル読み取り
- Pillow: 画像変換
- requests: Notion API 呼び出し
- dotenv: 環境変数管理（ses_work/config/.env を参照）

## ファイル構成
```
skill_reader/
  CLAUDE.md       ← このファイル
  SPEC.md         ← 仕様書
  TASKS.md        ← 実装チェックリスト
  skill_reader.py ← メインスクリプト
  test_run.py     ← テスト用スクリプト
```

## 環境変数（ses_work/config/.env）
- NOTION_API_KEY
- NOTION_ENGINEER_DB_ID
- NOTION_PROJECT_DB_ID
- ANTHROPIC_API_KEY

## 禁止事項
- スキルシートの個人情報をログに出力しない
- 外部APIへのスキルシート原本送信は Anthropic API のみ許可
- エンジニアDB への書き込みは明示的な引数指定時のみ

## 入力ソース
- メール添付: ses_work/mail_mcp 経由で取得したバイナリ
- LINE: Webhook 経由で届いた画像/PDF（base64）
- ローカルファイル: テスト用にパス直指定も可

## 出力形式
```json
{
  "engineer_name": "田中太郎",
  "skills_extracted": ["Java", "Spring", "AWS", ...],
  "match_results": [
    {
      "project_name": "Struts Java 基本設計〜 70万（ICD）",
      "required": {"Java": true, "Spring": true},
      "optional": {"AWS": false},
      "required_all_ok": true,
      "optional_rate": 0.0
    }
  ]
}
```
