# 【Cursor作業指示】Task Z: matching_v3 構造化エラー率改善（ERROR 72%→30%以下）

対象ディレクトリ: ses_work/matching_v3/
対象ファイル: structurer.py, matching_v3.py, processed_db.py
作業内容: 構造化（structurer）の失敗率72%を30%以下に削減
参照ファイル: CLAUDE.md / INVESTIGATION_REPORT.md
完了条件: ERROR率≤30% + 既存MATCHケースが壊れないこと
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 現状の問題

matching_v3_processed.db の統計:
- 処理案件: 2,089件
- ERROR: 1,509件 (72%) ← 構造化段階で失敗
- matched: 574件 (27%)
- SKIPPED: 3件

ERROR案件の件名例（全て正当な案件）:
- "WEBディレクター案件"
- "React+Java 基本設計～ 基幹システム刷新"
- "医療系AI SaaSにおけるモバイルアプリ開発（Swift/Kotlin）"
→ 件名は正しい案件情報だが、structurerがJSON構造化に失敗している

## 根本原因の調査・修正

### 1. structurer.py のJSON parse失敗ハンドリング (P1-19)
場所: structurer.py:171-209

現状: JSONパース失敗 → 空の案件dictを返す → マッチング結果なし → ERROR扱い
修正:
- JSON失敗時のフォールバック: 件名+本文からルールベースで最低限のフィールド(案件名, 必須スキル, 単価帯)を抽出
- `price_extractor.py` と `skill_extractor.py` を呼んでNotion案件DBの既存データも参照
- 完全失敗時のみERROR、部分成功はREVIEW扱いに

### 2. Notion案件DBの既存データ活用
matching_v3はNotionの案件レコードを処理する。レコードには以下が既にある:
- 必要スキル（skill_extractorで抽出済み）
- 単価情報（price_extractorで抽出済み）
- 案件名

structurerがLLMで構造化する前に、まずNotionの既存フィールドを使う:
```python
def structure_project(notion_record):
    # Step 1: Notion既存データから構造化
    skills = notion_record.get('必要スキル', [])
    price = notion_record.get('単価', None)
    name = notion_record.get('案件名', '')
    
    # Step 2: 既存データで十分ならLLM不要
    if skills and price:
        return {"name": name, "skills": skills, "price": price, "source": "notion_direct"}
    
    # Step 3: 不足分のみLLMで補完
    # ...existing structurer logic...
```

### 3. ERROR案件の再処理可能化 (P1-18)
場所: processed_db.py:18-24

修正: ERROR状態の案件を再処理可能にする
- `business_status='ERROR'` のレコードにretry_count追加
- retry_count < 3 のERROR案件は次回実行時に再処理

### 4. daily_stats カウンターの修正
daily_statsのNG/REVIEW/MATCH countが全て0になっている。
match_results_json にはREVIEW判定が記録されているのにカウントされていない。
→ stats更新ロジックを確認・修正

## テスト
- 上記5件のERROR案件が構造化成功すること
- 既存574件のmatched案件の結果が変わらないこと
- daily_statsが正しくカウントされること
