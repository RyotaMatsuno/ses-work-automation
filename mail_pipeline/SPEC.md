# SPEC.md - メールパイプライン自動化

最終更新: 2026-05-08

## 全体フロー

```
[30分おき・タスクスケジューラ]
↓
mail_pipeline.py 起動
↓
sessalesメール未読チェック（IMAP）
↓
Claude AIで「案件 / 人材 / その他」判定
↓
【案件の場合】
  → Notion案件DB登録
  → エンジニアDBからマッチング（既存matching.pyのロジック流用）
  → ダブルチェック自動実行
  → 提案メール下書きを pipeline_drafts/ に保存
  → pipeline.log に「提案文生成完了：{案件名}」記録
【人材の場合】
  → Notion人材DB登録
  → pipeline.log に「人材登録完了：{名前}」記録
【その他】
  → スキップ・ログ記録
↓
メールを既読化（重複処理防止）
```

## 提案文下書きの保存形式
- 保存先: `mail_pipeline/pipeline_drafts/YYYYMMDD_HHMMSS_{案件名}.txt`
- 内容:
  - 送信元メールアドレス（返信先）
  - 案件名
  - 候補者リスト（名前・単価・サマリー）
  - ダブルチェック結果（OK/NG）
  - 提案メール本文（送信可能版）

## ジョブズへの通知方法
- pipeline.log に記録
- 松野が「メールパイプライン確認して」と言ったらジョブズがログを読んで報告

## 重複防止
- IMAPで未読メールのみ取得（`UNSEEN`フラグ）
- 処理完了後に既読化

## 定期実行
- Windowsタスクスケジューラで30分おきに run_pipeline.bat を実行
- ログ: ses_work/mail_pipeline/pipeline.log に追記

## 使用するNotion DB
- エンジニアDB: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
- 案件DB: 343450ff-37c0-81e4-934e-f25f90284a3c

## Claude AI呼び出し仕様
- モデル: claude-sonnet-4-20250514
- 判定: 案件/人材/その他の3分類（JSONで返す）
- マッチング: webhook_server.pyと同じロジック
- ダブルチェック: double_check.pyと同じシステムプロンプト
