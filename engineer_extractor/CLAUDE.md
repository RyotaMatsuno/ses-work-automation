# CLAUDE.md - Engineer Extractor Pipeline

## Project Context
SES人材マッチングエンジンのエンジニアDB品質改善パイプライン。
Notion エンジニアDB（208件）の人員情報原文・備考LINEメモから
スキル・単価・最寄駅・経験年数・稼働可能日を自動抽出し、空欄を補完する。

## Absolute Rules
1. **空欄補完のみ。既存値は絶対に上書きしない**
2. **Notion更新は --apply フラグ時のみ。デフォルトは dry-run**
3. **CostGuardを通す（LLM呼び出しがある場合）**
4. **日本語テキスト処理はUTF-8必須**
5. **sys.stdout.reconfigure(encoding='utf-8', errors='replace') をスクリプト冒頭に必ず入れる**

## Architecture
```
engineer_text_parser.py    -- パターン判定 + テキスト分離
field_extractors/
  skills_extractor.py      -- スキル抽出（辞書+ルール）
  rate_extractor_eng.py    -- 単価抽出（エンジニア向け）
  station_extractor.py     -- 最寄駅・居住地抽出
  experience_extractor.py  -- 経験年数抽出
  availability_extractor.py -- 稼働可能日抽出
  demographics_extractor.py -- 年齢・性別抽出
merge_policy.py            -- 空欄補完ルール
update_runner.py           -- dry-run / shadow / apply 実行
skill_dictionary.json      -- 技術用語辞書
```

## Text Patterns (3 types)
### Pattern 1: [自動取込]
```
[自動取込] 件名: 【SasaTech 人材】【7月〜65万】【RHEL / JP1】...
送信元: ...
受信日: ...
```

### Pattern 2: 【メールから自動登録】
```
【メールから自動登録】
送信者: ...
件名: D.E｜蕨駅｜iOS開発11年／Swift・Kotlin・Java...
本文テキスト...
```

### Pattern 3: [LINE登録/auto-register]
```
[LINE登録: matsuno]
【名前】Y.S（33歳男性）
【単価】40万円(応相談)
【スキル】PHP, Java, SQL...
```

## Notion Engineer DB
- DB ID: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
- API Key: config/.env の NOTION_API_KEY
- Notion-Version: 2022-06-28
- Target fields: スキル(multi_select), 単価（万円）(number), 最寄り駅(rich_text), 経験年数(number), 稼働可能日(date), 居住地(select)

## Merge Policy
- null / empty string / whitespace only → 空欄扱い → 補完OK
- 既存値あり → 絶対に上書きしない → shadow reportに差異を記録
- 数値0 → 項目依存（単価0は空欄扱い、経験年数0は要確認）

## Testing
- pytest でユニットテスト
- テスト用テキストサンプルは tests/fixtures/ に配置
- 各extractorにテストファイルを用意

## Prohibited
- LLMをCostGuardなしで呼び出す
- 既存DBデータの上書き
- dry-run確認前のapply実行
- ハードコードされたNotion API Key
