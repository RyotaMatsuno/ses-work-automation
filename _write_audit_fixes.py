import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cost_control"
doc = """# AUDIT_FIXES.md — 監査指摘の実装仕様（cost_control Phase3a）

設計: ジョブズ / 2026-06-05 / 実装: Codex
前提: CLAUDE.md の禁止事項を厳守（送信系に触れない・モデル名ハードコード禁止・py_compile確認・stderr直読み禁止）。
behaviorを変えるのは下記の明示箇所のみ。それ以外の挙動は一切変えない。

## F2: 現役importerのガード装着（コスト）
対象: mail_attachment_importer/ai_extractor.py の3関数 classify_content / extract_engineers / extract_projects
- 各 client.messages.create の直前に common/ledger.py の can_spend を確認し、Falseならフォールバック（既存のfallback_classify等）かスキップして返す。
- create成功直後に common/ledger.py の record(in_tokens, out_tokens, model, script="ai_extractor") を呼ぶ（response.usage から取得）。
- モデル名はベタ書き("claude-haiku-4-5-20251001")をやめ common/model_config.py の TEXT_MODEL を参照。
- 同様に reply_parser/reply_parser.py の call_claude も、現役なら can_spend+record でガードしモデルを TEXT_MODEL 参照に（reply_parserが未使用なら触らず、その旨ログ）。

## F3: 鮮度判定を created_time 基準へ（精度）
対象: line_webhook/line_query.py
- engineer_query 内 `business_days_since(project.get("last_edited_time"))` → `business_days_since(project.get("created_time"))`
- project_query 内 `business_days_since(eng.get("last_edited_time"))` → `business_days_since(eng.get("created_time"))`
- 他に last_edited_time を鮮度判定に使っている箇所があれば同様に created_time へ。
- 注意: created_time が無い/Noneのページは「鮮度不明」として除外せず通す（KeyError回避、get で None→ business_days_since が扱えるよう、None時はスキップせず従来通り）。安全側に倒す。

## F6: assignee別の粗利下限を適用（精度・バグ確定）
対象: line_webhook/line_query.py
- project_query: gross を計算後（現 L391付近）、`if gross < threshold: continue` を追加（threshold は既に L381 で算出済み = _gross_threshold(assignee)）。
- engineer_query: project ループ内で各案件の担当者から threshold を算出し下限適用する。
  具体: gross 計算の前後に
    `_th = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))`
  を入れ、`if gross < _th: continue` を追加（既存の gross>15 / gross<0 はそのまま残す）。
- GROSS_THRESHOLDS / _gross_threshold は既存のものを使う。新規定数を作らない。

## F8: FETCH_LIMIT 低減（コスト）
対象: mail_pipeline/mail_pipeline.py
- FETCH_LIMIT を 2000 → 200 に変更（CLASSIFY_LIMIT=150 はそのまま）。
- 取得上限を下げるだけ。配信フィルタ is_broadcast のロジックは変更しない。

## F10: 処理済みID読み書きの握りつぶし修正（バグ・コスト）
対象: load_processed_id / save_processed_id を持つ現役ファイル
  （mail_pipeline/mail_pipeline.py, outlook/outlook_to_notion.py, mail_attachment_importer/importer.py, mail_attachment_importer/mail_fetcher.py）
- `except: pass` / `except Exception: pass` を、最低限 logging.error/print でエラー内容を出すように変更。
- 重要: 読み込み失敗時に「空集合を返して全件再処理」になる実装なら、ファイルが存在するのに読めない場合は例外を再送出せず**処理を中断**する（誤って全件再取得→コスト爆発を防ぐ）。ファイルが存在しない初回のみ空集合でOK（os.path.exists で分岐）。
- 挙動の本筋（正常時の読み書き）は変えない。

## 除外（このバッチでは実装しない）
- F7（register_engineer/register_project の5重複common化）: 各実装が乖離しており、共通化は正準挙動の決定を要する大規模リファクタ。誤ると登録データ破損。別途レビュー付きの専用パスで実施。今回は着手しない。
- F12（Cloud Run webhook_server.py の日本語直書き）: 再デプロイが必要・低リスク。今回は着手しない。
- F4（エンジニア古record整理）: Notion操作のためジョブズが直接実施（Codex対象外）。

## 完了条件
- 全変更後 py_compile 全通過（結果を cost_control_phase3_compile.txt に出力）。
- ai_extractor / reply_parser(現役なら) に can_spend と record の両方が入る。
- line_query の鮮度が created_time、粗利下限が threshold で効く。
- mail_pipeline FETCH_LIMIT=200。
- 変更ファイル一覧を最後に出力。TASKS該当項目をチェック。
"""
with open(os.path.join(BASE, "AUDIT_FIXES.md"), "w", encoding="utf-8") as f:
    f.write(doc)
print("AUDIT_FIXES.md written", len(doc), "chars")
