# SPEC.md - mail_pipeline コスト最適化改修

最終更新: 2026-05-27

## 目的
現状: claude-sonnet で全メールを毎回API呼び出し → 月$1,220
目標: claude-haiku-4-5 + ルール分類 + Batch API で月$28〜56（98%削減）

## 改修方針
**変更箇所は classify_email 関数の置き換えのみ。他は一切触らない。**

---

## 新しい分類フロー（classify_email_v2 として追加実装）

### Step1: ルールベース分類（APIコスト0）

件名+送信者アドレスで以下のパターンマッチ（analyze_final.py と同一ロジックをインポートして使う）：

```
SKIP → APIコスト0で廃棄
engineer → Haiku で本文冒頭200文字から構造抽出
project → Haiku で本文冒頭200文字から構造抽出
unknown → Haiku で件名+冒頭100文字から project/engineer/skip/other に分類
```

### Step2: ルールパターン（analyze_final.py から流用）

SKIP_PATTERNS, ENGINEER_PATTERNS, PROJECT_PATTERNS をそのまま使う。
インポート方法:
```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from analyze_final import SKIP_PATTERNS, ENGINEER_PATTERNS, PROJECT_PATTERNS
```
※ analyze_final.py には classify_by_rule(subj, frm) 関数もある。これも使う。

### Step3: Batch API 実装

分類方法: Anthropic Messages Batch API
- エンドポイント: POST https://api.anthropic.com/v1/messages/batches
- 同バッチ内で分類リクエストと抽出リクエストをまとめて送信
- ポーリング: GET https://api.anthropic.com/v1/messages/batches/{id} で status=ended 待ち（30秒おき、最大60分）
- 結果取得: GET https://api.anthropic.com/v1/messages/batches/{id}/results

バッチリクエスト構造:
```json
{
  "requests": [
    {
      "custom_id": "classify_0",
      "params": {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "件名+冒頭100文字"}]
      }
    },
    {
      "custom_id": "extract_project_3",
      "params": {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": "本文冒頭200文字から案件情報をJSONで抽出"}]
      }
    }
  ]
}
```

custom_id の命名規則:
- `classify_{index}` : unknownメールの分類
- `extract_project_{index}` : project確定メールの情報抽出
- `extract_engineer_{index}` : engineer確定メールの情報抽出

### Step4: few-shot プロンプト

分類プロンプト（systemに設定）:
```
あなたはSES業界のメール分類AIです。件名と本文冒頭から email_type を判定し、JSONのみで返してください。
形式: {"type": "project"|"engineer"|"skip"|"other"}

SES業界用語:
- BP/プロパー/商流/稼働/並行 = SES業界の一般用語
- 案件 = 業務委託の仕事依頼
- 要員/人材 = エンジニア紹介

例:
入力: 件名「【案件】Java開発 渋谷 7月〜」 本文「お世話になっております。下記案件いかがでしょうか」
出力: {"type": "project"}

入力: 件名「弊社Java 3年 30万」 本文「いつもお世話になっております。弊社エンジニアをご紹介します」
出力: {"type": "engineer"}

入力: 件名「セミナーのご案内」 本文「AI活用セミナーのご案内です」
出力: {"type": "skip"}
```

抽出プロンプト（project）:
```
SES案件メールから情報をJSONのみで返してください。
{"type":"project","name":"案件名","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"note":"業務内容"}
価格は万円単位の整数。不明な項目は空文字または0。
```

抽出プロンプト（engineer）:
```
SES人材メールから情報をJSONのみで返してください。
{"type":"engineer","name":"氏名","skills":[],"price":0,"available_date":"","experience_years":0,"company":"","note":"備考"}
価格は万円単位の整数。不明な項目は空文字または0。
```

### Step5: 本文文字数制限

- Batch APIに送る本文は冒頭200文字のみ（body[:200]）
- 分類(unknown)は冒頭100文字のみ（body[:100]）
- 現行の body[:8000] を body[:200] に削減

### Step6: マッチングのルール絞り込み

既存の filter_engineers_by_skills() の結果をさらに上位3件に絞ってから ai_matching() に渡す。
変更箇所: main の処理ループ内の以下の行:
```python
# 変更前
filtered = filter_engineers_by_skills(info, engineers, top_n=MATCH_TOP_N)
# 変更後
filtered = filter_engineers_by_skills(info, engineers, top_n=3)
```

---

## 実装方針

1. **新関数 classify_email_v2(emails: list) → dict[index, dict]** を追加
   - メールリストを受け取り、バッチAPIで一括処理して結果を返す
   - 既存の classify_email() は残す（互換性維持）

2. **main() の処理ループを改修**
   - 取得したメール全件を classify_email_v2() で一括分類
   - 結果に基づいて各メールを処理（現行ロジックをそのまま使用）

3. **フォールバック**
   - Batch API が失敗したら既存の classify_email() にフォールバック

---

## 検証方法

```
python -m py_compile mail_pipeline.py
python -c "from mail_pipeline.mail_pipeline import classify_email_v2; print('import OK')"
```

---

## 変更履歴
| 日付 | 内容 |
|---|---|
| 2026-05-27 | v1初版。コスト最適化改修仕様。 |
