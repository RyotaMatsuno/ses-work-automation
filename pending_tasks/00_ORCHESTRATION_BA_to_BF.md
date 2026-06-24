# 【Cursor統合作業指示】BA〜BF 精度向上パイプライン

## 実行ルール（必ず守ること）
- **Phase順に実行。次Phaseに進む前に現Phaseの完了条件を全て満たすこと**
- 並列マークのタスクは同時着手OK
- 各Phase完了時にTASKS.mdのチェックボックスを更新
- エラーで詰まったら次に進まず、エラー内容をTASKS.mdに記録して停止

---

## Phase 1: BA — CostGuard phase分離
**目的**: matching_batchとmatching_pipelineの予算競合を解消

### 変更対象
- `config/.env`: `DAILY_CALL_LIMIT_MATCHING_BATCH=40` / `DAILY_CALL_LIMIT_MATCHING_PIPELINE=30` 追加
- `common/ledger.py`: `_call_limit()` で新phase名を認識、未定義時は `DAILY_CALL_LIMIT_MATCHING` にフォールバック
- `matching_v3/matching_v3.py`: `phase="matching"` → `phase="matching_batch"`
- `matching_v3/cost_guard.py`: 同上
- `mail_pipeline/mail_pipeline.py`: `call_claude(..., phase="matching")` → `phase="matching_pipeline"`（line 1169付近）

### 完了条件
- [ ] matching_v3 dry-run → phase_callsに `matching_batch` 記録
- [ ] mail_pipeline実行 → phase_callsに `matching_pipeline` 記録
- [ ] 既存テスト全PASS

---

## Phase 2: BB — 分類ラベル正規化
**目的**: LLM出力の非標準ラベル（talent, resume等）を正規ラベルに変換

### 変更対象
- `mail_pipeline/mail_pipeline.py`:
  - 冒頭定数に `LABEL_NORMALIZE_MAP` 辞書追加
  - classify_email_v2() のBatch応答パース後に正規化適用
  - 正規ラベルセット: `{"project", "engineer", "skip", "other"}`
  - 未知ラベル → `"other"` に変換
  - ログ: `[LABEL_NORM] "{元}" → "{正規}" (msg_id={id})`

### 完了条件
- [ ] talent→engineer, resume→engineer, spam→skip 等の変換テスト
- [ ] 正規ラベルはそのまま通過するテスト
- [ ] 既存テスト全PASS

---

## Phase 3: BC — 構造化精度改善（売上直結）
**目的**: 案件メールからのスキル/単価/勤務地の抽出精度を向上

### 変更対象
- `matching_v3/structurer.py`:
  - 出力スキーマ厳格化（must_have_skills[], nice_to_have_skills[], budget_min/max, location_normalized, remote_type, start_date, interview_count, nationality_ok）
  - 未抽出フィールドはnull（空文字列禁止）
  - 単価正規化: "70万前後"→min=67/max=73, "スキル見合い"→null, "80-90万"→min=80/max=90
- `matching_v3/location_aliases.json`（新規）: 勤務地正規化辞書
- `matching_v3/skill_aliases.json`: 182→250正規スキルへ拡張（SAP, Salesforce, ServiceNow, COBOL, VB.NET, Flutter, Terraform, Kubernetes等）

### 完了条件
- [ ] 代表案件メール10件で抽出結果を検証
- [ ] 単価パターン変換の単体テスト
- [ ] 勤務地正規化の単体テスト
- [ ] skill_aliases.json拡張後に既存テスト全PASS

---

## Phase 4: BD + BE（並列実行OK — BCの完了を待たなくてよい）

### BD — CostGuardテストモード
**目的**: CostGuardのブロック動作を自動検証

#### 変更対象
- `common/ledger.py`: `COSTGUARD_TEST_MODE=true` 時にTEST_*値を優先 + テスト用別DB
- `tests/test_costguard_integration.py`（新規）:
  - test_call_limit_blocks_at_threshold
  - test_call_limit_pending_queue
  - test_usd_daily_blocks
  - test_matching_batch_pipeline_isolation（BA完了後に有効化）
  - test_pending_queue_fifo
  - test_pending_expire

#### 完了条件
- [ ] `COSTGUARD_TEST_MODE=true python -m pytest tests/test_costguard_integration.py -v` 全PASS
- [ ] テスト用DBは本番DBに一切触れない

### BE — Batch APIハング防止
**目的**: パイプラインのBatch API応答待ちハングを防止

#### 変更対象
- `mail_pipeline/mail_pipeline.py`:
  - `acquire_lock()` にTTL追加（45分超で自動解除、ログ出力）
  - Batch APIポーリングにタイムアウト追加（20分でabandon、次回再処理）
  - ログ強化: BATCH submitted/polling/TIMEOUT

#### 完了条件
- [ ] 45分超のlockファイルが自動解除される
- [ ] Batch timeout後にメールが次回実行で再分類される
- [ ] 既存テスト全PASS

---

## Phase 5: BF — マッチング重み設計（BC完了が前提）
**目的**: スキルマッチの重み付け改善と除外条件の厳格化

### 変更対象
- `matching_v3/matcher.py`:
  - 重み定数: MUST_HAVE=10, NICE_TO_HAVE=3, MUST_MISS=-100, PRICE=5, LOCATION=3, REMOTE=2
  - 強制除外: 必須×あり / 単価乖離5万超 / 粗利5万未満 / 粗利15万超
  - スコア内訳を各候補に付与（breakdown辞書）
- `matching_v3/skill_judge.py`:
  - NEVER_MERGE除外リスト: {Java,JavaScript}, {C,C++,C#}, {PM,PMO}, {React,React Native}

### 完了条件
- [ ] 必須スキル不一致で除外テスト
- [ ] 重み計算テスト（必須>尚可）
- [ ] Java/JavaScript混同防止テスト
- [ ] 粗利フィルター（5万下限・15万上限）テスト
- [ ] 既存テスト全PASS

---

## 全体完了条件
- [ ] Phase 1〜5の全チェックボックスが✅
- [ ] git commit + push済み
- [ ] TASKS.mdに最終結果を記録
