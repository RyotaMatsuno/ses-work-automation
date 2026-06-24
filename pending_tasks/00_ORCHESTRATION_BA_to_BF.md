# 【Cursor統合作業指示】BB→BC→BF（順序実行）

## ⚠️ BA/BD/BEは別Composerで進行中。このファイルはBB→BC→BFのみ。

## 実行ルール
- **Phase順に実行。次Phaseに進む前に現Phaseの完了条件を全て満たすこと**
- 各Phase完了時にチェックボックスを更新
- 詳細仕様は同フォルダ内の個別タスクファイルを参照

---

## Phase 1: BB — 分類ラベル正規化
**詳細**: `pending_tasks/20260624_165904_taskBB_label_normalize.md`

### やること
- `mail_pipeline/mail_pipeline.py` 冒頭に `LABEL_NORMALIZE_MAP` 辞書追加
- classify_email_v2() のBatch応答パース後に正規化適用
- 正規ラベル: {"project", "engineer", "skip", "other"}
- 未知ラベル → "other"
- ログ: `[LABEL_NORM] "{元}" → "{正規}"`

### 完了条件
- [ ] 変換テスト（talent→engineer等）
- [ ] 正規ラベル通過テスト
- [ ] 既存テスト全PASS

---

## Phase 2: BC — 構造化精度改善（売上直結）
**詳細**: `pending_tasks/20260624_165904_taskBC_structurer_accuracy.md`

### やること
- `matching_v3/structurer.py`: 出力スキーマ厳格化（must_have_skills[], budget_min/max, location_normalized等）
- `matching_v3/location_aliases.json`（新規）: 勤務地正規化辞書
- `matching_v3/skill_aliases.json`: 182→250正規スキルへ拡張
- 単価正規化ロジック追加

### 完了条件
- [ ] 代表案件10件で抽出検証
- [ ] 単価/勤務地正規化テスト
- [ ] 既存テスト全PASS

---

## Phase 3: BF — マッチング重み設計（BC完了が前提）
**詳細**: `pending_tasks/20260624_165904_taskBF_matching_weight.md`

### やること
- `matching_v3/matcher.py`: 重み定数設定（MUST=10, NICE=3, MISS=-100）、強制除外条件、スコア内訳
- `matching_v3/skill_judge.py`: NEVER_MERGE除外リスト（Java≠JavaScript等）

### 完了条件
- [ ] 必須不一致で除外テスト
- [ ] 重み計算テスト
- [ ] Java/JS混同防止テスト
- [ ] 既存テスト全PASS

---

## 全体完了条件
- [ ] Phase 1〜3の全チェックボックスが✅
- [ ] git commit + push済み
