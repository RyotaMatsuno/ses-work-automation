# Phase 2A1: ステータス管理 + Active Pool — SPEC.md
Version: 1.0
Date: 2026-06-26

## 目的
エンジニアDBの「稼働状況」フィールドを投入し、
マッチングのActive Poolフィルタリングに組み込む。

## 方針（GPT-5.4合意済み）
- **除外ロジックのみ**: 稼働状況="稼働中"をマッチング対象から除外
- **未設定はActive Pool対象**: 空欄=unknown=eligible（マッチング対象に含める）
- **147名の未設定は空欄維持**: "稼働可能"にデフォルト設定しない

## 変更内容

### 1. ステータス投入バッチスクリプト (scripts/populate_status.py)
メモ（備考LINEメモ）のキーワード分析で稼働状況を投入。

キーワードマッピング:
| 検出キーワード | 設定値 | 予測件数 |
|---|---|---|
| 稼働可能/即日/即稼働/参画可能/フリー/空き/待機中/案件探し | 稼働可能 | ~42 |
| 稼働中/参画中/就業中/現場/常駐中/現在稼働 | 稼働中 | ~14 |
| 辞退/休養/引退/対象外/提案不可/営業停止 | 調整中 | ~5 |
| (該当なし) | (空欄のまま) | ~147 |

実行: dry-run → 確認 → apply
出力: research_results/status_populate_report.md

### 2. notion_client.py 修正
- `update_engineer_status(page_id, status)` メソッド追加
- `get_active_engineers()` に稼働状況フィルタ追加:
  稼働状況 != "稼働中" のみ取得（空欄も含む）

### 3. matching_v3.py 修正
- get_active_engineers()の返却値が自動的にフィルタリング済みのため、
  matching_v3.py自体の変更は不要

## テスト要件
1. 既存テスト全PASS
2. 新テスト:
   - test_status_excluded: 稼働中エンジニアがActive Pool対象外
   - test_blank_status_included: 空欄エンジニアがActive Pool対象
   - test_available_included: 稼働可能エンジニアがActive Pool対象
   - test_adjusting_included: 調整中エンジニアがActive Pool対象
3. バッチスクリプトのdry-run検証

## 制約
- LLM呼び出しなし（キーワードマッチのみ）
- 既存の提案対象フラグ・staleness_checkerは変更しない
- Active Pool = 提案対象フラグ=True AND staleness OK AND 稼働状況 != "稼働中"
