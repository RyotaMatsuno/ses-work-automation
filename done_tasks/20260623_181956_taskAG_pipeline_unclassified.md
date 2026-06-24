# 【Cursor作業指示】Task AG: mail_pipeline未分類メール対応

対象ディレクトリ: ses_work/
作業内容: 未分類138件の原因調査 + analyze_final.pyの分類カバレッジ改善
参照ファイル: CLAUDE.md / mail_pipeline.py / analyze_final.py
完了条件: 未分類率を1%以下に維持

---

## 背景
- raw_inbox.dbに直近(6/20〜)未分類(classify_result=NULL)が138件ある
- mail_pipelineは30分おきに実行されている
- 未分類メールの例:
  - 【関西要員/7月】TypeScript... → engineer（skipすべき）
  - 【案件】8月案件/SAP... → project
  - ★C++ エンジニア/要件定義～... → engineer
  - 【7月案件/〜70万】★急募... → project

## 調査1: 未分類の原因特定

以下を確認:
1. mail_pipeline.pyのclassify処理でanalyze_final.classify_by_ruleを呼んでいるか
2. classify_by_ruleがNone/空文字を返すパターンがあるか
3. 138件が「パイプライン未到達」なのか「分類不能」なのか
4. mail_pipeline.pyのログで該当メールの処理記録があるか

## 調査2: 直近の分類パフォーマンス

138件を手動でclassify_by_ruleにかけて、何が返るか確認:
```python
for each unclassified email:
    result = classify_by_rule(subject, body)
    print(result)  # None? unknown? 正常値?
```

## 修正: 未分類メールの再処理

調査結果に基づいて:
- パイプライン未到達 → 再処理バッチを実行
- 分類不能 → analyze_final.pyの分類ルールを拡張
- unknown返却 → unknownをproject/engineer/skipに振り分けるフォールバック追加

## 禁止事項
- raw_inbox.dbの構造を変更しない
- 分類精度96.4%（project）を下げない
- engineer取り込みルールは変更しない（LINEのみの原則は維持）
