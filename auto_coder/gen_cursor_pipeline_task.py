# -*- coding: utf-8 -*-
"""Cursor指示書: mail_pipeline 案件全件取り込み改修"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TASK = r"""【Cursor作業指示】
対象ディレクトリ: ses_work/mail_pipeline/
作業内容: 案件メール全件取り込み改修（Phase 1-2）
参照ファイル: CLAUDE.md / このファイル自体がSPEC兼TASKS
完了条件: 下記TASKS全チェック + テスト通過
質問がある場合: Claude.aiチャットに貼り付けて確認

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 背景
mail_pipeline.pyの現状:
- 2段階分類: ルールベース → LLM（Claude Batch API, gpt-4.1-nano）
- LLMが「project」と判定したもの → 構造化 → Notion登録（26-31件/日）
- 「skip」「other」→ 捨てる
- 問題: 事務・ヘルプデスク・ロースキル案件がskip判定されて取りこぼし
- CEO指示: 案件メールは全件Notion登録。月次業界動向分析もやりたい

## 改修方針
1. 受信メール全件をSQLiteに保存（取りこぼしゼロの基盤）
2. 分類をRecall重視に変更（案件っぽいものは全部取り込む）
3. 案件メールは全件Notion登録（今まで通りのDBに入れる）
4. 人員メールも今まで通りNotion登録
5. メルマガ・広告・自動返信等のみskip

## コスト前提
- gpt-4.1-nano + Batch API（50%割引）
- 全件分類しても $0.10/日程度（DAILY_COST_LIMIT=$2.0内）
- コスト理由で取り込みを絞る必要なし

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## SPEC

### 1. SQLite全件保存（raw_inbox）

ファイル: ses_work/mail_pipeline/raw_inbox.db

テーブル: raw_emails
- id INTEGER PRIMARY KEY AUTOINCREMENT
- message_id TEXT UNIQUE  -- メールのMessage-ID
- account TEXT  -- sessales / matsuno / okamoto
- received_at TEXT  -- ISO8601
- sender TEXT
- subject TEXT
- body_text TEXT
- body_hash TEXT  -- SHA256（重複検出用）
- has_attachment INTEGER DEFAULT 0
- attachment_names TEXT  -- JSON array
- processed INTEGER DEFAULT 0  -- pipeline処理済みフラグ
- classify_result TEXT  -- project/engineer/skip/other
- created_at TEXT DEFAULT (datetime('now'))

※ メール取得直後、LLM分類前に必ずINSERT
※ 既存のprocessed_ids.jsonは廃止 → SQLiteのprocessedフラグに移行
※ processed_ids.json → SQLiteへの初期マイグレーション処理を入れること

### 2. 分類ロジック変更

#### 現行 classify_system プロンプト（L556）を以下に差し替え:

```
あなたはSES業界のメール分類AIです。
件名と本文冒頭からemail_typeを判定し、JSONのみで返してください。

形式: {"type": "project"|"engineer"|"skip"}

分類ルール:
- project: 業務委託・SES・派遣の案件情報。開発案件だけでなく、
  事務、ヘルプデスク、PMO、運用監視、キッティング、情シス支援、
  テスト、データ入力、コールセンター等も全て「project」。
  「案件」「募集」「○万」「○月〜」等のキーワードがあればproject。
  迷ったらprojectにする（Recall最優先）。
- engineer: エンジニア・技術者・人材の紹介メール
- skip: セミナー案内、メルマガ、配信停止通知、自動返信、
  営業挨拶（案件情報なし）、求人広告、ニュースレター

SES業界用語:
- BP/プロパー/商流/稼働/並行 = SES業界の一般用語
- 案件 = 業務委託の仕事依頼
- 要員/人材 = エンジニア紹介
```

#### ルール分類（analyze_final.py）も同様に緩和:
- SKIP_PATTERNS: 明らかなノイズのみ（セミナー、メルマガ、自動返信）
- PROJECT_PATTERNS: 広く取る（「案件」「募集」「○月〜」「○万」等）
- 判定に迷うものは「unknown」→ LLM分類に回す（skipにしない）

### 3. FETCH/PROCESS LIMIT

- FETCH_LIMIT: 200（フル復帰）
- PROCESS_LIMIT: 50（フル復帰）
- DAILY_COST_LIMIT_USD: 2.0（据え置き）
- ※段階復旧ではなく一気にフル復帰する（コスト問題なしと確認済み）

### 4. 構造化スキーマ拡張

project_system プロンプト（L573）に job_category を追加:

```json
{
  "type": "project",
  "name": "案件名",
  "job_category": "development|infrastructure|pmo|helpdesk|office|testing|operations|data|sap|other",
  "required_skills": [],
  "optional_skills": [],
  "price": 0,
  "start_date": "",
  "location": "",
  "remote": "不明",
  "period": "",
  "interview_count": 1,
  "foreign_ok": false,
  "age_limit": "",
  "headcount": 1,
  "commercial_flow": "",
  "note": "業務内容"
}
```

追加項目:
- job_category: 開発/インフラ/PMO/ヘルプデスク/事務/テスト/運用/データ/SAP/その他
- age_limit: "40代まで" "50代まで" "年齢不問" "" 等
- headcount: 募集人数
- commercial_flow: "元請直" "1社先まで" "2社先まで" "" 等

### 5. Notion案件DBプロパティ追加

既存DBに以下を追加（なければ作成）:
- 職種カテゴリ (select): development/infrastructure/pmo/helpdesk/office/testing/operations/data/sap/other
- 年齢制限 (rich_text): "40代まで" 等
- 募集人数 (number)
- 商流 (rich_text): "元請直" 等

### 6. processed_ids.json → SQLite移行

- 起動時にprocessed_ids.jsonが存在すれば、全IDをSQLiteにINSERT（processed=1）
- 移行完了後、processed_ids.json を processed_ids.json.bak にリネーム
- 以降はSQLiteのみで管理

### 7. 月次分析用ビュー（SQLiteに作成）

CREATE VIEW monthly_stats AS
SELECT
  strftime('%Y-%m', received_at) as month,
  classify_result,
  COUNT(*) as count
FROM raw_emails
GROUP BY month, classify_result;

※ 詳細な月次分析バッチは Phase 6 で別途実装。ここではデータ蓄積のみ。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## TASKS

Phase 1: 全件保存基盤
- [ ] raw_inbox.db スキーマ作成（raw_emails テーブル + monthly_stats ビュー）
- [ ] メール取得直後にSQLite INSERTする処理を追加
- [ ] processed_ids.json → SQLite移行処理
- [ ] 移行テスト（既存1535件が正しくINSERTされること）

Phase 2: 分類緩和 + フル復帰
- [ ] classify_system プロンプト差し替え（Recall重視版）
- [ ] analyze_final.py のSKIP_PATTERNS緩和
- [ ] FETCH_LIMIT=200, PROCESS_LIMIT=50 に復帰
- [ ] project_system プロンプトに job_category 等追加
- [ ] Notion案件DBにプロパティ追加（職種カテゴリ/年齢制限/募集人数/商流）
- [ ] 構造化結果をNotion登録時に新プロパティにマッピング

テスト:
- [ ] 既存テストが通ること
- [ ] dry-run で10件処理して分類結果確認
- [ ] SQLiteに正しく保存されること
- [ ] Notion登録が正しく動作すること
- [ ] コスト確認（$2/日以内）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 注意事項
- CostGuard通すこと（既存のledger.py経由）
- エンコーディング: UTF-8必須、sys.stdout.reconfigure
- OneDriveパス問題: 日本語パスをcwdに直接渡さない
- Notion API: Notion-Version: 2022-06-28
- 既存のmail_pipeline.pyを壊さないよう、段階的に変更すること
"""

# pending_tasksに保存
import datetime

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
fname = f"{ts}_pipeline_full_intake.md"
path = rf"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks\{fname}"
with open(path, "w", encoding="utf-8") as f:
    f.write(TASK)
print(f"Saved: {path}")
print(f"Filename: {fname}")
