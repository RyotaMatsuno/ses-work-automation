# SPEC_project_detail.md
content = """# SPEC - 案件側マッチング詳細照会

## 背景
- 人員側: 「HS 北小金」→ マッチング案件一覧 → 「詳細 ①」→ 案件全文 ✅
- 案件側: 「案件名」→ マッチング人員一覧 → 「詳細 ①」→ ❌ 未実装（_LAST_RESULTSが案件キャッシュのみ）

## 修正対象
ファイル: line_webhook/line_query.py

## 修正内容

### 1. キャッシュを人員側・案件側で分離
現在: _LAST_RESULTS = {}  # 案件リストしかキャッシュされていない

変更後:
_LAST_ENG_RESULTS = {}   # 案件名クエリ時のエンジニア結果キャッシュ
                          # key=案件名 value=matched_engsリスト（辞書: {page, gross_profit}）
_LAST_PROJ_RESULTS = {}  # 人員クエリ時の案件結果キャッシュ（既存の_LAST_RESULTS）
                          # key=イニシャル value=matched_projsリスト

### 2. project_query()でエンジニアキャッシュを保存
project_query()の末尾（format_engineer_result呼び出し前）に追加:
  _LAST_ENG_RESULTS["latest"] = matched_engs  # ← 追加
  return format_engineer_result(project, matched_engs)

### 3. detail_query()を人員側・案件側両対応に拡張
現在: _LAST_RESULTSから案件を取得してformat
変更後:
  1. _LAST_ENG_RESULTSに"latest"がある場合 → エンジニア詳細として返す
  2. _LAST_PROJ_RESULTSに"latest"がある場合 → 案件詳細として返す（既存動作）
  3. 両方ある場合は直近のクエリ種別で判定

### 4. エンジニア詳細フォーマット（新規）
format_engineer_detail(eng_item, idx) -> str:
  eng = eng_item["page"]
  fields:
  - 【詳細 {num}】{名前}｜{最寄り駅}
  - スキル: {スキル}
  - 稼働: {稼働状況} / 単価: {単価}万 / 粗利: {粗利}万
  - 稼働可能: {稼働可能日} / 鮮度: {business_days_since}日前
  - 所属: {所属会社名} / {所属担当者名} / {所属メール}
  - 【人員情報原文】（※「人員情報原文」フィールドがある場合のみ）
  - {人員情報原文全文}
  - 📎 スキルシート：{DriveリンクURL}（※「DriveリンクURL」フィールドがある場合のみ）

### 5. 最後のクエリ種別を記憶
_LAST_QUERY_TYPE = ""  # "engineer" or "project"
classify_query()の結果をhandle_line_query()でセットする

## 実装制約
- 既存の人員側（HS 北小金 → 詳細 ①）の動作を壊さないこと
- encoding='utf-8'・flush=True必須
- DRY_RUN非依存（Notion読み取りのみなので問題なし）
- バックアップ: line_query.py.bak_0602を先に作成
"""

import os

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(BASE, "line_webhook", "SPEC_project_detail.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

import sys

sys.stdout.reconfigure(encoding="utf-8")
print(f"SPEC作成: {path}", flush=True)
