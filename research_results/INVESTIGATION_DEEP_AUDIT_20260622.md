# Investigation + GPT Wall-Hit: System Deep Audit
Date: 2026-06-22

## Investigation Results (500件テスト)
- Accuracy: 95.6% / FALSE_PROJECT: 1.4% / FALSE_ENGINEER: 1.6%
- 案件DB: 57% no skills, 47% no price, 21% high quality
- エンジニアDB: 99% no station, 9件の単価異常値(525-670万)
- classify_result: 12種→4種に正規化済み

## Immediate Fixes Applied (ジョブズ直接)
1. classify_result正規化: 40件を4値(project/engineer/skip/other)に統一
2. エンジニアDB単価異常値9件 → null化
3. 分類ルール: 弊社注力案件/弊社直案件をPROJECT強化 + PROJECT_OVERRIDE拡張

## GPT推奨改修計画 (合意済み)
### 最優先: 既存データのバックフィル
- 案件617件のskills/price再抽出(raw_inbox.dbの原文から)
- エンジニア207件のskills/price/station再抽出
- 方式: 空欄のみ更新(方式A) + 低品質値上書き(方式B)

### 次: マッチングガード
- スキル0件のエンジニア → 低信頼/自動マッチ除外
- 異常単価 → 除外
- 案件スキル0件 → スコア上限制限

### その後: 再テスト
- 500件再分類テスト
- マッチングシミュレーション
