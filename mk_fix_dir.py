content = r"""# CLAUDE.md - mail_pipeline + notify_line 修正

## 作業ディレクトリ
C:\Users\ma_py\OneDrive\デスクトップ\ses_work\

## 修正対象ファイル
1. mail_pipeline\mail_pipeline.py
2. matching_v2\notify_line.py
3. matching_v2\matching_v2.py (result.jsonのスキーマ追加)

## 禁止事項
- Notionへの書き込みテスト（読み取りのみ可）
- LINEへの実際の送信（--dry-runオプションで動作確認）
- APIキーのハードコード（config/.envから読む）
- 既存の backup ファイル（.bak_*）の変更

## 文字コード
UTF-8必須（# -*- coding: utf-8 -*-）

## 完了報告フォーマット
## 完了
- 変更ファイル: [パス]
- 変更概要: [1〜3行]
- 動作確認: [pass/fail]
"""

with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_notify_fix\CLAUDE.md', 'w', encoding='utf-8') as f:
    f.write(content)
print('CLAUDE.md written')
