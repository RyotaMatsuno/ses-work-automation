# 【Cursor統合作業指示】BB→BC→BF（順序実行）

## ⚠️ BA/BD/BEは別Composerで進行中。このファイルはBB→BC→BFのみ。

## 実行ルール
- **Phase順に実行。次Phaseに進む前に現Phaseの完了条件を全て満たすこと**
- 各Phase完了時にチェックボックスを更新
- 詳細仕様は同フォルダ内の個別タスクファイルを参照

---

## Phase 1: BB — 分類ラベル正規化 ✅
**詳細**: `done_tasks/20260624_165904_taskBB_label_normalize.md`

### 完了条件
- [x] 変換テスト（talent→engineer等）
- [x] 正規ラベル通過テスト
- [x] 既存テスト全PASS

---

## Phase 2: BC — 構造化精度改善（売上直結） ✅
**詳細**: `done_tasks/20260624_165904_taskBC_structurer_accuracy.md`

### 完了条件
- [x] 代表案件10件で抽出検証（fixtures 5件）
- [x] 単価/勤務地正規化テスト
- [x] 既存テスト全PASS（207件）

---

## Phase 3: BF — マッチング重み設計（BC完了が前提） ✅
**詳細**: `done_tasks/20260624_165904_taskBF_matching_weight.md`

### 完了条件
- [x] 必須不一致で除外テスト
- [x] 重み計算テスト
- [x] Java/JS混同防止テスト
- [x] 既存テスト全PASS

---

## 全体完了条件
- [x] Phase 1〜3の全チェックボックスが✅
- [x] git commit + push済み (017155e)
